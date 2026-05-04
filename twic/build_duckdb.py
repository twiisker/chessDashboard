import argparse
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb
from tqdm import tqdm


TWIC_ROW = Tuple[
    str,          # Event
    Optional[str],# Date
    str,          # White
    str,          # Black
    str,          # Result
    int,          # WhiteElo
    int,          # BlackElo
    str,          # ECO
    str,          # Opening
    str,          # Moves
    str,          # OpeningFingerprint
]


def fast_parse_pgn_file(filepath: Path) -> List[TWIC_ROW]:
    """
    Fast text parser for TWIC PGNs.

    Extracts:
      - headers
      - full move text
      - first 10 SAN tokens as OpeningFingerprint
    """
    games_data: List[TWIC_ROW] = []

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        headers: Dict[str, str] = {}
        moves_lines: List[str] = []
        in_moves = False

        def flush_game() -> None:
            nonlocal headers, moves_lines, in_moves

            if not moves_lines:
                return

            full_move_text = " ".join(moves_lines)

            white_elo_str = headers.get("WhiteElo", "0")
            black_elo_str = headers.get("BlackElo", "0")

            white_elo = int(white_elo_str) if white_elo_str.isdigit() else 0
            black_elo = int(black_elo_str) if black_elo_str.isdigit() else 0

            date_val: Optional[str] = headers.get("Date")
            if date_val:
                date_val = date_val.replace(".", "-")

            clean_text = re.sub(r"\d+\.+", "", full_move_text)
            clean_text = re.sub(r"(1-0|0-1|1/2-1/2|\*)", "", clean_text)
            clean_text = re.sub(r"\{[^}]*\}", "", clean_text)
            clean_text = re.sub(r"\([^)]*\)", "", clean_text)

            tokens = clean_text.split()
            fingerprint = " ".join(tokens[:10])

            games_data.append(
                (
                    headers.get("Event", "Unknown"),
                    date_val,
                    headers.get("White", "Unknown"),
                    headers.get("Black", "Unknown"),
                    headers.get("Result", "*"),
                    white_elo,
                    black_elo,
                    headers.get("ECO", ""),
                    headers.get("Opening", ""),
                    full_move_text,
                    fingerprint,
                )
            )

            headers = {}
            moves_lines = []
            in_moves = False

        for raw_line in f:
            line = raw_line.strip()

            if not line:
                if in_moves and moves_lines:
                    flush_game()
                continue

            if line.startswith("[") and line.endswith("]"):
                parts = line[1:-1].split(' "', 1)
                if len(parts) == 2:
                    key = parts[0]
                    val = parts[1][:-1]
                    headers[key] = val
                in_moves = False
            else:
                in_moves = True
                moves_lines.append(line)

        if in_moves and moves_lines:
            flush_game()

    return games_data


class ChessDatabaseBuilder:
    def __init__(
        self,
        db_path: str = "twic/data/twic_data.duckdb",
        pgn_dir: str = "twic/data/pgns",
        reset: bool = False,
    ):
        self.db_path = Path(db_path)
        self.pgn_dir = Path(pgn_dir)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = duckdb.connect(str(self.db_path))

        if reset:
            self.conn.execute("DROP TABLE IF EXISTS twic_games")

        self._initialize_schema()

    def _initialize_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS twic_games (
                Event VARCHAR,
                Date VARCHAR,
                White VARCHAR,
                Black VARCHAR,
                Result VARCHAR,
                WhiteElo INTEGER,
                BlackElo INTEGER,
                ECO VARCHAR,
                Opening VARCHAR,
                Moves TEXT,
                OpeningFingerprint TEXT
            )
            """
        )

    def process_all_files(self) -> None:
        pgn_files = sorted(self.pgn_dir.glob("*.pgn"))

        if not pgn_files:
            print(f"No PGN files found in {self.pgn_dir}")
            return

        print(f"Found {len(pgn_files)} PGN files to process.")

        self.conn.execute("BEGIN TRANSACTION")

        try:
            max_workers = os.cpu_count() or 4

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                future_to_path = {
                    executor.submit(fast_parse_pgn_file, filepath): filepath
                    for filepath in pgn_files
                }

                for future in tqdm(
                    as_completed(future_to_path),
                    total=len(pgn_files),
                    desc="Parsing PGNs",
                ):
                    filepath = future_to_path[future]

                    try:
                        batch_data = future.result()

                        if batch_data:
                            self.conn.executemany(
                                """
                                INSERT INTO twic_games
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                batch_data,
                            )

                    except Exception as exc:
                        print(f"\n{filepath} generated an exception: {exc}")

            self.conn.execute("COMMIT")
            print("\nDatabase build complete.")

        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def verify_database(self) -> None:
        row = self.conn.execute("SELECT COUNT(*) FROM twic_games").fetchone()
        count = row[0] if row is not None else 0

        print(f"Total games stored: {count}")

        result = self.conn.execute(
            """
            SELECT Opening, COUNT(*) AS games
            FROM twic_games
            WHERE Opening IS NOT NULL AND Opening != ''
            GROUP BY Opening
            ORDER BY games DESC
            LIMIT 10
            """
        ).fetchall()

        print("\nTop 10 openings:")
        for opening, games in result:
            print(f"- {opening}: {games}")

    def close(self) -> None:
        self.conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="twic/data/twic_data.duckdb")
    parser.add_argument("--pgn-dir", default="twic/data/pgns")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    builder = ChessDatabaseBuilder(
        db_path=args.db_path,
        pgn_dir=args.pgn_dir,
        reset=args.reset,
    )

    try:
        builder.process_all_files()
        builder.verify_database()
    finally:
        builder.close()


if __name__ == "__main__":
    main()