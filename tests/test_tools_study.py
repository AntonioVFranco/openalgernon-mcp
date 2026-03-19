import json
import pytest
from datetime import date
from openalgernon_mcp.db import init_db, get_connection


@pytest.fixture
def db_with_cards(tmp_path):
    db_path = str(tmp_path / "study.db")
    init_db(db_path)
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO materials (slug, name, local_path, algernonspec) VALUES ('m', 'M', '/tmp', '1')"
    )
    conn.execute("INSERT INTO decks (material_id, name) VALUES (1, 'Deck')")
    for i in range(3):
        conn.execute(
            "INSERT INTO cards (deck_id, type, front, back, tags) VALUES (1, 'flashcard', ?, ?, '[]')",
            (f"Q{i}", f"A{i}"),
        )
        conn.execute("INSERT INTO card_state (card_id) VALUES (?)", (i + 1,))
    conn.commit()
    conn.close()
    return db_path


def test_get_due_cards_returns_due(db_with_cards):
    from openalgernon_mcp.tools.study import get_due_cards_impl
    result = get_due_cards_impl(db_path=db_with_cards)
    assert len(result["cards"]) == 3  # all new cards are due today


def test_get_due_cards_empty_after_future_schedule(db_with_cards):
    from openalgernon_mcp.tools.study import get_due_cards_impl
    conn = get_connection(db_with_cards)
    conn.execute("UPDATE card_state SET due_date = date('now', '+10 days')")
    conn.commit()
    conn.close()
    result = get_due_cards_impl(db_path=db_with_cards)
    assert len(result["cards"]) == 0


def test_score_card_again(db_with_cards):
    from openalgernon_mcp.tools.study import score_card_impl
    result = score_card_impl(1, 1, db_path=db_with_cards)
    assert result["state"] == "learning"
    assert result["next_interval"] == 1


def test_score_card_good(db_with_cards):
    from openalgernon_mcp.tools.study import score_card_impl
    result = score_card_impl(1, 3, db_path=db_with_cards)
    assert result["state"] == "review"
    assert result["next_interval"] >= 1


def test_score_card_invalid_grade(db_with_cards):
    from openalgernon_mcp.tools.study import score_card_impl
    with pytest.raises(ValueError, match="grade"):
        score_card_impl(1, 2, db_path=db_with_cards)


def test_get_progress(db_with_cards):
    from openalgernon_mcp.tools.study import get_progress_impl
    result = get_progress_impl(db_path=db_with_cards)
    assert result["total_cards"] == 3
    assert "due_today" in result
