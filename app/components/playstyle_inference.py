from typing import Any

import pandas as pd
import streamlit as st

from app.api_client import ChessApiError, fetch_style_report


def _infer_single_time_class(df: pd.DataFrame) -> str | None:
    """
    If the current filtered dashboard contains exactly one time_class,
    request style for that time_class. Otherwise use all time controls.
    """
    if "time_class" not in df.columns:
        return None

    time_classes = sorted(df["time_class"].dropna().astype(str).unique().tolist())

    if len(time_classes) == 1:
        return time_classes[0]

    return None


def _format_gm_match(item: Any) -> str:
    """
    Handles both old style:
      "Magnus Carlsen"

    and new API style:
      {"player": "Magnus Carlsen", "distance": 1.234}
    """
    if isinstance(item, dict):
        player = item.get("player", "Unknown")
        distance = item.get("distance")

        if distance is None:
            return str(player)

        return f"{player} · distance {distance}"

    return str(item)


def render_playstyle_inference(df: pd.DataFrame, username: str) -> None:
    st.subheader("AI Playstyle Analysis")

    include_unrated = bool(st.session_state.get("include_unrated", False))
    time_class = _infer_single_time_class(df)

    with st.spinner("Calculating your chess fingerprint..."):
        try:
            result = fetch_style_report(
                username=username,
                include_unrated=include_unrated,
                time_class=time_class,
            )

        except ChessApiError as exc:
            st.error(f"Could not calculate playstyle: {exc}")
            return

    style = result.get("style", {})
    profile = result.get("profile", {})

    if not style:
        st.warning("No style result returned by the backend.")
        return

    archetype = style.get("archetype", "Unknown")
    cluster = style.get("cluster", "N/A")
    pca_x = style.get("pca_x", 0.0)
    pca_y = style.get("pca_y", 0.0)

    st.success(f"Playstyle match found: **{archetype}**")

    col1, col2, col3 = st.columns(3)
    col1.metric("Archetype", str(archetype))
    col2.metric("Cluster", f"Cluster {cluster}")
    col3.metric("Style Coordinates", f"X: {float(pca_x):.2f} | Y: {float(pca_y):.2f}")

    if time_class is None:
        st.caption("Style inference uses all selected user games.")
    else:
        st.caption(f"Style inference filtered to: {time_class}")

    closest_gms = style.get("closest_gms", [])

    if closest_gms:
        st.markdown("**Closest Grandmaster Matches**")

        cols = st.columns(min(3, len(closest_gms)))

        medals = ["🥇", "🥈", "🥉"]

        for idx, item in enumerate(closest_gms[:3]):
            with cols[idx]:
                st.info(f"{medals[idx]} {_format_gm_match(item)}")

    with st.expander("View raw 14-feature profile"):
        st.json(profile)