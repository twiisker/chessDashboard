import pandas as pd


def compute_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds calendar/time features.

    Requires:
      - end_time

    Adds:
      - end_time: converted to datetime if needed
      - weekday
      - hour
      - year_month
    """
    if df.empty:
        out = df.copy()
        out["weekday"] = pd.Series(dtype="object")
        out["hour"] = pd.Series(dtype="Int64")
        out["year_month"] = pd.Series(dtype="object")
        return out

    if "end_time" not in df.columns:
        raise KeyError("Missing required column 'end_time'.")

    out = df.copy()

    # If end_time comes from DuckDB/raw Chess.com, it is usually Unix seconds.
    # If it is already datetime, this keeps it as datetime.
    if not pd.api.types.is_datetime64_any_dtype(out["end_time"]):
        out["end_time"] = pd.to_datetime(out["end_time"], unit="s", utc=True)
    else:
        out["end_time"] = pd.to_datetime(out["end_time"], utc=True)

    out["weekday"] = out["end_time"].dt.day_name()
    out["hour"] = out["end_time"].dt.hour.astype("Int64")

    # Period dtype can be annoying in JSON/API responses, so store as string.
    out["year_month"] = out["end_time"].dt.strftime("%Y-%m")

    return out