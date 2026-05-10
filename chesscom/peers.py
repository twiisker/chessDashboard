import duckdb
from pathlib import Path

from chesscom.fetcher import fetch_all_games
from chesscom.insertDB import ingest_games_to_duckdb
from chesscom.config import DB_PATH


CREATE_PEER_COHORT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS peer_cohort_members (
    target_username VARCHAR,
    peer_username VARCHAR,
    source_game_uuid VARCHAR,
    source_game_date TIMESTAMP,
    time_class VARCHAR,
    target_rating INTEGER,
    peer_rating INTEGER,
    rating_diff INTEGER,
    cohort_name VARCHAR,
    created_at TIMESTAMP DEFAULT current_timestamp
)
"""

def create_peer_cohort(
    target_username: str,
    db_path: str | Path = DB_PATH,
    max_peers: int = 50,
    time_class: str = "rapid",
    cohort_name: str | None = None,
    rating_window: int | None = None,
    refresh: bool = True,
) -> list[str]:
    """
    Selects the last N unique opponents for a target user in a specific time control
    and stores them in peer_cohort_members.

    Important:
      - avoids duplicate peer rows
      - reuses an existing cohort when refresh=False
      - separates cohorts by rating_window
    """

    if cohort_name is None:
        rating_label = "any" if rating_window is None else f"rw_{rating_window}"
        cohort_name = f"last_{max_peers}_{time_class}_{rating_label}"

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    rating_filter = ""
    params: list[object] = [
        target_username,
        time_class,
    ]

    if rating_window is not None:
        rating_filter = """
          AND owner_rating IS NOT NULL
          AND opponent_rating IS NOT NULL
          AND ABS(owner_rating - opponent_rating) <= ?
        """
        params.append(rating_window)

    params.extend([cohort_name, max_peers])

    insert_query = f"""
        INSERT INTO peer_cohort_members BY NAME
        WITH candidate_games AS (
            SELECT
                owner_username AS target_username,
                opponent_username AS peer_username,
                uuid AS source_game_uuid,
                date_played AS source_game_date,
                time_class,
                owner_rating AS target_rating,
                opponent_rating AS peer_rating,
                ABS(owner_rating - opponent_rating) AS rating_diff,

                ROW_NUMBER() OVER (
                    PARTITION BY LOWER(opponent_username)
                    ORDER BY date_played DESC
                ) AS opponent_recency_rank

            FROM matches_enriched
            WHERE LOWER(owner_username) = LOWER(?)
              AND time_class = ?
              AND opponent_username IS NOT NULL
              {rating_filter}
        ),
        selected AS (
            SELECT
                target_username,
                peer_username,
                source_game_uuid,
                source_game_date,
                time_class,
                target_rating,
                peer_rating,
                rating_diff,
                ? AS cohort_name
            FROM candidate_games
            WHERE opponent_recency_rank = 1
            ORDER BY source_game_date DESC
            LIMIT ?
        )
        SELECT *
        FROM selected
    """

    with duckdb.connect(str(db_path)) as con:
        con.execute(CREATE_PEER_COHORT_TABLE_SQL)

        if not refresh:
            existing_df = con.execute(
                """
                WITH ranked AS (
                    SELECT
                        peer_username,
                        source_game_date,
                        ROW_NUMBER() OVER (
                            PARTITION BY LOWER(peer_username)
                            ORDER BY source_game_date DESC
                        ) AS rn
                    FROM peer_cohort_members
                    WHERE LOWER(target_username) = LOWER(?)
                      AND cohort_name = ?
                      AND time_class = ?
                )
                SELECT peer_username
                FROM ranked
                WHERE rn = 1
                ORDER BY source_game_date DESC
                LIMIT ?
                """,
                [target_username, cohort_name, time_class, max_peers],
            ).df()

            if not existing_df.empty:
                return existing_df["peer_username"].dropna().tolist()

        con.execute(
            """
            DELETE FROM peer_cohort_members
            WHERE LOWER(target_username) = LOWER(?)
              AND cohort_name = ?
              AND time_class = ?
            """,
            [target_username, cohort_name, time_class],
        )

        con.execute(insert_query, params)

        peers_df = con.execute(
            """
            WITH ranked AS (
                SELECT
                    peer_username,
                    source_game_date,
                    ROW_NUMBER() OVER (
                        PARTITION BY LOWER(peer_username)
                        ORDER BY source_game_date DESC
                    ) AS rn
                FROM peer_cohort_members
                WHERE LOWER(target_username) = LOWER(?)
                  AND cohort_name = ?
                  AND time_class = ?
            )
            SELECT peer_username
            FROM ranked
            WHERE rn = 1
            ORDER BY source_game_date DESC
            LIMIT ?
            """,
            [target_username, cohort_name, time_class, max_peers],
        ).df()

    return peers_df["peer_username"].dropna().tolist()


def download_peer_games(
    target_username: str,
    db_path: str | Path = DB_PATH,
    max_peers: int = 50,
    time_class: str = "rapid",
    cohort_name: str | None = None,
    rating_window: int | None = None,
    refresh: bool = True,
) -> list[str]:
    """
    Creates/refetches a peer cohort and downloads each peer's games into the same database.
    """

    peers = create_peer_cohort(
        target_username=target_username,
        db_path=db_path,
        max_peers=max_peers,
        time_class=time_class,
        cohort_name=cohort_name,
        rating_window=rating_window,
        refresh=refresh,
    )

    # Defensive dedupe, preserving order.
    peers = list(dict.fromkeys(peers))

    print(f"\nFound {len(peers)} {time_class} peers for {target_username}:")
    for peer in peers:
        print(f"  - {peer}")

    for peer in peers:
        print(f"\nDownloading peer games for {peer}...")
        games = fetch_all_games(peer)
        ingest_games_to_duckdb(games, db_path=db_path)

    return peers