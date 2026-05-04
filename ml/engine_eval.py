import chess.engine


def extract_float_score(
    pov_score: chess.engine.PovScore,
    am_i_white: bool,
) -> float:
    """
    Converts an engine score into the user's perspective.

    Returns pawn units:
      +1.50 means the user is better by about 1.5 pawns.
      -0.70 means the user is worse by about 0.7 pawns.

    Mate scores are capped at +/-103.0.
    """
    my_score: chess.engine.Score = (
        pov_score.white() if am_i_white else pov_score.black()
    )

    if my_score.is_mate():
        mate_in_x = my_score.mate()

        if mate_in_x is None:
            return 0.0

        return 103.0 if mate_in_x >= 0 else -103.0

    raw_cp = my_score.score()

    if raw_cp is None:
        return 0.0

    return round(raw_cp / 100.0, 2)