from chesscom.config import DB_PATH
from chesscom.peers import create_peer_cohort

from features.pipeline import (
    build_feature_frame,
    build_peer_group_feature_frame,
)

from aggregations.peer_comparison import (
    get_overall_peer_comparison,
    get_opening_peer_comparison,
    get_opening_play_share_gap,
    get_opening_score_gap,
    get_repertoire_width_comparison,
    get_top_n_opening_share,
    get_rating_bucket_comparison,
    get_peer_leaderboard,
)

def main() -> None:
    target_username = ""
    time_class = "rapid"

    print(f"Using DB: {DB_PATH}")
    print(f"Target user: {target_username}")
    print(f"Time class: {time_class}")

    peers = create_peer_cohort(
        target_username=target_username,
        db_path=DB_PATH,
        max_peers=10,
        time_class=time_class,
        rating_window=100,
        refresh=False,
    )

    print(f"\nPeers found: {len(peers)}")
    print(peers[:10])

    user_df = build_feature_frame(
        username=target_username,
        db_path=DB_PATH,
        time_class=time_class,
        include_unrated=False,
        include_opening_clock=False,
    )

    peer_df = build_peer_group_feature_frame(
        target_username=target_username,
        peers=peers,
        db_path=DB_PATH,
        time_class=time_class,
        include_unrated=False,
        include_opening_clock=False,
    )

    print(f"\nUser games: {len(user_df)}")
    print(f"Peer games: {len(peer_df)}")

    print("\nUser columns:")
    print(user_df.columns.tolist())

    print("\nPeer columns:")
    print(peer_df.columns.tolist())

    overall_df = get_overall_peer_comparison(user_df, peer_df)
    opening_comparison_df = get_opening_peer_comparison(
        user_df,
        peer_df,
        min_games=10,
    )
    opening_gap_df = get_opening_play_share_gap(opening_comparison_df)
    opening_score_gap_df = get_opening_score_gap(opening_comparison_df)
    repertoire_width_df = get_repertoire_width_comparison(user_df, peer_df)
    top3_share_df = get_top_n_opening_share(user_df, peer_df, n=3)
    rating_bucket_df = get_rating_bucket_comparison(user_df, peer_df)
    peer_leaderboard_df = get_peer_leaderboard(peer_df)

    print("\n=== Overall comparison ===")
    print(overall_df)

    print("\n=== Opening comparison ===")
    print(opening_comparison_df.head(20))

    print("\n=== Opening play-share gap ===")
    print(opening_gap_df.head(20))

    print("\n=== Opening score gap ===")
    print(opening_score_gap_df.head(20))

    print("\n=== Repertoire width ===")
    print(repertoire_width_df)

    print("\n=== Top 3 opening share ===")
    print(top3_share_df)

    print("\n=== Rating bucket comparison ===")
    print(rating_bucket_df.head(20))

    print("\n=== Peer leaderboard ===")
    print(peer_leaderboard_df.head(20))


if __name__ == "__main__":
    main()