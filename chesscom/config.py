from pathlib import Path
from typing import Final
import os

# Core Identity
USERNAME: Final[str] = ""
TIMEZONE: Final[str] = "Europe/Berlin"

# Paths
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DATA_DIR: Final[Path] = PROJECT_ROOT / "chess_com_data"
DB_PATH: Final[Path] = DATA_DIR / "chess_analysis.db"
CACHE_DIR: Final[Path] = DATA_DIR / "chess_data_cache"
OUTPUT_DIR: Final[Path] = PROJECT_ROOT / "outputs"

TWIC_DB = Path("twic/data/twic_data.duckdb")

# Engine Configuration
STOCKFISH_PATH: Final[str] = "/usr/local/bin/stockfish"
OPENING_PLY_LIMIT: Final[int] = 20

# chess com api
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "")

# API URL

API_BASE_URL = os.getenv(
    "CHESS_API_BASE_URL",
    "http://localhost:8000/api/v1",
)
