import pandera.pandas as pa
from pandera.typing import Series
from pydantic import BaseModel


class UserSearchRequest(BaseModel):
    username: str
    include_unrated: bool = False
    time_class: str | None = None


class DeepDiveRequest(BaseModel):
    username: str
    opening_name: str
    color: str
    include_unrated: bool = False
    time_class: str | None = None
    game_limit: int = 10


class RepertoireTreeRequest(BaseModel):
    username: str
    opening_name: str
    color: str = "white"
    include_unrated: bool = False
    time_class: str | None = None


class PeerReportRequest(BaseModel):
    username: str
    time_class: str = "rapid"
    max_peers: int = 50
    rating_window: int | None = None
    refresh: bool = False
    max_games_per_peer: int | None = 500
    include_unrated: bool = False
    include_opening_clock: bool = False

# pandera df model: time control
class TimeControlSchema(pa.DataFrameModel):
    time_class: Series[str] = pa.Field(coerce=True)
    Win: Series[int] = pa.Field(ge=0, coerce=True)      # ge=0 : => 0
    Draw: Series[int] = pa.Field(ge=0, coerce=True)
    Loss: Series[int] = pa.Field(ge=0, coerce=True)
    total_games: Series[int] = pa.Field(ge=0, coerce=True)
    win_rate_pct: Series[float] = pa.Field(ge=0.0, le=100.0, coerce=True) # => 0 ; <= 100

# pandera df model: hour
class HourStatsSchema(pa.DataFrameModel):
    hour: Series[int] = pa.Field(ge=0, le=23, coerce=True) # => 0 ; <= 23
    Win: Series[int] = pa.Field(ge=0, coerce=True)
    Draw: Series[int] = pa.Field(ge=0, coerce=True)
    Loss: Series[int] = pa.Field(ge=0, coerce=True)
    total_games: Series[int] = pa.Field(ge=0, coerce=True)
    win_rate_pct: Series[float] = pa.Field(ge=0.0, le=100.0, coerce=True)

# pandera df model: opening
class OpeningStatsSchema(pa.DataFrameModel):
    opening_name: Series[str] = pa.Field(coerce=True)
    eco_url: Series[str] = pa.Field(coerce=True, nullable=True) # <-- ADD THIS
    Win: Series[int] = pa.Field(ge=0, coerce=True)
    Draw: Series[int] = pa.Field(ge=0, coerce=True)
    Loss: Series[int] = pa.Field(ge=0, coerce=True)
    total_games: Series[int] = pa.Field(ge=0, coerce=True)
    win_rate_pct: Series[float] = pa.Field(ge=0.0, le=100.0, coerce=True)