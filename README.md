# 🔥 Devil's Advocate

**A multi-agent AI system that dismantles confirmation bias in real-time.**

Start a research session, browse articles normally, and Devil's Advocate will **automatically analyze every page you visit** — accumulating counter-perspectives, tracking your bias trajectory, and surfacing real-world sources that challenge your echo chamber.

![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-brightgreen?style=flat-square&logo=googlechrome)
![Python 3.12](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)
![Llama 3](https://img.shields.io/badge/LLM-Llama%203-orange?style=flat-square)

---

## 🧠 How It Works

```
User browses research articles with session active
                    │
                    ▼ (auto-extracts text from each page)
┌──────────────────────────────────────────────────────────────────┐
│                    FastAPI Gateway (Port 8000)                    │
│                                                                  │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────────┐  │
│  │  Agent 1     │ → │  Agent 2      │ → │  Agent 3             │  │
│  │  Gatekeeper  │   │  Bias Auditor │   │  Counter-Opinion     │  │
│  │              │   │              │   │  Architect           │  │
│  │  4-Level     │   │  Vector      │   │                      │  │
│  │  Safety Gate │   │  Clustering  │   │  Truth-Gating        │  │
│  │              │   │  Bias Score  │   │  Guardrail           │  │
│  └─────────────┘   └──────────────┘   └──────────┬───────────┘  │
│                                                    │             │
│                                        ┌───────────▼──────────┐  │
│                                        │  Agent 4             │  │
│                                        │  Retrieval &         │  │
│                                        │  Verification        │  │
│                                        │  (SerpAPI Search)    │  │
│                                        └──────────────────────┘  │
│                                                                  │
│  Counter-perspectives are merged with real source links          │
│  and accumulated across all pages in the session.                │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
         Extension popup shows accumulated
         session data, clickable counter-links,
         and evolving bias trajectory
```

### The 4-Agent Pipeline

| Agent | Role | Key Innovation |
|-------|------|----------------|
| **Gatekeeper** | Filters noise, blocks banking/social/shopping pages | 4-Level Safety Gate (URL → Keywords → Vector Similarity → LLM) |
| **Bias Auditor** | Calculates cumulative bias score (0–10) | Mathematical vector clustering — detects echo chambers |
| **Counter-Opinion Architect** | Generates 3–5 credible counter-perspectives | Truth-Gating Guardrail — refuses to fabricate conflict on objective facts |
| **Retrieval & Verification** | Finds real-world sources via Google Search | LLM-ranked results by credibility, perspective, and diversity |

---

## 🖥️ Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.10+ | [python.org/downloads](https://www.python.org/downloads/) |
| **pip** | Latest | Comes with Python |
| **Google Chrome** | Any modern version | For the browser extension |
| **Git** | Any | To clone the repository |

### API Keys (free tiers available)

| Key | Required | Get it from |
|-----|----------|-------------|
| `GROQ_API_KEY` | **Yes** | [console.groq.com](https://console.groq.com) |
| `SERPAPI_API_KEY` | **Yes** (for sources) | [serpapi.com](https://serpapi.com) |
| `PINECONE_API_KEY` | No (optional) | [pinecone.io](https://www.pinecone.io) |

---

## ⚡ Setup — macOS

### 1. Clone the repository

```bash
git clone https://github.com/gauri-dhanakshirur/The-Devils-Advocate.git
cd The-Devils-Advocate
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

Copy the example and fill in your keys:

```bash
cp .env.example .env
```

Then edit `.env`:

```bash
nano .env
```

```
GROQ_API_KEY=gsk_your_key_here
SERPAPI_API_KEY=your_key_here
PINECONE_API_KEY=              # optional
```

### 5. Start the backend server

```bash
python3 main.py
```

You should see:

```
✅ All API keys loaded successfully.
🚀 Devil's Advocate Gateway running on http://0.0.0.0:8000
```

### 6. Load the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in the top-right corner)
3. Click **Load unpacked**
4. Navigate to and select the `extension/` folder inside the project
5. The Devil's Advocate icon will appear in your toolbar

---

## ⚡ Setup — Windows

### 1. Clone the repository

Open **Command Prompt** or **PowerShell**:

```cmd
git clone https://github.com/gauri-dhanakshirur/The-Devils-Advocate.git
cd The-Devils-Advocate
```

### 2. Create a virtual environment (recommended)

```cmd
python -m venv venv
venv\Scripts\activate
```

> **Note:** If you get a "running scripts is disabled" error in PowerShell, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then try activating again.

### 3. Install dependencies

```cmd
pip install -r requirements.txt
```

### 4. Configure API keys

```cmd
copy .env.example .env
```

Open `.env` in any text editor (Notepad, VS Code, etc.) and fill in your keys:

```
GROQ_API_KEY=gsk_your_key_here
SERPAPI_API_KEY=your_key_here
PINECONE_API_KEY=
```

### 5. Start the backend server

```cmd
python main.py
```

You should see:

```
✅ All API keys loaded successfully.
🚀 Devil's Advocate Gateway running on http://0.0.0.0:8000
```

### 6. Load the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in the top-right corner)
3. Click **Load unpacked**
4. Navigate to and select the `extension\` folder inside the project
5. The Devil's Advocate icon will appear in your toolbar

---

## 🎯 How to Use

Devil's Advocate is **session-based** — it tracks your entire research session, not just one page.

### Step 1: Start a Session

Click the extension icon → Click **Start Research Session**.

### Step 2: Browse Normally

Open any research articles, news stories, or opinion pieces in your browser. The extension **automatically analyzes each page** in the background as you browse.

### Step 3: Check Your Session

Click the extension icon anytime to see:

- **Research Trajectory** — your current topic and cumulative bias score
- **Pages Analyzed** — list of every page processed in this session
- **Counter-Perspectives** — opposing viewpoints with clickable source links
- **Curated Sources** — real-world articles ranked by credibility
- **Session Stats** — pages analyzed, accepted, filtered, and session duration

### Step 4: Manually Analyze

You can also click **Analyze This Page** to immediately process the current tab.

### Step 5: End Session

Click **End Session** when you're done. All accumulated data resets.

---

## 🧪 Run Tests

**macOS:**
```bash
python3 test_pipeline.py
```

**Windows:**
```cmd
python test_pipeline.py
```

The test suite covers:
- Configuration validation
- Vector memory mathematics (bias scoring, cosine similarity)
- Gatekeeper Level 1–4 filtering (URL blacklist, keywords, vector similarity, LLM)
- Bias Auditor analysis
- Counter-Opinion generation + Truth Guardrail
- Full pipeline orchestration (end-to-end)
- Edge cases (Unicode, empty URLs, case sensitivity, whitespace)
- Live API health check and validation

---

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check — shows configured keys and server status |
| `/analyze` | POST | Full 4-agent pipeline with merged counter-perspectives |
| `/quick-bias` | POST | Lightweight — only Gatekeeper + Bias Auditor |

### Example Request

**macOS / Linux:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "AI will replace all software engineers within 5 years. The evidence is overwhelming that automation is accelerating.", "url": "https://techblog.com/ai-replaces-devs"}'
```

**Windows (PowerShell):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/analyze" -Method Post -ContentType "application/json" -Body '{"text": "AI will replace all software engineers within 5 years. The evidence is overwhelming that automation is accelerating.", "url": "https://techblog.com/ai-replaces-devs"}'
```

### Example Response

```json
{
  "error": false,
  "gatekeeper": {
    "status": "ACCEPTED",
    "overarching_topic": "AI Replacing Software Engineers",
    "stance_vector": [0.7, -0.3, 0.8]
  },
  "mirror": {
    "cumulative_bias_score": 7.2,
    "research_theme": "Impact of AI on Software Engineering Jobs"
  },
  "counter_perspectives": [
    {
      "topic": "AI as Augmentation, Not Replacement",
      "viewpoint": "Historical evidence suggests technology augments human work...",
      "sources": [
        {
          "title": "Why AI Won't Replace Developers",
          "url": "https://...",
          "credibility": "High"
        }
      ]
    }
  ],
  "guardrail_triggered": false,
  "synthesis": "Topic: AI Replacing Engineers | Bias: 7.2/10 (Echo Chamber) | 4 counter-perspectives",
  "elapsed_seconds": 3.21
}
```

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
```

The server will start on `http://localhost:8000`. Load the Chrome extension as described above.

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| **LLM** | Llama 3.1 via Groq (ultra-fast inference) |
| **Search** | SerpAPI (Google search results) |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | Chrome Extension (Manifest V3) |
| **Vector Memory** | In-memory (Pinecone optional) |

---

## 📁 Project Structure

```
The-Devils-Advocate/
├── main.py                          # FastAPI gateway server
├── config.py                        # Environment configuration
├── vector_memory.py                 # Vector storage & bias math
├── test_pipeline.py                 # Comprehensive test suite
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Docker image
├── docker-compose.yml               # Docker compose config
├── .env.example                     # Template for API keys
├── agents/
│   ├── base_agent.py                # Base class with Groq LLM
│   ├── orchestrator.py              # Lead orchestrator (pipeline)
│   ├── session_integrity_agent.py   # Agent 1: Gatekeeper
│   ├── bias_auditor_agent.py        # Agent 2: Mirror
│   ├── counter_opinion_agent.py     # Agent 3: Devil's Advocate
│   └── retrieval_verification_agent.py  # Agent 4: Librarian
└── extension/
    ├── manifest.json                # Chrome extension manifest (V3)
    ├── popup.html                   # Extension popup UI
    ├── popup.css                    # Dark theme styles
    ├── popup.js                     # Session-based popup logic
    ├── background.js                # Auto-scraping service worker
    ├── content.js                   # Page content extractor
    ├── storage.js                   # Chrome storage manager
    └── icons/                       # Extension icons
```

---

## ❓ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'dotenv'` | Run `pip install python-dotenv` |
| `GROQ_API_KEY is not configured` | Check your `.env` file has valid keys |
| Extension shows "Backend offline" | Make sure `python main.py` is running |
| `command not found: python` (macOS) | Use `python3` instead of `python` |
| PowerShell script execution error (Windows) | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Port 8000 already in use | Kill the existing process: macOS `lsof -ti:8000 \| xargs kill`, Windows `netstat -ano \| findstr :8000` then `taskkill /PID <PID> /F` |
| No curated sources appearing | Check your `SERPAPI_API_KEY` is valid and has remaining quota |
| Extension not auto-analyzing pages | Ensure you clicked **Start Research Session** first |
