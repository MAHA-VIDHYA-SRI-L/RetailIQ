"""Configuration settings for RetailIQ."""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Application settings
APP_NAME = "RetailIQ"
TRACK_ID = "PS03"
DESCRIPTION = "Evidence-First Sales & Inventory Copilot"
VERSION = "0.1.0"

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Database settings
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "retailiq.db"))
