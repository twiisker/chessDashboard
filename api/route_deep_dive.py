import io
import os
from typing import Any

import chess.engine
import chess.pgn
from fastapi import APIRouter, HTTPException

from api.schemas import DeepDiveRequest
from chesscom.config import DB_PATH
from chesscom.fetcher import fetch_all_games
from chesscom.insertDB import ingest_games_to_duckdb
from features.pipeline import build_feature_frame
from ml.diagnostics import evaluate_opening
from api.opening_matching import (
    filter_opening_games,
    get_available_openings_for_color,
)

router = APIRouter(prefix="/api/v1", tags=["deep-dive"])

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "/usr/local/bin/stockfish")


@router.post("/deep_dive")
def serve_opening_diagnostics(request: DeepDiveRequest) -> dict[str, Any]:
    target_user = request.username.lower()
    target_color = request.color.lower()

    raw_games = fetch_all_games(target_user)
    if not raw_games:
        raise HTTPException(status_code=404, detail="No games found.")

    ingest_games_to_duckdb(raw_games, db_path=DB_PATH)

    df = build_feature_frame(
        username=target_user,
        db_path=DB_PATH,
        time_class=request.time_class,
        include_unrated=request.include_unrated,
        include_opening_clock=False,
    )

    target_df = filter_opening_games(
        df=df,
        opening_query=request.opening_name,
        color=target_color,
    ).tail(request.game_limit)

    if target_df.empty:
        available = get_available_openings_for_color(
            df=df,
            color=target_color,
            limit=20,
        )

        raise HTTPException(
            status_code=404,
            detail={
                "message": "Opening not found for this color/time_class.",
                "requested_opening": request.opening_name,
                "requested_color": target_color,
                "available_examples": available,
            },
        )
    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not start Stockfish at {STOCKFISH_PATH}: {exc}",
        )

    engine.configure({"Threads": 10, "Hash": 2048})

    results: list[dict[str, Any]] = []

    try:
        for _, row in target_df.iterrows():
            pgn_str = str(row["pgn"])
            pgn_stream = io.StringIO(pgn_str)
            game_obj = chess.pgn.read_game(pgn_stream)

            diag = evaluate_opening(
                game_obj,
                engine,
                target_user,
                ply_limit=20,
            )

            if diag is not None:
                enriched_diag: dict[str, Any] = dict(diag)
                enriched_diag["url"] = row.get("url", "")
                enriched_diag["end_time"] = str(row.get("end_time", ""))
                results.append(enriched_diag)

    finally:
        engine.quit()

    merged_pgn = "\n\n".join(target_df["pgn"].astype(str).tolist())

    return {
        "diagnostics": results,
        "merged_pgn": merged_pgn,
    }