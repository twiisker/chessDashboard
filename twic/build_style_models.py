import argparse
import json
from pathlib import Path
from typing import Final

import duckdb
import joblib  # type: ignore
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


FEATURE_COLUMNS: Final[list[str]] = [
    "white_win_rate",
    "black_win_rate",
    "white_avg_moves",
    "black_avg_moves",
    "white_draw_rate",
    "black_draw_rate",
    "white_avg_captures",
    "black_avg_captures",
    "white_avg_checks",
    "black_avg_checks",
    "white_unique_openings",
    "black_unique_openings",
    "white_avg_opp_elo",
    "black_avg_opp_elo",
]


PROFILE_QUERY = """
WITH white_stats AS (
    SELECT
        White AS Player,
        COUNT(*) AS total_white_games,
        AVG(CASE WHEN Result = '1-0' THEN 1.0 ELSE 0.0 END) AS white_win_rate,
        AVG(LENGTH(Moves) - LENGTH(REPLACE(Moves, '.', ''))) AS white_avg_moves,
        AVG(CASE WHEN Result = '1/2-1/2' THEN 1.0 ELSE 0.0 END) AS white_draw_rate,
        AVG(LENGTH(Moves) - LENGTH(REPLACE(Moves, 'x', ''))) AS white_avg_captures,
        AVG(LENGTH(Moves) - LENGTH(REPLACE(Moves, '+', ''))) AS white_avg_checks,
        COUNT(DISTINCT ECO) AS white_unique_openings,
        AVG(BlackElo) AS white_avg_opp_elo
    FROM twic_games
    WHERE White IS NOT NULL
      AND White != ''
      AND WhiteElo > 0
      AND BlackElo > 0
    GROUP BY White
),

black_stats AS (
    SELECT
        Black AS Player,
        COUNT(*) AS total_black_games,
        AVG(CASE WHEN Result = '0-1' THEN 1.0 ELSE 0.0 END) AS black_win_rate,
        AVG(LENGTH(Moves) - LENGTH(REPLACE(Moves, '.', ''))) AS black_avg_moves,
        AVG(CASE WHEN Result = '1/2-1/2' THEN 1.0 ELSE 0.0 END) AS black_draw_rate,
        AVG(LENGTH(Moves) - LENGTH(REPLACE(Moves, 'x', ''))) AS black_avg_captures,
        AVG(LENGTH(Moves) - LENGTH(REPLACE(Moves, '+', ''))) AS black_avg_checks,
        COUNT(DISTINCT ECO) AS black_unique_openings,
        AVG(WhiteElo) AS black_avg_opp_elo
    FROM twic_games
    WHERE Black IS NOT NULL
      AND Black != ''
      AND WhiteElo > 0
      AND BlackElo > 0
    GROUP BY Black
)

SELECT
    w.Player,
    (w.total_white_games + b.total_black_games) AS total_games,
    w.white_win_rate,
    b.black_win_rate,
    w.white_avg_moves,
    b.black_avg_moves,
    w.white_draw_rate,
    b.black_draw_rate,
    w.white_avg_captures,
    b.black_avg_captures,
    w.white_avg_checks,
    b.black_avg_checks,
    w.white_unique_openings,
    b.black_unique_openings,
    w.white_avg_opp_elo,
    b.black_avg_opp_elo
FROM white_stats w
JOIN black_stats b ON w.Player = b.Player
WHERE (w.total_white_games + b.total_black_games) >= ?
ORDER BY total_games DESC
"""


def load_gm_profiles(
    db_path: Path,
    min_games: int,
) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(f"TWIC DuckDB not found: {db_path}")

    with duckdb.connect(str(db_path), read_only=True) as con:
        tables = con.execute("SHOW TABLES").df()["name"].tolist()

        if "twic_games" not in tables:
            raise RuntimeError(
                f"Expected table 'twic_games' in {db_path}, found: {tables}"
            )

        df = con.execute(PROFILE_QUERY, [min_games]).df()

    if df.empty:
        raise RuntimeError(
            f"No GM profiles created. Try lowering --min-games below {min_games}."
        )

    df = df.dropna(subset=FEATURE_COLUMNS).copy()

    if df.empty:
        raise RuntimeError("All GM profiles had missing feature values.")

    return df


def build_models(
    profiles_df: pd.DataFrame,
    n_clusters: int,
    n_neighbors: int,
    random_state: int,
) -> tuple[StandardScaler, PCA, KMeans, NearestNeighbors, pd.DataFrame, pd.DataFrame]:
    features_df = profiles_df[FEATURE_COLUMNS].copy()

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features_df)

    pca = PCA(n_components=2, random_state=random_state)
    pca_result = pca.fit_transform(scaled_features)

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10,
    )
    cluster_labels = kmeans.fit_predict(scaled_features)

    knn = NearestNeighbors(
        n_neighbors=n_neighbors,
        metric="euclidean",
    )
    knn.fit(scaled_features)

    gm_reference = profiles_df[["Player", "total_games"] + FEATURE_COLUMNS].copy()
    gm_reference["pca_x"] = pca_result[:, 0]
    gm_reference["pca_y"] = pca_result[:, 1]
    gm_reference["cluster"] = cluster_labels

    cluster_profiles = (
        gm_reference
        .drop(columns=["Player", "pca_x", "pca_y"])
        .groupby("cluster")
        .mean(numeric_only=True)
        .reset_index()
    )

    return scaler, pca, kmeans, knn, gm_reference, cluster_profiles


def save_outputs(
    output_dir: Path,
    scaler: StandardScaler,
    pca: PCA,
    kmeans: KMeans,
    knn: NearestNeighbors,
    gm_reference: pd.DataFrame,
    cluster_profiles: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(scaler, output_dir / "scaler.joblib")
    joblib.dump(pca, output_dir / "pca.joblib")
    joblib.dump(kmeans, output_dir / "kmeans.joblib")
    joblib.dump(knn, output_dir / "knn.joblib")

    gm_reference.to_parquet(output_dir / "gm_reference.parquet", index=False)
    cluster_profiles.to_parquet(output_dir / "cluster_profiles.parquet", index=False)

    with open(output_dir / "feature_columns.json", "w", encoding="utf-8") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)

    metadata = {
        "feature_columns": FEATURE_COLUMNS,
        "n_clusters": int(kmeans.n_clusters),
        "n_neighbors": int(knn.n_neighbors),
        "pca_explained_variance_ratio": [
            float(x) for x in pca.explained_variance_ratio_
        ],
        "gm_reference_rows": int(len(gm_reference)),
    }

    with open(output_dir / "style_model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build style-inference models from the TWIC DuckDB database."
    )
    parser.add_argument(
        "--db-path",
        default="twic/data/twic_data.duckdb",
        help="Path to TWIC DuckDB file.",
    )
    parser.add_argument(
        "--output-dir",
        default="twic/outputs",
        help="Directory where model artifacts will be saved.",
    )
    parser.add_argument(
        "--min-games",
        type=int,
        default=100,
        help="Minimum total TWIC games required per player.",
    )
    parser.add_argument(
        "--clusters",
        type=int,
        default=4,
        help="Number of KMeans clusters.",
    )
    parser.add_argument(
        "--neighbors",
        type=int,
        default=3,
        help="Number of nearest GMs to return.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)
    output_dir = Path(args.output_dir)

    print(f"Loading GM profiles from: {db_path}")
    profiles_df = load_gm_profiles(
        db_path=db_path,
        min_games=args.min_games,
    )

    print(f"Profiles created: {len(profiles_df):,}")
    print(f"Output dir: {output_dir}")

    scaler, pca, kmeans, knn, gm_reference, cluster_profiles = build_models(
        profiles_df=profiles_df,
        n_clusters=args.clusters,
        n_neighbors=args.neighbors,
        random_state=args.random_state,
    )

    save_outputs(
        output_dir=output_dir,
        scaler=scaler,
        pca=pca,
        kmeans=kmeans,
        knn=knn,
        gm_reference=gm_reference,
        cluster_profiles=cluster_profiles,
    )

    print("\nSaved:")
    print(f"- {output_dir / 'scaler.joblib'}")
    print(f"- {output_dir / 'pca.joblib'}")
    print(f"- {output_dir / 'kmeans.joblib'}")
    print(f"- {output_dir / 'knn.joblib'}")
    print(f"- {output_dir / 'gm_reference.parquet'}")
    print(f"- {output_dir / 'cluster_profiles.parquet'}")
    print(f"- {output_dir / 'feature_columns.json'}")
    print(f"- {output_dir / 'style_model_metadata.json'}")

    print("\nCluster profiles:")
    print(cluster_profiles)


if __name__ == "__main__":
    main()


"""
INSPECT CLUSTER PROFILES:

python - <<'PY'
import pandas as pd

df = pd.read_parquet("twic/outputs/cluster_profiles.parquet")
print(df)
PY
"""