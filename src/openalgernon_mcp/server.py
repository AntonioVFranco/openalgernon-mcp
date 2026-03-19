from mcp.server.fastmcp import FastMCP

mcp = FastMCP("openalgernon")

from openalgernon_mcp.tools.content import (
    list_materials_impl,
    get_material_info_impl,
    remove_material_impl,
)


@mcp.tool()
def list_materials() -> list[dict]:
    """List all installed OpenAlgernon study materials."""
    return list_materials_impl()


@mcp.tool()
def get_material_info(slug: str) -> dict:
    """Get details about an installed material: version, author, card count, last review."""
    return get_material_info_impl(slug)


@mcp.tool()
def remove_material(slug: str) -> dict:
    """Remove an installed material and all its cards from the database."""
    return remove_material_impl(slug)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
