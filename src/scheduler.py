"""
Daily scheduler — runs the full digest pipeline at the configured time each day.
Keeps running until interrupted (Ctrl+C or SIGTERM).
"""

import logging
import time
import schedule
from config import DIGEST_TIME
from .pipeline import run_pipeline

logger = logging.getLogger(__name__)


def _job():
    logger.info("Scheduler triggered — starting daily digest pipeline...")
    success = run_pipeline()
    if success:
        logger.info("Daily digest job completed successfully.")
    else:
        logger.error("Daily digest job finished with errors — check logs.")


def start():
    logger.info("Scheduler started. Digest will run daily at %s.", DIGEST_TIME)
    schedule.every().day.at(DIGEST_TIME).do(_job)

    while True:
        schedule.run_pending()
        time.sleep(30)
