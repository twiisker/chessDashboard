from typing import Any

import duckdb
import pandas as pd
import re

from chesscom.config import TWIC_DB

def _quote_duckdb_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _dedupe_twic_games(df: pd.DataFrame) -> pd.DataFrame:
    subset = [c for c in ["Date", "White", "Black", "Moves"] if c in df.columns]
    if subset:
        return df.drop_duplicates(subset=subset)
    return df.drop_duplicates()


def _opening_name_patterns(opening_name: str) -> list[str]:
    cleaned = re.sub(r"\s+\d+\..*$", "", opening_name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    variants = {
        cleaned,
        cleaned.replace("Defense", "Defence"),
        cleaned.replace("Defence", "Defense"),
        cleaned.replace("Birds", "Bird's"),
        cleaned.replace("Bird's", "Birds"),
    }

    broad = re.split(r":|,|\bVariation\b", cleaned, maxsplit=1)[0].strip()
    if broad:
        variants.add(broad)
        variants.add(broad.replace("Defense", "Defence"))
        variants.add(broad.replace("Defence", "Defense"))

    return [f"%{v}%" for v in variants if v]


def fetch_twic_games_for_repertoire(
    builder: Any,
    target_opening: str,
    limit: int = 10000,
    min_rows_before_broadening: int = 250,
) -> pd.DataFrame:
    
    
    con = duckdb.connect(str(TWIC_DB), read_only=True)

    try:
        tables_df = con.execute("SHOW TABLES").df()
        if tables_df.empty:
            print(f"Warning: TWIC DuckDB has no tables: {TWIC_DB}")
            return pd.DataFrame()

        table_names = tables_df["name"].tolist()
        table_name = "twic_games" if "twic_games" in table_names else table_names[0]
        table_sql = _quote_duckdb_identifier(table_name)

        frames: list[pd.DataFrame] = []

        prefixes: list[str] = []
        for ply_depth in (6, 4, 2, 1):
            prefix = builder.get_mainline_fingerprint(ply_depth=ply_depth)
            if prefix and prefix not in prefixes:
                prefixes.append(prefix)

        for prefix in prefixes:
            df = con.execute(
                f"""
                SELECT *
                FROM {table_sql}
                WHERE OpeningFingerprint LIKE ?
                LIMIT {limit}
                """,
                [f"{prefix}%"],
            ).df()

            if not df.empty:
                frames.append(df)

            merged = (
                _dedupe_twic_games(pd.concat(frames, ignore_index=True))
                if frames
                else pd.DataFrame()
            )
            if len(merged) >= min_rows_before_broadening:
                return merged.head(limit)

        for pattern in _opening_name_patterns(target_opening):
            df = con.execute(
                f"""
                SELECT *
                FROM {table_sql}
                WHERE Opening ILIKE ?
                LIMIT {limit}
                """,
                [pattern],
            ).df()

            if not df.empty:
                frames.append(df)

            merged = (
                _dedupe_twic_games(pd.concat(frames, ignore_index=True))
                if frames
                else pd.DataFrame()
            )
            if len(merged) >= min_rows_before_broadening:
                return merged.head(limit)

        if frames:
            return _dedupe_twic_games(pd.concat(frames, ignore_index=True)).head(limit)

        return pd.DataFrame()

    finally:
        con.close()