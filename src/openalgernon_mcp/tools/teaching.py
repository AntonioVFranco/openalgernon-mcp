"""Teaching engine tool implementations for OpenAlgernon MCP server."""

from __future__ import annotations

import json
import sqlite3
from html.parser import HTMLParser
from typing import Optional
import urllib.request
import urllib.error

from openalgernon_mcp.db import DEFAULT_DB_PATH, get_connection
from openalgernon_mcp.profiles import get_profile


class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML to plain text extractor."""

    def __init__(self) -> None:
        super().__init__()
        self._texts: list[str] = []
        self._skip_tags = {"script", "style", "nav", "footer", "header"}
        self._current_skip: int = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._skip_tags:
            self._current_skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags and self._current_skip > 0:
            self._current_skip -= 1

    def handle_data(self, data: str) -> None:
        if self._current_skip == 0:
            text = data.strip()
            if text:
                self._texts.append(text)

    def get_text(self) -> str:
        return " ".join(self._texts)


def _fetch_url_text(url: str, max_chars: int = 8000) -> tuple[str, str]:
    """Fetch a URL and return (title, body_text).

    Args:
        url: The URL to fetch.
        max_chars: Maximum characters of body text to return.

    Returns:
        Tuple of (title, body_text). Title may be empty string on failure.

    Raises:
        ValueError: If the URL does not start with https://.
        urllib.error.URLError: If the fetch fails.
    """
    if not url.startswith("https://"):
        raise ValueError(f"Only https:// URLs are supported, got: {url!r}")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "OpenAlgernon-MCP/1.0 (course ingestion)"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:  # noqa: S310
        raw = response.read(200_000).decode("utf-8", errors="replace")

    extractor = _HTMLTextExtractor()
    extractor.feed(raw)
    body = extractor.get_text()[:max_chars]

    # Extract title from <title> tag
    title = ""
    start = raw.lower().find("<title>")
    end = raw.lower().find("</title>")
    if start != -1 and end != -1:
        title = raw[start + 7 : end].strip()

    return title, body


def ingest_course_impl(
    urls: list[str],
    db_path: str = DEFAULT_DB_PATH,
) -> dict:
    """Fetch course landing pages and store raw content for roadmap generation.

    Fetches each URL, extracts text, and stores in the roadmaps table as raw
    source content. Claude then analyzes this content to generate the roadmap.

    Args:
        urls: List of course landing page URLs (https:// only).
        db_path: Path to the SQLite database.

    Returns:
        Dict with roadmap_id, source_count, and source_previews for each URL.

    Raises:
        ValueError: If urls is empty or any URL does not start with https://.
    """
    if not urls:
        raise ValueError("urls must be a non-empty list")

    # Validate all URLs before fetching any
    for url in urls:
        if not url.startswith("https://"):
            raise ValueError(f"Only https:// URLs are supported, got: {url!r}")

    sources = []
    for url in urls:
        try:
            title, body = _fetch_url_text(url)
            sources.append({"url": url, "title": title, "text": body, "error": None})
        except (urllib.error.URLError, ValueError) as exc:
            sources.append({"url": url, "title": "", "text": "", "error": str(exc)})

    modules_json = json.dumps(
        {
            "status": "pending_analysis",
            "sources": [
                {"url": s["url"], "title": s["title"], "preview": s["text"][:500]}
                for s in sources
            ],
        }
    )

    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO roadmaps (discipline, source_urls, modules_json) VALUES (?, ?, ?)",
            ("unknown", json.dumps(urls), modules_json),
        )
        conn.commit()
        roadmap_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    finally:
        conn.close()

    return {
        "roadmap_id": roadmap_id,
        "source_count": len(sources),
        "sources_fetched": sum(1 for s in sources if s["error"] is None),
        "sources_failed": sum(1 for s in sources if s["error"] is not None),
        "source_previews": [
            {
                "url": s["url"],
                "title": s["title"],
                "preview": s["text"][:300],
                "error": s["error"],
            }
            for s in sources
        ],
        "note": (
            "Raw content stored. Call get_roadmap to retrieve content, "
            "analyze it, then update the roadmap with structured modules."
        ),
    }


def get_roadmap_impl(
    roadmap_id: int,
    db_path: str = DEFAULT_DB_PATH,
) -> dict:
    """Return a stored roadmap by ID.

    Args:
        roadmap_id: The roadmap's database ID.
        db_path: Path to the SQLite database.

    Returns:
        Dict with roadmap fields including modules_json parsed as a dict.

    Raises:
        ValueError: If roadmap_id is not found.
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, discipline, source_urls, modules_json, created_at "
            "FROM roadmaps WHERE id = ?",
            (roadmap_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise ValueError(f"Roadmap {roadmap_id} not found")

    return {
        "roadmap_id": row["id"],
        "discipline": row["discipline"],
        "source_urls": json.loads(row["source_urls"]),
        "modules": json.loads(row["modules_json"]),
        "created_at": row["created_at"],
    }


def start_lesson_impl(
    module_id: str,
    topic_id: str,
    topic_name: str,
    discipline: str,
    material_id: Optional[int] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> dict:
    """Create a lesson_state row and return lesson context.

    Args:
        module_id: The module identifier from the roadmap.
        topic_id: The topic identifier from the roadmap.
        topic_name: Human-readable name of the topic.
        discipline: One of 'math', 'cs', 'ai-engineering', 'english'.
        material_id: Optional reference to an installed material.
        db_path: Path to the SQLite database.

    Returns:
        Dict with lesson_id, module_id, topic_id, discipline, and teaching profile.
    """
    initial_plan = json.dumps(
        {
            "topic": topic_name,
            "discipline": discipline,
            "status": "initializing",
        }
    )

    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO lesson_state "
            "(material_id, module_id, topic_id, lesson_plan_json, technique_used, student_level) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (material_id, module_id, topic_id, initial_plan, "pending", "beginner"),
        )
        conn.commit()
        lesson_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    finally:
        conn.close()

    try:
        profile = get_profile(discipline)
    except ValueError:
        profile = f"No profile available for discipline '{discipline}'."

    return {
        "lesson_id": lesson_id,
        "module_id": module_id,
        "topic_id": topic_id,
        "topic_name": topic_name,
        "discipline": discipline,
        "teaching_profile": profile,
        "status": "active",
        "instructions": (
            "Use the teaching profile to guide your lesson. "
            "When the student responds, call submit_response with the lesson_id."
        ),
    }


def submit_response_impl(
    lesson_id: int,
    response_text: str,
    db_path: str = DEFAULT_DB_PATH,
) -> dict:
    """Store a student response and return the full comprehension history.

    Args:
        lesson_id: The lesson_state ID.
        response_text: The student's response text.
        db_path: Path to the SQLite database.

    Returns:
        Dict with the new log entry and full history for this lesson.

    Raises:
        ValueError: If lesson_id does not exist.
    """
    conn = get_connection(db_path)
    try:
        lesson = conn.execute(
            "SELECT id, lesson_plan_json, student_level FROM lesson_state WHERE id = ?",
            (lesson_id,),
        ).fetchone()

        if lesson is None:
            raise ValueError(f"Lesson {lesson_id} not found")

        conn.execute(
            "INSERT INTO comprehension_log (lesson_id, response_text, next_action) "
            "VALUES (?, ?, ?)",
            (lesson_id, response_text, "pending"),
        )
        conn.commit()
        log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        history = conn.execute(
            "SELECT id, response_text, score, misconception, next_action, logged_at "
            "FROM comprehension_log WHERE lesson_id = ? ORDER BY logged_at ASC",
            (lesson_id,),
        ).fetchall()
    finally:
        conn.close()

    return {
        "log_id": log_id,
        "lesson_id": lesson_id,
        "response_stored": True,
        "response_count": len(history),
        "history": [
            {
                "id": row["id"],
                "response_text": row["response_text"],
                "score": row["score"],
                "misconception": row["misconception"],
                "next_action": row["next_action"],
                "logged_at": row["logged_at"],
            }
            for row in history
        ],
        "instructions": (
            "Evaluate the response against the lesson objectives. "
            "Update next_action to: continue | deepen | pivot | advance. "
            "Use score_response_impl to set the score and next_action."
        ),
    }


def get_teaching_profile_impl(discipline: str) -> dict:
    """Return the pedagogical profile for a discipline.

    Args:
        discipline: One of 'math', 'cs', 'ai-engineering', 'english'.

    Returns:
        Dict with discipline and profile markdown text.

    Raises:
        ValueError: If the discipline is not recognized.
    """
    profile = get_profile(discipline)
    return {"discipline": discipline, "profile": profile}
