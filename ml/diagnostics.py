import chess.pgn
import chess.engine
from typing import TypedDict

from ml.engine_eval import extract_float_score


class OpeningDiagnostic(TypedDict):
    total_cpl_loss: float
    avg_cpl_loss: float
    my_worst_cpl: float
    my_worst_move: str
    opp_worst_cpl: float
    opp_worst_move: str
    missed_punishment: bool
    punishment_cpl: float
    best_engine_move: str
    my_actual_response: str


def _score_from_info(
    info: chess.engine.InfoDict,
    am_i_white: bool,
) -> float:
    score = info.get("score")

    if score is None:
        return 0.0

    return extract_float_score(score, am_i_white)


def evaluate_opening(
    game: chess.pgn.Game | None,
    engine: chess.engine.SimpleEngine,
    username: str,
    ply_limit: int = 20,
    engine_time: float = 0.05,
) -> OpeningDiagnostic | None:
    """
    Runs Stockfish over the first N plies and calculates opening diagnostics
    from the user's perspective.
    """
    if game is None:
        return None

    target_user = username.lower()

    white_player = game.headers.get("White", "").lower()
    black_player = game.headers.get("Black", "").lower()

    if white_player == target_user:
        am_i_white = True
    elif black_player == target_user:
        am_i_white = False
    else:
        return None

    current_ply = 0
    total_cpl_loss = 0.0
    my_moves_analyzed = 0

    my_worst_cpl = 0.0
    my_worst_move = "None"

    opp_worst_cpl = 0.0
    opp_worst_move = "None"

    waiting_to_punish = False
    my_punishment_cpl = 0.0
    my_response_move = "None"
    engine_best_move = "None"

    initial_info = engine.analyse(
        game.board(),
        chess.engine.Limit(time=engine_time),
    )
    previous_eval = _score_from_info(initial_info, am_i_white)

    for node in game.mainline():
        current_ply += 1

        info = engine.analyse(
            node.board(),
            chess.engine.Limit(time=engine_time),
        )
        current_eval = _score_from_info(info, am_i_white)

        white_just_moved = current_ply % 2 != 0
        i_just_moved = (
            (am_i_white and white_just_moved)
            or ((not am_i_white) and (not white_just_moved))
        )

        actual_move_number = (current_ply + 1) // 2

        if i_just_moved:
            my_moves_analyzed += 1
            cpl = previous_eval - current_eval

            if cpl > 0:
                total_cpl_loss += cpl

                if cpl > my_worst_cpl:
                    my_worst_cpl = cpl
                    my_worst_move = f"Move {actual_move_number}: {node.san()}"

            if waiting_to_punish:
                my_punishment_cpl = max(0.0, cpl)
                my_response_move = node.san()
                waiting_to_punish = False

        else:
            opp_cpl = current_eval - previous_eval

            if opp_cpl > 0 and opp_cpl > opp_worst_cpl:
                opp_worst_cpl = opp_cpl
                opp_worst_move = f"Move {actual_move_number}: {node.san()}"
                waiting_to_punish = True

                if "pv" in info and len(info["pv"]) > 0:
                    try:
                        engine_best_move = node.board().san(info["pv"][0])
                    except Exception:
                        engine_best_move = "None"

        previous_eval = current_eval

        if current_ply >= ply_limit and not waiting_to_punish:
            break

    if my_moves_analyzed == 0:
        return None

    avg_cpl = total_cpl_loss / my_moves_analyzed

    return {
        "total_cpl_loss": round(total_cpl_loss, 2),
        "avg_cpl_loss": round(avg_cpl, 2),
        "my_worst_cpl": round(my_worst_cpl, 2),
        "my_worst_move": my_worst_move,
        "opp_worst_cpl": round(opp_worst_cpl, 2),
        "opp_worst_move": opp_worst_move,
        "missed_punishment": (
            opp_worst_cpl > 1.0
            and my_punishment_cpl >= 0.5
            and my_response_move != engine_best_move
        ),
        "punishment_cpl": round(my_punishment_cpl, 2),
        "best_engine_move": engine_best_move,
        "my_actual_response": my_response_move,
    }