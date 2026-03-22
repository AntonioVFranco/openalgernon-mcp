<img width="1798" height="707" alt="opalg-mcp-logo" src="https://github.com/user-attachments/assets/f631cf75-b1e8-46ca-b280-03f0bce056d0" />

# openalgernon-mcp

MCP server for the [OpenAlgernon](https://github.com/AntonioVFranco/openalgernon)
study platform. Exposes OpenAlgernon tools to any MCP-compatible client:
claude.ai, Claude Desktop, and Claude Code.

## Requirements

- Python 3.11+ (managed automatically by `uvx`)
- sqlite3 (pre-installed on macOS and Ubuntu)
- git

## Install

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "openalgernon": {
      "command": "uvx",
      "args": ["openalgernon-mcp"]
    }
  }
}
```

### Claude Code

Add to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "openalgernon": {
      "command": "uvx",
      "args": ["openalgernon-mcp"]
    }
  }
}
```

## Shared database

The MCP server uses `~/.openalgernon/data/study.db` — the same database as
the Claude Code installation. Materials installed via MCP are available in
Claude Code and vice versa.

## Tools

| Tool | Description |
|------|-------------|
| `list_materials` | List installed study materials |
| `install_material` | Install from GitHub (`github:author/repo`) |
| `remove_material` | Remove a material and its cards |
| `get_material_info` | Details about a material |
| `get_material_content` | Paginated Markdown content for card generation |
| `create_deck` | Create a study deck |
| `save_cards` | Save generated cards to a deck |
| `get_due_cards` | Get cards due for FSRS review |
| `score_card` | Update FSRS state (1=Again, 3=Good) |
| `get_progress` | Study statistics and retention rate |

## Prompts

- `review [slug]` — FSRS review session
- `study <slug>` — Generate cards then review
- `feynman <slug>` — Feynman technique session

## Development

```bash
git clone https://github.com/AntonioVFranco/openalgernon-mcp
cd openalgernon-mcp
pip install -e . pytest
pytest tests/ -v
```
