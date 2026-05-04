import re
from typing import Final

import pandas as pd


PROFILE_FEATURE_COLUMNS: Final[list[str]] = [
    "white_win_rate",
    "black_win_rate",
    "white_avg_moves",
    "black_avg_moves",
    "white_draw_rate",
    "black_draw_rate",
    "white_avg_captures",
    "black_avg_captures",
    "white_avg_checks",
    "black_avg_checks",
    "white_unique_openings",
    "black_unique_openings",
    "white_avg_opp_elo",
    "black_avg_opp_elo",
]


_RESULT_TOKENS: Final[set[str]] = {"1-0", "0-1", "1/2-1/2", "*"}


def _extract_movetext_from_pgn(pgn: str) -> str:
    """
    Removes PGN headers and common annotation blocks.
    Keeps SAN move text.
    """
    text = str(pgn)

    # Remove PGN headers.
    text = re.sub(r"^\[.*?\]\s*$", "", text, flags=re.MULTILINE)

    # Remove comments and variations.
    text = re.sub(r"\{[^}]*\}", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)

    return text


def _count_pgn_features(pgn: str) -> tuple[int, int, int]:
    """
    Returns:
      - approximate full-move count
      - capture count
      - check/checkmate count

    This intentionally stays close to the old feature logic:
      moves ~= number of full move numbers in the PGN.
    """
    movetext = _extract_movetext_from_pgn(pgn)

    fullmove_numbers = re.findall(r"\b\d+\.", movetext)
    move_count = len(fullmove_numbers)

    capture_count = movetext.count("x")
    check_count = movetext.count("+") + movetext.count("#")

    return move_count, capture_count, check_count


def _empty_profile() -> dict[str, float]:
    return {col: 0.0 for col in PROFILE_FEATURE_COLUMNS}


def _summarize_color(df: pd.DataFrame, color: str) -> dict[str, float]:
    color_df = df[df["my_color"] == color].copy()

    if color_df.empty:
        prefix = "white" if color == "white" else "black"
        return {
            f"{prefix}_win_rate": 0.0,
            f"{prefix}_avg_moves": 0.0,
            f"{prefix}_draw_rate": 0.0,
            f"{prefix}_avg_captures": 0.0,
            f"{prefix}_avg_checks": 0.0,
            f"{prefix}_unique_openings": 0.0,
            f"{prefix}_avg_opp_elo": 0.0,
        }

    prefix = "white" if color == "white" else "black"

    games = len(color_df)

    simple_result = color_df["simple_result"].astype(str).str.lower()

    wins = int((simple_result == "win").sum())
    draws = int((simple_result == "draw").sum())

    pgn_features = color_df["pgn"].apply(_count_pgn_features)

    move_counts = [item[0] for item in pgn_features]
    capture_counts = [item[1] for item in pgn_features]
    check_counts = [item[2] for item in pgn_features]

    opp_rating = pd.to_numeric(color_df["opp_rating"], errors="coerce")

    return {
        f"{prefix}_win_rate": round(wins / games, 4),
        f"{prefix}_avg_moves": round(sum(move_counts) / games, 4),
        f"{prefix}_draw_rate": round(draws / games, 4),
        f"{prefix}_avg_captures": round(sum(capture_counts) / games, 4),
        f"{prefix}_avg_checks": round(sum(check_counts) / games, 4),
        f"{prefix}_unique_openings": float(color_df["eco"].nunique()),
        f"{prefix}_avg_opp_elo": round(float(opp_rating.mean()), 4)
        if not opp_rating.dropna().empty
        else 0.0,
    }


def calculate_user_profile_from_df(df: pd.DataFrame) -> dict[str, float]:
    """
    Calculates the 14-feature style vector from your processed feature DataFrame.

    Requires columns:
      - my_color
      - simple_result
      - pgn
      - opening_name
      - opp_rating

    Returns exactly the feature columns expected by StyleInferencer.
    """
    if df.empty:
        return _empty_profile()

    required_cols = {
        "my_color",
        "simple_result",
        "pgn",
        "eco",
        "opp_rating",
    }

    missing_cols = required_cols.difference(df.columns)

    if missing_cols:
        raise KeyError(
            f"Missing required columns for player profile: {sorted(missing_cols)}"
        )

    out: dict[str, float] = {}
    out.update(_summarize_color(df, "white"))
    out.update(_summarize_color(df, "black"))

    # Guarantee exact keys/order.
    return {col: float(out.get(col, 0.0)) for col in PROFILE_FEATURE_COLUMNS}