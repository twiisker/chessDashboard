import pandas as pd
import chess.pgn

from chesscom.pgnParsing import parse_pgn


def _parse_time_control(tc_str: str | None) -> tuple[float, float] | None:
    """
    Parses a Chess.com TimeControl string into:

      (base_seconds, increment_seconds)

    Examples:
      "300+5" -> (300.0, 5.0)
      "600"   -> (600.0, 0.0)

    Returns None for unsupported formats like daily/correspondence games.
    """
    if not isinstance(tc_str, str) or not tc_str.strip():
        return None

    tc_str = tc_str.strip()

    try:
        if "+" in tc_str:
            base, increment = tc_str.split("+", maxsplit=1)
            return float(base), float(increment)

        if tc_str.replace(".", "", 1).isdigit():
            return float(tc_str), 0.0

    except ValueError:
        return None

    return None


def get_opening_clock_usage(
    game: chess.pgn.Game | None,
    username: str,
    ply_limit: int = 20,
) -> float | None:
    """
    Calculates seconds spent by username in the first N plies.

    Default ply_limit=20 means first 10 full moves.
    Returns None if:
      - PGN is missing
      - clock comments are missing
      - time control is unsupported
      - username cannot be matched to White or Black
      - game ended before ply_limit
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

    tc_str = game.headers.get("TimeControl", "")
    parsed_tc = _parse_time_control(tc_str)

    if parsed_tc is None:
        return None

    base_seconds, increment_seconds = parsed_tc

    current_ply = 0
    my_moves_played = 0
    my_last_clock: float | None = None

    for node in game.mainline():
        current_ply += 1
        white_just_moved = current_ply % 2 != 0

        user_just_moved = (
            (am_i_white and white_just_moved)
            or ((not am_i_white) and (not white_just_moved))
        )

        if user_just_moved:
            my_moves_played += 1
            node_clock = node.clock()

            if node_clock is None:
                return None

            my_last_clock = float(node_clock)

        if current_ply >= ply_limit:
            break

    if current_ply < ply_limit:
        return None

    if my_last_clock is None:
        return None

    time_spent = base_seconds + (my_moves_played * increment_seconds) - my_last_clock

    # Defensive guard against bad/missing clock data.
    if time_spent < 0:
        return None

    return round(time_spent, 2)


def add_opening_time_feature(
    df: pd.DataFrame,
    username: str,
    ply_limit: int = 20,
) -> pd.DataFrame:
    """
    Adds time_spent_opening.

    time_spent_opening = seconds spent by username during the first N plies.
    """
    out = df.copy()

    if out.empty:
        out["time_spent_opening"] = pd.Series(dtype="float64")
        return out

    if "pgn" not in out.columns:
        out["time_spent_opening"] = pd.Series([None] * len(out), dtype="float64")
        return out

    out["time_spent_opening"] = [
        get_opening_clock_usage(parse_pgn(pgn), username, ply_limit)
        for pgn in out["pgn"]
    ]

    return out