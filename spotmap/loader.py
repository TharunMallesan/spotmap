"""Smart CSV loading with automatic latitude/longitude and outcome column detection."""

import re

import numpy as np
import pandas as pd

from .exceptions import ColumnNotFoundError

_FLOAT_PATTERN = re.compile(r"^-?\d+(\.\d+)?$")
_PAIR_PATTERN = re.compile(
    r"^[\[\(]?\s*(-?\d+(\.\d+)?)\s*,\s*(-?\d+(\.\d+)?)\s*[\]\)]?$"
)

_LAT_NAMES = {"lat", "latitude", "y", "northing"}
_LON_NAMES = {"lon", "long", "longitude", "lng", "x", "easting"}
_OUTCOME_CANDIDATES = ["outcome", "case_control", "status", "class", "target", "casecontrol"]
_CASE_VALUES = {"case", "cases", "1", "yes", "true", "positive", "present"}


def _sample(df: pd.DataFrame, col: str, n: int = 5) -> list:
    return df[col].dropna().astype(str).str.strip().head(n).tolist()


def _is_float_col(df: pd.DataFrame, col: str) -> bool:
    samples = _sample(df, col)
    return bool(samples) and all(_FLOAT_PATTERN.match(x) for x in samples)


def _is_pair_col(df: pd.DataFrame, col: str) -> bool:
    samples = _sample(df, col)
    return bool(samples) and all(_PAIR_PATTERN.match(x) for x in samples)


def _detect_from_combined(df: pd.DataFrame, col: str):
    """Split a 'lat,lon' or 'lon,lat' combined column; returns (lat_series, lon_series)."""
    split = (
        df[col]
        .astype(str)
        .str.replace(r"[\[\]()]", "", regex=True)
        .str.split(",", expand=True)
    )
    v1 = pd.to_numeric(split[0].str.strip(), errors="coerce")
    v2 = pd.to_numeric(split[1].str.strip(), errors="coerce")

    max1, max2 = v1.abs().max(), v2.abs().max()

    if max1 > 90 and max2 <= 90:
        # first > 90 → must be longitude
        return v2, v1
    if max2 > 90 and max1 <= 90:
        return v1, v2
    # ambiguous: larger absolute value is longitude
    lon = np.where(v1.abs() > v2.abs(), v1, v2)
    lat = np.where(v1.abs() > v2.abs(), v2, v1)
    return pd.Series(lat, index=df.index), pd.Series(lon, index=df.index)


def detect_lat_lon(df: pd.DataFrame, lat_col: str = None, long_col: str = None):
    """Return (lat_col_name, long_col_name) after detection or validation."""
    cols = list(df.columns)

    # User-supplied — validate they exist
    if lat_col and long_col:
        missing = [c for c in (lat_col, long_col) if c not in cols]
        if missing:
            raise ColumnNotFoundError(f"Columns not found in CSV: {missing}")
        return lat_col, long_col

    # Combined column?
    for col in cols:
        if _is_pair_col(df, col):
            lat_s, lon_s = _detect_from_combined(df, col)
            df["_auto_lat"] = lat_s
            df["_auto_lon"] = lon_s
            return "_auto_lat", "_auto_lon"

    # Separate numeric columns
    numeric_cols = [c for c in cols if _is_float_col(df, c)]
    found_lat, found_lon = None, None

    for c in numeric_cols:
        c_lower = c.lower()
        if any(name in c_lower for name in _LAT_NAMES):
            found_lat = c
        if any(name in c_lower for name in _LON_NAMES):
            found_lon = c

    if found_lat and found_lon:
        return found_lat, found_lon

    if len(numeric_cols) == 2:
        return numeric_cols[0], numeric_cols[1]

    raise ColumnNotFoundError(
        f"Could not auto-detect lat/lon columns. Available columns: {cols}. "
        "Pass lat_col and long_col explicitly."
    )


def detect_outcome(df: pd.DataFrame, outcome_col: str = None, case_value: str = None):
    """Return (outcome_col, case_value) after detection or validation."""
    cols = list(df.columns)

    if outcome_col and outcome_col not in cols:
        raise ColumnNotFoundError(
            f"outcome_col '{outcome_col}' not found. Available: {cols}"
        )

    if outcome_col is None:
        for cand in _OUTCOME_CANDIDATES:
            matches = [c for c in cols if cand in c.lower()]
            if matches:
                outcome_col = matches[0]
                break

    if outcome_col is None:
        raise ColumnNotFoundError(
            f"Could not find outcome column. Available columns: {cols}. "
            "Pass outcome_col explicitly."
        )

    norm = df[outcome_col].astype(str).str.strip().str.lower().replace({"nan": np.nan})
    values = norm.dropna().unique()

    if case_value is None:
        case_value = next((v for v in values if v in _CASE_VALUES), values[0] if len(values) else None)

    if case_value is None:
        raise ColumnNotFoundError(f"No values found in outcome column '{outcome_col}'.")

    return outcome_col, str(case_value)


def load_csv(
    data,
    lat_col: str = None,
    long_col: str = None,
    outcome_col: str = None,
    case_value: str = None,
) -> tuple:
    """Load and prepare the points data from a file path or DataFrame.

    Returns:
        (df, lat_col, long_col, outcome_col, case_value)
    """
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    else:
        df = pd.read_csv(data)

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    lat_col, long_col = detect_lat_lon(df, lat_col, long_col)

    outcome_col, case_value = detect_outcome(df, outcome_col, case_value)

    df["_outcome_norm"] = (
        df[outcome_col].astype(str).str.strip().str.lower().replace({"nan": np.nan})
    )

    return df, lat_col, long_col, outcome_col, case_value
