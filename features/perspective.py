import pandas as pd
import numpy as np

def add_user_perspective_columns(df: pd.DataFrame, username: str) -> pd.DataFrame:
    """
    Appends player-perspective features (is_white, my_color, my_result_raw, etc.)
    based on the provided username.

    Args:
        df: normalized DataFrame of chess games.
        username

    Returns:
        pd.DataFrame: new DataFrame with the user perspective columns appended.
    """
    if df.empty:
        out = df.copy()
        for col in [
            "is_white",
            "is_black",
            "my_color",
            "my_result_raw",
            "opp_result_raw",
            "my_rating",
            "opp_rating",
            "opp_username",
        ]:
            out[col] = pd.Series(dtype='object') # Guarantee column existence
        return out

    out = df.copy()
    
    # case insensitive
    target_user = username.lower()
    
    out["is_white"] = out["white_username"].str.lower().eq(target_user)
    out["is_black"] = out["black_username"].str.lower().eq(target_user)
    
    # find rows where it is NOT true that user is White or Black.
    # helped solving the case sensitivity
    invalid_mask = ~(out["is_white"] | out["is_black"])
    if invalid_mask.any():
        raise ValueError(f"Found {int(invalid_mask.sum())} invalid games where username {username!r} is neither white nor black.")

    # features
    # np.where(Condition, Do_This_If_True, Do_This_If_False)
    out["my_color"] = np.where(out["is_white"], "white", "black")
    out["my_result_raw"] = np.where(out["is_white"], out["white_result"], out["black_result"])
    out["opp_result_raw"] = np.where(out["is_white"], out["black_result"], out["white_result"])
    out["my_rating"] = np.where(out["is_white"], out["white_rating"], out["black_rating"])
    out["opp_rating"] = np.where(out["is_white"], out["black_rating"], out["white_rating"])
    out["opp_username"] = np.where(out["is_white"], out["black_username"], out["white_username"])

    return out