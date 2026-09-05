"""Configuration settings for RetailIQ."""

import os
import tempfile
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
# On Vercel / serverless environments, the root directory is read-only.
# SQLite database is placed in the writable /tmp directory.
if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(Path(tempfile.gettempdir()) / "retailiq.db"))
else:
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "retailiq.db"))

# --------------------------------------------------------------------------
# Inventory Intelligence Assumptions & Thresholds
# Documented as application decision-support heuristics, not universal standards.
# --------------------------------------------------------------------------

# Demand analysis historical window
INVENTORY_DEMAND_WINDOW_DAYS = int(os.getenv("INVENTORY_DEMAND_WINDOW_DAYS", "30"))

# Stock-out coverage risk thresholds (Days of Inventory Coverage)
RISK_THRESHOLD_CRITICAL = float(os.getenv("RISK_THRESHOLD_CRITICAL", "3.0"))   # < 3.0 days
RISK_THRESHOLD_HIGH = float(os.getenv("RISK_THRESHOLD_HIGH", "7.0"))           # 3.0 to 7.0 days
RISK_THRESHOLD_MEDIUM = float(os.getenv("RISK_THRESHOLD_MEDIUM", "14.0"))      # 7.0 to 14.0 days

# Overstock coverage thresholds (Days of Inventory Coverage)
OVERSTOCK_THRESHOLD_DAYS = float(os.getenv("OVERSTOCK_THRESHOLD_DAYS", "30.0")) # > 30.0 days
OVERSTOCK_CRITICAL_DAYS = float(os.getenv("OVERSTOCK_CRITICAL_DAYS", "60.0"))  # > 60.0 days

# Target replenishment coverage days for reorder calculation
TARGET_REORDER_COVERAGE_DAYS = float(os.getenv("TARGET_REORDER_COVERAGE_DAYS", "21.0"))

# Demand velocity classification thresholds (Network Units / Day over Demand Window)
VELOCITY_FAST_UNITS_PER_DAY = float(os.getenv("VELOCITY_FAST_UNITS_PER_DAY", "12.0"))  # >= 12.0 units/day network (>= 3 units/store/day)
VELOCITY_SLOW_UNITS_PER_DAY = float(os.getenv("VELOCITY_SLOW_UNITS_PER_DAY", "4.0"))   # < 4.0 units/day network (< 1 unit/store/day)

# --------------------------------------------------------------------------
# Google Gemini API Configuration
# Gemini is the ONLY external AI API allowed. Keys are strictly loaded from env.
# --------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "15.0"))
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
