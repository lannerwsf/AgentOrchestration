#!/usr/bin/env python3
"""Validate that all GitHub Actions workflow files use pinned commit SHAs.

This script checks every YAML workflow file under .github/workflows/ and
fails if any step references a third-party action by a mutable tag (e.g.,
``uses: actions/checkout@v4``) instead of an immutable commit SHA
(``uses: actions/checkout@<full-40-char-sha>``).

Mutable tags can be moved or force-pushed after the fact, reducing the
integrity of CI/CD pipelines. Using full commit SHAs guarantees that the
action version running in CI is exactly the version that was reviewed.

Exit codes:
    0  – all external action references are pinned to full SHAs
    1  – at least one external action reference uses a mutable tag
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# Regex that matches a ``uses:`` directive with a tag reference.
# We match the full reference and capture three groups:
#   1. Everything before the @
#   2. The tag name or partial SHA
#   3. Everything after
#
# A valid pin looks like:
#   uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
#
# A mutable (unpinned) reference looks like:
#   uses: actions/checkout@v4
#   uses: actions/setup-python@v5
#
# We exclude local action references (./path/to/action) and Docker
# references (docker://...) since those are not consumed from the
# GitHub Marketplace.
USES_RE = re.compile(
    r"""
    (?P<prefix>^\s*-\s+uses:\s+)
    (?P<action>[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)
    @
    (?P<ref>[^\s#]+)
    """,
    re.MULTILINE | re.VERBOSE,
)

# A full commit SHA is 40 hex characters.
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


def check_workflow(path: Path) -> list[str]:
    """Return a list of error messages for *path*."""
    errors: list[str] = []
    text = path.read_text()

    for match in USES_RE.finditer(text):
        ref = match.group("ref").strip()
        action = match.group("action")

        # Skip first-party actions within the same repository.
        if action.startswith("./"):
            continue

        # Allow Docker references (docker://).
        if action.startswith("docker://"):
            continue

        if not SHA40_RE.match(ref):
            errors.append(
                f"{path.name}: {action}@{ref} is mutable – "
                f"pin to a full 40-character commit SHA"
            )

    return errors


def main() -> int:
    if not WORKFLOWS_DIR.is_dir():
        print(f"Workflows directory not found: {WORKFLOWS_DIR}", file=sys.stderr)
        return 0

    all_errors: list[str] = []

    for yml_file in sorted(WORKFLOWS_DIR.glob("*.yml")):
        errors = check_workflow(yml_file)
        if errors:
            all_errors.extend(errors)

    if all_errors:
        print("❌ Action pinning check FAILED:\n", file=sys.stderr)
        for err in all_errors:
            print(f"   • {err}", file=sys.stderr)
        print(
            "\nTo fix, replace the mutable tag with the full 40-character "
            "commit SHA.\n"
            "Example:\n"
            "   uses: actions/checkout@v4\n"
            "   → uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5\n",
            file=sys.stderr,
        )
        return 1

    print("✅ All external action references are pinned to full commit SHAs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
