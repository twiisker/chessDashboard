import pandas as pd
import numpy as np
from typing import Final


MATCHUP_CATEGORIES: Final[list[str]] = ["Underdog", "Even Match", "Favorite"]
MATCHUP_BINS: Final[list[float]] = [-np.inf, -50.0, 50.0, np.inf]
# Panda: column of strings "Underdog", "Even Match", "Favorite" is generic object types
# pd.CategoricalDtype: column is strict multiple-choice with hierarchy."

MATCHUP_DTYPE: Final = pd.CategoricalDtype(
    categories=MATCHUP_CATEGORIES,
    ordered=True,
)


def compute_rating_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes rating delta and matchup category from the user's perspective.

    Requires:
      - my_rating
      - opp_rating

    Adds:
      - rating_delta: my_rating - opp_rating
      - matchup_type: Underdog / Even Match / Favorite
    """
    if df.empty:
        out = df.copy()
        out["rating_delta"] = pd.Series(dtype="float64")
        out["matchup_type"] = pd.Series(dtype=MATCHUP_DTYPE)
        return out

    required_cols = {"my_rating", "opp_rating"}
    missing_cols = required_cols.difference(df.columns)

    if missing_cols:
        raise KeyError(
            f"Missing required columns for rating features: {sorted(missing_cols)}. "
            "Run add_user_perspective_columns() before compute_rating_features()."
        )

    out = df.copy()

    out["my_rating"] = pd.to_numeric(out["my_rating"], errors="coerce")
    out["opp_rating"] = pd.to_numeric(out["opp_rating"], errors="coerce")

    # delta from user's perspective
    out["rating_delta"] = out["my_rating"] - out["opp_rating"]

    # pd.cut with right=False means the left edge is inclusive, right edge is exclusive.
    # delta of EXACTLY -50 falls into "Even Match".
    # delta of EXACTLY 50 falls into "Favorite".
    out["matchup_type"] = pd.cut(
        out["rating_delta"],
        bins=MATCHUP_BINS,
        labels=MATCHUP_CATEGORIES,
        right=False,
    ).astype(MATCHUP_DTYPE)

    return out