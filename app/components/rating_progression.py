import pandas as pd
import streamlit as st
import plotly.express as px # type: ignore #


def render_rating_progression(df: pd.DataFrame) -> None:
    st.subheader("Rating Progression Over Time")
    
    # Create a safe copy and ensure our timestamps are actual datetime objects
    prog_df = df.copy()
    prog_df["end_time"] = pd.to_datetime(prog_df["end_time"])
    
    # We MUST sort by time, otherwise Plotly will draw a scribbly mess
    prog_df = prog_df.sort_values("end_time")
    
    # Drop rows where rating is missing just in case
    prog_df = prog_df.dropna(subset=["my_rating", "time_class"])

    if prog_df.empty:
        st.info("Not enough data to plot rating progression.")
        return

    # Draw the multi-line chart
    fig = px.line(
        prog_df, 
        x="end_time", 
        y="my_rating", 
        color="time_class", # This automatically creates a separate line for Blitz, Bullet, etc.
        labels={"end_time": "Date", "my_rating": "Rating", "time_class": "Format"},
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    # Clean up the UI
    fig.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified", # Shows a clean vertical line spanning all formats when hovering
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, width="stretch")