import pandas as pd
import numpy as np

from chesscom.constants import DRAW_RESULTS, LOSS_RESULTS
from chesscom.chess_types import SimpleResult


def compute_result_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Translates raw Chess.com termination reasons into standard result categories.

    Requires:
      - my_result_raw

    Adds:
      - simple_result: win / draw / loss
      - is_win: boolean
    """
    if df.empty:
        out = df.copy()
        out["simple_result"] = pd.Series(dtype="object")
        out["is_win"] = pd.Series(dtype="bool")
        return out

    if "my_result_raw" not in df.columns:
        raise KeyError(
            "Missing required column 'my_result_raw'. "
            "Run add_user_perspective_columns() before compute_result_columns()."
        )

    out = df.copy()

    result_raw = out["my_result_raw"].astype("string").str.lower()

    draw_results = {result.lower() for result in DRAW_RESULTS}
    loss_results = {result.lower() for result in LOSS_RESULTS}

    conditions = [
        result_raw.eq("win"),
        result_raw.isin(draw_results),
        result_raw.isin(loss_results),
    ]

    choices = [
        SimpleResult.WIN.value,
        SimpleResult.DRAW.value,
        SimpleResult.LOSS.value,
    ]

    out["simple_result"] = np.select(
        conditions,
        choices,
        default="unknown",
    )

    unknown_mask = out["simple_result"] == "unknown"
    if unknown_mask.any():
        unknowns = result_raw[unknown_mask].dropna().unique().tolist()
        raise ValueError(f"Unknown Chess.com result codes found: {unknowns}")

    out["is_win"] = out["simple_result"] == SimpleResult.WIN.value

    return out