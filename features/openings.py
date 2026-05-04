import pandas as pd
import urllib.parse

def extract_opening_info(eco_url: str) -> pd.Series:
    """
    parses the Chess.com ECO URL into an opening name and a broader family.
    """

    # NaN would be float: check that it isnt
    if not eco_url.strip():
        return pd.Series(["Unknown", "Unknown"])
    
    # parse URL: https://www.chess.com/openings/Alekhines-Defense....
    parsed = urllib.parse.urlparse(eco_url)
    path = parsed.path.strip("/")
    
    temp = path.split("/")[-1]
    
    # temp to readable name
    clean_name = temp.replace("-", " ")
    
    # family ("Caro Kann Defense" from "Caro Kann Defense Advance Variation")
    # TODO: testing?!
    family = clean_name.split(" Variation")[0].split(" Defense")[0].split(" Attack")[0].split(" Gambit")[0]
    
    return pd.Series([clean_name, family.strip()])


def compute_opening_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parses the 'eco' URL column into distinct opening names and families.
    """
    if df.empty:
        out = df.copy()
        out["eco"] = pd.Series(dtype="object")
        out["opening_name"] = pd.Series(dtype="object")
        out["opening_family"] = pd.Series(dtype="object")
        return out

    out = df.copy()

    # get openings & families
    extracted = out["eco"].apply(extract_opening_info)
    out["opening_name"] = extracted[0]
    out["opening_family"] = extracted[1]

    return out