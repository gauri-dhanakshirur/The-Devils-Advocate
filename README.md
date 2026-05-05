# 🔥 Devil's Advocate

**A multi-agent AI system that dismantles confirmation bias.**

Submit any research text, article, or claim — and Devil's Advocate will coordinate 4 specialized AI agents to identify the core stance, expose blind spots, search for real counter-narrative sources, and synthesize a compelling Devil's Advocate perspective.

## Architecture

```
┌─────────────────────────────────────────────┐
│          Chrome Extension (Frontend)         │
│  • Right-click context menu                  │
│  • Popup with text input                     │
│  • Floating analysis panel on any page       │
└──────────────────┬──────────────────────────┘
                   │ POST /analyze
                   ▼
┌─────────────────────────────────────────────┐
│        FastAPI Gateway (localhost:8000)       │
│                                              │
│  ┌───────────┐  ┌──────────┐  ┌───────────┐ │
│  │  Stance   │→ │  Bias    │→ │ Researcher│ │
│  │  Agent    │  │  Agent   │  │  Agent    │ │
│  └───────────┘  └──────────┘  └───────────┘ │
│        │              │             │        │
│        └──────┬───────┘─────────────┘        │
│               ▼                              │
│       ┌──────────────┐                       │
│       │ Orchestrator │ → Final Synthesis     │
│       └──────────────┘                       │
└─────────────────────────────────────────────┘
         │                    │
    Groq (Llama-3)       SerpAPI
```

## Quick Start

### 1. Install Dependencies

```bash
cd The-Devils-Advocate
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit the `.env` file with your actual keys:

```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxx      # Get from https://console.groq.com
SERPAPI_API_KEY=xxxxxxxxxxxxxxx      # Get from https://serpapi.com
```

### 3. Start the Gateway

```bash
python main.py
```

You should see:
```
✅ All API keys loaded successfully.
🚀 Devil's Advocate Gateway running on http://0.0.0.0:8000
```

### 4. Load the Chrome Extension

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `extension/` folder

### 5. Use It

- **Option A**: Click the 🔥 extension icon → paste text → click "Analyze & Challenge"
- **Option B**: Highlight text on any webpage → right-click → "Devil's Advocate — Challenge This"

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check, shows configured keys |
| `/analyze` | POST | Full 4-agent Devil's Advocate pipeline |
| `/quick-stance` | POST | Lightweight stance-only analysis |

### Example cURL

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "AI will replace all software engineers within 5 years..."}'
```

## Docker Deployment

```bash
docker-compose up --build
```

## Tech Stack

- **LLM**: Llama-3 via Groq (ultra-fast inference)
- **Search**: SerpAPI (Google search results)
- **Backend**: FastAPI + Uvicorn
- **Frontend**: Chrome Extension (Manifest V3)
- **Optional**: Pinecone (vector memory for research sessions)
