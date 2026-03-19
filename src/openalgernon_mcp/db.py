"""SQLite database operations for OpenAlgernon MCP server."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Schema mirrors open-algernon/schema/study.sql
_SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS materials (
    id            INTEGER PRIMARY KEY,
    slug          TEXT    NOT NULL UNIQUE,
    name          TEXT    NOT NULL,
    author        TEXT,
    version       TEXT,
    repo_url      TEXT,
    local_path    TEXT    NOT NULL,
    algernonspec  TEXT    NOT NULL,
    installed_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS decks (
    id          INTEGER PRIMARY KEY,
    material_id INTEGER NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    topic       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cards (
    id           INTEGER PRIMARY KEY,
    deck_id      INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    type         TEXT    NOT NULL CHECK(type IN ('flashcard','dissertative','argumentative')),
    front        TEXT    NOT NULL,
    back         TEXT    NOT NULL,
    tags         TEXT    NOT NULL DEFAULT '[]',
    source_file  TEXT,
    source_title TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS card_state (
    card_id     INTEGER PRIMARY KEY REFERENCES cards(id) ON DELETE CASCADE,
    stability   REAL    NOT NULL DEFAULT 0.4,
    difficulty  REAL    NOT NULL DEFAULT 0.3,
    due_date    TEXT    NOT NULL DEFAULT (date('now')),
    last_review TEXT,
    reps        INTEGER NOT NULL DEFAULT 0,
    lapses      INTEGER NOT NULL DEFAULT 0,
    state       TEXT    NOT NULL DEFAULT 'new'
        CHECK(state IN ('new','learning','review','relearning'))
);

CREATE TABLE IF NOT EXISTS reviews (
    id             INTEGER PRIMARY KEY,
    card_id        INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    reviewed_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    grade          INTEGER NOT NULL CHECK(grade IN (1, 3)),
    response       TEXT,
    ai_feedback    TEXT,
    misconception  TEXT,
    scheduled_days REAL,
    elapsed_days   REAL
);

CREATE INDEX IF NOT EXISTS idx_card_state_due ON card_state(due_date);
CREATE INDEX IF NOT EXISTS idx_cards_deck     ON cards(deck_id);
CREATE INDEX IF NOT EXISTS idx_reviews_card   ON reviews(card_id);
"""

DEFAULT_DB_PATH = os.path.expanduser("~/.openalgernon/data/study.db")


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize the database schema. Idempotent."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return a connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
