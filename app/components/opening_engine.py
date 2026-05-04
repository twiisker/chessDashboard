import pandas as pd
import streamlit as st
from aggregations.tables import get_opening_stats
import requests
from app.components.opening_variations import render_variation_tree
from app.components.deep_dive_data import fetch_deep_dive_data

API_BASE_URL = "http://localhost:8000/api/v1"


def render_openings_and_engine(df: pd.DataFrame) -> None:
    st.subheader("Lifetime Opening Mastery")
    
    color_choice = st.radio("Analyze Repertoire as:", ["White", "Black"], horizontal=True)
    target_color = color_choice.lower()
    
    # Filter the dataframe down to just the selected color BEFORE doing any math!
    color_df = df[df["my_color"] == target_color]

    openings_df = get_opening_stats(color_df, min_games=1)
    if openings_df.empty: 
        st.info(f"No games found playing as {color_choice}.")
        return

    min_games = st.slider("Minimum games played to rank opening:", min_value=1, max_value=max(int(openings_df["total_games"].max()), 2), value=5)
    
    valid_openings = openings_df[openings_df["total_games"] >= min_games]
    if valid_openings.empty:
        st.warning("No openings meet this threshold.")
        return

    table_config = {"eco_url": st.column_config.LinkColumn("Opening", display_text=r"https://www.chess.com/openings/(.*)"),
                    "win_rate_pct": st.column_config.ProgressColumn("Win Rate", format="%.1f%%", min_value=0, max_value=100)}

    st.markdown(f"**Most Played as {color_choice}**")
    most_played = valid_openings.sort_values(by="total_games", ascending=False).head(10)
    st.dataframe(most_played[["eco_url", "total_games", "win_rate_pct"]], hide_index=True, width="stretch", column_config=table_config)

    col_top, col_worst = st.columns(2)
    with col_top:
        st.markdown("**Top Performing**")
        st.dataframe(valid_openings.sort_values(by=["win_rate_pct", "total_games"], ascending=[False, False]).head(10)[["eco_url", "total_games", "win_rate_pct"]], hide_index=True, width="stretch", column_config=table_config)
    with col_worst:
        st.markdown("**Needs Improvement**")
        st.dataframe(valid_openings.sort_values(by=["win_rate_pct", "total_games"], ascending=[True, False]).head(10)[["eco_url", "total_games", "win_rate_pct"]], hide_index=True, width="stretch", column_config=table_config)

    st.divider()

    available_openings = sorted(valid_openings["opening_name"].unique().tolist())

    st.markdown(f"### 🌳 Build Polyglot Tree ({color_choice})")
    st.info("Select an opening to generate a branching tree of exactly what your opponents play, and where your win rate drops.")
    
    tree_col1, tree_col2 = st.columns([3, 1])
    with tree_col1:
        tree_opening = st.selectbox("Select Opening for Tree:", available_openings, key="tree_select")
    with tree_col2:
        st.write("")
        st.write("")
        build_tree_btn = st.button("Generate Tree", width="stretch")
        
    if build_tree_btn and tree_opening:
        with st.spinner("Parsing PGNs, loading GMs, and booting Stockfish..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/repertoire_tree",
                    json={
                        "username": st.session_state["current_user"],
                        "opening_name": tree_opening,
                        "color": target_color
                    }
                )
                response.raise_for_status()
                data = response.json()
                tree_data = data.get("tree", {})
                study_pgn = data.get("study_pgn", "")
                
                if tree_data and tree_data.get("children"):
                    st.success("Study generated successfully!")
                    
                    # --- THE LICHESS EXPORT SECTION ---
                    st.markdown("### Export to Lichess Study")
                    col_lic1, _ = st.columns([1, 2])
                    with col_lic1:
                        st.link_button("Create Lichess Study", "https://lichess.org/study", width="stretch")
                    
                    # THIS LINE CREATES THE COPY-PASTE BOX!
                    st.code(study_pgn, language="text")
                    # -----------------------------------
                    
                    st.markdown("### Interactive Tree")
                    render_variation_tree(tree_data)
                else:
                    st.warning("Could not build tree. Ensure games contain PGN data.")
            except Exception as e:
                st.error(f"Failed to fetch tree: {e}")

    st.divider()
    st.markdown(f"### Engine Deep Dive (Stockfish 18 as {color_choice})")
        
    dd_col1, dd_col2 = st.columns([3, 1])
    with dd_col1:
        selected_opening = st.selectbox("Select an Opening to analyze:", available_openings)
    with dd_col2:
        st.write("")
        st.write("")
        run_engine = st.button("Run Diagnostics", type="primary", width="content")

    if run_engine and selected_opening:
        with st.spinner(f"Booting Stockfish 18... Analyzing {selected_opening}..."):
            username = st.session_state["current_user"]
            
            # Pass the target_color here!
            api_response = fetch_deep_dive_data(username, False, selected_opening, target_color)
            diagnostics = api_response.get("diagnostics", [])
            merged_pgn = api_response.get("merged_pgn", "")
            
            if diagnostics and len(diagnostics) > 0:
                st.success(f"Successfully analyzed {len(diagnostics)} recent games!")
                diag_df = pd.DataFrame(diagnostics)
                
                # --- UPGRADE 1: Engine KPI Tiles ---
                c1, c2, c3 = st.columns(3)
                c1.metric("Avg Centipawn Loss", f"{diag_df['avg_cpl_loss'].mean():.2f}")
                
                # A blunder is typically considered a single move losing > 1.5 pawns
                blunders = len(diag_df[diag_df['my_worst_cpl'] > 1.5])
                c2.metric("Major Blunders Made", blunders)
                
                missed_df = diag_df[diag_df['missed_punishment'] == True]
                c3.metric("Missed Punishments", len(missed_df))
                
                st.write("") # Spacer
                
                # --- UPGRADE 2: The "Missed Opportunities" Training Table ---
                if not missed_df.empty:
                    st.markdown("### 🚨 Missed Opportunities (Theory to Review)")
                    st.info("These are games where your opponent blundered in the opening, but you failed to find the engine's best continuation.")
                    
                    review_df = missed_df[["url", "opp_worst_move", "best_engine_move", "my_actual_response", "punishment_cpl"]].copy()
                    
                    # Sort by the most severe missed punishments first
                    review_df = review_df.sort_values("punishment_cpl", ascending=False)
                    
                    st.dataframe(
                        review_df,
                        width="stretch", hide_index=True,
                        column_config={
                            "url": st.column_config.LinkColumn("Game Link", display_text="Review Game"),
                            "opp_worst_move": "Opponent's Blunder",
                            "best_engine_move": "Stockfish Best Move",
                            "my_actual_response": "What You Played",
                            "punishment_cpl": "Centipawns Lost (Severity)"
                        }
                    )
                else:
                    st.success("You perfectly punished every opening blunder in this dataset. Great job!")

                # --- UPGRADE 3: The Raw Data Table (Minimized) ---
                with st.expander("View Raw Diagnostic Data"):
                    st.dataframe(
                        diag_df[["url", "total_cpl_loss", "my_worst_move", "opp_worst_move", "missed_punishment"]],
                        width="stretch", hide_index=True,
                        column_config={"url": st.column_config.LinkColumn("Game Link", display_text="View Game")}
                    )
                
                st.divider()
                st.markdown("### Export to Lichess")
                st.markdown("Copy the PGN block below, then click the button to open Lichess in a new tab. Paste it into the form to generate your interactive variation tree!")
                
                col_btn, _ = st.columns([1, 2])
                with col_btn:
                    st.link_button("Create Lichess Study", "https://lichess.org/study", width="content")
                
                st.code(merged_pgn, language="text")
            else:
                st.warning("Diagnostics failed. Games might be aborted, or missing clock times.")
