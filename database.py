"""
Devil's Advocate — Database Layer
SQLite database for persistent session storage and history tracking.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager

logger = logging.getLogger("database")

DB_PATH = "devils_advocate.db"


class Database:
    """Handles all database operations for session persistence."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_email TEXT DEFAULT '',
                    topic TEXT,
                    user_topic TEXT,
                    started_at INTEGER NOT NULL,
                    ended_at INTEGER,
                    duration_seconds INTEGER,
                    bias_score REAL,
                    opinions_summary TEXT,
                    guardrail_triggered INTEGER DEFAULT 0,
                    stats_analyzed INTEGER DEFAULT 0,
                    stats_approved INTEGER DEFAULT 0,
                    stats_skipped INTEGER DEFAULT 0,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)

            # Migrate: add user_email column if it doesn't exist yet
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN user_email TEXT DEFAULT ''")
            except Exception:
                pass  # Column already exists
            
            # Pages table (analyzed pages in sessions)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    topic TEXT,
                    bias_score REAL,
                    summary TEXT,
                    stance_vector TEXT,
                    analyzed_at INTEGER NOT NULL,
                    is_counter_opinion INTEGER DEFAULT 0,
                    is_citation INTEGER DEFAULT 0,
                    citation_note TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            
            # Counter perspectives table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS counter_perspectives (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    viewpoint TEXT,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            
            # Sources table (curated links from Librarian)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    counter_perspective_id INTEGER,
                    url TEXT NOT NULL,
                    title TEXT,
                    summary TEXT,
                    perspective TEXT,
                    credibility TEXT,
                    visited INTEGER DEFAULT 0,
                    visited_at INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    FOREIGN KEY (counter_perspective_id) REFERENCES counter_perspectives(id) ON DELETE SET NULL
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_session ON pages(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_counter_session ON counter_perspectives(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sources_session ON sources(session_id)")
            
            logger.info("Database initialized successfully")
    
    # ── Session Operations ──────────────────────────────────────────────
    
    def create_session(self, session_data: dict) -> int:
        """Create a new session record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (
                    session_id, user_email, topic, user_topic, started_at, bias_score,
                    opinions_summary, guardrail_triggered
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_data.get("session_id"),
                session_data.get("user_email", ""),
                session_data.get("topic", ""),
                session_data.get("user_topic", ""),
                session_data.get("started_at", int(datetime.now().timestamp() * 1000)),
                session_data.get("bias_score", 5.0),
                session_data.get("opinions_summary", ""),
                1 if session_data.get("guardrail_triggered") else 0
            ))
            return cursor.lastrowid
    
    def update_session(self, session_id: str, updates: dict):
        """Update session with latest data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            set_clauses = []
            values = []
            
            if "topic" in updates:
                set_clauses.append("topic = ?")
                values.append(updates["topic"])
            if "user_topic" in updates:
                set_clauses.append("user_topic = ?")
                values.append(updates["user_topic"])
            if "bias_score" in updates:
                set_clauses.append("bias_score = ?")
                values.append(updates["bias_score"])
            if "opinions_summary" in updates:
                set_clauses.append("opinions_summary = ?")
                values.append(updates["opinions_summary"])
            if "guardrail_triggered" in updates:
                set_clauses.append("guardrail_triggered = ?")
                values.append(1 if updates["guardrail_triggered"] else 0)
            if "stats_analyzed" in updates:
                set_clauses.append("stats_analyzed = ?")
                values.append(updates["stats_analyzed"])
            if "stats_approved" in updates:
                set_clauses.append("stats_approved = ?")
                values.append(updates["stats_approved"])
            if "stats_skipped" in updates:
                set_clauses.append("stats_skipped = ?")
                values.append(updates["stats_skipped"])
            if "user_email" in updates:
                set_clauses.append("user_email = ?")
                values.append(updates["user_email"])
            
            if set_clauses:
                values.append(session_id)
                cursor.execute(f"""
                    UPDATE sessions 
                    SET {', '.join(set_clauses)}
                    WHERE session_id = ?
                """, values)
    
    def end_session(self, session_id: str):
        """Mark session as ended."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = int(datetime.now().timestamp() * 1000)
            cursor.execute("""
                UPDATE sessions 
                SET ended_at = ?,
                    duration_seconds = (? - started_at) / 1000
                WHERE session_id = ?
            """, (now, now, session_id))
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve a session by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_sessions(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """Get all sessions ordered by most recent."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions 
                ORDER BY started_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def get_sessions_for_user(self, user_email: str, limit: int = 50, offset: int = 0) -> List[dict]:
        """Get sessions belonging to a specific user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions
                WHERE user_email = ?
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
            """, (user_email, limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def get_global_stats_for_user(self, user_email: str) -> dict:
        """Get statistics for a specific user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM sessions WHERE user_email = ?", (user_email,))
            total_sessions = cursor.fetchone()["total"]
            cursor.execute("""
                SELECT COUNT(*) as total FROM pages
                WHERE session_id IN (SELECT session_id FROM sessions WHERE user_email = ?)
            """, (user_email,))
            total_pages = cursor.fetchone()["total"]
            cursor.execute("""
                SELECT SUM(duration_seconds) as total FROM sessions
                WHERE user_email = ? AND duration_seconds IS NOT NULL
            """, (user_email,))
            total_time = cursor.fetchone()["total"] or 0
            cursor.execute("""
                SELECT AVG(bias_score) as avg FROM sessions
                WHERE user_email = ? AND bias_score IS NOT NULL
            """, (user_email,))
            avg_bias = cursor.fetchone()["avg"] or 5.0
            return {
                "total_sessions": total_sessions,
                "total_pages": total_pages,
                "total_time_seconds": int(total_time),
                "avg_bias_score": round(avg_bias, 1)
            }
    
    def delete_session(self, session_id: str):
        """Delete a session and all related data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    
    # ── Page Operations ─────────────────────────────────────────────────
    
    def add_page(self, session_id: str, page_data: dict) -> int:
        """Add an analyzed page to a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pages (
                    session_id, url, title, topic, bias_score, summary,
                    stance_vector, analyzed_at, is_counter_opinion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                page_data.get("url"),
                page_data.get("title"),
                page_data.get("topic"),
                page_data.get("bias_score"),
                page_data.get("summary", ""),
                json.dumps(page_data.get("stance_vector", [])),
                page_data.get("analyzed_at", int(datetime.now().timestamp() * 1000)),
                1 if page_data.get("is_counter_opinion") else 0
            ))
            return cursor.lastrowid
    
    def get_session_pages(self, session_id: str) -> List[dict]:
        """Get all pages for a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pages 
                WHERE session_id = ? 
                ORDER BY analyzed_at ASC
            """, (session_id,))
            pages = []
            for row in cursor.fetchall():
                page = dict(row)
                if page.get("stance_vector"):
                    try:
                        page["stance_vector"] = json.loads(page["stance_vector"])
                    except:
                        page["stance_vector"] = []
                pages.append(page)
            return pages
    
    def mark_as_citation(self, page_id: int, note: str = ""):
        """Mark a page as a citation."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pages 
                SET is_citation = 1, citation_note = ?
                WHERE id = ?
            """, (note, page_id))
    
    def get_citations(self, session_id: str) -> List[dict]:
        """Get all citations for a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pages 
                WHERE session_id = ? AND is_citation = 1
                ORDER BY analyzed_at ASC
            """, (session_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ── Counter Perspectives & Sources ──────────────────────────────────
    
    def add_counter_perspective(self, session_id: str, cp_data: dict) -> int:
        """Add a counter perspective."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO counter_perspectives (session_id, topic, viewpoint)
                VALUES (?, ?, ?)
            """, (session_id, cp_data.get("topic"), cp_data.get("viewpoint")))
            return cursor.lastrowid
    
    def add_source(self, session_id: str, source_data: dict, cp_id: Optional[int] = None) -> int:
        """Add a curated source."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sources (
                    session_id, counter_perspective_id, url, title, summary,
                    perspective, credibility
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                cp_id,
                source_data.get("url"),
                source_data.get("title"),
                source_data.get("summary", ""),
                source_data.get("perspective", "Neutral"),
                source_data.get("credibility", "Medium")
            ))
            return cursor.lastrowid
    
    def mark_source_visited(self, source_id: int):
        """Mark a source as visited."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = int(datetime.now().timestamp() * 1000)
            cursor.execute("""
                UPDATE sources 
                SET visited = 1, visited_at = ?
                WHERE id = ?
            """, (now, source_id))
    
    def get_session_counter_perspectives(self, session_id: str) -> List[dict]:
        """Get all counter perspectives with their sources."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM counter_perspectives 
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (session_id,))
            
            perspectives = []
            for row in cursor.fetchall():
                cp = dict(row)
                
                # Get sources for this counter perspective
                cursor.execute("""
                    SELECT * FROM sources 
                    WHERE counter_perspective_id = ?
                    ORDER BY id ASC
                """, (cp["id"],))
                cp["sources"] = [dict(s) for s in cursor.fetchall()]
                perspectives.append(cp)
            
            return perspectives
    
    def get_session_sources(self, session_id: str) -> List[dict]:
        """Get all sources for a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sources 
                WHERE session_id = ?
                ORDER BY id ASC
            """, (session_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ── Statistics ──────────────────────────────────────────────────────
    
    def get_global_stats(self) -> dict:
        """Get overall statistics across all sessions."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM sessions")
            total_sessions = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) as total FROM pages")
            total_pages = cursor.fetchone()["total"]
            cursor.execute("SELECT SUM(duration_seconds) as total FROM sessions WHERE duration_seconds IS NOT NULL")
            total_time = cursor.fetchone()["total"] or 0
            cursor.execute("SELECT AVG(bias_score) as avg FROM sessions WHERE bias_score IS NOT NULL")
            avg_bias = cursor.fetchone()["avg"] or 5.0
            return {
                "total_sessions": total_sessions,
                "total_pages": total_pages,
                "total_time_seconds": int(total_time),
                "avg_bias_score": round(avg_bias, 1)
            }


# Global database instance
db = Database()
