import pandas as pd
import numpy as np


def add_user_perspective_columns(df: pd.DataFrame, username: str) -> pd.DataFrame:
    """
    Appends player-perspective features based on the provided username.
    """

    if df.empty:
        out = df.copy()

        out["is_white"] = pd.Series(dtype="bool")
        out["is_black"] = pd.Series(dtype="bool")
        out["my_color"] = pd.Series(dtype="object")
        out["my_result_raw"] = pd.Series(dtype="object")
        out["opp_result_raw"] = pd.Series(dtype="object")
        out["my_rating"] = pd.Series(dtype="float64")
        out["opp_rating"] = pd.Series(dtype="float64")
        out["opp_username"] = pd.Series(dtype="object")

        return out

    out = df.copy()

    target_user = username.lower()

    out["is_white"] = out["white_username"].astype(str).str.lower().eq(target_user)
    out["is_black"] = out["black_username"].astype(str).str.lower().eq(target_user)

    invalid_mask = ~(out["is_white"] | out["is_black"])
    if invalid_mask.any():
        raise ValueError(
            f"Found {int(invalid_mask.sum())} invalid games where username "
            f"{username!r} is neither white nor black."
        )

    out["my_color"] = np.where(out["is_white"], "white", "black")
    out["my_result_raw"] = np.where(
        out["is_white"],
        out["white_result"],
        out["black_result"],
    )
    out["opp_result_raw"] = np.where(
        out["is_white"],
        out["black_result"],
        out["white_result"],
    )

    out["my_rating"] = np.where(
        out["is_white"],
        out["white_rating"],
        out["black_rating"],
    )
    out["opp_rating"] = np.where(
        out["is_white"],
        out["black_rating"],
        out["white_rating"],
    )

    out["my_rating"] = pd.to_numeric(out["my_rating"], errors="coerce")
    out["opp_rating"] = pd.to_numeric(out["opp_rating"], errors="coerce")

    out["opp_username"] = np.where(
        out["is_white"],
        out["black_username"],
        out["white_username"],
    )

    return out