import streamlit as st
from typing import Dict, Any

API_BASE_URL = "http://localhost:8000/api/v1"


def render_variation_tree(node: Dict[str, Any], depth: int = 1) -> None:
    """Recursively draws the opening tree using Streamlit expanders."""
    children: Dict[str, Any] = node.get("children", {})
    if not children:
        return
        
    # Sort children by how often they are played (most frequent first)
    sorted_children = sorted(children.values(), key=lambda x: x["count"], reverse=True)
    
    for child in sorted_children:
        move = child["move"]
        count = child["count"]
        wins = child["wins"]
        win_rate = (wins / count) * 100 if count > 0 else 0
        
        # Color code the metric based on win rate
        if win_rate >= 55:
            icon = "🟢"
        elif win_rate <= 45:
            icon = "🔴"
        else:
            icon = "⚪"
            
        label = f"{icon} Move {depth}: {move} ({count} games | {win_rate:.1f}% WR)"
        
        # Draw the expanding branch
        with st.expander(label, expanded=(depth == 1)): # Auto-expand the first move
            st.progress(win_rate / 100.0)
            # Call the function inside itself to draw the next move!
            render_variation_tree(child, depth + 1)
