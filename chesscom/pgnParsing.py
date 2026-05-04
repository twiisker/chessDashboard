import io
import chess.pgn

def parse_pgn(raw_pgn: str | None) -> chess.pgn.Game | None:
    """converts a raw PGN string into a python-chess Game object."""
    if not isinstance(raw_pgn, str) or not raw_pgn.strip():
        return None
        
    try:
        pgn_stream = io.StringIO(raw_pgn)
        game = chess.pgn.read_game(pgn_stream)
        return game
    except Exception:
        return None