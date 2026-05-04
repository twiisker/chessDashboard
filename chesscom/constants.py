# Final: strict-typing for Pylance: This variable is a constant!

from typing import Final

REQUIRED_RAW_COLUMNS: Final[set[str]] = {
    "end_time",
    "white.username",
    "black.username",
    "white.result",
    "black.result",
    "white.rating",
    "black.rating",
    "time_class",
    "eco",
    "pgn",
}

# Mapping raw JSON paths to strict snake_case names
COLUMN_RENAME_MAP: Final[dict[str, str]] = {
    "white.username": "white_username",
    "black.username": "black_username",
    "white.result": "white_result",
    "black.result": "black_result",
    "white.rating": "white_rating",
    "black.rating": "black_rating",
}

DRAW_RESULTS: Final[set[str]] = {
    "agreed",
    "repetition",
    "stalemate",
    "insufficient",
    "50move",
    "timevsinsufficient",
}

LOSS_RESULTS: Final[set[str]] = {
    "checkmated",
    "timeout",
    "resigned",
    "abandoned",
    "lose",
    "kingofthehill",
    "threecheck",
    "bughousepartnerlose"
}
