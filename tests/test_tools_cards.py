import json
import pytest
from openalgernon_mcp.db import init_db, get_connection


@pytest.fixture
def db_with_material(tmp_path):
    db_path = str(tmp_path / "study.db")
    init_db(db_path)

    content_dir = tmp_path / "content"
    content_dir.mkdir()
    ch1 = content_dir / "ch1.md"
    ch1.write_text("# Chapter 1\nThis is content about RAG.")

    local_path = str(tmp_path)
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO materials (slug, name, local_path, algernonspec) VALUES (?, ?, ?, ?)",
        ("test-mat", "Test Material", local_path, "1"),
    )

    import yaml
    (tmp_path / "algernon.yaml").write_text(yaml.dump({
        "algernonspec": "1",
        "name": "Test Material",
        "content": [{"title": "Chapter 1", "path": "content/ch1.md", "type": "text"}],
    }))
    conn.commit()
    conn.close()
    return db_path, local_path


def test_get_material_content_returns_text(db_with_material):
    db_path, _ = db_with_material
    from openalgernon_mcp.tools.cards import get_material_content_impl
    result = get_material_content_impl("test-mat", db_path=db_path)
    assert "Chapter 1" in result["content"]
    assert result["slug"] == "test-mat"


def test_create_deck(db_with_material):
    db_path, _ = db_with_material
    from openalgernon_mcp.tools.cards import create_deck_impl
    result = create_deck_impl("test-mat", "Test Deck", db_path=db_path)
    assert "deck_id" in result
    assert result["deck_id"] > 0


def test_save_cards(db_with_material):
    db_path, _ = db_with_material
    from openalgernon_mcp.tools.cards import create_deck_impl, save_cards_impl
    deck_result = create_deck_impl("test-mat", "Test Deck", db_path=db_path)
    deck_id = deck_result["deck_id"]

    cards = [
        {"type": "flashcard", "front": "What is RAG?", "back": "Retrieval-Augmented Generation", "tags": ["N1"]},
        {"type": "dissertative", "front": "Explain RAG.", "back": "Long answer.", "tags": ["N1"]},
    ]
    result = save_cards_impl(deck_id, cards, db_path=db_path)
    assert result["saved"] == 2

    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) AS n FROM cards WHERE deck_id = ?", (deck_id,)).fetchone()["n"]
    state_count = conn.execute(
        "SELECT COUNT(*) AS n FROM card_state WHERE card_id IN (SELECT id FROM cards WHERE deck_id = ?)",
        (deck_id,)
    ).fetchone()["n"]
    conn.close()
    assert count == 2
    assert state_count == 2
