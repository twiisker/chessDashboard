import pandas as pd
from pathlib import Path
from typing import Any

from chesscom.peers import download_peer_games, create_peer_cohort
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

    return {
        "target_username": target_username,
        "time_class": time_class,
        "peer_count": len(peers),
        "peers": peers,
        "user_game_count": int(len(user_df)),
        "peer_game_count": int(len(peer_df)),
        "overall": get_overall_peer_comparison(user_df, peer_df).to_dict("records"),
        "opening_comparison": opening_comparison_df.to_dict("records"),
        "opening_play_share_gap": get_opening_play_share_gap(
            opening_comparison_df
        ).to_dict("records"),
        "opening_score_gap": get_opening_score_gap(
            opening_comparison_df
        ).to_dict("records"),
        "repertoire_width": get_repertoire_width_comparison(
            user_df, peer_df
        ).to_dict("records"),
        "top_3_share": get_top_n_opening_share(
            user_df, peer_df, n=3
        ).to_dict("records"),
        "rating_bucket_comparison": get_rating_bucket_comparison(
            user_df, peer_df
        ).to_dict("records"),
        "peer_leaderboard": get_peer_leaderboard(peer_df).to_dict("records"),
    }