import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from chesscom.peers import download_peer_games
from features.pipeline import build_feature_frame, build_peer_group_feature_frame

from aggregations.peer_comparison import (
    get_overall_peer_comparison,
    get_opening_peer_comparison,
    get_opening_play_share_gap,
    get_opening_score_gap,
    get_repertoire_width_comparison,
    get_top_n_opening_share,
    get_rating_bucket_comparison,
    get_peer_leaderboard,
)

def _normalize_peer_report_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures comparison columns have stable dtypes before aggregation.

    This prevents errors like:
      Expected numeric dtype, got object instead.
    """

    out = df.copy()

    numeric_cols = [
        "my_rating",
        "opp_rating",
        "rating_delta",
        "hour",
        "time_spent_opening",
    ]

    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    string_cols = [
        "simple_result",
        "my_color",
        "opening_family",
        "opening_name",
        "peer_username",
        "target_username",
        "time_class",
    ]

    for col in string_cols:
        if col in out.columns:
            out[col] = out[col].astype("object")

    if "end_time" in out.columns:
        out["end_time"] = pd.to_datetime(out["end_time"], utc=True, errors="coerce")

    return out

def _json_safe_value(value: Any) -> Any:
    """
    Converts Pandas / NumPy values into strict JSON-safe Python values.
    Removes NaN, inf, -inf, pd.NA, and NaT.
    """

    if value is None:
        return None

    if value is pd.NA:
        return None

    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.isoformat()

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        value = float(value)

    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


def _json_safe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Converts a DataFrame to strict JSON-safe records.
    """

    if df.empty:
        return []

    safe_df = df.copy()
    safe_df = safe_df.replace([np.inf, -np.inf], np.nan)
    safe_df = safe_df.astype(object).where(pd.notna(safe_df), None)

    records = safe_df.to_dict("records")

    return [{key: _json_safe_value(value) for key, value in row.items()} for row in records]

def build_peer_report(
    target_username: str,
    db_path: str | Path,
    time_class: str = "rapid",
    max_peers: int = 50,
    rating_window: int | None = None,
    max_games_per_peer: int | None = 500,
    refresh: bool = False,
    include_unrated: bool = False,
    include_opening_clock: bool = False,
) -> dict[str, Any]:
    """
    Builds all peer-group comparison tables for one target user and one time class.
    """

    peers = download_peer_games(
        target_username=target_username,
        db_path=db_path,
        max_peers=max_peers,
        time_class=time_class,
        rating_window=rating_window,
        refresh=refresh,
    )

    user_df = build_feature_frame(
        username=target_username,
        db_path=db_path,
        time_class=time_class,
        include_unrated=include_unrated,
        include_opening_clock=include_opening_clock,
        max_games=None,
    )

    peer_df = build_peer_group_feature_frame(
        target_username=target_username,
        peers=peers,
        db_path=db_path,
        time_class=time_class,
        include_unrated=include_unrated,
        include_opening_clock=include_opening_clock,
        max_games_per_peer=max_games_per_peer,
    )

    user_df = _normalize_peer_report_dtypes(user_df)
    peer_df = _normalize_peer_report_dtypes(peer_df)
    
    opening_comparison_df = get_opening_peer_comparison(
        user_df=user_df,
        peer_df=peer_df,
        min_games=10,
    )

    overall_df = get_overall_peer_comparison(user_df, peer_df)
    opening_play_share_gap_df = get_opening_play_share_gap(opening_comparison_df)
    opening_score_gap_df = get_opening_score_gap(opening_comparison_df)
    repertoire_width_df = get_repertoire_width_comparison(user_df, peer_df)
    top_3_share_df = get_top_n_opening_share(user_df, peer_df, n=3)
    rating_bucket_df = get_rating_bucket_comparison(user_df, peer_df)
    peer_leaderboard_df = get_peer_leaderboard(peer_df)

    return {
        "target_username": target_username,
        "time_class": time_class,
        "peer_count": len(peers),
        "peers": peers,
        "user_game_count": int(len(user_df)),
        "peer_game_count": int(len(peer_df)),
        "overall": _json_safe_records(overall_df),
        "opening_comparison": _json_safe_records(opening_comparison_df),
        "opening_play_share_gap": _json_safe_records(opening_play_share_gap_df),
        "opening_score_gap": _json_safe_records(opening_score_gap_df),
        "repertoire_width": _json_safe_records(repertoire_width_df),
        "top_3_share": _json_safe_records(top_3_share_df),
        "rating_bucket_comparison": _json_safe_records(rating_bucket_df),
        "peer_leaderboard": _json_safe_records(peer_leaderboard_df),
    }