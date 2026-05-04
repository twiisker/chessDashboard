import pandas as pd
import streamlit as st

def render_kpi_tiles(df: pd.DataFrame) -> None:
    st.subheader("Current Live Ratings")
    kpi1, kpi2, kpi3 = st.columns(3)

    def get_latest_rating(tc: str) -> str:
        tc_df = df[df["time_class"] == tc]
        if not tc_df.empty:
            return str(int(tc_df.sort_values("end_time").iloc[-1]["my_rating"]))
        return "N/A"

    kpi1.metric("Bullet", get_latest_rating("bullet"))
    kpi2.metric("Blitz", get_latest_rating("blitz"))
    kpi3.metric("Rapid", get_latest_rating("rapid"))