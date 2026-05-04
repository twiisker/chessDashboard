from typing import cast

import pandas as pd


def get_recent_repertoire(
    df: pd.DataFrame,
    days_back: int = 30,
    min_games: int = 3,
) -> dict[str, pd.DataFrame]:
    """
    Slices a feature DataFrame to a recent window and returns top openings
    for White and Black.
    """
    empty: dict[str, pd.DataFrame] = {
        "white": pd.DataFrame(),
        "black": pd.DataFrame(),
    }

    if df.empty:
        return empty

    required_cols = {"end_time", "my_color", "opening_name"}
    missing_cols = required_cols.difference(df.columns)

    if missing_cols:
        raise KeyError(
            f"Missing required columns for recent repertoire: {sorted(missing_cols)}"
        )

    out = df.copy()

    if not pd.api.types.is_datetime64_any_dtype(out["end_time"]):
        out["end_time"] = pd.to_datetime(
            out["end_time"],
            utc=True,
            errors="coerce",
        )

    out = cast(pd.DataFrame, out.dropna(subset=["end_time"]))

    if out.empty:
        return empty

    invalid_openings: list[str] = ["", "Unknown", "Undefined"]

    out = cast(
        pd.DataFrame,
        out[
            out["opening_name"].notna()
            & ~out["opening_name"].isin(invalid_openings)
        ].copy(),
    )

    if out.empty:
        return empty

    latest_game = out["end_time"].max()
    cutoff_date = latest_game - pd.Timedelta(days=days_back)

    recent_df = cast(
        pd.DataFrame,
        out[out["end_time"] >= cutoff_date].copy(),
    )

    def summarize_repertoire(color: str) -> pd.DataFrame:
        color_df = cast(
            pd.DataFrame,
            recent_df[recent_df["my_color"] == color].copy(),
        )

        if color_df.empty:
            return pd.DataFrame()

        summary = cast(
            pd.DataFrame,
            color_df.groupby("opening_name").size().reset_index(name="games_played"),
        )

        summary = cast(
            pd.DataFrame,
            summary[summary["games_played"] >= min_games].copy(),
        )

        if summary.empty:
            return summary

        color_game_count = len(color_df)

        summary["frequency_pct"] = (
            100.0 * summary["games_played"] / color_game_count
        ).round(1)

        return cast(
            pd.DataFrame,
            summary.sort_values("games_played", ascending=False).reset_index(
                drop=True
            ),
        )

    return {
        "white": summarize_repertoire("white"),
        "black": summarize_repertoire("black"),
    }