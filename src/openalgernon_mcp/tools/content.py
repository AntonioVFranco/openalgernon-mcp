"""Content management tool implementations."""

from __future__ import annotations

from typing import Any

from openalgernon_mcp.db import DEFAULT_DB_PATH, get_connection


def list_materials_impl(db_path: str = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT m.slug, m.name, m.author, m.version, m.installed_at,
                  COUNT(c.id) AS card_count
           FROM materials m
           LEFT JOIN decks d ON d.material_id = m.id
           LEFT JOIN cards c ON c.deck_id = d.id
           GROUP BY m.id
           ORDER BY m.installed_at DESC"""
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_material_info_impl(slug: str, db_path: str = DEFAULT_DB_PATH) -> dict[str, Any]:
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM materials WHERE slug = ?", (slug,)
    ).fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"Material '{slug}' not installed.")
    return dict(row)


def remove_material_impl(slug: str, db_path: str = DEFAULT_DB_PATH) -> dict[str, str]:
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT id FROM materials WHERE slug = ?", (slug,)
    ).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Material '{slug}' not installed.")
    conn.execute("DELETE FROM materials WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    return {"status": "removed", "slug": slug}
