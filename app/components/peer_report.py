from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.api_client import ChessApiError, fetch_peer_report


def _to_df(report: dict[str, Any], key: str) -> pd.DataFrame:
    rows = report.get(key, [])
    if not isinstance(rows, list):
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _format_pct_columns(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()

    pct_cols = [
        "win_rate",
        "draw_rate",
        "loss_rate",
        "score_rate",
        "play_share",
        "target_minus_peers",
        "score_gap",
        "target_score",
        "peers_score",
        "top_3_share",
    ]

    for col in pct_cols:
        if col in formatted.columns:
            formatted[col] = pd.to_numeric(formatted[col], errors="coerce").round(1)

    return formatted


def _render_df(
    title: str,
    df: pd.DataFrame,
    columns: list[str] | None = None,
    help_text: str | None = None,
) -> None:
    st.markdown(f"**{title}**")

    if help_text:
        st.caption(help_text)

    if df.empty:
        st.info("No data returned for this section.")
        return

    view = df.copy()

    if columns:
        available_cols = [col for col in columns if col in view.columns]
        view = view[available_cols]

    view = _format_pct_columns(view)

    st.dataframe(
        view,
        hide_index=True,
        width="stretch",
    )


def _infer_time_class_options(df: pd.DataFrame) -> list[str]:
    if "time_class" not in df.columns:
        return ["rapid", "blitz", "bullet"]

    options = (
        df["time_class"]
        .dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

    return options or ["rapid", "blitz", "bullet"]


def _default_time_class(options: list[str]) -> str:
    for preferred in ["rapid", "blitz", "bullet"]:
        if preferred in options:
            return preferred

    return options[0]


def render_peer_report(df: pd.DataFrame, username: str) -> None:
    st.subheader("Peer Group Report")

    st.caption(
        "Compare this player against a cohort of similarly rated Chess.com players."
    )

    available_time_classes = _infer_time_class_options(df)
    default_tc = _default_time_class(available_time_classes)
    default_index = available_time_classes.index(default_tc)

    with st.form("peer_report_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            time_class = st.selectbox(
                "Time class",
                options=available_time_classes,
                index=default_index,
            )

        with col2:
            max_peers = st.slider(
                "Max peers",
                min_value=10,
                max_value=100,
                value=50,
                step=10,
            )

        with col3:
            max_games_per_peer = st.slider(
                "Max games per peer",
                min_value=100,
                max_value=1000,
                value=500,
                step=100,
            )

        col4, col5, col6 = st.columns(3)

        with col4:
            rating_window_raw = st.number_input(
                "Rating window",
                min_value=0,
                max_value=1000,
                value=200,
                step=50,
                help="Use 0 to let the backend choose.",
            )

        with col5:
            include_unrated = st.toggle(
                "Include unrated",
                value=bool(st.session_state.get("include_unrated", False)),
            )

        with col6:
            refresh = st.toggle(
                "Refresh peer cohort",
                value=False,
                help="Rebuilds the peer cohort instead of reusing cached data.",
            )

        submitted = st.form_submit_button(
            "Generate Peer Report",
            type="primary",
            width="stretch",
        )

    if not submitted:
        st.info("Choose settings and generate a peer report.")
        return

    rating_window = int(rating_window_raw) if rating_window_raw > 0 else None

    with st.spinner("Building peer cohort and comparison tables..."):
        try:
            report = fetch_peer_report(
                username=username,
                time_class=time_class,
                max_peers=int(max_peers),
                rating_window=rating_window,
                refresh=refresh,
                max_games_per_peer=int(max_games_per_peer),
                include_unrated=include_unrated,
                include_opening_clock=False,
            )

        except ChessApiError as exc:
            st.error(f"Could not build peer report: {exc}")
            return

    peer_count = report.get("peer_count", 0)
    user_game_count = report.get("user_game_count", 0)
    peer_game_count = report.get("peer_game_count", 0)

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Peers", peer_count)
    kpi2.metric("User games", user_game_count)
    kpi3.metric("Peer games", peer_game_count)

    overall_df = _to_df(report, "overall")
    opening_score_gap_df = _to_df(report, "opening_score_gap")
    opening_play_share_gap_df = _to_df(report, "opening_play_share_gap")
    repertoire_width_df = _to_df(report, "repertoire_width")
    top_3_share_df = _to_df(report, "top_3_share")
    rating_bucket_df = _to_df(report, "rating_bucket_comparison")
    leaderboard_df = _to_df(report, "peer_leaderboard")
    opening_comparison_df = _to_df(report, "opening_comparison")

    st.divider()

    _render_df(
        "Overall comparison",
        overall_df,
        columns=[
            "comparison_group",
            "games",
            "avg_rating",
            "avg_opp_rating",
            "wins",
            "draws",
            "losses",
            "win_rate",
            "draw_rate",
            "loss_rate",
            "score_rate",
        ],
    )

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        _render_df(
            "Best / worst score-rate gaps",
            opening_score_gap_df,
            columns=[
                "my_color",
                "opening_family",
                "target_score",
                "peers_score",
                "score_gap",
                "target_games",
                "peers_games",
            ],
            help_text="Positive score_gap means the user scores better than peers.",
        )

    with col_b:
        _render_df(
            "Opening play-share gaps",
            opening_play_share_gap_df,
            columns=[
                "my_color",
                "opening_family",
                "target",
                "peers",
                "target_minus_peers",
            ],
            help_text="Positive target_minus_peers means the user plays this more than peers.",
        )

    st.divider()

    col_c, col_d = st.columns(2)

    with col_c:
        _render_df(
            "Repertoire width",
            repertoire_width_df,
            columns=[
                "comparison_group",
                "my_color",
                "games",
                "unique_families",
                "unique_specific_openings",
                "games_per_family",
            ],
        )

    with col_d:
        _render_df(
            "Top-3 opening concentration",
            top_3_share_df,
            columns=[
                "comparison_group",
                "my_color",
                "total_games",
                "top_3_games",
                "top_3_share",
            ],
        )

    st.divider()

    _render_df(
        "Rating bucket comparison",
        rating_bucket_df,
        columns=[
            "comparison_group",
            "rating_bucket",
            "games",
            "avg_rating",
            "wins",
            "draws",
            "losses",
            "score_rate",
        ],
    )

    with st.expander("Peer leaderboard"):
        _render_df(
            "Individual peer leaderboard",
            leaderboard_df,
            columns=[
                "peer_username",
                "games",
                "avg_rating",
                "wins",
                "draws",
                "losses",
                "score_rate",
            ],
        )

    with st.expander("Raw opening comparison"):
        _render_df(
            "Opening comparison",
            opening_comparison_df,
            columns=[
                "comparison_group",
                "my_color",
                "opening_family",
                "games",
                "wins",
                "draws",
                "losses",
                "play_share",
                "win_rate",
                "score_rate",
            ],
        )