from peers import download_peer_games
from config import DB_PATH

def main() -> None:
    download_peer_games(
        target_username="forrest_gump",
        db_path=DB_PATH,
        max_peers=50,
        time_class="rapid",
        rating_window=100,
        refresh=True
    )


if __name__ == "__main__":
    main()
