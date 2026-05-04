from typing import Any

from fastapi import APIRouter, HTTPException

from api.schemas import RepertoireTreeRequest
from api.twic_helpers import fetch_twic_games_for_repertoire
from chesscom.config import DB_PATH
from chesscom.fetcher import fetch_all_games
from chesscom.insertDB import ingest_games_to_duckdb
from features.pipeline import build_feature_frame
from ml.polyglot_builder import HumanFirstRepertoireBuilder


router = APIRouter(prefix="/api/v1", tags=["repertoire"])


@router.post("/repertoire_tree")
def get_repertoire_tree(request: RepertoireTreeRequest) -> dict[str, Any]:
    username = request.username.lower()
    target_opening = request.opening_name
    color = request.color.lower()

    raw_games = fetch_all_games(username)
    if not raw_games:
        raise HTTPException(status_code=404, detail="No games found.")

    ingest_games_to_duckdb(raw_games, db_path=DB_PATH)

    user_df = build_feature_frame(
        username=username,
        db_path=DB_PATH,
        time_class=request.time_class,
        include_unrated=request.include_unrated,
        include_opening_clock=False,
    )

    builder = HumanFirstRepertoireBuilder(
        target_color=color,
        depth_limit=10,
    )

    builder.build_user_pass(
        user_df,
        target_opening=target_opening,
    )

    if builder.root.user_count == 0:
        from api.opening_matching import get_available_openings_for_color

        available = get_available_openings_for_color(
            df=user_df,
            color=color,
            limit=20,
        )

        raise HTTPException(
            status_code=404,
            detail={
                "message": "Opening not found for this color/time_class.",
                "requested_opening": target_opening,
                "requested_color": color,
                "available_examples": available,
            },
        )

    twic_df = fetch_twic_games_for_repertoire(
        builder,
        target_opening,
    )

    builder.build_gm_pass(twic_df)
    study_pgn = builder.export_to_lichess_study(target_opening)

    return {
        "tree": builder.root.to_dict(),
        "study_pgn": study_pgn,
        "gm_games_loaded": int(len(twic_df)),
    }