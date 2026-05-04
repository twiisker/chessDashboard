import json
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typeguard import typechecked

from tqdm import tqdm

from chesscom.config import CACHE_DIR, CONTACT_EMAIL

# https://support.chess.com/en/articles/9650547-what-is-the-pubapi-and-how-do-i-use-it


@dataclass
class ChessGame:
    #Game data
    owner_username: str
    url: str
    pgn: str
    time_control: str
    end_time: int
    rated: bool
    tcn: str
    uuid: str
    time_class: str
    rules: str
    
    # white player
    white_username: str
    white_rating: int
    white_result: str
    white_id: str
    white_uuid: str
    
    # black playerr
    black_username: str
    black_rating: int
    black_result: str
    black_id: str
    black_uuid: str

    # optional fields
    eco: Optional[str] = None
    initial_setup: Optional[str] = None
    fen: Optional[str] = None
    tournament: Optional[str] = None
    start_time: Optional[int] = None
    white_accuracy: Optional[float] = None
    black_accuracy: Optional[float] = None
    
@typechecked
def get_session() -> requests.Session:
    """
    Creates requests session with retries.
    
    Returns:
        requests.Session: session object with 5-retries 
                          and backoff factor for rate limits and server errors.
    """

    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1, 
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


@typechecked
def get_archives(username: str, headers: dict[str, str], session: requests.Session) -> list[str]:
    """
    Fetches the list of all monthly archive URLs for user.

    Args:
        username (str): chess.com username
        headers (dict[str, str]): HTTP headers, including required User-Agent.
        session (requests.Session): the get_session() object

    Returns:
        list[str]: list of monthly archive URLs, empty when user not found or session error.
    """

    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    try:
        response = session.get(url, headers=headers, timeout=15)
        if response.status_code == 404:
            return [] 
        response.raise_for_status()
        return response.json().get("archives", [])
    except Exception as e:
        print(f"Failed to fetch archives: {e}")
        return []


@typechecked
def parse_game(raw_game: dict[str, Any], owner: str) -> ChessGame:
    """
    Maps chess.com JSON dictionary to ChessGame dataclass
    
    Args:
        raw_game (dict[str, Any]): a single JSON game dict
        
    Returns:
        ChessGame: dataclass representation of the JSON game
    """

    white_data = raw_game.get("white", {})
    black_data = raw_game.get("black", {})
    accuracies = raw_game.get("accuracies", {})

    return ChessGame(
        owner_username=owner,
        url=raw_game.get("url", ""),
        pgn=raw_game.get("pgn", ""),
        time_control=raw_game.get("time_control", ""),
        end_time=raw_game.get("end_time", 0),
        rated=raw_game.get("rated", False),
        tcn=raw_game.get("tcn", ""),
        uuid=raw_game.get("uuid", ""),
        time_class=raw_game.get("time_class", ""),
        rules=raw_game.get("rules", ""),
        
        # White
        white_username=white_data.get("username", ""),
        white_rating=white_data.get("rating", 0),
        white_result=white_data.get("result", ""),
        white_id=white_data.get("@id", ""),
        white_uuid=white_data.get("uuid", ""),
        
        # Black
        black_username=black_data.get("username", ""),
        black_rating=black_data.get("rating", 0),
        black_result=black_data.get("result", ""),
        black_id=black_data.get("@id", ""),
        black_uuid=black_data.get("uuid", ""),
        
        # Optionals
        eco=raw_game.get("eco"),
        initial_setup=raw_game.get("initial_setup"),
        fen=raw_game.get("fen"),
        tournament=raw_game.get("tournament"),
        start_time=raw_game.get("start_time"),
        white_accuracy=accuracies.get("white"),
        black_accuracy=accuracies.get("black")
    )

@typechecked
def fetch_all_games(username: str) -> list[ChessGame]:
    """
    Fetches all games with ETag caching, schema validation.

    Args:
        username (str): chess.com username

    Returns:
        list[ChessGame]: complete list of user's games as dataclasses
    """

    user_cache_dir = CACHE_DIR / username
    user_cache_dir.mkdir(parents=True, exist_ok=True)
    
    # chess.com required header
    headers = {
        "User-Agent": f"chess-analyzer-backend/1.0 (username: {username}; contact: {CONTACT_EMAIL})",
        "Accept-Encoding": "gzip"
    }
    
    session = get_session()
    archives = get_archives(username, headers, session)
    
    # temp storing raw dicts for batch processing, last URL is current mont
    raw_games_list: list[dict[str, Any]] = []
    
    # iter list of monthly archive URLs with enum for index and url
    for i, archive_url in enumerate(tqdm(archives, desc=f"Fetching archives for {username}")):
        
        # Example URL: "https://api.chess.com/pub/player/username/games/2023/10"
        parts = archive_url.split('/')
        year, month = parts[-2], parts[-1]
        
        # local file paths for JSON, ETag
        data_file = user_cache_dir / f"games_{year}_{month}.json"
        etag_file = user_cache_dir / f"etag_{year}_{month}.txt"
        
        # last url is current month
        is_current_month = (i == len(archives) - 1)
        
        # offline cache: past games are static no new games
        if data_file.exists() and not is_current_month:
            with open(data_file, 'r') as f:
                raw_games_list.extend(json.load(f).get("games", []))
            continue
            
        # headers for API request
        req_headers = headers.copy()
        
        # ETag cache: attach ETag to request, if it changed get data
        if etag_file.exists():
            with open(etag_file, 'r') as f:
                req_headers["If-None-Match"] = f.read().strip()
                
        try:
            response = session.get(archive_url, headers=req_headers, timeout=5)
            
            # Status 304 (Not Modified): no new games
            if response.status_code == 304:
                if data_file.exists():
                    with open(data_file, "r", encoding="utf-8") as f:
                        raw_games_list.extend(json.load(f).get("games", []))
                else:
                    print(f"Missing cached data for {year}-{month}; skipping cache read.")
                    
            # Status 200 (OK): new data OR first download
            elif response.status_code == 200:
                data = response.json()
                
                with open(data_file, 'w') as f:
                    json.dump(data, f)
                    
                # save new ETag for further requests
                if "ETag" in response.headers:
                    with open(etag_file, 'w') as f:
                        f.write(response.headers["ETag"])
                        
                raw_games_list.extend(data.get("games", []))
                
            # blocked for rate limiting (Status 429)
            time.sleep(0.05) 
            
        except Exception as e:
            print(f"Skipping archive {year}-{month} due to connection error: {e}")
            continue
            
    # Convert all raw dictionaries to dataclass objects
    return [parse_game(game, username) for game in raw_games_list]
