import duckdb
from chesscom.config import DB_PATH

with duckdb.connect(str(DB_PATH)) as con:
    con.execute("DELETE FROM peer_cohort_members")
    print("Deleted all peer cohort rows.")