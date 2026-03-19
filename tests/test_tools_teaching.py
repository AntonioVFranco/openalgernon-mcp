"""Tests for teaching engine MCP tools."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from openalgernon_mcp.db import init_db
from openalgernon_mcp.tools.teaching import (
    _fetch_url_text,
    get_roadmap_impl,
    get_teaching_profile_impl,
    ingest_course_impl,
    start_lesson_impl,
    submit_response_impl,
)


class TestGetTeachingProfile(unittest.TestCase):
    def test_math_profile_returned(self):
        result = get_teaching_profile_impl("math")
        self.assertEqual(result["discipline"], "math")
        self.assertIn("Mathematics", result["profile"])
        self.assertIn("Pedagogical approach", result["profile"])

    def test_cs_profile_returned(self):
        result = get_teaching_profile_impl("cs")
        self.assertIn("Computer Science", result["profile"])

    def test_ai_engineering_profile_returned(self):
        result = get_teaching_profile_impl("ai-engineering")
        self.assertIn("AI Engineering", result["profile"])

    def test_english_profile_returned(self):
        result = get_teaching_profile_impl("english")
        self.assertIn("English", result["profile"])

    def test_unknown_discipline_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_teaching_profile_impl("physics")
        self.assertIn("physics", str(ctx.exception))

    def test_profile_is_non_empty_string(self):
        for discipline in ("math", "cs", "ai-engineering", "english"):
            with self.subTest(discipline=discipline):
                result = get_teaching_profile_impl(discipline)
                self.assertIsInstance(result["profile"], str)
                self.assertGreater(len(result["profile"]), 100)


class TestFetchUrlText(unittest.TestCase):
    def test_rejects_non_https_url(self):
        with self.assertRaises(ValueError) as ctx:
            _fetch_url_text("http://example.com")
        self.assertIn("https://", str(ctx.exception))

    def test_rejects_file_url(self):
        with self.assertRaises(ValueError):
            _fetch_url_text("file:///etc/passwd")

    def test_successful_fetch_returns_title_and_body(self):
        mock_html = b"<html><head><title>Test Course</title></head><body><h1>Welcome</h1><p>Content here.</p></body></html>"

        class MockResponse:
            def read(self, n):
                return mock_html
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        with patch("urllib.request.urlopen", return_value=MockResponse()):
            title, body = _fetch_url_text("https://example.com")
        self.assertEqual(title, "Test Course")
        self.assertIn("Welcome", body)
        self.assertIn("Content here", body)


class TestIngestCourse(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.db_file.name
        init_db(self.db_path)

    def _mock_fetch(self, url: str, max_chars: int = 8000):
        return (f"Course Page for {url}", f"This course teaches many things about {url}.")

    def test_creates_roadmap_row(self):
        with patch(
            "openalgernon_mcp.tools.teaching._fetch_url_text", side_effect=self._mock_fetch
        ):
            result = ingest_course_impl(
                ["https://example.com/course"], db_path=self.db_path
            )
        self.assertIn("roadmap_id", result)
        self.assertIsInstance(result["roadmap_id"], int)
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["sources_fetched"], 1)
        self.assertEqual(result["sources_failed"], 0)

    def test_roadmap_stored_in_db(self):
        with patch(
            "openalgernon_mcp.tools.teaching._fetch_url_text", side_effect=self._mock_fetch
        ):
            result = ingest_course_impl(
                ["https://example.com/a", "https://example.com/b"],
                db_path=self.db_path,
            )
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT source_urls FROM roadmaps WHERE id = ?", (result["roadmap_id"],)
        ).fetchone()
        conn.close()
        urls = json.loads(row[0])
        self.assertEqual(len(urls), 2)

    def test_failed_fetch_recorded(self):
        def failing_fetch(url, max_chars=8000):
            import urllib.error
            raise urllib.error.URLError("connection refused")

        with patch(
            "openalgernon_mcp.tools.teaching._fetch_url_text", side_effect=failing_fetch
        ):
            result = ingest_course_impl(
                ["https://unreachable.example.com/course"], db_path=self.db_path
            )
        self.assertEqual(result["sources_failed"], 1)
        self.assertEqual(result["sources_fetched"], 0)
        self.assertIsNotNone(result["source_previews"][0]["error"])

    def test_empty_urls_raises(self):
        with self.assertRaises(ValueError):
            ingest_course_impl([], db_path=self.db_path)

    def test_non_https_url_raises(self):
        with self.assertRaises(ValueError):
            ingest_course_impl(["http://example.com"], db_path=self.db_path)


class TestGetRoadmap(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.db_file.name
        init_db(self.db_path)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO roadmaps (discipline, source_urls, modules_json) VALUES (?,?,?)",
            ("cs", '["https://example.com"]', '{"modules": []}'),
        )
        conn.commit()
        self.roadmap_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

    def test_returns_roadmap(self):
        result = get_roadmap_impl(self.roadmap_id, db_path=self.db_path)
        self.assertEqual(result["roadmap_id"], self.roadmap_id)
        self.assertEqual(result["discipline"], "cs")
        self.assertIsInstance(result["source_urls"], list)
        self.assertIsInstance(result["modules"], dict)

    def test_unknown_id_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_roadmap_impl(99999, db_path=self.db_path)
        self.assertIn("99999", str(ctx.exception))


class TestStartLesson(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.db_file.name
        init_db(self.db_path)

    def test_creates_lesson_state_row(self):
        result = start_lesson_impl(
            module_id="module-01",
            topic_id="topic-01-01",
            topic_name="Transformers",
            discipline="ai-engineering",
            db_path=self.db_path,
        )
        self.assertIn("lesson_id", result)
        self.assertIsInstance(result["lesson_id"], int)
        self.assertEqual(result["status"], "active")

    def test_lesson_row_in_db(self):
        result = start_lesson_impl(
            module_id="module-02",
            topic_id="topic-02-01",
            topic_name="Recursion",
            discipline="cs",
            db_path=self.db_path,
        )
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT module_id, topic_id, status, student_level FROM lesson_state WHERE id = ?",
            (result["lesson_id"],),
        ).fetchone()
        conn.close()
        self.assertEqual(row[0], "module-02")
        self.assertEqual(row[1], "topic-02-01")
        self.assertEqual(row[2], "active")
        self.assertEqual(row[3], "beginner")

    def test_includes_teaching_profile(self):
        result = start_lesson_impl(
            module_id="m", topic_id="t", topic_name="Fractions",
            discipline="math", db_path=self.db_path,
        )
        self.assertIn("teaching_profile", result)
        self.assertIn("Mathematics", result["teaching_profile"])

    def test_unknown_discipline_still_creates_lesson(self):
        result = start_lesson_impl(
            module_id="m", topic_id="t", topic_name="History",
            discipline="history", db_path=self.db_path,
        )
        self.assertIn("lesson_id", result)

    def test_returns_instructions(self):
        result = start_lesson_impl(
            module_id="m", topic_id="t", topic_name="X",
            discipline="cs", db_path=self.db_path,
        )
        self.assertIn("instructions", result)


class TestSubmitResponse(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.db_file.name
        init_db(self.db_path)
        lesson = start_lesson_impl(
            module_id="m", topic_id="t", topic_name="Topic",
            discipline="cs", db_path=self.db_path,
        )
        self.lesson_id = lesson["lesson_id"]

    def test_stores_response_in_comprehension_log(self):
        result = submit_response_impl(
            self.lesson_id, "My answer here.", db_path=self.db_path
        )
        self.assertTrue(result["response_stored"])
        self.assertEqual(result["response_count"], 1)
        self.assertEqual(len(result["history"]), 1)
        self.assertEqual(result["history"][0]["response_text"], "My answer here.")

    def test_second_response_appends_to_history(self):
        submit_response_impl(self.lesson_id, "First answer.", db_path=self.db_path)
        result = submit_response_impl(
            self.lesson_id, "Second answer.", db_path=self.db_path
        )
        self.assertEqual(result["response_count"], 2)
        self.assertEqual(len(result["history"]), 2)

    def test_initial_next_action_is_pending(self):
        result = submit_response_impl(
            self.lesson_id, "Answer.", db_path=self.db_path
        )
        self.assertEqual(result["history"][0]["next_action"], "pending")

    def test_unknown_lesson_raises(self):
        with self.assertRaises(ValueError) as ctx:
            submit_response_impl(99999, "Answer.", db_path=self.db_path)
        self.assertIn("99999", str(ctx.exception))

    def test_returns_instructions(self):
        result = submit_response_impl(self.lesson_id, "Answer.", db_path=self.db_path)
        self.assertIn("instructions", result)


if __name__ == "__main__":
    unittest.main()
