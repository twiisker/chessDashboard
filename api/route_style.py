from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from api.schemas import UserSearchRequest
from chesscom.config import DB_PATH
from chesscom.fetcher import fetch_all_games
from chesscom.insertDB import ingest_games_to_duckdb
from features.pipeline import build_feature_frame
from ml.style_inference import infer_player_style_from_df


router = APIRouter(prefix="/api/v1", tags=["style"])


@router.post("/style")
def serve_style_report(request: UserSearchRequest) -> dict[str, Any]:
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
        include_opening_clock=False,
    )

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No matching games found for user: {username}",
        )

    try:
        result = infer_player_style_from_df(df)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to infer player style: {exc}",
        )

    return jsonable_encoder(result)