import streamlit as st
from typing import Dict, Any
import requests

API_BASE_URL = "http://localhost:8000/api/v1"

def fetch_deep_dive_data(username: str, include_unrated: bool, opening_name: str, color: str) -> Dict[str, Any]:
    try:
        response = requests.post(
            f"{API_BASE_URL}/deep_dive",
            json={
                "username": username, 
                "include_unrated": include_unrated, 
                "opening_name": opening_name,
                "color": color # Pass the color to the API!
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Deep Dive Error: {e}")
        return {}