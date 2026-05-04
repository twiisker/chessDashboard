from pathlib import Path
from typing import Any

import joblib  # type: ignore
import pandas as pd

from ml.player_profile import (
    PROFILE_FEATURE_COLUMNS,
    calculate_user_profile_from_df,
)

project_root = Path(__file__).resolve().parents[1]
model_dir = project_root / "twic" / "outputs"

class StyleInferencer:
    def __init__(self, model_dir: str | Path | None = None):
        if model_dir is None:
            project_root = Path(__file__).resolve().parents[1]
            model_dir = project_root / "twic" / "outputs"

        self.model_dir = Path(model_dir)

        self._validate_model_files()

        self.scaler = joblib.load(self.model_dir / "scaler.joblib")
        self.pca = joblib.load(self.model_dir / "pca.joblib")
        self.kmeans = joblib.load(self.model_dir / "kmeans.joblib")
        self.knn = joblib.load(self.model_dir / "knn.joblib")
        self.gm_ref = pd.read_parquet(self.model_dir / "gm_reference.parquet")

        self.feature_columns: list[str] = list(PROFILE_FEATURE_COLUMNS)

        self.archetypes: dict[int, str] = {
            0: "Peaceful",
            1: "Attacking",
            2: "Tactician",
            3: "Universalist",
        }

    def _validate_model_files(self) -> None:
        required_files = [
            "scaler.joblib",
            "pca.joblib",
            "kmeans.joblib",
            "knn.joblib",
            "gm_reference.parquet",
        ]

        missing = [
            filename
            for filename in required_files
            if not (self.model_dir / filename).exists()
        ]

        if missing:
            raise FileNotFoundError(
                "Missing style-inference model files in "
                f"{self.model_dir}: {missing}"
            )

    def predict_style(self, user_stats: dict[str, float]) -> dict[str, Any]:
        """
        Takes a 14-feature user profile and returns cluster/style information.
        """
        missing_features = [
            col for col in self.feature_columns if col not in user_stats
        ]

        if missing_features:
            raise KeyError(
                f"Missing style profile features: {missing_features}"
            )

        df = pd.DataFrame([user_stats], columns=self.feature_columns)

        df_scaled = self.scaler.transform(df)

        pca_result = self.pca.transform(df_scaled)
        pca_x = float(pca_result[0][0])
        pca_y = float(pca_result[0][1])

        cluster_id = int(self.kmeans.predict(df_scaled)[0])

        distances, indices = self.knn.kneighbors(df_scaled)

        closest_gms: list[dict[str, Any]] = []

        for distance, idx in zip(distances[0], indices[0]):
            row = self.gm_ref.iloc[int(idx)]

            player_name = (
                row["Player"]
                if "Player" in self.gm_ref.columns
                else row.get("player", "Unknown")
            )

            closest_gms.append(
                {
                    "player": str(player_name),
                    "distance": round(float(distance), 4),
                }
            )

        return {
            "cluster": cluster_id,
            "archetype": self.archetypes.get(
                cluster_id,
                f"Cluster {cluster_id}",
            ),
            "pca_x": round(pca_x, 4),
            "pca_y": round(pca_y, 4),
            "closest_gms": closest_gms,
        }


def infer_player_style_from_df(
    df: pd.DataFrame,
    model_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    Convenience wrapper for the API/dashboard.

    Takes a processed feature frame and returns:
      - profile vector
      - predicted style
    """
    profile = calculate_user_profile_from_df(df)

    inferencer = StyleInferencer(model_dir=model_dir)
    prediction = inferencer.predict_style(profile)

    return {
        "profile": profile,
        "style": prediction,
    }