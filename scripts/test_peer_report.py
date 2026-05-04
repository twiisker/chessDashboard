from chesscom.config import DB_PATH
from aggregations.peer_report import build_peer_report


def main() -> None:
    report = build_peer_report(
        target_username="",
        db_path=DB_PATH,
        time_class="rapid",
        max_peers=10,
        rating_window=100,
        max_games_per_peer=500,
        refresh=False,
        include_opening_clock=False,
    )

    print("Report keys:")
    print(report.keys())

    print("\nPeer count:")
    print(report["peer_count"])

    print("\nUser games:")
    print(report["user_game_count"])

    print("\nPeer games:")
    print(report["peer_game_count"])

    print("\nOverall:")
    print(report["overall"])

    print("\nOpening comparison first 3:")
    print(report["opening_comparison"][:3])


if __name__ == "__main__":
    main()