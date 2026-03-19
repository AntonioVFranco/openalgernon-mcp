"""Content management tool implementations."""

from __future__ import annotations

import os
from typing import Any

from openalgernon_mcp.content import (
    clone_or_update,
    load_algernon_yaml,
    parse_github_ref,
    validate_manifest,
)
from openalgernon_mcp.db import DEFAULT_DB_PATH, get_connection

DEFAULT_MATERIALS_ROOT = os.path.expanduser("~/.openalgernon/materials")


def list_materials_impl(db_path: str = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT m.slug, m.name, m.author, m.version, m.installed_at,
                      COUNT(c.id) AS card_count
               FROM materials m
               LEFT JOIN decks d ON d.material_id = m.id
               LEFT JOIN cards c ON c.deck_id = d.id
               GROUP BY m.id
               ORDER BY m.installed_at DESC"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_material_info_impl(slug: str, db_path: str = DEFAULT_DB_PATH) -> dict[str, Any]:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM materials WHERE slug = ?", (slug,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Material '{slug}' not installed.")
        return dict(row)
    finally:
        conn.close()


def remove_material_impl(slug: str, db_path: str = DEFAULT_DB_PATH) -> dict[str, str]:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM materials WHERE slug = ?", (slug,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Material '{slug}' not installed.")
        conn.execute("DELETE FROM materials WHERE id = ?", (row["id"],))
        conn.commit()
        return {"status": "removed", "slug": slug}
    finally:
        conn.close()


def install_material_impl(
    github_ref: str,
    db_path: str = DEFAULT_DB_PATH,
    materials_root: str = DEFAULT_MATERIALS_ROOT,
) -> dict[str, Any]:
    """Clone a GitHub material repo and register it in the database."""
    author, repo = parse_github_ref(github_ref)
    slug = f"{author}-{repo}"
    repo_url = f"https://github.com/{author}/{repo}.git"
    dest = os.path.join(materials_root, slug)

    clone_or_update(repo_url, dest)

    raw = load_algernon_yaml(dest)
    manifest = validate_manifest(raw, dest)

    conn = get_connection(db_path)
    try:
        existing = conn.execute(
            "SELECT id FROM materials WHERE slug = ?", (slug,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE materials SET name=?, author=?, version=?, repo_url=?, local_path=?, algernonspec=?
                   WHERE slug=?""",
                (manifest.name, manifest.author, manifest.version, repo_url, dest, manifest.algernonspec, slug),
            )
        else:
            conn.execute(
                """INSERT INTO materials (slug, name, author, version, repo_url, local_path, algernonspec)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (slug, manifest.name, manifest.author, manifest.version, repo_url, dest, manifest.algernonspec),
            )

        conn.commit()
        return {"status": "installed", "slug": slug, "name": manifest.name}
    finally:
        conn.close()
