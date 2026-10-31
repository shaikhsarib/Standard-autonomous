#!/usr/bin/env python3
"""
Standard Autonomous • Multi-Agent Autonomous OS
Main Application Entrypoint
------------------------------------------------
Provides unified access to:
  1. Web Command Center & API Server (`python main.py` or `python main.py server`)
  2. Unified Rich CLI (`python main.py cli ...`)
  3. Direct pipeline execution with backward compatibility flags
"""

import sys
import os
from pathlib import Path

# Ensure root and src are in python path
root_dir = Path(__file__).resolve().parent
src_dir = root_dir / "src"
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_server():
    """Start the FastAPI backend server and dashboard."""
    import uvicorn
    from config.settings import settings

    print("\n" + "=" * 65)
    print(" [Standard Autonomous] Multi-Agent Autonomous OS")
    print(f" Dashboard: http://127.0.0.1:{settings.PORT}")
    print(f" API Docs:  http://127.0.0.1:{settings.PORT}/docs")
    print("=" * 65 + "\n")
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=settings.PORT, reload=settings.DEBUG)


def run_cli(args):
    """Delegate to the rich CLI interface."""
    from cli import app
    sys.argv = [sys.argv[0]] + args
    app()


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in ("server", "serve", "api", "web"):
            run_server()
            return
        elif cmd in ("cli", "run"):
            run_cli(sys.argv[2:])
            return
        elif cmd in ("--help", "-h"):
            print("Standard Autonomous • Multi-Agent Autonomous OS")
            print("\nUsage:")
            print("  python main.py                  # Start Web Command Center (default)")
            print("  python main.py server           # Explicitly start Web Server")
            print("  python main.py cli <command>    # Run CLI commands (discover, outreach, etc.)")
            print("  python cli.py --help            # View all available CLI tools")
            return
        else:
            # Delegate arbitrary arguments to the CLI app
            run_cli(sys.argv[1:])
            return
    else:
        # Default behavior: Launch Web Command Center
        run_server()


if __name__ == "__main__":
    main()
