import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from api.schemas import UserSearchRequest
from chesscom.config import DB_PATH
from chesscom.fetcher import fetch_all_games
from chesscom.insertDB import ingest_games_to_duckdb
from features.pipeline import build_feature_frame


router = APIRouter(prefix="/api/v1", tags=["analysis"])


EXPORT_COLS = [
    "time_class",
    "simple_result",
    "is_win",
    "my_result_raw",
    "opp_result_raw",
    "hour",
    "weekday",
    "year_month",
    "opening_name",
    "opening_family",
    "eco",
    "matchup_type",
    "rating_delta",
    "my_rating",
    "opp_rating",
    "my_color",
    "opp_username",
    "end_time",
    "url",
    "time_spent_opening",
]


@router.post("/analyze")
def analyze_user_live(request: UserSearchRequest):
    username = request.username.lower()

    raw_games = fetch_all_games(username)
    if not raw_games:
        raise HTTPException(
            status_code=404,
            detail=f"No games found for user: {username}",
        )

    ingest_games_to_duckdb(raw_games, db_path=DB_PATH)

    df = build_feature_frame(
        username=username,
        db_path=DB_PATH,
        time_class=request.time_class,
        include_unrated=request.include_unrated,
        include_opening_clock=True,
    )

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No matching games found for user: {username}",
        )

    if "end_time" in df.columns:
        df["end_time"] = df["end_time"].astype(str)

    available_cols = [col for col in EXPORT_COLS if col in df.columns]

    df_export = df[available_cols].copy()
    df_export = df_export.astype(object).where(pd.notna(df_export), None)

    return jsonable_encoder(
        {"games": df_export.to_dict(orient="records")}
    )