from fetcher import fetch_all_games
from insertDB import ingest_games_to_duckdb

"""
    'ratatwIIsk3r',
    'VincentKeymer',
    'MagnusCarlsen',
    'GothamChess',
    'Hikaru'
"""


USERS = [
    'forrest_gump',
]


def main() -> None:
    for username in USERS:
        print(f"\nDownloading games for {username}...")
        games = fetch_all_games(username)
        ingest_games_to_duckdb(games)


if __name__ == "__main__":
    main()
