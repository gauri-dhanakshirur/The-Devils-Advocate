# Devil's Advocate — Webapp Integration Guide

## Overview

The Devil's Advocate webapp provides a persistent research history dashboard that syncs with the browser extension. It allows you to:

- **View all past research sessions** with full details
- **Track pages analyzed** across all sessions
- **Review counter-perspectives** and curated sources
- **Mark pages as citations** for later reference
- **Track which counter-opinion sources you've visited**
- **View global statistics** (total sessions, pages, bias scores)

---

## Architecture

```
Browser Extension (Chrome)
         │
         │ (syncs on session end)
         ▼
FastAPI Backend (Port 8000)
         │
         ├─ /analyze (analysis pipeline)
         ├─ /webapp/* (webapp API routes)
         └─ /history (webapp UI)
         │
         ▼
SQLite Database (devils_advocate.db)
         │
         ├─ sessions
         ├─ pages
         ├─ counter_perspectives
         └─ sources
```

---

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This includes the new `aiofiles` dependency for static file serving.

### 2. Start the Backend

```bash
python main.py
```

The server will start on `http://localhost:8000`.

### 3. Access the Webapp

Open your browser and navigate to:

```
http://localhost:8000/history
```

Or click the **"View Research History"** button in the extension popup.

---

## Features

### 📊 Global Statistics Dashboard

- **Total Sessions**: Number of research sessions completed
- **Pages Analyzed**: Total pages processed across all sessions
- **Total Time**: Cumulative research time
- **Average Bias Score**: Mean bias score across all sessions

### 📚 Session History

Each session card shows:
- Research topic (user-defined or auto-extracted)
- Date and time started
- Duration
- Bias score (0-10 scale with visual meter)
- Pages analyzed, approved, and skipped

Click any session to view full details.

### 🔍 Session Detail View

**Research Trajectory**
- Topic and bias score
- Opinions summary
- Session duration and stats

**Pages Analyzed**
- List of all pages visited during the session
- Click any page to open in a new tab
- "Add Citation" button to mark important pages

**Citations**
- Pages you've marked as key citations
- Optional notes for each citation
- Quick access to cited sources

**Counter-Perspectives**
- All counter-arguments generated during the session
- Linked to real-world sources
- Click sources to visit (automatically tracked)

### 📝 Citation Management

1. Click "Add Citation" on any analyzed page
2. Add an optional note (e.g., "Key study on AI bias")
3. Citations appear in a dedicated section
4. Export citations for research papers (coming soon)

### 🔗 Source Tracking

- All counter-opinion sources are tracked
- System records when you visit a source
- Helps measure engagement with opposing viewpoints

---

## API Endpoints

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webapp/sync-session` | POST | Sync session from extension to database |
| `/webapp/end-session/{id}` | POST | Mark session as ended |
| `/webapp/sessions` | GET | Get all sessions (paginated) |
| `/webapp/session/{id}` | GET | Get session details |
| `/webapp/session/{id}` | DELETE | Delete a session |

### Citations & Sources

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webapp/citation` | POST | Mark a page as citation |
| `/webapp/source/{id}/visited` | POST | Mark source as visited |

### Statistics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webapp/stats` | GET | Get global statistics |

---

## Database Schema

### `sessions` Table

```sql
- id (INTEGER PRIMARY KEY)
- session_id (TEXT UNIQUE)
- topic (TEXT)
- user_topic (TEXT)
- started_at (INTEGER)
- ended_at (INTEGER)
- duration_seconds (INTEGER)
- bias_score (REAL)
- opinions_summary (TEXT)
- guardrail_triggered (INTEGER)
- stats_analyzed (INTEGER)
- stats_approved (INTEGER)
- stats_skipped (INTEGER)
```

### `pages` Table

```sql
- id (INTEGER PRIMARY KEY)
- session_id (TEXT FK)
- url (TEXT)
- title (TEXT)
- topic (TEXT)
- bias_score (REAL)
- summary (TEXT)
- stance_vector (TEXT JSON)
- analyzed_at (INTEGER)
- is_counter_opinion (INTEGER)
- is_citation (INTEGER)
- citation_note (TEXT)
```

### `counter_perspectives` Table

```sql
- id (INTEGER PRIMARY KEY)
- session_id (TEXT FK)
- topic (TEXT)
- viewpoint (TEXT)
```

### `sources` Table

```sql
- id (INTEGER PRIMARY KEY)
- session_id (TEXT FK)
- counter_perspective_id (INTEGER FK)
- url (TEXT)
- title (TEXT)
- summary (TEXT)
- perspective (TEXT)
- credibility (TEXT)
- visited (INTEGER)
- visited_at (INTEGER)
```

---

## Extension Integration

### Automatic Sync

When you **end a research session** in the extension:

1. Extension calls `/webapp/end-session/{id}`
2. Extension calls `/webapp/sync-session` with full session data
3. Backend stores everything in SQLite
4. Session appears in webapp immediately

### Manual Sync (Future)

A "Save Session" button will allow syncing active sessions without ending them.

---

## Data Flow Example

```
User ends session in extension
         │
         ▼
storage.js → stopSession()
         │
         ├─ Calls syncSessionToBackend()
         │  ├─ POST /webapp/end-session/{id}
         │  └─ POST /webapp/sync-session (full payload)
         │
         ▼
webapp_routes.py → sync_session()
         │
         ├─ Creates/updates session record
         ├─ Adds pages
         ├─ Adds counter perspectives
         └─ Adds sources
         │
         ▼
database.py → SQLite operations
         │
         ▼
Webapp UI refreshes → shows new session
```

---

## Troubleshooting

### Webapp shows "No Sessions Yet"

- Make sure you've **ended at least one session** in the extension
- Check browser console for sync errors
- Verify backend is running on `http://localhost:8000`

### Sessions not syncing

- Check extension console: `chrome://extensions` → Devil's Advocate → Inspect views: service worker
- Look for sync errors in the console
- Verify backend is reachable: `curl http://localhost:8000/`

### Database errors

- Delete `devils_advocate.db` to reset (WARNING: loses all history)
- Check file permissions on the database file
- Ensure SQLite is available (comes with Python)

---

## Future Enhancements

- [ ] Export citations as BibTeX/APA/MLA
- [ ] Bias trend charts over time
- [ ] Topic clustering visualization
- [ ] Search across all sessions
- [ ] Session tagging and filtering
- [ ] Share sessions via link
- [ ] Multi-user support with authentication
- [ ] Cloud sync (optional)

---

## File Structure

```
The-Devils-Advocate/
├── database.py                  # SQLite database layer
├── webapp_routes.py             # FastAPI routes for webapp
├── webapp/
│   ├── static/
│   │   ├── webapp.css          # Webapp styles
│   │   └── webapp.js           # Webapp JavaScript
│   └── templates/
│       └── index.html          # Main webapp template
├── extension/
│   └── storage.js              # Updated with sync logic
└── devils_advocate.db          # SQLite database (auto-created)
```

---

## Development

### Running in Dev Mode

```bash
python main.py
```

FastAPI auto-reload is enabled by default.

### Testing the Sync

1. Start a session in the extension
2. Browse a few pages
3. End the session
4. Check webapp at `http://localhost:8000/history`
5. Session should appear immediately

### Debugging

- Backend logs: Check terminal where `python main.py` is running
- Extension logs: `chrome://extensions` → Inspect service worker
- Database inspection: Use SQLite browser or `sqlite3 devils_advocate.db`

---

## Production Deployment

### Using Docker

```bash
docker-compose up --build
```

The webapp will be available at `http://localhost:8000/history`.

### Environment Variables

No additional env vars needed. The webapp uses the same `.env` file as the backend.

---

## Security Notes

- **Local-only by default**: Webapp runs on `localhost:8000`
- **No authentication**: Anyone with access to localhost can view sessions
- **CORS enabled**: Extension can communicate with backend
- **SQLite database**: Stored locally, not encrypted

For production use, consider:
- Adding authentication (JWT, OAuth)
- Using PostgreSQL instead of SQLite
- Enabling HTTPS
- Restricting CORS origins

---

## Support

For issues or questions:
1. Check the main README.md
2. Review backend logs
3. Inspect extension console
4. Open an issue on GitHub

---

**Powered by Llama 3 + SerpAPI + FastAPI + SQLite**
