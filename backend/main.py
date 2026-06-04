"""
main.py
────────
Entry point for running the Ramp backend locally.

Usage:
    python -m backend.main
    or
    uvicorn backend.server:app --reload --port 8000
"""

import logging
import os

import uvicorn
from dotenv import load_dotenv

# Load .env before anything else
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Ramp backend...")
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=(os.getenv("APP_ENV", "development") == "development"),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
