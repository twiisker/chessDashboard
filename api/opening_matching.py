from typing import Any

import pandas as pd


def normalize_opening_text(value: Any) -> str:
    return str(value).strip().lower()


def filter_opening_games(
    df: pd.DataFrame,
    opening_query: str,
    color: str,
) -> pd.DataFrame:
    """
    Filters games by either exact opening_name or exact opening_family.

    Example:
      "Petrovs" can match opening_family.
      "Petrovs Defense Classical Attack" can match opening_name.
    """
    if df.empty:
        return df

    required_cols = {"opening_name", "opening_family", "my_color"}
    missing_cols = required_cols.difference(df.columns)

    if missing_cols:
        raise KeyError(f"Missing required opening columns: {sorted(missing_cols)}")

    query_norm = normalize_opening_text(opening_query)
    color_norm = normalize_opening_text(color)

    opening_name_norm = df["opening_name"].astype(str).str.strip().str.lower()
    opening_family_norm = df["opening_family"].astype(str).str.strip().str.lower()
    color_norm_series = df["my_color"].astype(str).str.strip().str.lower()

    return df[
        (color_norm_series == color_norm)
        & (
            (opening_name_norm == query_norm)
            | (opening_family_norm == query_norm)
        )
    ].copy()


def get_available_openings_for_color(
    df: pd.DataFrame,
    color: str,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """
    Returns useful opening options for debugging/API error messages.
    """
    if df.empty:
        return []

    required_cols = {"opening_name", "opening_family", "my_color"}
    missing_cols = required_cols.difference(df.columns)

    if missing_cols:
        return []

    color_norm = normalize_opening_text(color)

    color_df = df[
        df["my_color"].astype(str).str.strip().str.lower() == color_norm
    ].copy()

    if color_df.empty:
        return []

    grouped = (
        color_df
        .groupby(["opening_family", "opening_name"])
        .size()
        .reset_index(name="games")
        .sort_values("games", ascending=False)
        .head(limit)
    )

    return grouped.to_dict("records")