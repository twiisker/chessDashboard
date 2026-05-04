import pandas as pd
import streamlit as st
import plotly.express as px # type: ignore #

def render_clock_management(df: pd.DataFrame, username: str) -> None:
    st.subheader("⏱️ Opening Clock Management")
    
    # Filter for Rapid and Blitz where time_spent_opening successfully calculated
    if "time_spent_opening" not in df.columns:
        st.info("Opening time data has not been generated for this user.")
        return
        
    time_df = df[df["time_class"].isin(["rapid", "blitz"])].copy()
    time_df = time_df.dropna(subset=["time_spent_opening"])
    
    if time_df.empty:
        st.info("Not enough Rapid/Blitz data with clock times to analyze.")
        return

    st.markdown("Distribution of time spent (in seconds) during the first 10 moves.")

    # Create a beautiful Box Plot showing the median, quartiles, and outliers
    fig = px.box(
        time_df, 
        x="time_spent_opening", 
        y="time_class", 
        color="time_class",
        points="all", # Displays all individual games as dots next to the box
        hover_data=["opening_name", "simple_result"],
        labels={"time_spent_opening": "Seconds Spent in Opening (First 10 Moves)", "time_class": "Format"},
        color_discrete_sequence=["#1f77b4", "#ff7f0e"]
    )
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    st.plotly_chart(fig, width="stretch")