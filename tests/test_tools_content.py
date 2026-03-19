import sqlite3
import pytest
from openalgernon_mcp.db import init_db, get_connection


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "study.db")
    init_db(db_path)
    return db_path


def insert_material(db_path, slug="test-mat", name="Test Material", local_path="/tmp/test"):
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO materials (slug, name, local_path, algernonspec) VALUES (?, ?, ?, ?)",
        (slug, name, local_path, "1"),
    )
    conn.commit()
    conn.close()


def test_list_materials_empty(db):
    from openalgernon_mcp.tools.content import list_materials_impl
    result = list_materials_impl(db)
    assert result == []


def test_list_materials_returns_installed(db):
    insert_material(db)
    from openalgernon_mcp.tools.content import list_materials_impl
    result = list_materials_impl(db)
    assert len(result) == 1
    assert result[0]["slug"] == "test-mat"


def test_get_material_info_not_found(db):
    from openalgernon_mcp.tools.content import get_material_info_impl
    with pytest.raises(ValueError, match="not installed"):
        get_material_info_impl("nonexistent", db)


def test_get_material_info_found(db):
    insert_material(db)
    from openalgernon_mcp.tools.content import get_material_info_impl
    result = get_material_info_impl("test-mat", db)
    assert result["name"] == "Test Material"


def test_remove_material_not_found(db):
    from openalgernon_mcp.tools.content import remove_material_impl
    with pytest.raises(ValueError, match="not installed"):
        remove_material_impl("nonexistent", db)


def test_remove_material_deletes(db):
    insert_material(db)
    from openalgernon_mcp.tools.content import remove_material_impl
    remove_material_impl("test-mat", db)
    conn = get_connection(db)
    row = conn.execute("SELECT id FROM materials WHERE slug = 'test-mat'").fetchone()
    conn.close()
    assert row is None
