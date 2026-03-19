import pytest
from unittest.mock import patch
from pathlib import Path
from openalgernon_mcp.db import init_db, get_connection


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "study.db")
    init_db(db_path)
    return db_path


def test_install_material_registers_in_db(db, tmp_path):
    from openalgernon_mcp.tools.content import install_material_impl

    # Simulate a cloned repo with algernon.yaml and content file
    repo_dir = tmp_path / "materials" / "author-my-material"
    repo_dir.mkdir(parents=True)
    (repo_dir / "content").mkdir()
    (repo_dir / "content" / "ch1.md").write_text("# Chapter 1\nSome content.")
    (repo_dir / "algernon.yaml").write_text(
        "algernonspec: '1'\nname: My Material\nauthor: author\n"
        "content:\n  - title: Ch1\n    path: content/ch1.md\n    type: text\n"
    )

    with patch("openalgernon_mcp.tools.content.clone_or_update"):
        result = install_material_impl(
            "github:author/my-material",
            db_path=db,
            materials_root=str(tmp_path / "materials"),
        )

    assert result["slug"] == "author-my-material"
    conn = get_connection(db)
    row = conn.execute("SELECT slug, name FROM materials WHERE slug = 'author-my-material'").fetchone()
    conn.close()
    assert row is not None
    assert row["name"] == "My Material"
