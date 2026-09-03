"""SQLite trace store — PS A2.6: the observable execution trace is the graded
artifact. Every request is persisted: route, ingestion warnings, tool calls,
statuses, latencies, model versions. No internal reasoning text (PS P10)."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .schemas import Trace, TraceEvent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    query_id    TEXT PRIMARY KEY,
    ts          REAL NOT NULL,
    query       TEXT NOT NULL,
    task        TEXT,
    tool        TEXT,
    status      TEXT,
    fallback    INTEGER,
    trace_json  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id    TEXT NOT NULL,
    t           REAL NOT NULL,
    step        TEXT NOT NULL,
    tool        TEXT,
    status      TEXT,
    message     TEXT,
    data_json   TEXT
);
"""


class TraceStore:
    def __init__(self, path: str | Path = "trace.db"):
        self.path = str(path)
        # check_same_thread=False: FastAPI runs sync endpoints in a threadpool
        # and the Streamlit app may call from a worker thread; all writes are
        # short and committed immediately (SQLite serialises them internally).
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def add_event(self, trace: Trace, step: str, status: str = "ok",
                  tool: str | None = None, message: str = "",
                  data: dict | None = None) -> TraceEvent:
        ev = TraceEvent(step=step, tool=tool, status=status,
                        message=message, data=data or {})
        trace.events.append(ev)
        self.conn.execute(
            "INSERT INTO events (query_id, t, step, tool, status, message, data_json)"
            " VALUES (?,?,?,?,?,?,?)",
            (trace.query_id, ev.t, step, tool, status, message,
             json.dumps(ev.data, default=str)),
        )
        self.conn.commit()
        return ev

    def save(self, trace: Trace, status: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO runs (query_id, ts, query, task, tool, status, fallback, trace_json)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (trace.query_id, trace.started_at, trace.query,
             trace.route.task.value if trace.route else None,
             trace.route.tool if trace.route else None,
             status, int(trace.route.fallback_used) if trace.route else 1,
             trace.model_dump_json()),
        )
        self.conn.commit()

    def get(self, query_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT trace_json FROM runs WHERE query_id = ?", (query_id,)
        ).fetchone()
        return json.loads(row["trace_json"]) if row else None

    def recent(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT query_id, ts, query, task, tool, status FROM runs"
            " ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()


def now() -> float:
    return time.time()
