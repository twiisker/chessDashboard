import pandas as pd
from typing import Any

from chesscom.chess_types import SimpleResult


def build_win_draw_loss_table(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """
    Builds a win/draw/loss summary table grouped by group_col.

    Requires:
      - group_col
      - simple_result

    Returns columns:
      - group_col
      - win
      - draw
      - loss
      - total_games
      - win_rate_pct
      - score_rate_pct
    """
    expected_result_columns = [
        SimpleResult.WIN.value,
        SimpleResult.DRAW.value,
        SimpleResult.LOSS.value,
    ]

    if df.empty:
        return pd.DataFrame(
            columns=[
                group_col,
                *expected_result_columns,
                "total_games",
                "win_rate_pct",
                "score_rate_pct",
            ]
        )

    required_cols = {group_col, "simple_result"}
    missing_cols = required_cols.difference(df.columns)

    if missing_cols:
        raise KeyError(
            f"Missing required columns for W/D/L table: {sorted(missing_cols)}"
        )

    summary = (
        df.groupby([group_col, "simple_result"])
        .size()
        .unstack(fill_value=0)
    )

    summary = summary.reindex(columns=expected_result_columns, fill_value=0)

    summary["total_games"] = summary[expected_result_columns].sum(axis=1)

    valid_rows = summary["total_games"] > 0

    summary["win_rate_pct"] = 0.0
    summary.loc[valid_rows, "win_rate_pct"] = (
        100.0
        * summary.loc[valid_rows, SimpleResult.WIN.value]
        / summary.loc[valid_rows, "total_games"]
    ).round(1)

    summary["score_rate_pct"] = 0.0
    summary.loc[valid_rows, "score_rate_pct"] = (
        100.0
        * (
            summary.loc[valid_rows, SimpleResult.WIN.value]
            + 0.5 * summary.loc[valid_rows, SimpleResult.DRAW.value]
        )
        / summary.loc[valid_rows, "total_games"]
    ).round(1)

    return summary.reset_index()


def get_time_control_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates performance by time control.
    """
    return build_win_draw_loss_table(df, "time_class")


def get_weekday_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates performance by weekday.
    """
    return build_win_draw_loss_table(df, "weekday")


def get_hour_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates performance by hour of day.
    """
    return build_win_draw_loss_table(df, "hour")


def get_matchup_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates performance by matchup type:
      - Underdog
      - Even Match
      - Favorite
    """
    return build_win_draw_loss_table(df, "matchup_type")


def get_color_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates performance by color:
      - white
      - black
    """
    return build_win_draw_loss_table(df, "my_color")


def get_opening_stats(df: pd.DataFrame, min_games: int = 10) -> pd.DataFrame:
    """
    Aggregates performance by opening, filtering out rare or unknown openings.

    Requires:
      - opening_name
      - simple_result
      - eco
    """
    if df.empty:
        return pd.DataFrame()

    required_cols = {"opening_name", "simple_result", "eco"}
    missing_cols = required_cols.difference(df.columns)

    if missing_cols:
        raise KeyError(
            f"Missing required columns for opening stats: {sorted(missing_cols)}"
        )

    invalid_names: set[Any] = {"Unknown", "Undefined", "", None}

    valid_df = df[~df["opening_name"].isin(invalid_names)].copy()

    if valid_df.empty:
        return pd.DataFrame()

    stats = build_win_draw_loss_table(valid_df, "opening_name")

    if stats.empty:
        return stats

    eco_map = (
        valid_df
        .drop_duplicates("opening_name")
        .set_index("opening_name")["eco"]
    )

    stats["eco_url"] = stats["opening_name"].map(eco_map)

    stats = stats[stats["total_games"] >= min_games].copy()

    return (
        stats
        .sort_values("total_games", ascending=False)
        .reset_index(drop=True)
    )