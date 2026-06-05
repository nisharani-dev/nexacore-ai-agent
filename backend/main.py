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

from backend.logging_config import setup_logging

# Load .env before anything else
load_dotenv()

# Configure structured logging
log_format = "colored" if os.getenv("APP_ENV", "development") == "development" else "json"
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(
    log_level=log_level,
    log_format=log_format,
    log_file="app.log",
    log_dir=os.getenv("LOG_DIR", "./logs"),
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Ramp backend...")
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=(os.getenv("APP_ENV", "development") == "development"),
        reload_excludes=[
            "frontend/node_modules/*",
            "frontend/dist/*",
            "data/*",
            "backend/__pycache__/*",
            "backend/*/__pycache__/*",
            "config/__pycache__/*",
            ".git/*",
        ],
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
