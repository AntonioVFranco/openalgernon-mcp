"""Study session tool implementations (FSRS review, progress)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from openalgernon_mcp.db import DEFAULT_DB_PATH, get_connection
from openalgernon_mcp.fsrs import CardState, compute_next_state


def get_due_cards_impl(
    slug: str | None = None,
    limit: int = 50,
    db_path: str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Return cards due for review, optionally filtered by material slug."""
    conn = get_connection(db_path)
    query = """
        SELECT c.id, c.type, c.front, c.back, c.tags, c.source_title,
               c.deck_id, cs.stability, cs.reps, cs.state, cs.due_date
        FROM cards c
        JOIN card_state cs ON cs.card_id = c.id
        JOIN decks d ON d.id = c.deck_id
        JOIN materials m ON m.id = d.material_id
        WHERE cs.due_date <= date('now')
    """
    params: list[Any] = []
    if slug:
        query += " AND m.slug = ?"
        params.append(slug)
    query += " ORDER BY cs.due_date ASC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {
        "cards": [dict(row) for row in rows],
        "count": len(rows),
        "slug": slug,
    }


def score_card_impl(
    card_id: int,
    grade: int,
    db_path: str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Update FSRS state for a card after review."""
    if grade not in (1, 3):
        raise ValueError(f"grade must be 1 (Again) or 3 (Good), got: {grade}")

    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT stability, difficulty, reps, lapses, state, last_review FROM card_state WHERE card_id = ?",
        (card_id,),
    ).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Card {card_id} not found.")

    current = CardState(
        stability=row["stability"],
        difficulty=row["difficulty"],
        reps=row["reps"],
        lapses=row["lapses"],
        state=row["state"],
        last_review=row["last_review"],
    )

    if row["last_review"]:
        last_dt = datetime.fromisoformat(row["last_review"])
        elapsed = (datetime.now() - last_dt).total_seconds() / 86400
    else:
        elapsed = 0.0

    next_state = compute_next_state(current, grade, elapsed)

    conn.execute(
        f"""UPDATE card_state SET
            stability   = ?,
            difficulty  = ?,
            due_date    = date('now', '+' || ? || ' days'),
            last_review = datetime('now'),
            reps        = ?,
            lapses      = ?,
            state       = ?
          WHERE card_id = ?""",
        (
            next_state.stability,
            next_state.difficulty,
            next_state.next_interval,
            next_state.reps,
            next_state.lapses,
            next_state.state,
            card_id,
        ),
    )
    conn.execute(
        "INSERT INTO reviews (card_id, grade, scheduled_days, elapsed_days) VALUES (?, ?, ?, ?)",
        (card_id, grade, next_state.next_interval, round(elapsed, 2)),
    )
    conn.commit()
    conn.close()

    return {
        "card_id": card_id,
        "grade": grade,
        "state": next_state.state,
        "stability": round(next_state.stability, 3),
        "next_interval": next_state.next_interval,
    }


def get_progress_impl(
    slug: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Return study statistics, optionally filtered by material slug."""
    conn = get_connection(db_path)
    base = """FROM cards c
              JOIN card_state cs ON cs.card_id = c.id
              JOIN decks d ON d.id = c.deck_id
              JOIN materials m ON m.id = d.material_id"""
    where = "WHERE m.slug = ?" if slug else ""
    params = [slug] if slug else []

    total = conn.execute(f"SELECT COUNT(*) AS n {base} {where}", params).fetchone()["n"]
    due = conn.execute(
        f"SELECT COUNT(*) AS n {base} {where} {'AND' if where else 'WHERE'} cs.due_date <= date('now')",
        params,
    ).fetchone()["n"]

    review_params = [slug] if slug else []
    review_stats = conn.execute(
        f"""SELECT
              COUNT(*) AS total_reviews,
              SUM(CASE WHEN grade = 3 THEN 1 ELSE 0 END) AS good_reviews
            FROM reviews r
            JOIN cards c ON c.id = r.card_id
            JOIN decks d ON d.id = c.deck_id
            JOIN materials m ON m.id = d.material_id
            {"WHERE m.slug = ?" if slug else ""}""",
        review_params,
    ).fetchone()

    retention = None
    if review_stats["total_reviews"]:
        retention = round(review_stats["good_reviews"] / review_stats["total_reviews"], 3)

    conn.close()
    return {
        "total_cards": total,
        "due_today": due,
        "total_reviews": review_stats["total_reviews"] or 0,
        "retention_rate": retention,
        "slug": slug,
    }
