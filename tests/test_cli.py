"""Tests for CLI dry-run deploy mode."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# Ensure the project root is on sys.path so src is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _run_cli(args: list[str]) -> tuple[int, str, str]:
    """Run the CLI entry point with given args and capture stdout/stderr."""
    from src.cli.main import cli

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    old_argv = sys.argv

    out_buf = []
    err_buf = []

    class Capture:
        def write(self, s):
            out_buf.append(s)
        def flush(self):
            pass

    class CaptureErr:
        def write(self, s):
            err_buf.append(s)
        def flush(self):
            pass

    sys.stdout = Capture()
    sys.stderr = CaptureErr()

    exit_code = 0
    try:
        sys.argv = ["ao"] + args
        cli()
    except SystemExit as e:
        exit_code = e.code if e.code is not None else 0
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.argv = old_argv

    return exit_code, "".join(out_buf), "".join(err_buf)


class TestDeployDryRun:
    """Test the deploy --dry-run flag."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def _make_manifest(self, data: dict) -> str:
        path = os.path.join(self.tmpdir, "manifest.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_dry_run_valid_manifest(self):
        """Dry-run with a valid manifest should validate and not deploy."""
        manifest_path = self._make_manifest({
            "name": "test-agent",
            "agent_type": "assistant",
            "version": "1.0.0",
        })
        exit_code, stdout, stderr = _run_cli(
            ["deploy", manifest_path, "--dry-run"]
        )
        assert exit_code == 0, f"Expected exit 0, got {exit_code}. stderr: {stderr}"
        assert "Dry-run mode" in stdout
        assert "test-agent" in stdout
        assert "assistant" in stdout
        assert "valid" in stdout.lower()

    def test_dry_run_missing_manifest(self):
        """Dry-run with a non-existent manifest should fail."""
        exit_code, stdout, stderr = _run_cli(
            ["deploy", "/nonexistent/path.json", "--dry-run"]
        )
        assert exit_code != 0
        assert "not found" in stderr.lower()

    def test_dry_run_invalid_json(self):
        """Dry-run with malformed JSON should fail."""
        path = os.path.join(self.tmpdir, "bad.json")
        with open(path, "w") as f:
            f.write("not json content")
        exit_code, stdout, stderr = _run_cli(
            ["deploy", path, "--dry-run"]
        )
        assert exit_code != 0
        assert "invalid" in stderr.lower()

    def test_dry_run_missing_required_fields(self):
        """Dry-run with missing required fields should fail."""
        manifest_path = self._make_manifest({"name": "partial-agent"})
        exit_code, stdout, stderr = _run_cli(
            ["deploy", manifest_path, "--dry-run"]
        )
        assert exit_code != 0
        assert "missing" in stderr.lower()

    def test_regular_deploy_without_dry_run(self):
        """Normal deploy (no --dry-run) should proceed without dry-run message."""
        manifest_path = self._make_manifest({
            "name": "test-agent",
            "agent_type": "assistant",
        })
        exit_code, stdout, stderr = _run_cli(["deploy", manifest_path])
        assert exit_code == 0
        assert "Deploying" in stdout
        assert "Dry-run" not in stdout
