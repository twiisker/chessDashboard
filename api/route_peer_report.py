from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from api.schemas import PeerReportRequest
from aggregations.peer_report import build_peer_report
from chesscom.config import DB_PATH


router = APIRouter(prefix="/api/v1", tags=["peer-report"])


@router.post("/peer-report")
def serve_peer_report(request: PeerReportRequest):
    try:
        report = build_peer_report(
            target_username=request.username.lower(),
            db_path=DB_PATH,
            time_class=request.time_class,
            max_peers=request.max_peers,
            rating_window=request.rating_window,
            refresh=request.refresh,
            max_games_per_peer=request.max_games_per_peer,
            include_unrated=request.include_unrated,
            include_opening_clock=request.include_opening_clock,
        )

        return jsonable_encoder(report)

    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build peer report: {exc}",
        )