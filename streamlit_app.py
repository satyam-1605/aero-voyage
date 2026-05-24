import streamlit as st
import uuid
import getpass
import os
import re
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
from langgraph.errors import GraphInterrupt


# Set page config at the very beginning of the script
st.set_page_config(
    page_title="AeroVoyage - Luxury Travel Terminal",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Handle session selection via URL query parameters
if "thread_id" in st.query_params:
    st.session_state.thread_id = st.query_params["thread_id"]
if "user_name" in st.query_params:
    st.session_state.user_name = st.query_params["user_name"]

# Sync session state back to query parameters to maintain URL state
if "user_name" in st.session_state and st.session_state.user_name:
    st.query_params["user_name"] = st.session_state.user_name
if "thread_id" in st.session_state and st.session_state.thread_id:
    st.query_params["thread_id"] = st.session_state.thread_id

# Import backend components from main.py
from main import app, conn, get_past_sessions, format_timestamp

# ──────────────────────────────────────────────
# Luxury Aviation Terminal Theme Injector (CSS)
# ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Syne:wght@700;800&display=swap');

    /* Global Typography & Hide Streamlit Defaults */
    html, body, .stMarkdown, p, label {
        font-family: 'DM Sans', sans-serif !important;
        color: #B8D4EE;
    }
    div:not([class*="MaterialSymbols"]):not([class*="material-icons"]):not(.notranslate),
    span:not([class*="MaterialSymbols"]):not([class*="material-icons"]):not(.notranslate),
    [class*="css"]:not([class*="MaterialSymbols"]):not([class*="material-icons"]):not(.notranslate) {
        font-family: 'DM Sans', sans-serif !important;
        color: #B8D4EE;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Syne', sans-serif !important;
        color: #E8F4FF !important;
        font-weight: 700;
    }
    .stMarkdown h1 { font-size: 1.5rem !important; margin-top: 12px !important; margin-bottom: 8px !important; }
    .stMarkdown h2 { font-size: 1.35rem !important; margin-top: 12px !important; margin-bottom: 8px !important; }
    .stMarkdown h3 { font-size: 1.2rem !important; margin-top: 10px !important; margin-bottom: 6px !important; }
    .stMarkdown h4 { font-size: 1.1rem !important; margin-top: 8px !important; margin-bottom: 4px !important; }
    .stMarkdown h5 { font-size: 1.0rem !important; }
    .stMarkdown h6 { font-size: 0.95rem !important; }
    .stMarkdown p { font-size: 0.92rem !important; line-height: 1.6 !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    /* Hide Deploy button but keep toolbar container visible to avoid hiding expand/collapse toggle */
    button[data-testid="stDeployButton"],
    [data-testid="stConnectionStatus"] {
        display: none !important;
        visibility: hidden !important;
    }
    /* Guarantee visibility of the sidebar toggle wrappers and buttons */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[data-testid="stBaseButton-headerNoPadding"],
    [data-testid="stHeader"] button {
        visibility: visible !important;
        display: inline-flex !important;
        opacity: 1 !important;
    }
    /* Style the sidebar toggle buttons to match our premium theme */
    [data-testid="collapsedControl"] button,
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"] button,
    button[data-testid="stBaseButton-headerNoPadding"] {
        visibility: visible !important;
        color: #3B82F6 !important;
        background-color: rgba(15, 30, 53, 0.8) !important;
        border: 1px solid rgba(59, 130, 246, 0.45) !important;
        border-radius: 8px !important;
        margin: 10px !important;
        padding: 5px 10px !important;
        transition: all 0.25s ease !important;
        z-index: 999999 !important;
    }
    [data-testid="collapsedControl"] button:hover,
    button[data-testid="stSidebarCollapseButton"]:hover,
    [data-testid="stSidebarCollapseButton"] button:hover,
    button[data-testid="stBaseButton-headerNoPadding"]:hover {
        background-color: rgba(59, 130, 246, 0.2) !important;
        border-color: #3B82F6 !important;
    }

    .stApp {
        background-color: #05080F !important;
        color: #B8D4EE;
    }

    /* Selection Highlight */
    ::selection {
        background: rgba(59, 130, 246, 0.3);
        color: #E8F4FF;
    }

    /* Webkit Scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #05080F;
    }
    ::-webkit-scrollbar-thumb {
        background: #0F1E35;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #3B82F6;
    }

    /* Style columns as premium cards */
    div[data-testid="column"] {
        background-color: rgba(10, 15, 30, 0.6) !important;
        border: 1px solid #0F1E35 !important;
        border-radius: 20px !important;
        padding: 25px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        margin-bottom: 20px !important;
    }

    /* Sidebar Navigation Layout */
    [data-testid="stSidebar"] {
        background-color: #070B14 !important;
        border-right: 1px solid #0F1E35 !important;
        padding-top: 10px !important;
    }
    
    [data-testid="stSidebar"] h1 {
        font-family: 'Syne', sans-serif !important;
        font-size: 1.8rem !important;
        background: linear-gradient(135deg, #3B82F6, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem !important;
    }

    /* User input styled dark field with cyan focus ring */
    [data-testid="stSidebar"] input {
        background-color: #04070D !important;
        border: 1px solid #0F1E35 !important;
        color: #E8F4FF !important;
        border-radius: 8px !important;
        padding: 10px !important;
        transition: all 0.25s ease !important;
    }
    [data-testid="stSidebar"] input:focus {
        border-color: #06B6D4 !important;
        box-shadow: 0 0 10px rgba(6, 182, 212, 0.2) !important;
    }

    /* Tech Badge Pills */
    .tech-pill {
        display: inline-flex;
        align-items: center;
        background-color: #0A1424;
        border: 1px solid #0F1E35;
        border-radius: 16px;
        padding: 6px 12px;
        font-size: 0.78rem;
        font-weight: 500;
        color: #E8F4FF;
        margin: 4px;
        transition: all 0.25s ease;
    }
    .tech-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 8px;
    }

    /* Stepper Styling in Sidebar */
    .stepper-container {
        margin: 15px 0;
        padding-left: 10px;
    }
    .step-item {
        display: flex;
        align-items: center;
        margin-bottom: 15px;
        position: relative;
    }
    .step-item:not(:last-child)::after {
        content: '';
        position: absolute;
        left: 12px;
        top: 24px;
        width: 2px;
        height: 20px;
        background-color: #0F1E35;
    }
    .step-circle {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 700;
        margin-right: 12px;
        z-index: 2;
        transition: all 0.25s ease;
    }
    .step-circle.pending {
        border: 2px solid #0F1E35;
        color: #64748B;
        background-color: #070B14;
    }
    .step-circle.active {
        background-color: #3B82F6;
        color: #ffffff;
        border: 2px solid #3B82F6;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
    }
    .step-circle.complete {
        background-color: #10B981;
        color: #ffffff;
        border: 2px solid #10B981;
    }
    .step-name {
        font-size: 0.88rem;
        font-weight: 500;
        transition: all 0.25s ease;
    }
    .step-name.active {
        color: #E8F4FF;
        font-weight: 600;
    }
    .step-name.pending {
        color: #64748B;
    }

    /* Scrollable Session History Container */
    .session-list-container {
        max-height: 260px;
        overflow-y: auto;
        padding-right: 4px;
        margin-top: 10px;
    }
    
    /* Sleek Custom HTML Cards in Sidebar */
    .session-card {
        background: rgba(30, 41, 59, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.04) !important;
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
        border: 1px solid rgba(96, 165, 250, 0.4) !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.15) !important;
    }
    .session-card-title {
        font-size: 0.86rem !important;
        font-weight: 600 !important;
        color: #f1f5f9 !important;
        margin-bottom: 4px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    .session-card-meta {
        font-size: 0.76rem !important;
        color: #94a3b8 !important;
        margin-bottom: 2px !important;
    }
    .session-card-time {
        font-size: 0.7rem !important;
        color: #64748b !important;
    }

    /* Hero Section CSS */
    .hero-container {
        position: relative;
        height: 320px;
        border-radius: 20px;
        overflow: hidden;
        margin-bottom: 25px;
        background-size: cover;
        background-position: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .hero-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(180deg, rgba(5, 8, 15, 0.3) 0%, #05080F 100%), rgba(10, 30, 80, 0.5);
        backdrop-filter: brightness(0.25);
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 40px;
        z-index: 1;
    }
    
    /* Animated Gradient Sweep Keyframes */
    @keyframes sweep {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .hero-sweep {
        position: absolute;
        inset: 0;
        background: linear-gradient(270deg, rgba(59, 130, 246, 0.06), rgba(6, 182, 212, 0.06));
        background-size: 400% 400%;
        animation: sweep 8s ease infinite;
        z-index: 0;
        pointer-events: none;
    }
    
    .glowing-badge {
        display: inline-flex;
        align-self: flex-start;
        font-size: 0.72rem;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        padding: 4px 12px;
        border-radius: 20px;
        background-color: rgba(6, 182, 212, 0.1);
        border: 1px solid rgba(6, 182, 212, 0.45);
        box-shadow: 0 0 12px rgba(6, 182, 212, 0.2);
        color: #06B6D4;
        font-weight: 700;
        margin-bottom: 12px;
    }
    
    .hero-stats-row {
        display: flex;
        gap: 15px;
        margin-top: 20px;
    }
    .hero-stat-pill {
        display: flex;
        align-items: center;
        background-color: rgba(15, 30, 53, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 30px;
        padding: 5px 14px;
        font-size: 0.78rem;
        color: #E8F4FF;
        backdrop-filter: blur(10px);
    }
    .hero-stat-icon {
        margin-right: 6px;
        color: #3B82F6;
    }

    /* Destination Cards Grid */
    .dest-card {
        position: relative;
        height: 120px;
        border-radius: 14px;
        overflow: hidden;
        background-size: cover;
        background-position: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
        cursor: pointer;
        transition: all 0.25s ease;
    }
    .dest-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(180deg, rgba(0,0,0,0.1) 0%, rgba(5, 8, 15, 0.7) 100%);
        backdrop-filter: brightness(0.65);
        display: flex;
        align-items: flex-end;
        padding: 12px;
        transition: all 0.25s ease;
    }
    .dest-card:hover {
        transform: scale(1.04) !important;
        border-color: #3B82F6 !important;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.3) !important;
    }
    .dest-card:hover .dest-overlay {
        backdrop-filter: brightness(0.85) !important;
    }
    .dest-card::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 0;
        height: 3px;
        background: linear-gradient(90deg, #3B82F6, #06B6D4);
        transition: width 0.25s ease;
    }
    .dest-card:hover::after {
        width: 100%;
    }
    
    .dest-pill {
        background-color: rgba(5, 8, 15, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 4px 10px;
        font-size: 0.78rem;
        color: #E8F4FF;
        font-weight: 500;
        backdrop-filter: blur(8px);
    }

    /* Style Streamlit forms to serve as Luxury cards */
    div[data-testid="stForm"] {
        background-color: #0A1628 !important;
        border: 1px solid #1A3050 !important;
        border-radius: 16px !important;
        padding: 28px !important;
        box-shadow: 0 8px 30px rgba(0,0,0,0.3) !important;
        margin-bottom: 25px !important;
    }
    
    .input-label {
        font-size: 0.8rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #06B6D4;
        font-weight: 700;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    /* Quick Prompt Tactile Buttons */
    .prompt-chip {
        display: inline-block;
        background-color: #0F1E35;
        border: 1px solid #1E3A5F;
        border-radius: 24px;
        padding: 8px 16px;
        font-size: 0.82rem;
        color: #B8D4EE;
        margin-right: 8px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.25s ease;
    }
    .prompt-chip:hover {
        background-color: rgba(59, 130, 246, 0.15);
        border-color: #3B82F6;
        color: #E8F4FF;
        border-left: 3px solid #3B82F6;
    }

    /* Style Streamlit textarea */
    .stTextArea textarea {
        background-color: #060D1A !important;
        border: 1px solid #1A3050 !important;
        color: #E8F4FF !important;
        border-radius: 10px !important;
        padding: 14px !important;
        font-size: 0.95rem !important;
        transition: all 0.25s ease !important;
        line-height: 1.6 !important;
    }
    .stTextArea textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.25) !important;
    }
    
    /* Form Submit Button */
    div[data-testid="stForm"] button {
        background: linear-gradient(135deg, #1D4ED8, #1E40AF) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        height: 56px !important;
        font-family: 'Syne', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        box-shadow: 0 4px 18px rgba(29, 78, 216, 0.3) !important;
        transition: all 0.25s ease !important;
        width: 100% !important;
        cursor: pointer !important;
    }
    div[data-testid="stForm"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(29, 78, 216, 0.5) !important;
    }

    /* Agent Execution Cards with slideUp animation */
    .agent-card {
        background-color: #080F1E;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        position: relative;
        animation: slideUpFade 0.4s ease-out forwards;
    }
    
    @keyframes slideUpFade {
        from {
            opacity: 0;
            transform: translateY(15px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .agent-card.pending {
        border-left: 4px solid #475569;
    }
    .agent-card.active {
        border-left: 4px solid #3B82F6;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.1);
    }
    .agent-card.complete {
        border-left: 4px solid #10B981;
    }

    .agent-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }
    .agent-title {
        font-family: 'Syne', sans-serif;
        font-weight: 700;
        font-size: 0.95rem;
        color: #E8F4FF;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Live pulsing dot */
    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #3B82F6;
        border-radius: 50%;
        box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
        animation: pulse 1.2s infinite;
    }
    @keyframes pulse {
        0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
        }
        70% {
            transform: scale(1);
            box-shadow: 0 0 0 6px rgba(59, 130, 246, 0);
        }
        100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
        }
    }
    
    .agent-content {
        color: #8AAEC8;
        font-size: 0.9rem;
        line-height: 1.8;
    }

    /* Metrics Row Cards */
    .metric-card {
        background-color: #070B14;
        border: 1px solid #0F1E35;
        border-radius: 14px;
        height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        position: relative;
        overflow: hidden;
    }
    .metric-card-title {
        font-size: 0.75rem;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #64748B;
        margin-bottom: 4px;
    }
    .metric-val-blue {
        font-family: 'Syne', sans-serif;
        font-size: 2.4rem;
        font-weight: 700;
        color: #3B82F6;
    }
    .metric-val-cyan {
        font-family: 'Syne', sans-serif;
        font-size: 2.4rem;
        font-weight: 700;
        color: #06B6D4;
    }
    
    .pulse-status {
        animation: statusPulse 2s infinite ease-in-out;
    }
    @keyframes statusPulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.08); filter: drop-shadow(0 0 6px rgba(16, 185, 129, 0.4)); }
        100% { transform: scale(1); }
    }

    /* Final Plan Document Card */
    .plan-card {
        background-color: #080F1E;
        border-left: 5px solid #3B82F6;
        border-radius: 16px;
        padding: 28px 32px;
        box-shadow: 0 8px 35px rgba(0,0,0,0.4);
        margin-top: 25px;
    }
    .plan-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(59, 130, 246, 0.15);
        padding-bottom: 15px;
        margin-bottom: 20px;
    }
    .plan-title {
        font-family: 'Syne', sans-serif;
        font-size: 1.4rem;
        color: #E8F4FF;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .plan-timestamp {
        font-size: 0.8rem;
        color: #64748B;
    }
    .plan-body {
        color: #B8D4EE;
        font-size: 0.97rem;
        line-height: 2.0;
    }
    
    /* Day Labels auto-highlight styling */
    .day-highlight {
        color: #3B82F6;
        font-weight: 700;
        font-size: 1.15rem;
        margin-top: 20px;
        display: block;
        border-bottom: 1px solid rgba(59, 130, 246, 0.15);
        padding-bottom: 4px;
        margin-bottom: 10px;
    }
    
    .plan-divider {
        height: 1px;
        background-color: rgba(59, 130, 246, 0.1);
        margin: 20px 0;
    }

    /* Custom Streamlit Spinner Overlay */
    div[data-testid="stSpinner"] {
        background-color: rgba(5, 8, 15, 0.85) !important;
        position: fixed !important;
        inset: 0 !important;
        z-index: 99999 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        backdrop-filter: blur(8px) !important;
    }
    
    /* Styled warning and error blocks */
    div[data-testid="stAlert"] {
        background-color: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
    }

    /* ── Destination Card Columns ── */
    /* Remove global card styling from columns that contain a .dest-card-wrapper */
    div[data-testid="column"]:has(.dest-card-wrapper) {
        background-color: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0 !important;
        box-shadow: none !important;
        backdrop-filter: none !important;
        margin-bottom: 0 !important;
        position: relative !important;
    }

</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Onboarding Welcome Form (Dynamic User Info Setup)
# ──────────────────────────────────────────────
if "user_name" not in st.session_state or not st.session_state.user_name:
    st.markdown(
        f"<div style='max-width: 550px; margin: 100px auto 30px auto; padding: 40px; background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; box-shadow: 0 12px 40px rgba(0,0,0,0.5); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); text-align: center;'>"
        f"<h1 style='background: linear-gradient(135deg, #3B82F6, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; font-size: 3.2rem; margin-bottom: 10px; font-family: \"Syne\", sans-serif;'>AeroVoyage</h1>"
        f"<p style='color: #94a3b8; font-size: 1.15rem; margin-bottom: 0;'>Your luxury AI-powered multi-agent travel companion.</p>"
        f"</div>",
        unsafe_allow_html=True
    )
    
    _, col_form, _ = st.columns([1, 2, 1])
    with col_form:
        name_input = st.text_input("Enter passenger name for Lounge access:", placeholder="e.g. Satyam")
        if st.button("Enter Terminal Lounge", use_container_width=True):
            if name_input.strip():
                st.session_state.user_name = name_input.strip().lower()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.session_state.thread_id = f"session_{st.session_state.user_name}_{ts}"
                # Sync query params
                st.query_params["thread_id"] = st.session_state.thread_id
                st.query_params["user_name"] = st.session_state.user_name
                st.rerun()
            else:
                st.error("Passenger name cannot be empty.")
    st.stop()

# ──────────────────────────────────────────────
# Global Variables and Backend State Retrieval
# ──────────────────────────────────────────────
current_user = st.session_state.user_name
config = {"configurable": {"thread_id": st.session_state.thread_id}}

# Query active state variables
snapshot = app.get_state(config)
state_values = snapshot.values
messages = state_values.get("messages", [])
trip_start_msg_id = state_values.get("trip_start_msg_id", "")
itinerary = state_values.get("itinerary", "")
error = state_values.get("error", "")

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

# Stepper States initialization
if "stepper_states" not in st.session_state:
    st.session_state.stepper_states = {
        "query_parser": "pending",
        "iata_resolver": "pending",
        "flight_agent": "pending",
        "hotel_agent": "pending",
        "itinerary_agent": "pending",
        "final_agent": "pending"
    }

# Initialize session state for text area if not present
if "user_query_input" not in st.session_state:
    st.session_state.user_query_input = ""


# Sync stepper states if itinerary was already generated in the loaded thread
if itinerary:
    for k in st.session_state.stepper_states:
        st.session_state.stepper_states[k] = "complete"
else:
    # If not finished, and no active execution is running, reset
    if st.session_state.get("pipeline_status") != "running":
        for k in st.session_state.stepper_states:
            st.session_state.stepper_states[k] = "pending"

# ──────────────────────────────────────────────
# Sidebar - History & Stepper Navigation
# ──────────────────────────────────────────────
st.sidebar.markdown(
    f"<div style='text-align: center; margin-top: 10px; margin-bottom: 25px;'>"
    f"<h1>✈️ AeroVoyage<span style='color:#3B82F6;'>.</span></h1>"
    f"<p style='color: #64748b; font-size: 0.85rem; margin-top: 0;'>Active Lounge: <b>{st.session_state.user_name.upper()}</b></p>"
    f"</div>",
    unsafe_allow_html=True
)

# New Session Button
if st.sidebar.button("➕ New Trip Planner", use_container_width=True):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_thread = f"session_{st.session_state.user_name}_{ts}"
    st.session_state.thread_id = new_thread
    st.query_params["thread_id"] = new_thread
    # Reset pipeline status
    st.session_state.pipeline_status = "idle"
    for k in st.session_state.stepper_states:
        st.session_state.stepper_states[k] = "pending"
    st.rerun()

# Stepper UI
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 15px 0;'>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='font-family: \"Syne\", sans-serif; font-size: 0.9rem; font-weight: 700; color: #E8F4FF; margin-bottom: 12px;'>AGENT PIPELINE</div>", unsafe_allow_html=True)

steps = [
    ("query_parser", "Query Parser"),
    ("iata_resolver", "IATA Resolver"),
    ("flight_agent", "Flight Agent"),
    ("hotel_agent", "Hotel Agent"),
    ("itinerary_agent", "Itinerary Planner"),
    ("final_agent", "Summary Advisor")
]

stepper_html = []
for idx, (node_id, label) in enumerate(steps, 1):
    status = st.session_state.stepper_states.get(node_id, "pending")
    if status == "complete":
        circle = f"<div class='step-circle complete'>✓</div>"
        text_class = "complete"
    elif status == "active":
        circle = f"<div class='step-circle active'>{idx}</div>"
        text_class = "active"
    else:
        circle = f"<div class='step-circle pending'>{idx}</div>"
        text_class = "pending"
        
    stepper_html.append(
        f"<div class='step-item'>"
        f"{circle}"
        f"<div class='step-name {text_class}'>{label}</div>"
        f"</div>"
    )
    
st.sidebar.markdown(f"<div class='stepper-container'>{''.join(stepper_html)}</div>", unsafe_allow_html=True)

# Recent Session History
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 15px 0;'>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='font-family: \"Syne\", sans-serif; font-size: 0.9rem; font-weight: 700; color: #E8F4FF; margin-bottom: 10px;'>RECENT CONVERSATIONS</div>", unsafe_allow_html=True)
sessions = get_past_sessions(conn, st.session_state.user_name)

if not sessions:
    st.sidebar.markdown(
        "<div style='color: #475569; font-size: 0.8rem; text-align: center; margin-top: 10px;'>"
        "No recent flights logged."
        "</div>",
        unsafe_allow_html=True
    )
else:
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
            q_short = q[:25] + "..." if len(q) > 25 else q
            if not q_short or q_short == "...":
                q_short = "Untitled Flight"
            title = f"💬 {q_short}"
            meta = "📅 Logistics setup"
            
        card_html = (
            f'<a href="?thread_id={thread_id}&user_name={st.session_state.user_name}" target="_self" style="text-decoration: none; color: inherit;">'
            f'<div class="session-card {active_class}">'
            f'<div class="session-card-title">{title}</div>'
            f'<div class="session-card-meta">{meta}</div>'
            f'<div class="session-card-time">🕒 Activity: {updated_str}</div>'
            f'</div>'
            f'</a>'
        )
        html_cards.append(card_html)
        
    st.sidebar.markdown(
        f"<div class='session-list-container'>{''.join(html_cards)}</div>",
        unsafe_allow_html=True
    )

# Powered By badges
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 15px 0;'>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='font-family: \"Syne\", sans-serif; font-size: 0.9rem; font-weight: 700; color: #E8F4FF; margin-bottom: 8px;'>POWERED BY</div>", unsafe_allow_html=True)
tech_html = (
    "<div style='display: flex; flex-wrap: wrap; margin-bottom: 15px;'>"
    "<div class='tech-pill'><span class='tech-dot' style='background-color: #3B82F6;'></span>LangGraph</div>"
    "<div class='tech-pill'><span class='tech-dot' style='background-color: #F97316;'></span>Groq</div>"
    "<div class='tech-pill'><span class='tech-dot' style='background-color: #10B981;'></span>PostgreSQL</div>"
    "<div class='tech-pill'><span class='tech-dot' style='background-color: #A855F7;'></span>Tavily</div>"
    "<div class='tech-pill'><span class='tech-dot' style='background-color: #EF4444;'></span>SerpApi</div>"
    "</div>"
)
st.sidebar.markdown(tech_html, unsafe_allow_html=True)

# Session thread ID
st.sidebar.markdown(
    f"<div style='font-family: monospace; font-size: 0.72rem; color: #475569; padding-left: 10px; margin-top: 10px;'>"
    f"Session: {st.session_state.thread_id}</div>",
    unsafe_allow_html=True
)

# ──────────────────────────────────────────────
# Main Page Workspace
# ──────────────────────────────────────────────

# 1. Hero Section (Luxury Terminal Header)
hero_url = "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=2074&auto=format&fit=crop"
hero_html = f"""
<div class="hero-container" style="background-image: url('{hero_url}');">
    <div class="hero-sweep"></div>
    <div class="hero-overlay">
        <span class="glowing-badge">Aviation Lounge Departure</span>
        <h1 style="margin: 0; font-size: 2.8rem; color: #fff;">AeroVoyage Terminal</h1>
        <p style="margin: 5px 0 0 0; color: #8AAEC8; font-size: 1rem; font-family: 'DM Sans', sans-serif;">
            Luxury multi-agent itinerary architecture for elite travelers.
        </p>
        <div class="hero-stats-row">
            <div class="hero-stat-pill"><span class="hero-stat-icon">🤖</span>6 AI Agents</div>
            <div class="hero-stat-pill"><span class="hero-stat-icon">🔍</span>Real-Time Search</div>
            <div class="hero-stat-pill"><span class="hero-stat-icon">📅</span>Instant Itinerary</div>
        </div>
    </div>
</div>
"""
st.markdown(hero_html, unsafe_allow_html=True)

# 2. Destination Prefill Cards
destinations_info = [
    ("Tokyo", "🇯🇵 Tokyo", "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?q=80&w=600&auto=format&fit=crop", "Plan a 3-day luxury vacation in Tokyo under 3 lakhs from Mumbai starting 1 June"),
    ("Paris", "🇫🇷 Paris", "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?q=80&w=600&auto=format&fit=crop", "Plan a romantic 3-day getaway to Paris under 3 lakhs from Delhi starting 15 June"),
    ("Bangkok", "🇹🇭 Bangkok", "https://images.unsplash.com/photo-1508009603885-50cf7c579365?q=80&w=600&auto=format&fit=crop", "Plan an exciting 3-day trip to Bangkok under 1 lakh from Kolkata starting 5 June"),
    ("Rome", "🇮🇹 Rome", "https://images.unsplash.com/photo-1552832230-c0197dd311b5?q=80&w=600&auto=format&fit=crop", "Plan a historic 3-day tour of Rome under 3 lakhs from Mumbai starting 10 June"),
    ("Dubai", "🇦🇪 Dubai", "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?q=80&w=600&auto=format&fit=crop", "Plan a modern 3-day trip to Dubai under 2 lakhs from Delhi starting 1 June")
]

# Prefill query param parser
if "prefill" in st.query_params:
    city_name = st.query_params["prefill"]
    for city, label, img, prompt in destinations_info:
        if city.lower() == city_name.lower():
            st.session_state.user_query_input = prompt
            break
    del st.query_params["prefill"]

# Destination cards row — HTML card for visuals + transparent overlay button for clicks
col_list = st.columns(5)
for col, (city, label, img_url, prompt_text) in zip(col_list, destinations_info):
    with col:
        # Render the visual HTML card (background image, gradient)
        st.markdown(
            f'<div class="dest-card-wrapper">'
            f'<div class="dest-card" style="background-image: url(\'{img_url}\');">'
            f'<div class="dest-overlay">'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        # Button below the card — handles the click
        if st.button(label, key=f"dest_{city.lower()}", use_container_width=True):
            st.session_state.user_query_input = prompt_text
            st.rerun()

st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

# 3. Form Input Card (Styled via div[data-testid="stForm"])
# The prefilled prompt logic is handled directly in st.session_state.user_query_input

# Section Header
st.markdown("<div class='input-label'>📍 Describe Your Trip</div>", unsafe_allow_html=True)

with st.form("trip_form"):
    # Input Text Area (styled via CSS override)
    user_query = st.text_area(
        label="Trip details",
        label_visibility="collapsed",
        placeholder="e.g. Plan a trip from Mumbai to Tokyo for 3 days under 3 lakhs from 1 June to 4 June...", 
        height=140,
        key="user_query_input"
    )
    
    # Submit Button (styled via stForm button CSS)
    submit_clicked = st.form_submit_button("🚀 Construct Travel Architecture")

# ──────────────────────────────────────────────
# Interactive Agent Stream Handler
# ──────────────────────────────────────────────
def draw_agent_cards():
    cards_html = []
    
    agents = [
        ("query_parser", "🕵️", "Query Parser Agent"),
        ("iata_resolver", "🛫", "IATA Code Resolver Agent"),
        ("flight_agent", "✈️", "Flight Booking Agent"),
        ("hotel_agent", "🏨", "Hotel Booking Agent"),
        ("itinerary_agent", "📅", "Itinerary Planner Agent"),
        ("final_agent", "📝", "Final Travel Advisor Agent")
    ]
    
    for node_id, icon, name in agents:
        status = st.session_state.stepper_states.get(node_id, "pending")
        
        if status == "complete":
            border_color = "#10B981"
            card_class = "complete"
            indicator = "<span style='color: #10B981; font-weight: 700; font-size: 0.82rem;'>✓ Completed</span>"
        elif status == "active":
            border_color = "#3B82F6"
            card_class = "active"
            indicator = "<span class='pulse-dot'></span>"
        else:
            border_color = "#475569"
            card_class = "pending"
            indicator = "<span style='color: #475569; font-size: 0.82rem;'>Pending</span>"
            
        # Get dynamic description from results state
        output_text = ""
        if status == "complete":
            if node_id == "query_parser":
                output_text = f"Parsed Origin: <b>{state_values.get('origin_city', 'N/A').title()}</b> | Destination: <b>{state_values.get('destination_city', 'N/A').title()}</b> | Start Date: <b>{state_values.get('travel_date', 'N/A')}</b> | Budget: <b>₹{state_values.get('budget', 0):,}</b>"
            elif node_id == "iata_resolver":
                origin_code = state_values.get('origin_iata', 'N/A')
                dest_code = state_values.get('destination_iata', 'N/A')
                origin_display = state_values.get('origin_city', 'N/A').title() if origin_code.startswith("/") else origin_code
                dest_display = state_values.get('destination_city', 'N/A').title() if dest_code.startswith("/") else dest_code
                output_text = f"Resolved Airport Codes: <b>{origin_display}</b> ➔ <b>{dest_display}</b>"
            elif node_id == "flight_agent":
                output_text = state_values.get("flight_results", "Flights resolved successfully.").split("\n")[0]
            elif node_id == "hotel_agent":
                output_text = "Hotels search completed successfully within the specified budget."
            elif node_id == "itinerary_agent":
                output_text = "Detailed travel logistics and day-by-day planner completed."
            elif node_id == "final_agent":
                output_text = "Advisor summary and transit guides compiled."
        elif status == "active":
            output_text = "Agent is active and constructing trip details..."
            
        content_div = f"<div class='agent-content'>{output_text}</div>" if output_text else ""
            
        cards_html.append(
            f'<div class="agent-card {card_class}" style="border-left: 4px solid {border_color};">'
            f'<div class="agent-header">'
            f'<div class="agent-title">{icon} {name}</div>'
            f'{indicator}'
            f'</div>'
            f'{content_div}'
            f'</div>'
        )
        
    return f"<div>{''.join(cards_html)}</div>"

# Submit Actions
if submit_clicked and user_query.strip():
    # 1. Reset Session States
    for k in st.session_state.stepper_states:
        st.session_state.stepper_states[k] = "pending"
    st.session_state.pipeline_status = "running"
    
    # Create new message ID
    msg_id = str(uuid.uuid4())
    inputs = {
        "messages": [HumanMessage(content=user_query, id=msg_id)],
        "user_query": user_query,
        "flight_results": "", "hotel_results": "", "airport_results": "", "itinerary": "", "error": "",
        "llm_calls": 0
    }
    
    # 2. Render Live Stepper and Status Cards
    placeholder_cards = st.empty()
    st.session_state.stepper_states["query_parser"] = "active"
    
    try:
        # Run graph updates in real time using app.stream
        stream = app.stream(inputs, config=config)
        for event in stream:
            for node_name, values in event.items():
                st.session_state.stepper_states[node_name] = "complete"
                
                # Fetch recent state snapshot
                snapshot = app.get_state(config)
                state_values = snapshot.values
                
                # Stepper edge triggers
                if node_name == "query_parser":
                    st.session_state.stepper_states["iata_resolver"] = "active"
                elif node_name == "iata_resolver":
                    st.session_state.stepper_states["flight_agent"] = "active"
                    st.session_state.stepper_states["hotel_agent"] = "active"
                elif node_name in ["flight_agent", "hotel_agent"]:
                    if st.session_state.stepper_states["flight_agent"] == "complete" and st.session_state.stepper_states["hotel_agent"] == "complete":
                        st.session_state.stepper_states["itinerary_agent"] = "active"
                elif node_name == "itinerary_agent":
                    st.session_state.stepper_states["final_agent"] = "active"
                elif node_name == "final_agent":
                    st.session_state.pipeline_status = "complete"
                
                # Live draw updates in loop without script interruption
                with placeholder_cards:
                    st.markdown(draw_agent_cards(), unsafe_allow_html=True)
                    
        st.session_state.pipeline_status = "complete"
        st.rerun()
        
    except GraphInterrupt:
        snapshot = app.get_state(config)
        st.rerun()
    except Exception as e:
        st.error(f"Execution pipeline interrupted: {e}")

# Interrupt handling (Human-in-the-loop input resumes)
is_interrupted = bool(snapshot.next and snapshot.tasks and snapshot.tasks[0].interrupts)
if is_interrupted:
    question = snapshot.tasks[0].interrupts[0].value
    st.markdown(
        f"<div class='agent-card active' style='border-left: 4px solid #ef4444;'>"
        f"<div class='agent-header'>"
        f"<div class='agent-title' style='color:#fca5a5;'>🙋 Input Parameter Required</div>"
        f"<span class='pulse-dot' style='background-color:#ef4444;'></span>"
        f"</div>"
        f"<div class='agent-content' style='color:#fff; font-size:0.95rem; margin-top:5px;'>{question}</div>"
        f"</div>",
        unsafe_allow_html=True
    )
    
    # Inline resume form
    with st.form("resume_form"):
        answer = st.text_input("Enter response details:")
        resume_clicked = st.form_submit_button("Submit Response & Resume")
        
        if resume_clicked and answer.strip():
            msg_id = str(uuid.uuid4())
            app.update_state(config, {
                "messages": [HumanMessage(content=answer, id=msg_id)],
                "user_query": f"{state_values.get('user_query', '')} {answer}"
            })
            
            # Restart stepper active status
            st.session_state.stepper_states["query_parser"] = "active"
            st.session_state.pipeline_status = "running"
            
            placeholder_cards = st.empty()
            try:
                stream = app.stream(Command(resume=answer), config=config)
                for event in stream:
                    for node_name, values in event.items():
                        st.session_state.stepper_states[node_name] = "complete"
                        
                        snapshot = app.get_state(config)
                        state_values = snapshot.values
                        
                        if node_name == "query_parser":
                            st.session_state.stepper_states["iata_resolver"] = "active"
                        elif node_name == "iata_resolver":
                            st.session_state.stepper_states["flight_agent"] = "active"
                            st.session_state.stepper_states["hotel_agent"] = "active"
                        elif node_name in ["flight_agent", "hotel_agent"]:
                            if st.session_state.stepper_states["flight_agent"] == "complete" and st.session_state.stepper_states["hotel_agent"] == "complete":
                                st.session_state.stepper_states["itinerary_agent"] = "active"
                        elif node_name == "itinerary_agent":
                            st.session_state.stepper_states["final_agent"] = "active"
                        elif node_name == "final_agent":
                            st.session_state.pipeline_status = "complete"
                            
                        with placeholder_cards:
                            st.markdown(draw_agent_cards(), unsafe_allow_html=True)
                            
                st.session_state.pipeline_status = "complete"
                st.rerun()
            except GraphInterrupt:
                snapshot = app.get_state(config)
                st.rerun()
            except Exception as e:
                st.error(f"Execution pipeline interrupted: {e}")

# ──────────────────────────────────────────────
# Dashboard Output (Itinerary & Details Results)
# ──────────────────────────────────────────────
if itinerary or state_values.get("flight_results") or state_values.get("hotel_results"):
    st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 25px 0;'>", unsafe_allow_html=True)
    
    # Left Column: Metrics and Agent logs. Right Column: Plan document details
    col_dash_left, col_dash_right = st.columns([2, 3])
    
    with col_dash_left:
        # Metrics Cards
        st.markdown("<div style='font-family: \"Syne\", sans-serif; font-size: 1.1rem; font-weight: 700; color: #E8F4FF; margin-bottom: 12px;'>METRICS ENGINE</div>", unsafe_allow_html=True)
        col_m1, col_m2, col_m3 = st.columns(3)
        agents_run = sum(1 for status in st.session_state.stepper_states.values() if status == "complete")
        
        with col_m1:
            st.markdown(
                f'<div class="metric-card" style="border-top: 3px solid #3B82F6;">'
                f'<div class="metric-card-title">Agents Run</div>'
                f'<div class="metric-val-blue">{agents_run} / 6</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col_m2:
            st.markdown(
                f'<div class="metric-card" style="border-top: 3px solid #06B6D4;">'
                f'<div class="metric-card-title">LLM Calls</div>'
                f'<div class="metric-val-cyan">{state_values.get("llm_calls", 0)}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col_m3:
            status_label = "Active" if st.session_state.get("pipeline_status") == "running" else "Complete" if itinerary else "Ready"
            if status_label == "Complete":
                svg_checkmark = """
                <svg class="pulse-status" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                """
                indicator = svg_checkmark
            elif status_label == "Active":
                indicator = "<div class='pulse-dot' style='width:14px; height:14px;'></div>"
            else:
                indicator = "<span style='color: #64748B; font-weight:700;'>Ready</span>"
                
            st.markdown(
                f'<div class="metric-card" style="border-top: 3px solid #10B981;">'
                f'<div class="metric-card-title">Status</div>'
                f'<div style="margin-top: 6px;">{indicator}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            
        st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
        
        # Agent Cards history logs
        st.markdown("<div style='font-family: \"Syne\", sans-serif; font-size: 1.1rem; font-weight: 700; color: #E8F4FF; margin-bottom: 12px;'>PIPELINE AUDIT LOG</div>", unsafe_allow_html=True)
        st.markdown(draw_agent_cards(), unsafe_allow_html=True)
        
    with col_dash_right:
        st.markdown("<div style='font-family: \"Syne\", sans-serif; font-size: 1.1rem; font-weight: 700; color: #E8F4FF; margin-bottom: 12px;'>TRAVEL LOGISTICS DOCUMENT</div>", unsafe_allow_html=True)
        
        # Find latest final_agent conversational summary
        final_summary = ""
        if recent_messages:
            for m in reversed(recent_messages):
                if isinstance(m, AIMessage) and m.content != itinerary:
                    final_summary = m.content
                    break
                    
        tab_itinerary, tab_flights_hotels = st.tabs([
            "📅 Detailed Itinerary", 
            "✈️ Flights, Hotels & Transit"
        ])
        
        with tab_itinerary:
            if itinerary:
                # Helper function to auto-highlight Day labels
                def highlight_days(text: str) -> str:
                    if not text:
                        return ""
                    text_styled = re.sub(
                        r"(Day\s+\d+:?)", 
                        r"<span class='day-highlight'>\1</span>", 
                        text, 
                        flags=re.IGNORECASE
                    )
                    return text_styled
                    
                styled_itinerary = highlight_days(itinerary)
                
                # Document Plan Layout wrapper
                st.markdown(
                    f'<div class="plan-card">'
                    f'<div class="plan-header">'
                    f'<div class="plan-title">🧠 Final Travel Plan</div>'
                    f'<div class="plan-timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M")}</div>'
                    f'</div>'
                    f'<div class="plan-body">',
                    unsafe_allow_html=True
                )
                
                st.markdown(styled_itinerary, unsafe_allow_html=True)
                
                st.markdown(
                    f'</div>'
                    f'<div class="plan-divider"></div>'
                    f'<div class="plan-timestamp" style="text-align: center; margin-top: 10px;">'
                    f'Generated by AeroVoyage · {datetime.now().strftime("%b %d, %Y %I:%M %p")}'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.info("No detailed itinerary generated.")
                
        with tab_flights_hotels:
            col_fl, col_ht = st.columns(2)
            with col_fl:
                st.markdown("<h4 class='gradient-subheader'>✈️ Flight Options</h4>", unsafe_allow_html=True)
                fl_results = state_values.get("flight_results", "")
                if fl_results:
                    st.markdown(fl_results)
                else:
                    st.write("Flight options not resolved.")
                    
                st.markdown("<h4 class='gradient-subheader'>🏢 Airport Information</h4>", unsafe_allow_html=True)
                ap_results = state_values.get("airport_results", "")
                if ap_results:
                    st.markdown(ap_results)
                else:
                    st.write("Airport details not resolved.")
                    
            with col_ht:
                st.markdown("<h4 class='gradient-subheader'>🏨 Accommodation Options</h4>", unsafe_allow_html=True)
                ht_results = state_values.get("hotel_results", "")
                if ht_results:
                    st.markdown(ht_results)
                else:
                    st.write("Hotel options not resolved.")
                    
        # Download and Save file panel
        st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
        col_d1, col_d2 = st.columns([1, 2])
        
        with col_d1:
            st.download_button(
                label="📥 Download Travel Plan",
                data=itinerary,
                file_name=f"aerovoyage_plan_{st.session_state.thread_id}.md",
                mime="text/markdown",
                key="download_btn"
            )
            # Custom styled download buttons
            st.markdown("""
            <style>
                div[data-testid="stDownloadButton"] button {
                    background-color: #0F2040 !important;
                    border: 1px solid #2A5080 !important;
                    color: #06B6D4 !important;
                    border-radius: 10px !important;
                    padding: 10px 20px !important;
                    font-weight: 600 !important;
                    font-size: 0.9rem !important;
                    transition: all 0.25s ease !important;
                    width: 100% !important;
                }
                div[data-testid="stDownloadButton"] button:hover {
                    background-color: rgba(6, 182, 212, 0.1) !important;
                    border-color: #06B6D4 !important;
                }
            </style>
            """, unsafe_allow_html=True)
            
        with col_d2:
            save_path = f"c:\\Users\\ssaty\\multi_agent_system\\saved_plans\\{st.session_state.thread_id}.md"
            try:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(itinerary)
                save_status = "Saved"
                save_color = "#10B981"
            except Exception as e:
                save_status = "Save Error"
                save_color = "#ef4444"
                
            st.markdown(
                f'<div style="background-color: #04070D; border: 1px solid #0F1E35; border-radius: 10px; padding: 12px; display: flex; align-items: center; justify-content: space-between;">'
                f'<span style="font-family: monospace; font-size: 0.8rem; color: #8AAEC8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 80%;">'
                f'{save_path}'
                f'</span>'
                f'<div style="display: flex; align-items: center;">'
                f'<span class="blink-dot"></span>'
                f'<span style="color: {save_color}; font-size: 0.8rem; font-weight: 600;">{save_status}</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            
        # Display the conversational final advisor summary text under itinerary details
        if final_summary:
            st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 20px 0;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-family: \"Syne\", sans-serif; font-size: 1.1rem; font-weight: 700; color: #E8F4FF; margin-bottom: 12px;'>📝 ADVISOR SUMMARY & TRANSIT RECOMMENDATIONS</div>", unsafe_allow_html=True)
            st.markdown(final_summary)
