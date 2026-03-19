"""
Shared dependencies for the FastAPI application.
Provides DB connection and pipeline state management.
"""

import sqlite3
import os
import threading
from typing import Optional

from config.settings import DB_PATH, DATA_DIR
from contracts import (
    PipelineProgress, PipelineStatus, PipelineStats, StreamingProgress,
)

# ── Database connection ──────────────────────────────

_conn = None
_lock = threading.Lock()


def get_db_path() -> str:
    db_full_path = os.path.join(DATA_DIR, "..", DB_PATH) if not os.path.isabs(DB_PATH) else DB_PATH
    return os.path.normpath(db_full_path)


def get_db() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            db_full_path = get_db_path()
            os.makedirs(os.path.dirname(db_full_path), exist_ok=True)
            _conn = sqlite3.connect(db_full_path, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
        return _conn


def close_db():
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


# ── Pipeline state (shared across threads) ──────────

class PipelineState:
    """Thread-safe pipeline execution state."""

    def __init__(self):
        self._lock = threading.Lock()
        self.progress: PipelineProgress = PipelineProgress(
            status=PipelineStatus.IDLE,
            current_step="",
            step_number=0,
            total_steps=0,
            progress_pct=0.0,
        )
        self.stats: Optional[PipelineStats] = None
        self.streaming: StreamingProgress = StreamingProgress(
            processed=0, total=0, pct=0.0, falls=0, anomalies=0, patients=0,
        )
        self.is_running: bool = False

    def update_progress(self, progress: PipelineProgress):
        with self._lock:
            self.progress = progress

    def update_stats(self, stats: PipelineStats):
        with self._lock:
            self.stats = stats

    def update_streaming(self, streaming: StreamingProgress):
        with self._lock:
            self.streaming = streaming

    def get_progress(self) -> PipelineProgress:
        with self._lock:
            return self.progress

    def get_stats(self) -> Optional[PipelineStats]:
        with self._lock:
            return self.stats

    def get_streaming(self) -> StreamingProgress:
        with self._lock:
            return self.streaming


# Singleton pipeline state
pipeline_state = PipelineState()


# ── Ask Your Data history ────────────────────────────

_ask_history: list[dict] = []
_ask_lock = threading.Lock()


def add_ask_history(entry: dict):
    with _ask_lock:
        _ask_history.append(entry)


def get_ask_history_list() -> list[dict]:
    with _ask_lock:
        return list(_ask_history)


# ── Correction history ───────────────────────────────

_correction_history: list[dict] = []
_correction_lock = threading.Lock()


def add_correction_history(entry: dict):
    with _correction_lock:
        _correction_history.append(entry)


def get_correction_history_list() -> list[dict]:
    with _correction_lock:
        return list(_correction_history)


# ── Helper to convert sqlite3.Row to dict ────────────

def rows_to_dicts(rows: list[object]) -> list[dict]:
    """Convert a list of sqlite3.Row objects to a list of dicts."""
    return [dict(row) for row in rows]
