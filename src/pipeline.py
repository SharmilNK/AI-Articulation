"""
Orchestrates the full digest pipeline:
  1. Crawl all sources
  2. Synthesize content via Claude
  3. Generate Word doc
  4. Email it
"""

import logging
from datetime import date
from config import SOURCES
from .crawler import crawl_all
from .content_processor import generate_digest
from .doc_generator import build_document
from .email_sender import send_digest

logger = logging.getLogger(__name__)


def run_pipeline(dry_run: bool = False) -> bool:
    """
    Execute the full pipeline.
    dry_run=True: generate and save the doc but skip emailing.
    Returns True on success, False if any step failed.
    """
    today_str = date.today().strftime("%B %d, %Y")
    logger.info("=== AI Articulation Daily Digest — %s ===", today_str)

    # Step 1: Crawl
    logger.info("Step 1/4 — Crawling %d sources...", len(SOURCES))
    pages = crawl_all(SOURCES)
    usable = [p for p in pages if not p.error and p.content]
    logger.info("%d/%d sources scraped successfully.", len(usable), len(SOURCES))

    if not usable:
        logger.error("No usable content scraped. Aborting.")
        return False

    # Step 2: Synthesize via Claude
    logger.info("Step 2/4 — Synthesizing content with Claude...")
    try:
        digest = generate_digest(usable)
    except Exception as e:
        logger.error("Content synthesis failed: %s", e)
        return False

    # Step 3: Build Word document
    logger.info("Step 3/4 — Building Word document...")
    try:
        doc_path = build_document(digest, today_str)
    except Exception as e:
        logger.error("Document generation failed: %s", e)
        return False

    if dry_run:
        logger.info("Dry run complete. Document saved to: %s", doc_path)
        return True

    # Step 4: Email
    logger.info("Step 4/4 — Sending email...")
    success = send_digest(doc_path)
    return success
