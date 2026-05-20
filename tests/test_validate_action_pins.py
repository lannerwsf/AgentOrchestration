"""Tests for the validate_action_pins script."""

import os
import tempfile
import textwrap
from pathlib import Path

from scripts.validate_action_pins import USES_RE, SHA40_RE, check_workflow


def _pinned_yml(content: str) -> Path:
    """Write *content* to a temp .yml file and return the Path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
    f.write(textwrap.dedent(content))
    f.close()
    return Path(f.name)


def test_sha40_re_valid():
    assert SHA40_RE.match("34e114876b0b11c390a56381ad16ebd13914f8d5")
    assert SHA40_RE.match("a26af69be951a213d495a4c3e4e4022e16d87065")
    assert SHA40_RE.match("37802adc94f370f7bcb16953c6d4d6f4339cf36e")


def test_sha40_re_invalid():
    assert not SHA40_RE.match("v4")
    assert not SHA40_RE.match("v5.6.0")
    assert not SHA40_RE.match("short")
    assert not SHA40_RE.match("")
    assert not SHA40_RE.match("34e114876b0b11c390a56381ad16ebd13914f8dXX")


def test_uses_re_matches_pinned():
    text = textwrap.dedent("""\
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
    """)
    matches = list(USES_RE.finditer(text))
    assert len(matches) == 1
    assert matches[0].group("ref") == "34e114876b0b11c390a56381ad16ebd13914f8d5"


def test_uses_re_matches_tag():
    text = textwrap.dedent("""\
      - uses: actions/checkout@v4
    """)
    matches = list(USES_RE.finditer(text))
    assert len(matches) == 1
    assert matches[0].group("ref") == "v4"
    assert not SHA40_RE.match(matches[0].group("ref"))


def test_check_workflow_pinned():
    """A fully pinned workflow should produce zero errors."""
    content = """\
      name: CI
      jobs:
        test:
          runs-on: ubuntu-latest
          steps:
            - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
            - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
            - uses: astral-sh/setup-uv@37802adc94f370f7bcb16953c6d4d6f4339cf36e
    """
    path = _pinned_yml(content)
    try:
        errors = check_workflow(path)
        assert errors == [], f"Expected no errors, got: {errors}"
    finally:
        os.unlink(str(path))


def test_check_workflow_tag_detected():
    """A workflow with a mutable tag should produce an error."""
    content = """\
      name: CI
      jobs:
        test:
          runs-on: ubuntu-latest
          steps:
            - uses: actions/checkout@v4
    """
    path = _pinned_yml(content)
    try:
        errors = check_workflow(path)
        assert len(errors) >= 1
        assert "mutable" in errors[0].lower()
    finally:
        os.unlink(str(path))


def test_check_workflow_mixed():
    """Mixed pinned/unpinned references should only flag the unpinned ones."""
    content = """\
      name: CI
      jobs:
        test:
          runs-on: ubuntu-latest
          steps:
            - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
            - uses: actions/setup-python@v5
    """
    path = _pinned_yml(content)
    try:
        errors = check_workflow(path)
        assert len(errors) == 1
        assert "v5" in errors[0]
    finally:
        os.unlink(str(path))
