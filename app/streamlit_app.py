from pathlib import Path
import sys
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px  # type: ignore
import streamlit as st

from aggregations.tables import get_hour_stats, get_weekday_stats
from app.sidebar import render_sidebar
from app.components.kpis import render_kpi_tiles
from app.components.rating_progression import render_rating_progression
from app.components.playstyle_inference import render_playstyle_inference
from app.components.volume_outcome import render_volume_and_outcomes
from app.components.clock_management import render_clock_management
from app.components.recent_repertoire import render_recent_repertoire
from app.components.opening_engine import render_openings_and_engine
from app.components.peer_report import render_peer_report

def main() -> None:
    st.set_page_config(page_title="Chess Analytics Dashboard", page_icon="♟️", layout="wide")
    
    selected_tcs: List[str] = render_sidebar()
    
    if "chess_df" in st.session_state:
        df = st.session_state["chess_df"]
        
        # GLOBAL FILTERING
        if selected_tcs:
            filtered_df = df[df["time_class"].isin(selected_tcs)]
        else:
            filtered_df = df
            
        render_kpi_tiles(filtered_df)
        st.divider()
        
        st.write("")
        render_rating_progression(filtered_df)
        st.divider()
        
        render_playstyle_inference(filtered_df, st.session_state["current_user"])
        st.divider()
        
        
        render_volume_and_outcomes(filtered_df)
        st.divider()
        
        st.subheader("Performance by Time of Play")
        col_hour, col_day = st.columns(2)
        
        with col_hour:
            st.markdown("**By Hour of Day**")
            hour_df = get_hour_stats(filtered_df)
            if not hour_df.empty:
                fig_hour = px.bar(hour_df, x="hour", y="win_rate_pct", color_discrete_sequence=["#2ca02c"])
                fig_hour.update_layout(
                    xaxis=dict(tickmode='linear', dtick=1, tickangle=0), 
                    height=300, 
                    margin=dict(l=0, r=0, t=10, b=0)
                )
                st.plotly_chart(fig_hour, width="stretch")

        with col_day:
            st.markdown("**By Day of Week**")
            weekday_df = get_weekday_stats(filtered_df)
            if not weekday_df.empty:
                # Ensure the days display cleanly (Mapping 0-6 to Day Names if your backend outputs integers)
                day_mapping = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
                if pd.api.types.is_numeric_dtype(weekday_df["weekday"]):
                    weekday_df["weekday"] = weekday_df["weekday"].map(day_mapping)
                
                # Force Plotly to keep the days in chronological order instead of alphabetizing them
                category_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                
                fig_day = px.bar(weekday_df, x="weekday", y="win_rate_pct", color_discrete_sequence=["#ff7f0e"])
                fig_day.update_layout(
                    xaxis={'categoryorder':'array', 'categoryarray': category_order},
                    height=300, 
                    margin=dict(l=0, r=0, t=10, b=0)
                )
                st.plotly_chart(fig_day, width="stretch")
            
        st.divider()

        render_clock_management(filtered_df, st.session_state["current_user"])
        st.divider()

        render_peer_report(filtered_df, st.session_state["current_user"])
        st.divider()
        
        render_recent_repertoire(filtered_df)
        st.divider()
        
        render_openings_and_engine(filtered_df)
    else:
        st.markdown("<h1 style='text-align: center;'>Chess Analytics Dashboard</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Use the Control Panel on the left to analyze a user.</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()

#TODO:
#1. add search for moves in twic gm games: user inputs pgn notation moves or fen position
#2. add puzzle: user has tp evaluate position (+-, +=, ==, -=, ,-+) + solve for best moves