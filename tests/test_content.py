import os
import pytest
from unittest.mock import patch, MagicMock
from openalgernon_mcp.content import (
    parse_github_ref,
    load_algernon_yaml,
    validate_manifest,
    AlgernonManifest,
    AlgernonValidationError,
)


def test_parse_github_ref_valid():
    result = parse_github_ref("github:author/repo-name")
    assert result == ("author", "repo-name")


def test_parse_github_ref_invalid():
    with pytest.raises(ValueError, match="Expected format"):
        parse_github_ref("author/repo")


def test_load_algernon_yaml(tmp_path):
    yaml_content = """
algernonspec: "1"
name: Test Material
content:
  - title: Chapter 1
    path: content/ch1.md
    type: text
"""
    (tmp_path / "algernon.yaml").write_text(yaml_content)
    manifest = load_algernon_yaml(str(tmp_path))
    assert manifest["name"] == "Test Material"
    assert len(manifest["content"]) == 1


def test_validate_manifest_valid(tmp_path):
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "ch1.md").write_text("# Chapter 1")
    raw = {
        "algernonspec": "1",
        "name": "Test Material",
        "content": [{"title": "Ch1", "path": "content/ch1.md", "type": "text"}],
    }
    manifest = validate_manifest(raw, str(tmp_path))
    assert manifest.name == "Test Material"
    assert manifest.algernonspec == "1"


def test_validate_manifest_missing_name():
    with pytest.raises(AlgernonValidationError, match="name"):
        validate_manifest(
            {"algernonspec": "1", "content": [{"title": "x", "path": "x.md", "type": "text"}]},
            "/any",
        )


def test_validate_manifest_wrong_version():
    with pytest.raises(AlgernonValidationError, match="algernonspec"):
        validate_manifest(
            {"algernonspec": "2", "name": "x", "content": []},
            "/any",
        )


def test_validate_manifest_missing_content():
    with pytest.raises(AlgernonValidationError, match="content"):
        validate_manifest(
            {"algernonspec": "1", "name": "x", "content": []},
            "/any",
        )
