from typing import Any

import pandas as pd
import streamlit as st

from app.api_client import ChessApiError, fetch_live_user_data


def render_sidebar() -> list[str]:
    st.sidebar.title("♟️ Control Panel")

    with st.sidebar.form(key="search_form"):
        username_input = st.text_input(
            "Chess.com Username",
            placeholder="e.g., Hikaru",
        )
        include_unrated = st.toggle("Include Unrated", value=False)
        submit_search = st.form_submit_button("Analyze User", width="stretch")

    if submit_search and username_input:
        username = username_input.strip()

        with st.spinner(f"Downloading game history for {username}..."):
            try:
                raw_games: list[dict[str, Any]] = fetch_live_user_data(
                    username=username,
                    include_unrated=include_unrated,
                )

            except ChessApiError as exc:
                st.sidebar.error(str(exc))
                return []

            if raw_games:
                df = pd.DataFrame(raw_games)

                if "end_time" in df.columns:
                    df["end_time"] = pd.to_datetime(
                        df["end_time"],
                        utc=True,
                        errors="coerce",
                    )

                st.session_state["chess_df"] = df
                st.session_state["current_user"] = username
                st.session_state["include_unrated"] = include_unrated

            else:
                st.sidebar.warning("No games returned for this user.")

    if "chess_df" in st.session_state:
        df = st.session_state["chess_df"]

        st.sidebar.divider()
        st.sidebar.markdown(f"**Viewing:** {st.session_state['current_user']}")

        available_tcs = sorted(df["time_class"].dropna().unique().tolist())

        return st.sidebar.multiselect(
            "Filter Time Controls",
            options=available_tcs,
            default=available_tcs,
        )

    return []