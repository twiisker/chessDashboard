from typing import TypedDict
from enum import StrEnum

class Color(StrEnum):
    WHITE = "white"
    BLACK = "black"

class SimpleResult(StrEnum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"

# typed dict expects every key to exist
# total=False : if they exist -> they are of this type
#               if they are missing -> thats okay

class PlayerPayload(TypedDict, total=False):
    username: str
    rating: int
    result: str
    uuid: str

class GamePayload(TypedDict, total=False):
    end_time: int
    time_class: str
    eco: str
    pgn: str
    url: str
    white: PlayerPayload
    black: PlayerPayload