"""Tests for CLI deploy manifest validation."""

import os
import sys
import tempfile
from unittest.mock import patch

import pytest

from src.cli.main import cli


class TestDeployManifestValidation:
    def test_deploy_missing_manifest_exits_nonzero(self):
        """deploy should exit with non-zero code when manifest path does not exist."""
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["ao", "deploy", "/nonexistent/manifest.yaml"]):
                cli()
        assert exc_info.value.code == 1

    def test_deploy_missing_manifest_prints_error(self, capsys):
        """deploy should print an error to stderr when manifest is missing."""
        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["ao", "deploy", "/nonexistent/manifest.yaml"]):
                cli()
        stderr = capsys.readouterr().err
        assert "Error" in stderr
        assert "not found" in stderr or "manifest" in stderr.lower()

    def test_deploy_with_existing_manifest_proceeds(self, capsys):
        """deploy should proceed normally when manifest path exists."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            f.write(b"key: value")
            manifest_path = f.name
        try:
            with patch.object(sys, "argv", ["ao", "deploy", manifest_path]):
                cli()
            stdout = capsys.readouterr().out
            assert "Deploying agent from manifest" in stdout
        finally:
            os.unlink(manifest_path)
