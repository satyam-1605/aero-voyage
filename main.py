import os
import re
import json
import operator
import requests
import uuid
import getpass
from typing import TypedDict, Annotated
from datetime import datetime

import psycopg
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import interrupt, Command
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from tools.flight import search_flights
from tools.tavily import tavily_search

load_dotenv()

# ──────────────────────────────────────────────
# Initialization
# ──────────────────────────────────────────────
llm = ChatGroq(model="llama-3.3-70b-versatile")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# ──────────────────────────────────────────────
# 1. Define the State
# ──────────────────────────────────────────────
# This is the "memory" of your graph. Every node reads from and writes to this.
class TravelState(TypedDict):
    messages        : Annotated[list[AnyMessage], operator.add] # Appends new messages automatically
    user_query      : str
    origin_city     : str
    destination_city: str
    origin_iata     : str
    destination_iata: str
    travel_date     : str
    return_date     : str
    trip_type       : str
    budget          : int
    hotel_budget    : int  
    flight_results  : str
    hotel_results   : str
    airport_results : str
    itinerary       : str
    error           : str
    llm_calls       : int
    trip_start_msg_id: str

# ──────────────────────────────────────────────
# Helper function
# ──────────────────────────────────────────────
# def get_iata_code(city_name: str) -> str | None:
#     """Simple API call to Google Flights Autocomplete to get the 3-letter airport code."""
#     try:
#         res = requests.get(
#             "https://serpapi.com/search",
#             params={"engine": "google_flights_autocomplete", "q": city_name, "api_key": SERPAPI_KEY}
#         )
#         airports = res.json().get("airports", [])
#         return airports[0].get("id") if airports else None
#     except Exception:
#         return None

# ──────────────────────────────────────────────
# Helper function
# ──────────────────────────────────────────────
def get_iata_code(location_name: str) -> str | None:
    """API call to Google Flights Autocomplete to get the airport code or location ID."""
    try:
        res = requests.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_flights_autocomplete", 
                "q": location_name, 
                "api_key": SERPAPI_KEY
            }
        )
        
        # FIX: SerpApi uses the key 'suggestions', not 'airports'
        suggestions = res.json().get("suggestions", [])
        
        # This will return a 3-letter code (like 'DEL') OR a location ID (like '/m/03_3d')
        return suggestions[0].get("id") if suggestions else None
        
    except Exception as e:
        print(f"[get_iata_code] failed for {location_name}: {e}")
        return None

# ──────────────────────────────────────────────
# Helper — format past conversation (Last 10)
# ──────────────────────────────────────────────
def format_past_conversation(messages: list, trip_start_msg_id: str = None) -> str:
    recent = messages
    if trip_start_msg_id:
        start_idx = 0
        for idx, m in enumerate(messages):
            if getattr(m, "id", None) == trip_start_msg_id:
                start_idx = idx
                break
        recent = messages[start_idx:]
        
    limit = 10
    recent = recent[-limit:] if len(recent) > limit else recent
    lines  = []
    for m in recent:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines) if lines else "No previous conversation."

# ──────────────────────────────────────────────
# 2. Define the Nodes (The Agents)
# ──────────────────────────────────────────────

def query_parser_agent(state: TravelState) -> dict:
    """Extracts data from the query and pauses execution if anything is missing."""
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    llm_calls = state.get("llm_calls", 0)
    
    parse_prompt = f"""
    Today's date is {current_date}. 
    Analyze the user's query: "{state['user_query']}"
    
    Return a JSON object with these keys:
    - "is_new_trip": true if this is a completely new trip request (e.g. user wants to plan a new trip). false if it is a follow-up adjustment to the current trip (e.g. changing budget, date, or adding requirements).
    - "origin_city": departure city name.
    - "destination_city": arrival city name.
    - "travel_date": departure date in YYYY-MM-DD format.
    - "return_date": return date in YYYY-MM-DD format.
    - "trip_type": "round_trip" or "one_way".
    - "budget": total budget as an integer.
    - "hotel_budget": hotel budget as an integer.
    
    STRICT RULES:
    1. If the user gives a COUNTRY (like "Japan" or "China"), you MUST change 'destination_city' to its capital or most popular city (e.g., "Tokyo", "Beijing"). Do not output country names.
    2. Any parsed 'travel_date' or 'return_date' MUST be in the future relative to today's date ({current_date}). 
       If the user specifies a date or month that has already passed in the current year, you MUST set the year to the next year.
       For example, if today is {current_date} and the user says "1 april", the year must be set to 2027 (giving "2027-04-01").
    3. Format all dates as YYYY-MM-DD.
    4. If 'hotel_budget' is 0, calculate it as 35% of the total budget.
    """

    # Parse JSON from LLM
    text = llm.invoke([HumanMessage(content=parse_prompt)]).content
    llm_calls += 1
    try:
        info = json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0))
    except:
        info = {}

    is_new_trip = info.get("is_new_trip", False)
    trip_start_msg_id = state.get("trip_start_msg_id", "")

    if is_new_trip:
        # Fresh start: only take what is parsed in this query and clear old state
        origin_city      = info.get("origin_city", "")
        destination_city = info.get("destination_city", "")
        travel_date      = info.get("travel_date", "")
        return_date      = info.get("return_date", "")
        trip_type        = info.get("trip_type", "one_way")
        budget           = info.get("budget", 0)
        hotel_budget     = info.get("hotel_budget", 0)
        
        # Mark the current user message as the start of this trip's conversation
        if state.get("messages"):
            trip_start_msg_id = getattr(state["messages"][-1], "id", "")
    else:
        # Follow-up: merge parsed info with existing state
        origin_city      = info.get("origin_city") or state.get("origin_city", "")
        destination_city = info.get("destination_city") or state.get("destination_city", "")
        travel_date      = info.get("travel_date") or state.get("travel_date", "")
        return_date      = info.get("return_date") or state.get("return_date", "")
        trip_type        = info.get("trip_type") or state.get("trip_type", "one_way")
        budget           = info.get("budget") or state.get("budget", 0)
        hotel_budget     = info.get("hotel_budget") or state.get("hotel_budget", 0)

    try:
        budget = int(budget)
    except:
        budget = 0

    try:
        hotel_budget = int(hotel_budget)
    except:
        hotel_budget = 0
    if budget and (not hotel_budget or hotel_budget == 0):
        hotel_budget = int(budget * 0.35)

    # LangGraph Interrupts (Human-in-the-loop)
    # The graph pauses here. When resumed, the user's answer becomes the variable value.
    if not origin_city:
        origin_city = interrupt("Where will you be travelling from?")
    if not destination_city:
        destination_city = interrupt("Where would you like to travel to?")
    if not travel_date:
        travel_date = interrupt("When are you planning to travel? (YYYY-MM-DD)")
    if not budget:
        budget_input = interrupt("What is your total budget for this trip?")
        budget = int(re.sub(r"[^\d]", "", llm.invoke([HumanMessage(content=f"Extract integer from: {budget_input}")]).content))
        llm_calls += 1
        hotel_budget = int(budget * 0.35)

    return {
        "origin_city": origin_city,
        "destination_city": destination_city,
        "travel_date": travel_date,
        "return_date": return_date,
        "trip_type": trip_type,
        "budget": budget,
        "hotel_budget": hotel_budget,
        "llm_calls": llm_calls,
        "trip_start_msg_id": trip_start_msg_id
    }


def iata_resolver_agent(state: TravelState) -> dict:
    """Converts city names into airport codes."""
    origin_iata = get_iata_code(state.get("origin_city", ""))
    destination_iata = get_iata_code(state.get("destination_city", ""))

    if not origin_iata or not destination_iata:
        return {"error": "Could not resolve airport codes. Check city names."}

    return {"origin_iata": origin_iata, "destination_iata": destination_iata}


def flight_agent(state: TravelState) -> dict:
    """Searches for flights (Runs in parallel with Hotel Agent)."""
    try:
        res = search_flights(
            origin=state["origin_iata"], destination=state["destination_iata"], 
            outbound_date=state["travel_date"], return_date=state.get("return_date"),
            trip_type=state.get("trip_type", "one_way")
        )
        flights = res.get("flights", [])
        airports = res.get("airports", [])
        
        # Format the results into a readable string
        lines = [f"Flights to {state['destination_city']}:"]
        for f in flights[:3]: # Keep top 3
            lines.append(f"- {f.get('airline')}: ₹{f.get('price', 'N/A')} ({f.get('departure_airport')} -> {f.get('arrival_airport')})")
            
        # Format the airport details
        airport_lines = []
        if airports and isinstance(airports, list) and len(airports) > 0:
            airport_data = airports[0]
            dep_info = airport_data.get("departure", [])
            arr_info = airport_data.get("arrival", [])
            
            if dep_info:
                dep_ap = dep_info[0].get("airport", {})
                dep_id = dep_ap.get("id", "")
                dep_id_display = f" ({dep_id})" if dep_id and not dep_id.startswith("/") else ""
                airport_lines.append(f"Departure Airport: {dep_ap.get('name')}{dep_id_display} in {dep_info[0].get('city')}, {dep_info[0].get('country')}")
            if arr_info:
                arr_ap = arr_info[0].get("airport", {})
                arr_id = arr_ap.get("id", "")
                arr_id_display = f" ({arr_id})" if arr_id and not arr_id.startswith("/") else ""
                airport_lines.append(f"Arrival Airport: {arr_ap.get('name')}{arr_id_display} in {arr_info[0].get('city')}, {arr_info[0].get('country')}")
                
        airport_results = "\n".join(airport_lines) if airport_lines else "No detailed airport information found."
        
        return {
            "flight_results": "\n".join(lines),
            "airport_results": airport_results
        }
    except Exception as e:
        return {
            "flight_results": f"Flight API Error: {e}",
            "airport_results": f"Airport Error: Could not fetch airport details due to flight search failure."
        }


def hotel_agent(state: TravelState) -> dict:
    """Searches for hotels and formats the top 5 hotels with details and prices using LLM."""
    query = f"Best hotels in {state['destination_city']} under ₹{state['hotel_budget']} total budget"
    llm_calls = state.get("llm_calls", 0)
    try:
        raw_results = tavily_search(query)
        
        prompt = f"""
        Analyze the following hotel search results in {state['destination_city']} under a total budget of ₹{state['hotel_budget']:,}:
        
        {raw_results}
        
        Extract and present the top 5 specific hotels that fit within this budget.
        Format your response as a clean Markdown list.
        For each hotel, provide:
        1. **[Hotel Name]** (with a link to their website or the source URL if available)
        2. **Price**: Estimated price per night in INR
        3. **Location & Key Details**: 2-3 sentences describing the hotel's location, amenities, and why it is a great choice.
        
        Do not return generic articles or search result summaries. Return exactly 5 concrete hotel listings.
        """
        response = llm.invoke([HumanMessage(content=prompt)])
        llm_calls += 1
        return {
            "hotel_results": response.content,
            "llm_calls": llm_calls
        }
    except Exception as e:
        return {
            "hotel_results": f"Hotel API Error: {e}",
            "llm_calls": llm_calls
        }


def itinerary_agent(state: TravelState) -> dict:
    budget = state.get("budget")
    past_conversation = format_past_conversation(state.get("messages", []), state.get("trip_start_msg_id"))
    llm_calls = state.get("llm_calls", 0)

    prompt = f"""
You are an expert travel planner.

Past Conversation History:
{past_conversation}

Current Request:
Origin          : {state.get('origin_city')} ({state.get('origin_iata')})
Destination     : {state.get('destination_city')} ({state.get('destination_iata')})
Travel Date     : {state.get('travel_date')}
Total Budget    : ₹{budget:,}

Flight Results:
{state.get('flight_results', 'N/A')}

Hotel Results:
{state.get('hotel_results', 'N/A')}

Airport Transit & Terminal Info:
{state.get('airport_results', 'N/A')}

STRICT RULES:
- Total cost MUST stay within ₹{budget:,}
- Use ONLY the flight and hotel data provided above
- Include a budget breakdown at the end
"""

    try:
        response = llm.invoke([
            SystemMessage(content="You are an expert travel planner."),
            HumanMessage(content=prompt),
        ])
        llm_calls += 1
        itinerary = response.content
    except Exception as e:
        itinerary = f"Itinerary generation failed: {e}"
        response  = AIMessage(content=itinerary)

    return {"itinerary": itinerary, "messages" : [response], "llm_calls": llm_calls}


def final_agent(state: TravelState) -> dict:
    """Generates the final summary, highlighting tourist spots."""
    budget = state.get("budget")
    past_conversation = format_past_conversation(state.get("messages", []), state.get("trip_start_msg_id"))
    llm_calls = state.get("llm_calls", 0)
    prompt = f"""
You are a travel advisor writing a final trip summary for a customer.

Past Conversation History:
{past_conversation}

Original Request : {state.get('user_query')}
Origin           : {state.get('origin_city')}
Destination      : {state.get('destination_city')}
Total Budget     : ₹{budget:,}

Itinerary:
{state.get('itinerary')}

Airport Info:
{state.get('airport_results', 'N/A')}

Your task:
1. Write a short friendly summary (3-4 lines).
2. Recommend 3-4 beautiful tourist attractions or sightseeing spots in {state.get('destination_city')} that the user must visit.
3. Show a clear budget breakdown (flights + hotel + food + activities + total).
4. Confirm if the trip fits within ₹{budget:,}.
5. Add 2-3 practical booking and airport transit tips (mentioning resolved airports and specific transit options like express trains, taxis, or metro lines based on the airport info).
6. Do NOT repeat the full day-by-day itinerary.
"""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        llm_calls += 1
    except Exception as e:
        response = AIMessage(content=f"Could not generate summary: {e}")

    return {"messages" : [response], "llm_calls": llm_calls}

# ──────────────────────────────────────────────
# 3. Build the Graph
# ──────────────────────────────────────────────
graph = StateGraph(TravelState)

graph.add_node("query_parser", query_parser_agent)
graph.add_node("iata_resolver", iata_resolver_agent)
graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

# Define the flow
graph.add_edge(START, "query_parser")
graph.add_edge("query_parser", "iata_resolver")


# Conditional Routing: Stop if IATA fails, otherwise run Flight/Hotel in parallel
def iata_router(state: TravelState):
    if state.get("error"):
        return ["end"]
    return ["flight_agent", "hotel_agent"]

graph.add_conditional_edges(
    "iata_resolver",
    iata_router,
    {
        "flight_agent": "flight_agent",
        "hotel_agent": "hotel_agent",
        "end": END
    }
)
graph.add_edge("flight_agent", "itinerary_agent")
graph.add_edge("hotel_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)

# Setup PostgreSQL Checkpointer (Memory)
conn = psycopg.connect(os.getenv("DATABASE_URL"), autocommit=True)
checkpointer = PostgresSaver(conn)
checkpointer.setup()

app = graph.compile(checkpointer=checkpointer)

# ──────────────────────────────────────────────
# Helper Functions for Session History
# ──────────────────────────────────────────────
def format_timestamp(ts_str: str) -> str:
    if not ts_str:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        try:
            dt = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")
            return dt.strftime("%b %d, %Y %I:%M %p")
        except Exception:
            return ts_str

def get_past_sessions(conn, current_user: str) -> list[dict]:
    """Fetches the latest 10 sessions for the current user from the checkpoints database."""
    query = """
        WITH latest_checkpoints AS (
            SELECT DISTINCT ON (thread_id) 
                thread_id, 
                checkpoint
            FROM checkpoints
            ORDER BY thread_id, checkpoint->>'ts' DESC
        )
        SELECT 
            thread_id,
            checkpoint->'channel_values'->>'user_query' as user_query,
            checkpoint->'channel_values'->>'origin_city' as origin_city,
            checkpoint->'channel_values'->>'destination_city' as destination_city,
            checkpoint->'channel_values'->>'travel_date' as travel_date,
            checkpoint->>'ts' as last_updated
        FROM latest_checkpoints
        WHERE thread_id LIKE %s OR thread_id = %s
        ORDER BY last_updated DESC
        LIMIT 10
    """
    sessions = []
    try:
        with conn.cursor() as cur:
            cur.execute(query, (f"session_{current_user}_%", f"user_{current_user}"))
            rows = cur.fetchall()
            for r in rows:
                sessions.append({
                    "thread_id": r[0],
                    "user_query": r[1] or "",
                    "origin_city": r[2] or "",
                    "destination_city": r[3] or "",
                    "travel_date": r[4] or "",
                    "last_updated": r[5] or ""
                })
    except Exception as e:
        print(f"Error fetching past sessions: {e}")
    return sessions

def print_sessions_list(sessions: list[dict]) -> bool:
    print("\n" + "="*55)
    print("  PAST TRIPS & CONVERSATIONS")
    print("="*55)
    if not sessions:
        print("  No past sessions found. A new session will be created.")
        print("="*55)
        return False
        
    for idx, s in enumerate(sessions, 1):
        origin = s.get("origin_city")
        dest = s.get("destination_city")
        date = s.get("travel_date")
        updated = format_timestamp(s.get("last_updated"))
        
        # Build description
        if origin and dest:
            desc = f"Trip from {origin} to {dest}"
            if date:
                desc += f" (on {date})"
        else:
            query = s.get("user_query", "")
            desc = query[:40] + "..." if len(query) > 40 else query
            if not desc or desc == "...":
                desc = "Untitled Session"
                
        print(f" [{idx}] {desc}")
        print(f"     Last activity: {updated}")
    
    print("\n [N] Start a completely new trip (Default)")
    print("="*55)
    return True

def select_session(conn, current_user: str) -> tuple[str, dict | None]:
    sessions = get_past_sessions(conn, current_user)
    has_sessions = print_sessions_list(sessions)
    
    if not has_sessions:
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{current_user}_{session_timestamp}", None
        
    while True:
        choice = input(f"Select an option (1-{len(sessions)} or N) [N]: ").strip().upper()
        if not choice or choice == "N":
            session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"session_{current_user}_{session_timestamp}", None
        try:
            idx = int(choice)
            if 1 <= idx <= len(sessions):
                selected = sessions[idx-1]
                return selected["thread_id"], selected
        except ValueError:
            pass
        print(f"Invalid selection. Please enter a number between 1 and {len(sessions)}, or N.")

# ──────────────────────────────────────────────
# 4. Execution Loop
# ──────────────────────────────────────────────
if __name__ == "__main__":
    session_id = getpass.getuser()
    
    # Let user select session on startup
    thread_id, selected_session_info = select_session(conn, session_id)
    config = {"configurable": {"thread_id": thread_id}}
    
    if selected_session_info:
        print(f"\nResumed session: '{thread_id}'")
        # Load and display past context
        state_values = app.get_state(config).values
        if state_values.get("itinerary"):
            print("\n" + "="*40 + "\nRESUMED ITINERARY\n" + "="*40)
            print(state_values.get("itinerary"))
        elif state_values.get("messages"):
            print("\n" + "="*40 + "\nLAST CONVERSATION\n" + "="*40)
            print(f"Assistant: {state_values['messages'][-1].content}")
    else:
        print(f"\nStarted a brand new trip session! ID: '{thread_id}'")

    print("\nWelcome! Type your queries below. Type /help to see available commands.")

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
            
        # Parse slash commands
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            
            if cmd in ["/exit", "/quit"]:
                break
            elif cmd == "/new":
                session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                thread_id = f"session_{session_id}_{session_timestamp}"
                config = {"configurable": {"thread_id": thread_id}}
                print(f"\nStarted a brand new trip session! ID: '{thread_id}'")
                continue
            elif cmd in ["/history", "/list"]:
                sessions = get_past_sessions(conn, session_id)
                print_sessions_list(sessions)
                continue
            elif cmd in ["/load", "/switch"]:
                if len(parts) < 2:
                    print("Usage: /load <number>")
                    continue
                try:
                    idx = int(parts[1])
                    sessions = get_past_sessions(conn, session_id)
                    if 1 <= idx <= len(sessions):
                        selected = sessions[idx-1]
                        thread_id = selected["thread_id"]
                        config = {"configurable": {"thread_id": thread_id}}
                        print(f"\nSwitched to session: '{thread_id}'")
                        
                        # Print resumed state context
                        state_values = app.get_state(config).values
                        if state_values.get("itinerary"):
                            print("\n" + "="*40 + "\nRESUMED ITINERARY\n" + "="*40)
                            print(state_values.get("itinerary"))
                        elif state_values.get("messages"):
                            print("\n" + "="*40 + "\nLAST CONVERSATION\n" + "="*40)
                            print(f"Assistant: {state_values['messages'][-1].content}")
                    else:
                        print(f"Invalid session number. Must be between 1 and {len(sessions)}.")
                except ValueError:
                    print("Usage: /load <number>")
                continue
            elif cmd == "/help":
                print("\nAvailable Commands:")
                print("  /new             - Start a brand new travel planning session")
                print("  /history         - List all your past travel planning sessions")
                print("  /load <number>   - Switch to/resume a specific past session")
                print("  /help            - Show this help message")
                print("  /exit            - Exit the application")
                continue
            else:
                print(f"Unknown command: {cmd}. Type /help for a list of commands.")
                continue

        # Generate a unique message ID for history tracking
        msg_id = str(uuid.uuid4())

        # Check if there is a pending interrupt
        snapshot = app.get_state(config)
        if snapshot.next and snapshot.tasks[0].interrupts:
            # Resume execution, passing the answer directly to the paused node
            app.update_state(config, {
                "messages": [HumanMessage(content=user_input, id=msg_id)],
                "user_query": f"{snapshot.values.get('user_query', '')} {user_input}"
            })
            app.invoke(Command(resume=user_input), config=config)
        else:
            # Reset transient data for a fresh query, but keep chat history via operator.add
            app.invoke({
                "messages": [HumanMessage(content=user_input, id=msg_id)],
                "user_query": user_input,
                "flight_results": "", "hotel_results": "", "airport_results": "", "itinerary": "", "error": "",
                "llm_calls": 0
            }, config=config)

        # Handle interrupts
        while True:
            snapshot = app.get_state(config)
            if snapshot.next and snapshot.tasks[0].interrupts:
                # Graph is paused. Ask the user the question.
                question = snapshot.tasks[0].interrupts[0].value
                answer = input(f"\nAssistant: {question}\nYou: ").strip()
                
                # Save answer to chat history and update user_query for better context
                msg_id = str(uuid.uuid4())
                app.update_state(config, {
                    "messages": [HumanMessage(content=answer, id=msg_id)],
                    "user_query": f"{snapshot.values.get('user_query', '')} {answer}"
                }) 
                
                # Resume execution, passing the answer directly to the paused node
                app.invoke(Command(resume=answer), config=config)
            else:
                break # Graph finished completely

        # Print Final Results
        final_state = app.get_state(config).values
        if final_state.get("error"):
            print(f"\nError: {final_state['error']}")
        else:
            print("\n" + "="*40 + "\nITINERARY\n" + "="*40)
            print(final_state.get("itinerary", ""))
            print("\n" + "="*40 + "\nFINAL SUMMARY\n" + "="*40)
            print(final_state["messages"][-1].content)