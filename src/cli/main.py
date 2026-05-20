"""CLI entry point for the agent orchestrator."""

import argparse
import json
import os
import sys

from src.common.config import Config
from src.common.logging import configure_logging


def validate_manifest(path: str) -> dict:
    """Validate a manifest file exists and is parseable JSON.
    
    Returns the parsed manifest as a dict on success.
    Raises SystemExit on validation failure.
    """
    if not os.path.isfile(path):
        print(f"Error: Manifest file not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid manifest JSON at {path}: {e}", file=sys.stderr)
        sys.exit(1)

    # Basic structure validation
    if not isinstance(manifest, dict):
        print(f"Error: Manifest must be a JSON object (dict), got {type(manifest).__name__}", file=sys.stderr)
        sys.exit(1)

    required_fields = ["name", "agent_type"]
    missing = [f for f in required_fields if f not in manifest]
    if missing:
        print(f"Error: Manifest missing required fields: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    return manifest


def cli():
    parser = argparse.ArgumentParser(description="Agent Orchestrator CLI")
    parser.add_argument("--config", "-c", help="Path to config file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("name", help="Project name")

    deploy_parser = subparsers.add_parser("deploy", help="Deploy an agent")
    deploy_parser.add_argument("manifest", help="Path to agent manifest file")
    deploy_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the manifest and print result without deploying",
    )

    status_parser = subparsers.add_parser("status", help="Show agent status")
    status_parser.add_argument("--watch", "-w", action="store_true", help="Watch mode")

    logs_parser = subparsers.add_parser("logs", help="View agent logs")
    logs_parser.add_argument("agent_id", help="Agent ID")
    logs_parser.add_argument("--tail", "-t", type=int, default=50, help="Number of lines")

    args = parser.parse_args()

    if args.verbose:
        configure_logging("DEBUG")
    else:
        configure_logging("INFO")

    if args.command == "init":
        print(f"Initializing project: {args.name}")
    elif args.command == "deploy":
        manifest = validate_manifest(args.manifest)
        if args.dry_run:
            print("Dry-run mode — validating manifest without deploying.")
            print(f"  Manifest:     {args.manifest}")
            print(f"  Agent name:   {manifest.get('name', 'N/A')}")
            print(f"  Agent type:   {manifest.get('agent_type', 'N/A')}")
            print(f"  Config keys:  {len(manifest)} top-level fields")
            print("✓ Manifest is valid. No deployment performed.")
        else:
            print(f"Deploying agent from manifest: {args.manifest}")
    elif args.command == "status":
        print("Checking agent status...")
    elif args.command == "logs":
        print(f"Fetching logs for agent: {args.agent_id}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli()
