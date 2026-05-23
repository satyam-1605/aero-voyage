# ✈️ AeroVoyage — AI Multi-Agent Travel Planner

> An intelligent, conversational travel planning assistant powered by **LangGraph**, **Groq (Llama 3.3 70B)**, and **Streamlit**. Plan flights, hotels, and full itineraries — just describe your trip.

---

## 🌟 Features

- 🤖 **Multi-Agent Architecture** — Specialized agents for parsing, IATA resolution, flight search, hotel search, itinerary generation, and final summarization
- ✈️ **Real-Time Flight Search** — Powered by SerpAPI Google Flights
- 🏨 **Hotel Recommendations** — Powered by Tavily AI web search
- 🗺️ **Full Itinerary Generation** — Day-by-day plans with budget breakdowns
- 💬 **Conversational Memory** — Persistent sessions stored in PostgreSQL via LangGraph checkpointing
- 🔄 **Human-in-the-Loop** — Pauses and asks for missing info (city, date, budget) mid-flow
- 🌐 **Streamlit Web UI** — Luxury "Aviation Terminal" themed interface
- 🖥️ **CLI Mode** — Terminal-based interface via `main.py`
- 📋 **Session Management** — Resume past trips, switch between sessions

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌─────────────────┐
│  Query Parser   │  ← Extracts origin, destination, dates, budget
│     Agent       │    Interrupts if info is missing (human-in-the-loop)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  IATA Resolver  │  ← Converts city names → airport codes (SerpAPI)
│     Agent       │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ Flight │ │ Hotel  │  ← Run in PARALLEL
│ Agent  │ │ Agent  │
└────┬───┘ └───┬────┘
     └────┬────┘
          ▼
┌─────────────────┐
│   Itinerary     │  ← Generates day-by-day plan using Groq LLM
│     Agent       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Final Summary  │  ← Tourist spots, budget breakdown, booking tips
│     Agent       │
└─────────────────┘
```

Built with **LangGraph** `StateGraph` — supports conditional routing, parallel edges, and PostgreSQL-backed checkpointing.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Groq — Llama 3.3 70B Versatile |
| **Agent Framework** | LangGraph + LangChain |
| **Flight Search** | SerpAPI (Google Flights engine) |
| **Hotel Search** | Tavily AI |
| **Memory / Checkpointing** | PostgreSQL via `langgraph-checkpoint-postgres` |
| **Web UI** | Streamlit |
| **Language** | Python 3.12+ |

---

## 📁 Project Structure

```
aero-voyage/
├── main.py              # LangGraph graph definition, all agents, CLI entry point
├── streamlit_app.py     # Streamlit web UI (Luxury Aviation Terminal theme)
├── frontend.py          # Additional frontend components
├── tools/
│   ├── flight.py        # SerpAPI Google Flights wrapper
│   └── tavily.py        # Tavily web search wrapper
├── requirements.txt
├── .env                 # API keys (not committed — see .env setup below)
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/satyam-1605/aero-voyage.git
cd aero-voyage
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the root directory:

```env
# Groq API Key — https://console.groq.com
GROQ_API_KEY=your_groq_api_key

# SerpAPI Key — https://serpapi.com
SERPAPI_KEY=your_serpapi_key

# Tavily API Key — https://tavily.com
TAVILY_API_KEY=your_tavily_api_key

# PostgreSQL connection string
DATABASE_URL=postgresql://user:password@localhost:5432/travel_db
```

### 5. Set up PostgreSQL

Make sure you have a running PostgreSQL instance. The app auto-creates required checkpointing tables on first run.

```bash
# Quick setup using Docker
docker run --name travel-pg \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=travel_db \
  -p 5432:5432 -d postgres
```

---

## 🚀 Running the App

### Streamlit Web UI *(Recommended)*

```bash
streamlit run streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### CLI Mode

```bash
python main.py
```

Available commands inside the CLI:

| Command | Description |
|---|---|
| `/new` | Start a fresh travel planning session |
| `/history` | List all past sessions |
| `/load <n>` | Resume a specific past session |
| `/help` | Show all available commands |
| `/exit` | Quit the application |

---

## 💬 Example Usage

Just describe your trip naturally — the assistant handles the rest:

- *"Plan a trip from Delhi to Tokyo in June with a budget of 1,50,000 rupees"*
- *"I want to go to Bali from Mumbai next month, round trip, budget 80k"*
- *"Find me flights to Paris from Hyderabad for December"*

If any detail is missing, the assistant will pause and ask you directly.

---

## 🔑 API Keys Reference

| Service | Where to get it | Used for |
|---|---|---|
| **Groq** | [console.groq.com](https://console.groq.com) | LLM inference (free tier available) |
| **SerpAPI** | [serpapi.com](https://serpapi.com) | Google Flights + airport autocomplete |
| **Tavily** | [tavily.com](https://tavily.com) | Hotel & travel web search |
| **PostgreSQL** | Self-hosted or [Supabase](https://supabase.com) / [Railway](https://railway.app) | Conversation memory & session persistence |

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

<p align="center">Built with ❤️ using LangGraph, Groq &amp; Streamlit</p>
