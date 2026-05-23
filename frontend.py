import streamlit as st
import uuid
import getpass
import os
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

# Set page config at the very beginning of the script
st.set_page_config(
    page_title="AeroVoyage - Premium Travel Advisor",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Handle session selection via URL query parameters
if "thread_id" in st.query_params:
    st.session_state.thread_id = st.query_params["thread_id"]

# Import backend components from main.py
from main import app, conn, get_past_sessions, format_timestamp

# ──────────────────────────────────────────────
# Custom CSS Injections for Premium Aesthetics
# ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    /* Global Typography & Font Overrides */
    html, body, [class*="css"], .stMarkdown, p, div, span, h1, h2, h3, h4, h5, h6, label {
        font-family: 'Outfit', sans-serif !important;
    }

    /* Dark Mode App Background */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
    }

    /* Style columns as premium cards (removes empty markdown card bugs) */
    div[data-testid="column"] {
        background-color: rgba(15, 23, 42, 0.55) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        padding: 25px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        margin-bottom: 20px !important;
    }

    /* Title & Text Gradient Styling */
    .gradient-header {
        background: linear-gradient(135deg, #60a5fa, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }

    .gradient-subheader {
        background: linear-gradient(135deg, #34d399, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 600;
        font-size: 1.3rem;
        margin-top: 1.2rem;
        margin-bottom: 0.8rem;
    }

    /* Sidebar Background & Visual Overrides */
    [data-testid="stSidebar"] {
        background-color: #070a13 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    
    [data-testid="stSidebar"] h1 {
        font-size: 1.8rem !important;
        background: linear-gradient(135deg, #a5b4fc, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem !important;
    }

    /* Custom Scrollable Session History Container */
    .session-list-container {
        max-height: 480px;
        overflow-y: auto;
        padding-right: 4px;
        margin-top: 10px;
    }
    
    /* Sleek Custom HTML Cards in Sidebar */
    .session-card {
        background: rgba(30, 41, 59, 0.35) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        padding: 12px 14px !important;
        margin-bottom: 10px !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    .session-card:hover {
        background: rgba(59, 130, 246, 0.08) !important;
        border-color: rgba(59, 130, 246, 0.35) !important;
        transform: translateX(4px) !important;
    }

    .session-card.active {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(124, 58, 237, 0.15)) !important;
        border: 1px solid rgba(96, 165, 250, 0.45) !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.15) !important;
    }

    .session-card-title {
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        color: #f1f5f9 !important;
        margin-bottom: 4px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    .session-card-meta {
        font-size: 0.78rem !important;
        color: #94a3b8 !important;
        margin-bottom: 2px !important;
    }

    .session-card-time {
        font-size: 0.72rem !important;
        color: #64748b !important;
    }
    
    /* Special Style for st.button inside Sidebar (+ New Trip button) */
    [data-testid="stSidebar"] button {
        background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        text-align: center !important;
        justify-content: center !important;
        align-items: center !important;
        display: flex !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
        padding: 12px 20px !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stSidebar"] button:hover {
        background: linear-gradient(135deg, #2563eb, #4f46e5) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45) !important;
    }

    /* Style Streamlit Tabs */
    button[data-baseweb="tab"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: #64748b !important;
        background-color: transparent !important;
        border: none !important;
        padding: 10px 18px !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #60a5fa !important;
        border-bottom: 2px solid #60a5fa !important;
    }

    /* Custom Chat Container Overrides */
    div[data-testid="stChatMessage"] {
        background-color: rgba(30, 41, 59, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 14px !important;
        padding: 14px !important;
        margin-bottom: 12px !important;
    }
    
    /* Scrollbars Styling */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #0b0f19;
    }
    ::-webkit-scrollbar-thumb {
        background: #1e293b;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #334155;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Onboarding Welcome Form (Dynamic User Info Setup)
# ──────────────────────────────────────────────
if "user_name" not in st.session_state or not st.session_state.user_name:
    st.markdown("""
    <div style='max-width: 550px; margin: 100px auto 30px auto; padding: 40px; background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; box-shadow: 0 12px 40px rgba(0,0,0,0.5); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); text-align: center;'>
        <h1 style='background: linear-gradient(135deg, #60a5fa, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 3.2rem; margin-bottom: 10px;'>AeroVoyage</h1>
        <p style='color: #94a3b8; font-size: 1.15rem; margin-bottom: 0;'>Your premium AI-powered multi-agent travel companion.</p>
    </div>
    """, unsafe_allow_html=True)
    
    _, col_form, _ = st.columns([1, 2, 1])
    with col_form:
        name_input = st.text_input("Enter your name to access your private lounge:", placeholder="e.g. Satyam")
        if st.button("Enter Lounge", use_container_width=True):
            if name_input.strip():
                st.session_state.user_name = name_input.strip().lower()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.session_state.thread_id = f"session_{st.session_state.user_name}_{ts}"
                # Sync query params
                st.query_params["thread_id"] = st.session_state.thread_id
                st.rerun()
            else:
                st.error("Name cannot be empty.")
    st.stop()

# Load verified session variables
current_user = st.session_state.user_name
config = {"configurable": {"thread_id": st.session_state.thread_id}}

# Query active state variables
snapshot = app.get_state(config)
state_values = snapshot.values
messages = state_values.get("messages", [])
trip_start_msg_id = state_values.get("trip_start_msg_id", "")
itinerary = state_values.get("itinerary", "")
error = state_values.get("error", "")

# ──────────────────────────────────────────────
# Sidebar - History Manager
# ──────────────────────────────────────────────
st.sidebar.markdown(
    f"<div style='text-align: center; margin-top: 10px; margin-bottom: 25px;'>"
    f"<h1>AeroVoyage</h1>"
    f"<p style='color: #64748b; font-size: 0.95rem; margin-top: 0;'>Active Lounge: <b>{st.session_state.user_name.capitalize()}</b></p>"
    f"</div>",
    unsafe_allow_html=True
)

# New Session Button
if st.sidebar.button("➕ New Trip Planner", use_container_width=True):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_thread = f"session_{st.session_state.user_name}_{ts}"
    st.session_state.thread_id = new_thread
    st.query_params["thread_id"] = new_thread
    st.rerun()

st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 20px 0;'>", unsafe_allow_html=True)
st.sidebar.subheader("Recent Trips")

# Fetch recent sessions from database
sessions = get_past_sessions(conn, st.session_state.user_name)

if not sessions:
    st.sidebar.markdown(
        "<div style='color: #64748b; font-size: 0.9rem; text-align: center; margin-top: 20px;'>"
        "No past conversations found.<br>Plan a trip to start!"
        "</div>",
        unsafe_allow_html=True
    )
else:
    # Render scrollable trip history list as custom styled HTML cards
    html_cards = []
    for idx, s in enumerate(sessions):
        origin = s.get("origin_city")
        dest = s.get("destination_city")
        date = s.get("travel_date")
        thread_id = s.get("thread_id")
        updated_str = format_timestamp(s.get("last_updated"))
        
        active_class = "active" if thread_id == st.session_state.thread_id else ""
        
        if origin and dest:
            title = f"✈️ {origin} ➔ {dest}"
            meta = f"📅 Travel: {date}"
        else:
            q = s.get("user_query", "")
            q_short = q[:30] + "..." if len(q) > 30 else q
            if not q_short or q_short == "...":
                q_short = "Untitled Session"
            title = f"💬 {q_short}"
            meta = "📅 Planning phase"
            
        card_html = f"""
        <a href="?thread_id={thread_id}" target="_self" style="text-decoration: none; color: inherit;">
            <div class="session-card {active_class}">
                <div class="session-card-title">{title}</div>
                <div class="session-card-meta">{meta}</div>
                <div class="session-card-time">🕒 Activity: {updated_str}</div>
            </div>
        </a>
        """
        html_cards.append(card_html)
        
    st.sidebar.markdown(
        f"<div class='session-list-container'>{''.join(html_cards)}</div>",
        unsafe_allow_html=True
    )

# ──────────────────────────────────────────────
# Main Workspace Layout
# ──────────────────────────────────────────────
# Filter message history to only show messages belonging to the current trip
recent_messages = []
if messages:
    start_idx = 0
    if trip_start_msg_id:
        for idx, m in enumerate(messages):
            if getattr(m, "id", None) == trip_start_msg_id:
                start_idx = idx
                break
    recent_messages = messages[start_idx:]

# Determine layout division: Double-pane dashboard if itinerary is generated, single pane otherwise
has_results = bool(itinerary or state_values.get("flight_results") or state_values.get("hotel_results"))

if has_results:
    col_chat, col_results = st.columns([1, 1])
else:
    col_chat = st.container()
    col_results = None

# Left Panel (Chat & Input Interface)
with col_chat:
    st.markdown("<h2 class='gradient-header'>AeroVoyage Advisor</h2>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='color: #64748b; font-size: 0.9rem; margin-bottom: 15px; margin-top: 0;'>"
        f"Active Session: <code style='background-color: #1e293b; color: #60a5fa; padding: 2px 5px; border-radius: 4px; font-size: 0.8rem;'>{st.session_state.thread_id}</code>"
        f"</p>",
        unsafe_allow_html=True
    )
    
    # Message Display Box (with scroll height limits for balance)
    chat_container = st.container(height=520)
    with chat_container:
        for m in recent_messages:
            if m.content:
                # Skip printing the raw itinerary in the chat bubble since it is displayed on the right pane!
                if itinerary and m.content.strip() == itinerary.strip():
                    continue
                    
                role = "user" if isinstance(m, HumanMessage) else "assistant"
                avatar = "👤" if role == "user" else "✈️"
                with st.chat_message(role, avatar=avatar):
                    st.markdown(m.content)
                    
        # Interrupt Handler Display
        is_interrupted = bool(snapshot.next and snapshot.tasks[0].interrupts)
        if is_interrupted:
            question = snapshot.tasks[0].interrupts[0].value
            st.markdown(
                f"<div style='border-left: 4px solid #ef4444; background-color: rgba(239, 68, 68, 0.08); padding: 12px; border-radius: 0 10px 10px 0; margin: 15px 0;'>"
                f"<span style='color: #fca5a5; font-weight: 600; font-size: 0.9rem;'>🙋 Agent Question:</span>"
                f"<p style='margin: 4px 0 0 0; color: #fff; font-size: 0.95rem;'>{question}</p>"
                f"</div>",
                unsafe_allow_html=True
            )
            
    # Main Input Bar
    user_input = st.chat_input("Where would you like to travel, or answer the agent's question...")
    
    if user_input:
        msg_id = str(uuid.uuid4())
        
        # Display message immediately
        with chat_container:
            with st.chat_message("user", avatar="👤"):
                st.markdown(user_input)
                
        with st.spinner("Routing details to travel planner agents..."):
            if is_interrupted:
                # User is answering the question, update parser context and resume
                app.update_state(config, {
                    "messages": [HumanMessage(content=user_input, id=msg_id)],
                    "user_query": f"{state_values.get('user_query', '')} {user_input}"
                })
                app.invoke(Command(resume=user_input), config=config)
            else:
                # Start a clean state or follow-up invocation
                app.invoke({
                    "messages": [HumanMessage(content=user_input, id=msg_id)],
                    "user_query": user_input,
                    "flight_results": "", "hotel_results": "", "airport_results": "", "itinerary": "", "error": "",
                    "llm_calls": 0
                }, config=config)
                
        st.rerun()

# Right Panel (Interactive Itinerary Display)
if col_results is not None:
    with col_results:
        st.markdown("<h3 style='margin-top:0; font-size:1.6rem; font-weight:700; color:#fff;'>🗺️ Planned Trip Details</h3>", unsafe_allow_html=True)
        
        # Display metadata budget breakdown at the top of results
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Allocated Budget", f"₹{state_values.get('budget', 0):,}")
        with col_m2:
            st.metric("Total LLM Calls", f"{state_values.get('llm_calls', 0)}")
            
        st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 15px 0;'>", unsafe_allow_html=True)

        tab_itinerary, tab_flights_hotels = st.tabs([
            "📅 Detailed Itinerary", 
            "✈️ Flights, Hotels & Transit"
        ])
        
        with tab_itinerary:
            if itinerary:
                st.markdown(itinerary)
            else:
                st.info("No detailed day-by-day itinerary generated yet.")
                
        with tab_flights_hotels:
            col_fl, col_ht = st.columns(2)
            with col_fl:
                st.markdown("<h4 class='gradient-subheader'>✈️ Flight Options</h4>", unsafe_allow_html=True)
                fl_results = state_values.get("flight_results", "")
                if fl_results:
                    st.markdown(fl_results)
                else:
                    st.write("Flight data is not yet resolved.")
                    
                st.markdown("<h4 class='gradient-subheader'>🏢 Airport Information</h4>", unsafe_allow_html=True)
                ap_results = state_values.get("airport_results", "")
                if ap_results:
                    st.markdown(ap_results)
                else:
                    st.write("Transit airport details are not resolved.")
                    
            with col_ht:
                st.markdown("<h4 class='gradient-subheader'>🏨 Accommodation Options</h4>", unsafe_allow_html=True)
                ht_results = state_values.get("hotel_results", "")
                if ht_results:
                    st.markdown(ht_results)
                else:
                    st.write("Hotel search data is not yet resolved.")
