from typing import Any

import requests
import streamlit as st

from chesscom.config import API_BASE_URL

DEFAULT_TIMEOUT_SECONDS = 300


class ChessApiError(RuntimeError):
    """Raised when the chess analytics API returns an error."""


def _extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or f"HTTP {response.status_code}"

    detail = payload.get("detail")

    if isinstance(detail, str):
        return detail

    if isinstance(detail, dict):
        message = detail.get("message")
        if message:
            return str(message)
        return str(detail)

    if isinstance(detail, list):
        return str(detail)

    return str(payload)


def post_api(
    endpoint: str,
    payload: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    url = f"{API_BASE_URL}{endpoint}"

    try:
        response = requests.post(url, json=payload, timeout=timeout)

        if response.status_code >= 400:
            raise ChessApiError(_extract_error_message(response))

        data = response.json()

        if not isinstance(data, dict):
            raise ChessApiError(f"Expected JSON object from {url}, got {type(data)}")

        return data

    except requests.exceptions.ConnectionError as exc:
        raise ChessApiError(
            "Could not connect to the backend API. "
            "Start it with: uvicorn api.main:app --reload --port 8000"
        ) from exc

    except requests.exceptions.Timeout as exc:
        raise ChessApiError(
            f"The backend request timed out after {timeout} seconds."
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise ChessApiError(f"Backend request failed: {exc}") from exc


def fetch_live_user_data(
    username: str,
    include_unrated: bool,
    time_class: str | None = None,
) -> list[dict[str, Any]]:
    data = post_api(
        "/analyze",
        {
            "username": username,
            "include_unrated": include_unrated,
            "time_class": time_class,
        },
        timeout=300,
    )

    games = data.get("games", [])

    if not isinstance(games, list):
        raise ChessApiError("API response field 'games' was not a list.")

    return games


def fetch_peer_report(
    username: str,
    time_class: str = "rapid",
    max_peers: int = 50,
    rating_window: int | None = None,
    refresh: bool = False,
    max_games_per_peer: int | None = 500,
    include_unrated: bool = False,
    include_opening_clock: bool = False,
) -> dict[str, Any]:
    return post_api(
        "/peer-report",
        {
            "username": username,
            "time_class": time_class,
            "max_peers": max_peers,
            "rating_window": rating_window,
            "refresh": refresh,
            "max_games_per_peer": max_games_per_peer,
            "include_unrated": include_unrated,
            "include_opening_clock": include_opening_clock,
        },
        timeout=180,
    )


def fetch_style_report(
    username: str,
    include_unrated: bool = False,
    time_class: str | None = None,
) -> dict[str, Any]:
    return post_api(
        "/style",
        {
            "username": username,
            "include_unrated": include_unrated,
            "time_class": time_class,
        },
    )


def fetch_repertoire_tree(
    username: str,
    opening_name: str,
    color: str,
    include_unrated: bool = False,
    time_class: str | None = None,
) -> dict[str, Any]:
    return post_api(
        "/repertoire_tree",
        {
            "username": username,
            "opening_name": opening_name,
            "color": color,
            "include_unrated": include_unrated,
            "time_class": time_class,
        },
        timeout=180,
    )


def fetch_deep_dive_report(
    username: str,
    opening_name: str,
    color: str,
    include_unrated: bool = False,
    time_class: str | None = None,
    game_limit: int = 5,
) -> dict[str, Any]:
    return post_api(
        "/deep_dive",
        {
            "username": username,
            "opening_name": opening_name,
            "color": color,
            "include_unrated": include_unrated,
            "time_class": time_class,
            "game_limit": game_limit,
        },
        timeout=300,
    )


def display_api_error(exc: Exception, location: str = "API") -> None:
    st.error(f"{location} error: {exc}")