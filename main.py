#!/usr/bin/env python3
"""
AI Articulation Daily Digest
=============================
Crawls AI/ML sources, synthesizes conversation-ready content via Claude,
generates a Word doc, and emails it to the configured recipient.

Usage:
  python main.py           -- Run once right now (send email)
  python main.py --dry-run -- Generate doc only, skip email
  python main.py --schedule -- Run daily at the time set in DIGEST_TIME (.env)
"""

import argparse
import logging
import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("main")


def main():
    parser = argparse.ArgumentParser(description="AI Articulation Daily Digest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the Word doc but do not send the email",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run as a daily scheduler (keeps process alive)",
    )
    args = parser.parse_args()

    if args.schedule:
        from src.scheduler import start
        start()
    else:
        from src.pipeline import run_pipeline
        success = run_pipeline(dry_run=args.dry_run)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
