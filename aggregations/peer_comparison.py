import pandas as pd

# _ private funcs
def _count_wins(s: pd.Series) -> int:
    return int((s == "win").sum())

def _count_draws(s: pd.Series) -> int:
    return int((s == "draw").sum())

def _count_losses(s: pd.Series) -> int:
    return int((s == "loss").sum())

def _add_comparison_group(
    user_df: pd.DataFrame,
    peer_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combines target-user games and peer games into one DataFrame.

    Adds:
      - comparison_group: target / peers
    """
    user_part = user_df.copy()
    peer_part = peer_df.copy()

    user_part["comparison_group"] = "target"
    peer_part["comparison_group"] = "peers"

    return pd.concat([user_part, peer_part], ignore_index=True)


def get_overall_peer_comparison(
    user_df: pd.DataFrame,
    peer_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Overall target-vs-peer comparison.

    Returns:
      - comparison_group
      - games
      - avg_rating
      - avg_opp_rating
      - wins
      - draws
      - losses
      - win_rate
      - draw_rate
      - loss_rate
      - score_rate
    """
    combined = _add_comparison_group(user_df, peer_df)

    if combined.empty:
        return pd.DataFrame()

    required_cols = {"comparison_group", "simple_result", "my_rating", "opp_rating"}
    missing_cols = required_cols.difference(combined.columns)

    if missing_cols:
        raise KeyError(f"Missing required columns: {sorted(missing_cols)}")

    result = (
        combined
        .groupby("comparison_group")
        .agg(
            games=("simple_result", "count"),
            avg_rating=("my_rating", "mean"),
            avg_opp_rating=("opp_rating", "mean"),
            wins=("simple_result", _count_wins),
            draws=("simple_result", _count_draws),
            losses=("simple_result", _count_losses),
        )
        .reset_index()
    )

    result["avg_rating"] = result["avg_rating"].round(0)
    result["avg_opp_rating"] = result["avg_opp_rating"].round(0)

    result["win_rate"] = (100 * result["wins"] / result["games"]).round(1)
    result["draw_rate"] = (100 * result["draws"] / result["games"]).round(1)
    result["loss_rate"] = (100 * result["losses"] / result["games"]).round(1)

    result["score_rate"] = (
        100 * (result["wins"] + 0.5 * result["draws"]) / result["games"]
    ).round(1)

    return result


def get_opening_peer_comparison(
    user_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    min_games: int = 10,
) -> pd.DataFrame:
    """
    Compares target vs peers by opening family and color.

    Returns:
      - comparison_group
      - my_color
      - opening_family
      - games
      - wins
      - draws
      - losses
      - play_share
      - win_rate
      - score_rate
    """
    combined = _add_comparison_group(user_df, peer_df)

    if combined.empty:
        return pd.DataFrame()

    required_cols = {
        "comparison_group",
        "my_color",
        "opening_family",
        "simple_result",
    }
    missing_cols = required_cols.difference(combined.columns)

    if missing_cols:
        raise KeyError(f"Missing required columns: {sorted(missing_cols)}")

    valid_df = combined[
        combined["opening_family"].notna()
        & ~combined["opening_family"].isin(["", "Unknown", "Undefined"])
    ].copy()

    if valid_df.empty:
        return pd.DataFrame()

    result = (
        valid_df
        .groupby(["comparison_group", "my_color", "opening_family"])
        .agg(
            games=("simple_result", "count"),
            wins=("simple_result", _count_wins),
            draws=("simple_result", _count_draws),
            losses=("simple_result", _count_losses),
        )
        .reset_index()
    )

    result["play_share"] = (
        100
        * result["games"]
        / result.groupby(["comparison_group", "my_color"])["games"].transform("sum")
    ).round(1)

    result["win_rate"] = (
        100 * result["wins"] / result["games"]
    ).round(1)

    result["score_rate"] = (
        100 * (result["wins"] + 0.5 * result["draws"]) / result["games"]
    ).round(1)

    result = result[result["games"] >= min_games].copy()

    return result.sort_values(
        ["comparison_group", "my_color", "games"],
        ascending=[True, True, False],
    ).reset_index(drop=True)


def get_opening_play_share_gap(
    opening_comparison_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculates how much more/less the target plays an opening family
    compared with peers.

    Positive target_minus_peers = target overplays this opening.
    Negative target_minus_peers = target underplays this opening.
    """
    if opening_comparison_df.empty:
        return pd.DataFrame()

    required_cols = {
        "comparison_group",
        "my_color",
        "opening_family",
        "play_share",
    }
    missing_cols = required_cols.difference(opening_comparison_df.columns)

    if missing_cols:
        raise KeyError(f"Missing required columns: {sorted(missing_cols)}")

    gap_df = opening_comparison_df.pivot_table(
        index=["my_color", "opening_family"],
        columns="comparison_group",
        values="play_share",
        fill_value=0,
    ).reset_index()

    gap_df.columns.name = None

    if "target" not in gap_df.columns:
        gap_df["target"] = 0.0

    if "peers" not in gap_df.columns:
        gap_df["peers"] = 0.0

    gap_df["target_minus_peers"] = (gap_df["target"] - gap_df["peers"]).round(1)

    gap_df = gap_df[(gap_df["target"] > 0) | (gap_df["peers"] > 0)].copy()

    return gap_df.sort_values(
        "target_minus_peers",
        ascending=False,
    ).reset_index(drop=True)


def get_opening_score_gap(
    opening_comparison_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    calcs target score-rate gap vs peers by color/opening family.

    Positive score_gap = target scores better than peers.
    Negative score_gap = target scores worse than peers.
    """
    if opening_comparison_df.empty:
        return pd.DataFrame()

    score_df = opening_comparison_df.pivot_table(
        index=["my_color", "opening_family"],
        columns="comparison_group",
        values="score_rate",
    ).reset_index()

    score_df.columns.name = None

    games_df = opening_comparison_df.pivot_table(
        index=["my_color", "opening_family"],
        columns="comparison_group",
        values="games",
        fill_value=0,
    ).reset_index()

    games_df.columns.name = None

    result = score_df.merge(
        games_df,
        on=["my_color", "opening_family"],
        suffixes=("_score", "_games"),
    )

    for col in ["target_score", "peers_score", "target_games", "peers_games"]:
        if col not in result.columns:
            result[col] = pd.NA

    result["score_gap"] = (result["target_score"] - result["peers_score"]).round(1)

    result = result[result["target_games"].fillna(0) > 0].copy()

    return result.sort_values(
        "score_gap",
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)


def get_repertoire_width_comparison(
    user_df: pd.DataFrame,
    peer_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compares repertoire width between target and peers.

    Measures:
      - unique opening families
      - unique specific openings
      - games per family
    """
    combined = _add_comparison_group(user_df, peer_df)

    if combined.empty:
        return pd.DataFrame()

    required_cols = {
        "comparison_group",
        "my_color",
        "opening_family",
        "opening_name",
    }
    missing_cols = required_cols.difference(combined.columns)

    if missing_cols:
        raise KeyError(f"Missing required columns: {sorted(missing_cols)}")

    valid_df = combined[
        combined["opening_family"].notna()
        & ~combined["opening_family"].isin(["", "Unknown", "Undefined"])
    ].copy()

    result = (
        valid_df
        .groupby(["comparison_group", "my_color"])
        .agg(
            games=("opening_family", "count"),
            unique_families=("opening_family", "nunique"),
            unique_specific_openings=("opening_name", "nunique"),
        )
        .reset_index()
    )

    result["games_per_family"] = (
        result["games"] / result["unique_families"]
    ).round(1)

    return result


def get_top_n_opening_share(
    user_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    n: int = 3,
) -> pd.DataFrame:
    """
    Calculates how concentrated the repertoire is.

    Example:
      top_3_share = percentage of games covered by the top 3 opening families.
    """
    combined = _add_comparison_group(user_df, peer_df)

    if combined.empty:
        return pd.DataFrame()

    grouped = (
        combined
        .groupby(["comparison_group", "my_color", "opening_family"])
        .size()
        .reset_index(name="games")
    )

    total = (
        grouped
        .groupby(["comparison_group", "my_color"])["games"]
        .sum()
        .reset_index(name="total_games")
    )

    top_n = (
        grouped
        .sort_values(
            ["comparison_group", "my_color", "games"],
            ascending=[True, True, False],
        )
        .groupby(["comparison_group", "my_color"])
        .head(n)
        .groupby(["comparison_group", "my_color"])["games"]
        .sum()
        .reset_index(name=f"top_{n}_games")
    )

    result = total.merge(
        top_n,
        on=["comparison_group", "my_color"],
        how="left",
    )

    result[f"top_{n}_games"] = result[f"top_{n}_games"].fillna(0)

    result[f"top_{n}_share"] = (
        100 * result[f"top_{n}_games"] / result["total_games"]
    ).round(1)

    return result


def get_rating_bucket_comparison(
    user_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    bucket_size: int = 100,
) -> pd.DataFrame:
    """
    Compares score rate by rating bucket.

    Rating bucket is calculated from my_rating.
    """
    combined = _add_comparison_group(user_df, peer_df)

    if combined.empty:
        return pd.DataFrame()

    required_cols = {"comparison_group", "my_rating", "simple_result"}
    missing_cols = required_cols.difference(combined.columns)

    if missing_cols:
        raise KeyError(f"Missing required columns: {sorted(missing_cols)}")

    combined = combined.copy()
    combined["rating_bucket"] = (
        (combined["my_rating"] // bucket_size) * bucket_size
    ).astype("Int64")

    result = (
        combined
        .groupby(["comparison_group", "rating_bucket"])
        .agg(
            games=("simple_result", "count"),
            avg_rating=("my_rating", "mean"),
            wins=("simple_result", _count_wins),
            draws=("simple_result", _count_draws),
            losses=("simple_result", _count_losses),
        )
        .reset_index()
    )

    result["avg_rating"] = result["avg_rating"].round(0)

    result["score_rate"] = (
        100 * (result["wins"] + 0.5 * result["draws"]) / result["games"]
    ).round(1)

    return result.sort_values(
        ["rating_bucket", "comparison_group"],
    ).reset_index(drop=True)


def get_peer_leaderboard(
    peer_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Leaderboard of individual peers by score rate.
    Requires peer_df to include peer_username.
    """
    if peer_df.empty:
        return pd.DataFrame()

    required_cols = {"peer_username", "my_rating", "simple_result"}
    missing_cols = required_cols.difference(peer_df.columns)

    if missing_cols:
        raise KeyError(f"Missing required columns: {sorted(missing_cols)}")

    result = (
        peer_df
        .groupby("peer_username")
        .agg(
            games=("simple_result", "count"),
            avg_rating=("my_rating", "mean"),
            wins=("simple_result", _count_wins),
            draws=("simple_result", _count_draws),
            losses=("simple_result", _count_losses),
        )
        .reset_index()
    )

    result["avg_rating"] = result["avg_rating"].round(0)

    result["score_rate"] = (
        100 * (result["wins"] + 0.5 * result["draws"]) / result["games"]
    ).round(1)

    return result.sort_values(
        "score_rate",
        ascending=False,
    ).reset_index(drop=True)