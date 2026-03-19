import sqlite3
import pytest
from openalgernon_mcp.db import init_db, get_connection


def test_init_db_creates_tables(tmp_path):
    db_path = tmp_path / "study.db"
    init_db(str(db_path))
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    )
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    assert "materials" in tables
    assert "decks" in tables
    assert "cards" in tables
    assert "card_state" in tables
    assert "reviews" in tables


def test_init_db_idempotent(tmp_path):
    db_path = str(tmp_path / "study.db")
    init_db(db_path)
    init_db(db_path)  # must not raise


def test_get_connection_returns_row_factory(tmp_path):
    db_path = str(tmp_path / "study.db")
    init_db(db_path)
    conn = get_connection(db_path)
    row = conn.execute("SELECT 1 AS val").fetchone()
    assert row["val"] == 1
    conn.close()
