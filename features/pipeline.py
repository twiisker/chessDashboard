from pathlib import Path

import duckdb
import pandas as pd

from features.perspective import add_user_perspective_columns
from features.results import compute_result_columns
from features.time_features import compute_time_features
from features.openings import compute_opening_features
from features.rating_features import compute_rating_features
from features.opening_clock import add_opening_time_feature

def load_owner_games_from_db(
    username: str,
    db_path: str | Path,
    time_class: str | None = None,
    include_unrated: bool = False,
) -> pd.DataFrame:
    """
    Loads raw games for one owner_username from DuckDB.
    Returns rows from the raw matches table, not matches_enriched.
    """

    filters = [
        "LOWER(owner_username) = LOWER(?)",
        "rules = 'chess'",
    ]
    params: list[object] = [username]

    if not include_unrated:
        filters.append("rated = TRUE")

    if time_class is not None:
        filters.append("time_class = ?")
        params.append(time_class)

    where_sql = " AND ".join(filters)

    query = f"""
        SELECT *
        FROM matches
        WHERE {where_sql}
        ORDER BY end_time
    """

    with duckdb.connect(str(db_path)) as con:
        df = con.execute(query, params).df()

    if not df.empty:
        df["end_time"] = pd.to_datetime(df["end_time"], unit="s", utc=True)

    return df


def build_feature_frame(
    username: str,
    db_path: str | Path,
    time_class: str | None = None,
    include_unrated: bool = False,
    max_games: int | None = None,
    include_opening_clock: bool = True,
) -> pd.DataFrame:
    """
    Shared feature pipeline for both the target user and peer users.
    """

    df = load_owner_games_from_db(
        username=username,
        db_path=db_path,
        time_class=time_class,
        include_unrated=include_unrated,
    )

    if max_games is not None and max_games > 0 and not df.empty:
        df = df.tail(max_games).copy()

    df = add_user_perspective_columns(df, username)
    df = compute_result_columns(df)
    df = compute_time_features(df)
    df = compute_opening_features(df)
    df = compute_rating_features(df)

    if include_opening_clock:
        df = add_opening_time_feature(df, username)

    return df


def build_peer_group_feature_frame(
    target_username: str,
    peers: list[str],
    db_path: str | Path,
    time_class: str | None = None,
    include_unrated: bool = False,
    max_games_per_peer: int | None = 500,
    include_opening_clock: bool = False,
) -> pd.DataFrame:
    """
    Builds one combined feature DataFrame for all peer users.
    Each peer is processed from their own perspective.
    """

    frames: list[pd.DataFrame] = []

    for peer in peers:
        peer_df = build_feature_frame(
            username=peer,
            db_path=db_path,
            time_class=time_class,
            include_unrated=include_unrated,
            max_games=max_games_per_peer,
            include_opening_clock=include_opening_clock,
        )

        if peer_df.empty:
            continue

        peer_df["peer_username"] = peer
        peer_df["target_username"] = target_username
        frames.append(peer_df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)