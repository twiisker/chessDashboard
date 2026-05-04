import pandas as pd
import streamlit as st
import plotly.express as px # type: ignore #
from aggregations.tables import get_opening_stats

def render_recent_repertoire(df: pd.DataFrame) -> None:
    st.subheader("Recent Repertoire (Last 100 Games)")
    recent_100 = df.sort_values("end_time", ascending=False).head(100)
    
    table_config = {
        "eco_url": st.column_config.LinkColumn("Opening", display_text=r"https://www.chess.com/openings/(.*)"),
        "win_rate_pct": st.column_config.ProgressColumn("Win Rate", format="%.1f%%", min_value=0, max_value=100)
    }
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**White**")
        w_stats = get_opening_stats(recent_100[recent_100["my_color"] == "white"], min_games=1).head(5)
        if not w_stats.empty: 
            st.dataframe(w_stats[["eco_url", "total_games", "win_rate_pct"]], hide_index=True, width="stretch", column_config=table_config)
    with col2:
        st.markdown("**Black**")
        b_stats = get_opening_stats(recent_100[recent_100["my_color"] == "black"], min_games=1).head(5)
        if not b_stats.empty: 
            st.dataframe(b_stats[["eco_url", "total_games", "win_rate_pct"]], hide_index=True, width="stretch", column_config=table_config)
