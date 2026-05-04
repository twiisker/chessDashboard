from typing import Any

import pandas as pd
import plotly.express as px  # type: ignore
import streamlit as st

from aggregations.tables import get_time_control_stats, build_win_draw_loss_table


def _normalize_result_columns(stats: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes result columns from possible variants:

      Win / Draw / Loss
      win / draw / loss
      SimpleResult.WIN / SimpleResult.DRAW / SimpleResult.LOSS

    into:

      win / draw / loss
    """
    out = stats.copy()

    rename_map: dict[Any, str] = {}

    for col in out.columns:
        raw = getattr(col, "value", col)
        text = str(raw).strip().lower()

        if text == "win" or text == "win" or text.endswith(".win"):
            rename_map[col] = "win"
        elif text == "draw" or text == "draw" or text.endswith(".draw"):
            rename_map[col] = "draw"
        elif text == "loss" or text == "loss" or text.endswith(".loss"):
            rename_map[col] = "loss"

    out = out.rename(columns=rename_map)

    for col in ["win", "draw", "loss"]:
        if col not in out.columns:
            out[col] = 0

    return out


def _render_wdl_table(stats: pd.DataFrame, group_col: str) -> None:
    if stats.empty:
        st.info("No data available.")
        return

    table_df = _normalize_result_columns(stats)

    required = [group_col, "total_games", "win", "draw", "loss", "win_rate_pct"]
    existing = [col for col in required if col in table_df.columns]

    st.dataframe(
        table_df[existing],
        hide_index=True,
        width="stretch",
        column_config={
            "win": st.column_config.NumberColumn("win"),
            "draw": st.column_config.NumberColumn("draw"),
            "loss": st.column_config.NumberColumn("loss"),
            "win_rate_pct": st.column_config.ProgressColumn(
                "Win Rate",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        },
    )


def render_volume_and_outcomes(df: pd.DataFrame) -> None:
    st.subheader("Volume & Format Outcomes")

    if df.empty:
        st.info("No games in the current filter.")
        return

    col_pie, col_table = st.columns([1, 1.2])

    tc_stats = get_time_control_stats(df)

    with col_pie:
        if not tc_stats.empty:
            fig = px.pie(
                tc_stats,
                values="total_games",
                names="time_class",
                hole=0.4,
            )
            fig.update_layout(
                margin=dict(t=0, b=0, l=0, r=0),
                height=300,
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No time-control stats available.")

    with col_table:
        st.markdown("**Win/Loss/Draw Breakdown**")
        _render_wdl_table(tc_stats, "time_class")

    st.divider()
    st.subheader("Performance vs. Opponent Strength")

    if "matchup_type" not in df.columns:
        st.info("No matchup strength data available.")
        return

    matchup_stats = build_win_draw_loss_table(df, "matchup_type")
    _render_wdl_table(matchup_stats, "matchup_type")