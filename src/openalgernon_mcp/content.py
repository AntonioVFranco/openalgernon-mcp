"""Material installation and AlgernonSpec YAML parsing."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class AlgernonValidationError(ValueError):
    pass


@dataclass
class ContentItem:
    title: str
    path: str
    type: str


@dataclass
class AlgernonManifest:
    algernonspec: str
    name: str
    content: list[ContentItem]
    author: str | None = None
    version: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    license: str | None = None


def parse_github_ref(github_ref: str) -> tuple[str, str]:
    """Parse 'github:author/repo' into (author, repo).

    Raises ValueError if format is invalid.
    """
    if not github_ref.startswith("github:"):
        raise ValueError(f"Expected format 'github:author/repo', got: {github_ref}")
    path = github_ref[len("github:"):]
    parts = path.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Expected format 'github:author/repo', got: {github_ref}")
    return parts[0], parts[1]


def load_algernon_yaml(repo_path: str) -> dict[str, Any]:
    """Load and parse algernon.yaml from a repo directory.

    Raises FileNotFoundError if not present, yaml.YAMLError if invalid YAML.
    """
    yaml_path = Path(repo_path) / "algernon.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"algernon.yaml not found in {repo_path}")
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def validate_manifest(raw: dict[str, Any], repo_path: str) -> AlgernonManifest:
    """Validate a raw algernon.yaml dict and return an AlgernonManifest.

    Raises AlgernonValidationError on any rule violation.
    Rules per AlgernonSpec v1:
      1. algernonspec must be "1"
      2. name must be non-empty string
      3. content must be non-empty array
      4. each content item type must be "text"
      5. each content path must exist in the repo
    """
    spec = raw.get("algernonspec")
    if str(spec) != "1":
        raise AlgernonValidationError(
            f"algernonspec must be '1', got: {spec!r}"
        )

    name = raw.get("name")
    if not name or not isinstance(name, str):
        raise AlgernonValidationError("name must be a non-empty string")

    content_raw = raw.get("content")
    if not content_raw or not isinstance(content_raw, list):
        raise AlgernonValidationError("content must be a non-empty array")

    items: list[ContentItem] = []
    for item in content_raw:
        if item.get("type") != "text":
            raise AlgernonValidationError(
                f"content item type must be 'text', got: {item.get('type')!r}"
            )
        item_path = Path(repo_path) / item["path"]
        if not item_path.exists():
            raise AlgernonValidationError(
                f"content path does not exist: {item['path']}"
            )
        items.append(ContentItem(
            title=item["title"],
            path=item["path"],
            type=item["type"],
        ))

    return AlgernonManifest(
        algernonspec=str(spec),
        name=name,
        content=items,
        author=raw.get("author"),
        version=raw.get("version"),
        description=raw.get("description"),
        tags=raw.get("tags", []),
        license=raw.get("license"),
    )


def clone_or_update(github_url: str, dest_path: str) -> None:
    """Clone a GitHub repo or pull latest if already cloned.

    Args:
        github_url: Full HTTPS GitHub URL.
        dest_path: Local path to clone into.

    Raises:
        RuntimeError: If git command fails.
    """
    if Path(dest_path).joinpath(".git").exists():
        result = subprocess.run(
            ["git", "-C", dest_path, "pull", "--ff-only"],
            capture_output=True,
            text=True,
        )
    else:
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", github_url, dest_path],
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"git command failed:\n{result.stderr.strip()}"
        )
