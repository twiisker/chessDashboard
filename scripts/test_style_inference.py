from chesscom.config import DB_PATH
from features.pipeline import build_feature_frame
from ml.style_inference import infer_player_style_from_df


def main() -> None:
    username = "forrest_gump"

    df = build_feature_frame(
        username=username,
        db_path=DB_PATH,
        time_class="rapid",
        include_unrated=False,
        include_opening_clock=False,
    )

    result = infer_player_style_from_df(df)

    print("Profile:")
    print(result["profile"])

    print("\nStyle:")
    print(result["style"])


if __name__ == "__main__":
    main()