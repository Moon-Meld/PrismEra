"""PrismEra SQLite Session & Spectrum Profile Store.

Provides persistent SQLite storage for multi-student applicant profiles,
conversation histories, HITL review states, and version snapshots across sessions.
"""

from __future__ import annotations
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from prismera.state import StudentSpectrumProfile, create_initial_spectrum_profile

logger = logging.getLogger("PrismEraSessionStore")

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_SESSION_SQLITE_PATH = DEFAULT_DATA_DIR / "session_store.sqlite"


class SessionStore:
    """SQLite-backed multi-student profile and session persistence engine."""

    def __init__(self, sqlite_path: Optional[Union[str, Path]] = None):
        self.sqlite_path = Path(sqlite_path) if sqlite_path else DEFAULT_SESSION_SQLITE_PATH
        if str(self.sqlite_path) != ":memory:":
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with foreign keys and dict-like rows enabled."""
        conn = sqlite3.connect(str(self.sqlite_path), timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize SQLite database tables and indexes."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    student_profile TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    pending_human_review TEXT,
                    active_agent TEXT,
                    routing_decision TEXT,
                    luminary_thought TEXT,
                    task_briefing TEXT,
                    latest_response TEXT,
                    metadata TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_updated_at 
                ON sessions(updated_at DESC);
            """)
            conn.commit()

    @staticmethod
    def _derive_session_name(session_id: str, profile: Dict[str, Any], custom_name: Optional[str] = None) -> str:
        """Synthesize an intuitive student profile title."""
        if custom_name and custom_name.strip():
            return custom_name.strip()

        undergrad = profile.get("undergrad_name")
        major = profile.get("major")
        tier = profile.get("undergrad_tier")

        if undergrad and major:
            return f"{undergrad} · {major} 光谱档案"
        elif undergrad:
            return f"{undergrad} 学员档案"
        elif tier and major:
            return f"{tier} ({major}) 档案"
        elif tier:
            return f"{tier} 学员档案"
        
        short_id = session_id[:8] if len(session_id) >= 8 else session_id
        return f"学员档案 ({short_id})"

    def save_session(
        self,
        session_id: str,
        state: Dict[str, Any],
        name: Optional[str] = None
    ) -> None:
        """Upsert session state into SQLite."""
        if not session_id:
            return

        profile = state.get("student_profile") or create_initial_spectrum_profile()
        messages = state.get("messages") or []
        metadata = dict(state.get("metadata") or {})
        metadata["thread_id"] = session_id

        now = datetime.now(timezone.utc).isoformat()

        # Check existing name if not explicitly passed
        existing_name = None
        created_at = now
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT name, created_at FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cur.fetchone()
            if row:
                existing_name = row["name"]
                created_at = row["created_at"]

        # Determine resolved name
        if name and name.strip():
            resolved_name = name.strip()
        elif metadata.get("name") and metadata["name"].strip():
            resolved_name = metadata["name"].strip()
        elif existing_name and not existing_name.startswith("学员档案 ("):
            resolved_name = existing_name
        else:
            resolved_name = self._derive_session_name(session_id, profile, existing_name)

        metadata["name"] = resolved_name

        profile_json = json.dumps(profile, ensure_ascii=False, default=str)
        messages_json = json.dumps(messages, ensure_ascii=False, default=str)
        metadata_json = json.dumps(metadata, ensure_ascii=False, default=str)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO sessions (
                    session_id, name, created_at, updated_at,
                    student_profile, messages, pending_human_review,
                    active_agent, routing_decision, luminary_thought,
                    task_briefing, latest_response, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    name = excluded.name,
                    updated_at = excluded.updated_at,
                    student_profile = excluded.student_profile,
                    messages = excluded.messages,
                    pending_human_review = excluded.pending_human_review,
                    active_agent = excluded.active_agent,
                    routing_decision = excluded.routing_decision,
                    luminary_thought = excluded.luminary_thought,
                    task_briefing = excluded.task_briefing,
                    latest_response = excluded.latest_response,
                    metadata = excluded.metadata;
            """, (
                session_id,
                resolved_name,
                created_at,
                now,
                profile_json,
                messages_json,
                state.get("pending_human_review"),
                state.get("active_agent"),
                state.get("routing_decision"),
                state.get("luminary_thought"),
                state.get("task_briefing"),
                state.get("latest_response"),
                metadata_json,
            ))
            conn.commit()

    def load_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load raw state data from SQLite for a session."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cur.fetchone()
            if not row:
                return None

            try:
                profile_data = json.loads(row["student_profile"])
            except Exception:
                profile_data = {}

            # Merge with default profile to ensure schema completeness
            full_profile = create_initial_spectrum_profile()
            full_profile.update(profile_data)

            try:
                messages_data = json.loads(row["messages"])
            except Exception:
                messages_data = []

            try:
                meta_data = json.loads(row["metadata"])
            except Exception:
                meta_data = {}

            meta_data["name"] = row["name"]
            meta_data["thread_id"] = row["session_id"]

            return {
                "session_id": row["session_id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "student_profile": full_profile,
                "messages": messages_data,
                "pending_human_review": row["pending_human_review"],
                "active_agent": row["active_agent"],
                "routing_decision": row["routing_decision"],
                "luminary_thought": row["luminary_thought"],
                "task_briefing": row["task_briefing"],
                "latest_response": row["latest_response"],
                "metadata": meta_data,
            }

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Retrieve list of all student sessions with summary metadata."""
        summaries: List[Dict[str, Any]] = []
        with self._get_connection() as conn:
            cur = conn.execute("""
                SELECT session_id, name, created_at, updated_at,
                       student_profile, messages, pending_human_review,
                       active_agent, routing_decision
                FROM sessions
                ORDER BY updated_at DESC
            """)
            rows = cur.fetchall()
            for r in rows:
                try:
                    profile = json.loads(r["student_profile"])
                except Exception:
                    profile = {}

                try:
                    messages = json.loads(r["messages"])
                except Exception:
                    messages = []

                summaries.append({
                    "session_id": r["session_id"],
                    "name": r["name"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "turns": len(messages),
                    "undergrad_name": profile.get("undergrad_name"),
                    "undergrad_tier": profile.get("undergrad_tier"),
                    "major": profile.get("major"),
                    "gpa_raw": profile.get("gpa_raw"),
                    "target_regions": profile.get("target_regions", []),
                    "sop_stage": profile.get("sop_stage", 1),
                    "shortlisted_count": len(profile.get("shortlisted_programs") or []),
                    "has_sop_draft": bool(profile.get("sop_draft")),
                    "target_prof_count": len(profile.get("target_professors") or []),
                    "pending_human_review": r["pending_human_review"],
                })

        return summaries

    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Rename an existing student session."""
        new_name = new_name.strip()
        if not new_name:
            return False

        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.execute(
                "UPDATE sessions SET name = ?, updated_at = ? WHERE session_id = ?",
                (new_name, now, session_id)
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_session(self, session_id: str) -> bool:
        """Delete a student session from SQLite."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()
            return cur.rowcount > 0

    def create_session(
        self,
        session_id: Optional[str] = None,
        name: Optional[str] = None,
        initial_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a fresh student session and persist immediately."""
        sid = session_id or f"prism_{uuid.uuid4().hex[:8]}"
        profile = create_initial_spectrum_profile()
        if initial_profile:
            profile.update(initial_profile)

        resolved_name = name or self._derive_session_name(sid, profile)
        initial_state = {
            "messages": [],
            "student_profile": profile,
            "active_agent": None,
            "routing_decision": None,
            "luminary_thought": None,
            "task_briefing": None,
            "latest_response": None,
            "pending_human_review": None,
            "metadata": {"thread_id": sid, "name": resolved_name}
        }

        self.save_session(sid, initial_state, name=resolved_name)
        return self.load_session_data(sid)  # type: ignore


# Global singleton instance
_GLOBAL_SESSION_STORE: Optional[SessionStore] = None


def get_session_store(sqlite_path: Optional[Union[str, Path]] = None) -> SessionStore:
    """Retrieve or initialize the global SessionStore singleton."""
    global _GLOBAL_SESSION_STORE
    if _GLOBAL_SESSION_STORE is None or (sqlite_path and Path(sqlite_path) != _GLOBAL_SESSION_STORE.sqlite_path):
        _GLOBAL_SESSION_STORE = SessionStore(sqlite_path=sqlite_path)
    return _GLOBAL_SESSION_STORE
