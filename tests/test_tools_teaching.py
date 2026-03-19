"""Tests for teaching engine MCP tools."""

import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from openalgernon_mcp.db import init_db
from openalgernon_mcp.tools.teaching import (
    ingest_course_impl,
    get_roadmap_impl,
    start_lesson_impl,
    submit_response_impl,
    get_teaching_profile_impl,
)


class TestGetTeachingProfile(unittest.TestCase):
    def test_returns_math_profile(self):
        result = get_teaching_profile_impl("math")
        self.assertIn("profile", result)
        self.assertIn("Mathematics", result["profile"])

    def test_returns_cs_profile(self):
        result = get_teaching_profile_impl("cs")
        self.assertIn("Computer Science", result["profile"])

    def test_raises_on_unknown_discipline(self):
        with self.assertRaises(ValueError):
            get_teaching_profile_impl("physics")


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
        self.assertEqual(result["module_id"], "module-01")
        self.assertEqual(result["topic_id"], "topic-01-01")

    def test_lesson_status_is_active(self):
        result = start_lesson_impl(
            module_id="module-01",
            topic_id="topic-01-01",
            topic_name="Transformers",
            discipline="ai-engineering",
            db_path=self.db_path,
        )
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT status FROM lesson_state WHERE id = ?", (result["lesson_id"],)
        ).fetchone()
        conn.close()
        self.assertEqual(row[0], "active")
