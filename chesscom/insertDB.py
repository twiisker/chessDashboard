import duckdb
import pandas as pd
from dataclasses import asdict
from typeguard import typechecked
from pathlib import Path

from chesscom.fetcher import ChessGame
from chesscom.config import DB_PATH

CREATE_MATCHES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS matches (
    owner_username VARCHAR,
    url VARCHAR,
    pgn VARCHAR,
    time_control VARCHAR,
    end_time BIGINT,
    rated BOOLEAN,
    tcn VARCHAR,
    uuid VARCHAR,
    time_class VARCHAR,
    rules VARCHAR,

    white_username VARCHAR,
    white_rating INTEGER,
    white_result VARCHAR,
    white_id VARCHAR,
    white_uuid VARCHAR,

    black_username VARCHAR,
    black_rating INTEGER,
    black_result VARCHAR,
    black_id VARCHAR,
    black_uuid VARCHAR,

    eco VARCHAR,
    initial_setup VARCHAR,
    fen VARCHAR,
    tournament VARCHAR,
    start_time BIGINT,
    white_accuracy DOUBLE,
    black_accuracy DOUBLE
)
"""


CREATE_ENRICHED_VIEW_SQL = """
CREATE OR REPLACE VIEW matches_enriched AS
WITH extracted AS (
    SELECT
        *,
        REPLACE(regexp_extract(eco, '([^/]+)$', 1), '-', ' ') AS opening_specific_raw
    FROM matches
),
cleaned AS (
    SELECT
        *,
        REGEXP_REPLACE(opening_specific_raw, ' [0-9]+\\..*', '') AS opening_specific
    FROM extracted
),
enriched AS (
    SELECT
        *,
        COALESCE(
            NULLIF(
                REGEXP_EXTRACT(
                    opening_specific,
                    '^(.*?(?:Opening|Defense|Defence|Gambit|Game|Attack|System))',
                    1
                ),
                ''
            ),
            opening_specific
        ) AS opening_family,

        CASE
            WHEN LOWER(white_username) = LOWER(owner_username) THEN 'White'
            WHEN LOWER(black_username) = LOWER(owner_username) THEN 'Black'
            ELSE NULL
        END AS played_as,

        CASE
            WHEN LOWER(white_username) = LOWER(owner_username) THEN white_rating
            WHEN LOWER(black_username) = LOWER(owner_username) THEN black_rating
            ELSE NULL
        END AS owner_rating,
        
        CASE
            WHEN LOWER(white_username) = LOWER(owner_username) THEN black_username
            WHEN LOWER(black_username) = LOWER(owner_username) THEN white_username
            ELSE NULL
        END AS opponent_username,
        
        CASE
            WHEN LOWER(white_username) = LOWER(owner_username) THEN black_rating
            WHEN LOWER(black_username) = LOWER(owner_username) THEN white_rating
            ELSE NULL
        END AS opponent_rating,

        CASE
            WHEN (
                LOWER(white_username) = LOWER(owner_username)
                AND white_result = 'Win'
            )
            OR (
                LOWER(black_username) = LOWER(owner_username)
                AND black_result = 'Win'
            )
            THEN 'Win'

            WHEN (
                LOWER(white_username) = LOWER(owner_username)
                AND white_result IN (
                    'agreed', 'repetition', 'stalemate',
                    '50move', 'insufficient', 'timevsinsufficient'
                )
            )
            OR (
                LOWER(black_username) = LOWER(owner_username)
                AND black_result IN (
                    'agreed', 'repetition', 'stalemate',
                    '50move', 'insufficient', 'timevsinsufficient'
                )
            )
            THEN 'Draw'

            ELSE 'Loss'
        END AS outcome,

        to_timestamp(end_time) AS date_played,

        CAST(
            FLOOR(
                CASE
                    WHEN LOWER(white_username) = LOWER(owner_username) THEN white_rating
                    WHEN LOWER(black_username) = LOWER(owner_username) THEN black_rating
                    ELSE NULL
                END / 100
            ) * 100
            AS INTEGER
        ) AS rating_bucket

    FROM cleaned
)
SELECT *
FROM enriched
"""

@typechecked
def ingest_games_to_duckdb(
    games: list[ChessGame],
    db_path: str | Path = DB_PATH,
) -> None:
    if not games:
        print("No games found to ingest.")
        return

    games_data = [asdict(game) for game in games]
    df: pd.DataFrame = pd.DataFrame(games_data)  # type: ignore

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        con.register("games_df", df)

        con.execute(CREATE_MATCHES_TABLE_SQL)

        con.execute("""
            INSERT INTO matches BY NAME
            SELECT
                owner_username::VARCHAR AS owner_username,
                url::VARCHAR AS url,
                pgn::VARCHAR AS pgn,
                time_control::VARCHAR AS time_control,
                end_time::BIGINT AS end_time,
                rated::BOOLEAN AS rated,
                tcn::VARCHAR AS tcn,
                uuid::VARCHAR AS uuid,
                time_class::VARCHAR AS time_class,
                rules::VARCHAR AS rules,

                white_username::VARCHAR AS white_username,
                white_rating::INTEGER AS white_rating,
                white_result::VARCHAR AS white_result,
                white_id::VARCHAR AS white_id,
                white_uuid::VARCHAR AS white_uuid,

                black_username::VARCHAR AS black_username,
                black_rating::INTEGER AS black_rating,
                black_result::VARCHAR AS black_result,
                black_id::VARCHAR AS black_id,
                black_uuid::VARCHAR AS black_uuid,

                eco::VARCHAR AS eco,
                initial_setup::VARCHAR AS initial_setup,
                fen::VARCHAR AS fen,
                tournament::VARCHAR AS tournament,
                start_time::BIGINT AS start_time,
                white_accuracy::DOUBLE AS white_accuracy,
                black_accuracy::DOUBLE AS black_accuracy
            FROM games_df
            WHERE NOT EXISTS (
                SELECT 1
                FROM matches m
                WHERE m.owner_username = games_df.owner_username
                  AND m.uuid = games_df.uuid
            )
        """)

        con.execute(CREATE_ENRICHED_VIEW_SQL)

        result = con.execute("SELECT COUNT(*) FROM matches").fetchone()
        total_rows = int(result[0]) if result else 0

        print(
            f"\nSuccess: Appended new games."
            f"\nTotal records in 'matches' table: {total_rows}"
        )
