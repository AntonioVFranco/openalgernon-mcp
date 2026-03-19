"""Card generation tool implementations."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from openalgernon_mcp.db import DEFAULT_DB_PATH, get_connection


def get_material_content_impl(
    slug: str,
    page: int = 0,
    page_size: int = 5,
    db_path: str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Return paginated Markdown content of a material."""
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT local_path, name FROM materials WHERE slug = ?", (slug,)
    ).fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"Material '{slug}' not installed.")

    local_path = row["local_path"]
    yaml_path = Path(local_path) / "algernon.yaml"
    with open(yaml_path) as f:
        raw = yaml.safe_load(f)

    items = raw.get("content", [])
    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    page_items = items[page * page_size:(page + 1) * page_size]

    blocks = []
    for item in page_items:
        file_path = Path(local_path) / item["path"]
        if file_path.exists():
            text = file_path.read_text()
            blocks.append(f"## {item['title']}\n\n{text}")

    return {
        "slug": slug,
        "name": row["name"],
        "content": "\n\n---\n\n".join(blocks),
        "page": page,
        "total_pages": total_pages,
        "items_this_page": len(page_items),
    }


def create_deck_impl(
    slug: str,
    name: str,
    db_path: str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Create a deck for a material. Returns the deck_id."""
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT id FROM materials WHERE slug = ?", (slug,)
    ).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Material '{slug}' not installed.")
    cursor = conn.execute(
        "INSERT INTO decks (material_id, name) VALUES (?, ?)",
        (row["id"], name),
    )
    deck_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"deck_id": deck_id, "name": name, "slug": slug}


def save_cards_impl(
    deck_id: int,
    cards: list[dict[str, Any]],
    db_path: str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Save generated cards to a deck and initialize their FSRS state."""
    conn = get_connection(db_path)
    row = conn.execute("SELECT id FROM decks WHERE id = ?", (deck_id,)).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Deck {deck_id} not found.")

    saved = 0
    for card in cards:
        cursor = conn.execute(
            """INSERT INTO cards (deck_id, type, front, back, tags, source_title)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                deck_id,
                card["type"],
                card["front"],
                card["back"],
                json.dumps(card.get("tags", [])),
                card.get("source_title"),
            ),
        )
        card_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO card_state (card_id) VALUES (?)",
            (card_id,),
        )
        saved += 1

    conn.commit()
    conn.close()
    return {"saved": saved, "deck_id": deck_id}
