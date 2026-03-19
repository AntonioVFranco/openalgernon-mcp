from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import GetPromptResult, PromptMessage, TextContent

from openalgernon_mcp.db import init_db
from openalgernon_mcp.tools.content import (
    install_material_impl,
    list_materials_impl,
    get_material_info_impl,
    remove_material_impl,
)
from openalgernon_mcp.tools.cards import (
    get_material_content_impl,
    create_deck_impl,
    save_cards_impl,
)
from openalgernon_mcp.tools.study import (
    get_due_cards_impl,
    score_card_impl,
    get_progress_impl,
)

mcp = FastMCP("openalgernon")

# Ensure database exists on startup
init_db()


# --- Content management tools ---

@mcp.tool()
def install_material(github_ref: str) -> dict:
    """Install a study material from GitHub. Format: github:author/repo"""
    return install_material_impl(github_ref)


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


# --- Card generation tools ---

@mcp.tool()
def get_material_content(slug: str, page: int = 0) -> dict:
    """Get paginated Markdown content of a material for card generation. Call with page=0,1,2... until total_pages reached."""
    return get_material_content_impl(slug, page=page)


@mcp.tool()
def create_deck(slug: str, name: str) -> dict:
    """Create a new study deck for a material. Returns deck_id."""
    return create_deck_impl(slug, name)


@mcp.tool()
def save_cards(deck_id: int, cards: list[dict]) -> dict:
    """Save Claude-generated cards to a deck. Each card: {type, front, back, tags, source_title?}. Types: flashcard|dissertative|argumentative."""
    return save_cards_impl(deck_id, cards)


# --- Study tools ---

@mcp.tool()
def get_due_cards(slug: str | None = None) -> dict:
    """Get cards due for FSRS review. Pass slug to filter by material, or omit for all materials."""
    return get_due_cards_impl(slug=slug)


@mcp.tool()
def score_card(card_id: int, grade: int) -> dict:
    """Update FSRS state after reviewing a card. grade: 1=Again, 3=Good."""
    return score_card_impl(card_id, grade)


@mcp.tool()
def get_progress(slug: str | None = None) -> dict:
    """Get study progress statistics. Pass slug to filter by material."""
    return get_progress_impl(slug=slug)


# --- MCP Prompts ---

@mcp.prompt()
def review(slug: str | None = None) -> GetPromptResult:
    """Start an FSRS review session."""
    target = f"material '{slug}'" if slug else "all installed materials"
    return GetPromptResult(
        description=f"FSRS review session for {target}",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=(
                        f"Start an OpenAlgernon review session for {target}.\n\n"
                        "1. Call get_due_cards to fetch due cards.\n"
                        "2. For each card: show the front, wait for the user to respond, "
                        "show the back, ask 'Again (1) or Good (3)?', then call score_card.\n"
                        "3. After all cards, call get_progress and show a session summary.\n"
                        "Keep it focused and efficient."
                    ),
                ),
            )
        ],
    )


@mcp.prompt()
def study(slug: str) -> GetPromptResult:
    """Generate cards for a material (if needed) then start review."""
    return GetPromptResult(
        description=f"Study session for '{slug}'",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=(
                        f"Start an OpenAlgernon study session for '{slug}'.\n\n"
                        f"1. Call get_due_cards with slug='{slug}'.\n"
                        "2. If cards exist, go straight to review (same flow as the review prompt).\n"
                        "3. If no cards exist:\n"
                        f"   a. Call get_material_content(slug='{slug}', page=0) and repeat for all pages.\n"
                        "   b. Generate cards: 50% flashcard, 30% dissertative, 20% argumentative. "
                        "Tag all cards ['N1']. Target 20-30 cards per content block.\n"
                        f"   c. Call create_deck(slug='{slug}', name='{slug}') to get a deck_id.\n"
                        "   d. Call save_cards(deck_id, cards) to persist.\n"
                        "   e. Then start the review session.\n"
                    ),
                ),
            )
        ],
    )


@mcp.prompt()
def feynman(slug: str) -> GetPromptResult:
    """Feynman technique session on a material."""
    return GetPromptResult(
        description=f"Feynman technique session for '{slug}'",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=(
                        f"Run a Feynman technique study session for '{slug}'.\n\n"
                        f"1. Call get_material_content(slug='{slug}', page=0).\n"
                        "2. Pick one key concept from the content.\n"
                        "3. Ask the user to explain it in simple terms as if teaching a 12-year-old.\n"
                        "4. Identify gaps or misconceptions in their explanation.\n"
                        "5. Provide a precise correction and ask them to re-explain.\n"
                        "6. Repeat for 3-5 concepts from the material.\n"
                        "Focus on depth over breadth. Challenge vague answers."
                    ),
                ),
            )
        ],
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
