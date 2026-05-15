"""
spotmap/loader.py
=================
Handles:
  - Loading and validating the CSV file
  - Auto-detecting lat/lon/outcome columns
  - Loading boundary files (lite or full)
  - Building GeoDataFrames from points
"""

import re
import os
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from spotmap.exceptions import (
    ColumnDetectionError,
    BoundaryFileError,
    CSVError,
    NoDataError,
)
from spotmap.downloader import get_bundled_path, get_full_path

os.environ["SHAPE_RESTORE_SHX"] = "YES"

# =========================================================
# REGEX PATTERNS
# =========================================================

_FLOAT_PATTERN = r'^-?\d+(\.\d+)?$'
_PAIR_PATTERN  = r'^[\[\(]?\s*(-?\d+(\.\d+)?)\s*,\s*(-?\d+(\.\d+)?)\s*[\]\)]?$'

# =========================================================
# PUBLIC: LOAD CSV
# =========================================================

def load_points(
    csv_path: str,
    lat_col: str = None,
    lon_col: str = None,
    outcome_col: str = None,
    case_value: str = None,
) -> gpd.GeoDataFrame:
    """
    Load a CSV file and return a GeoDataFrame with all points.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file containing case/control data.
    lat_col : str, optional
        Column name for latitude. Auto-detected if not provided.
    lon_col : str, optional
        Column name for longitude. Auto-detected if not provided.
    outcome_col : str, optional
        Column name for case/control status. Auto-detected if not provided.
    case_value : str, optional
        Value in outcome_col that represents a case. Auto-detected if not provided.

    Returns
    -------
    GeoDataFrame with columns:
        _lat, _lon, _outcome_norm, _is_case, geometry
    """

    # ── Load CSV ────────────────────────────────────────────
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        raise CSVError(f"CSV file not found: '{csv_path}'")
    except Exception as e:
        raise CSVError(f"Could not read CSV file: {e}")

    if df.empty:
        raise CSVError(f"CSV file is empty: '{csv_path}'")

    cols = list(df.columns)
    print(f"[spotmap] Loaded CSV: {len(df)} rows, {len(cols)} columns")

    # ── Detect lat/lon ──────────────────────────────────────
    if lat_col is None or lon_col is None:
        lat_col, lon_col = _detect_lat_lon(df, cols, lat_col, lon_col)

    # Validate columns exist
    _check_column_exists(lat_col, cols, "latitude")
    _check_column_exists(lon_col, cols, "longitude")

    print(f"[spotmap] Lat: '{lat_col}' | Lon: '{lon_col}'")

    # ── Detect outcome column ───────────────────────────────
    if outcome_col is None:
        outcome_col = _detect_outcome_col(cols)

    _check_column_exists(outcome_col, cols, "outcome")

    # ── Normalize outcome values ────────────────────────────
    df["_outcome_norm"] = (
        df[outcome_col]
        .astype(str)
        .str.strip()
        .str.lower()
        .replace({"nan": np.nan})
    )

    # ── Detect case value ───────────────────────────────────
    if case_value is None:
        case_value = _detect_case_value(df["_outcome_norm"])

    print(f"[spotmap] Outcome: '{outcome_col}' | Case value: '{case_value}'")

    df["_is_case"] = df["_outcome_norm"] == str(case_value).strip().lower()
    df["_lat"]     = pd.to_numeric(df[lat_col], errors="coerce")
    df["_lon"]     = pd.to_numeric(df[lon_col], errors="coerce")

    # Drop rows with missing coordinates
    before = len(df)
    df = df.dropna(subset=["_lat", "_lon"])
    dropped = before - len(df)
    if dropped > 0:
        print(f"[spotmap] Dropped {dropped} rows with missing coordinates")

    if df.empty:
        raise NoDataError(
            "No valid coordinates found in the CSV. "
            "Please check your lat/lon columns."
        )

    # ── Build GeoDataFrame ──────────────────────────────────
    geometry = [Point(xy) for xy in zip(df["_lon"], df["_lat"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    cases    = gdf["_is_case"].sum()
    controls = (~gdf["_is_case"]).sum()
    print(f"[spotmap] Cases: {cases} | Controls: {controls}")

    if cases == 0:
        raise NoDataError(
            f"No case points found where outcome == '{case_value}'. "
            f"Unique values in outcome column: {df['_outcome_norm'].dropna().unique().tolist()}\n"
            f"Pass the correct value using: case_value='your_value'"
        )

    return gdf


# =========================================================
# PUBLIC: LOAD BOUNDARIES
# =========================================================

def load_boundaries(
    district_path: str = None,
    state_path: str = None,
    full_resolution: bool = False,
):
    """
    Load state and district boundary files.

    Parameters
    ----------
    district_path : str, optional
        Path to a custom district boundary file.
        If None, uses the bundled lite file.
    state_path : str, optional
        Path to a custom state boundary file.
        If None, uses the bundled lite file.
    full_resolution : bool, optional
        If True, downloads and uses full resolution boundaries.
        Ignored if custom paths are provided.

    Returns
    -------
    tuple: (districts GeoDataFrame, states GeoDataFrame)
    """

    # ── Resolve paths ───────────────────────────────────────
    if district_path is None:
        if full_resolution:
            district_path = get_full_path("district_boundary_full.fgb")
        else:
            district_path = get_bundled_path("district_boundary_lite.fgb")

    if state_path is None:
        if full_resolution:
            state_path = get_full_path("state_boundary_full.fgb")
        else:
            state_path = get_bundled_path("state_boundary_lite.fgb")

    # ── Load districts ──────────────────────────────────────
    print(f"[spotmap] Loading districts: {os.path.basename(district_path)}")
    districts = _load_boundary_file(district_path)

    DISTRICT_CANDIDATES = [
        "DISTRICT", "DIST_NEW", "DISTRICT_N",
        "DT_NAME", "DIST_ROMAN", "dtname", "NAME"
    ]
    district_name_col = _find_name_column(districts, DISTRICT_CANDIDATES, "district")

    # ── Load states ─────────────────────────────────────────
    print(f"[spotmap] Loading states: {os.path.basename(state_path)}")
    states = _load_boundary_file(state_path)

    STATE_CANDIDATES = ["STATE", "STATE_UT", "ST_NM", "STATE_NAME", "STNAME", "NAME"]
    state_name_col = _find_name_column(states, STATE_CANDIDATES, "state")

    print(f"[spotmap] Districts: {len(districts)} | States: {len(states)}")

    return districts, states, district_name_col, state_name_col


# =========================================================
# INTERNAL HELPERS
# =========================================================

def _load_boundary_file(path: str) -> gpd.GeoDataFrame:
    """Load a boundary file, fix CRS and geometries."""
    try:
        gdf = gpd.read_file(path)
    except Exception as e:
        raise BoundaryFileError(
            f"Could not read boundary file: '{path}'\nError: {e}"
        )

    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    gdf["geometry"] = gdf["geometry"].buffer(0)
    return gdf


def _find_name_column(gdf: gpd.GeoDataFrame, candidates: list, label: str) -> str:
    """Find the name column in a GeoDataFrame from a list of candidates."""
    col = next((c for c in candidates if c in gdf.columns), None)
    if col is None:
        raise BoundaryFileError(
            f"Could not find {label} name column in boundary file.\n"
            f"Available columns: {list(gdf.columns)}\n"
            f"Expected one of: {candidates}"
        )
    return col


def _get_sample_values(df, col, n=5):
    return df[col].dropna().astype(str).str.strip().head(n).tolist()


def _is_float_column(df, col):
    samples = _get_sample_values(df, col)
    return bool(samples) and all(re.match(_FLOAT_PATTERN, x) for x in samples)


def _is_pair_column(df, col):
    samples = _get_sample_values(df, col)
    return bool(samples) and all(re.match(_PAIR_PATTERN, x) for x in samples)


def _detect_lat_lon(df, cols, lat_col, lon_col):
    """Auto-detect latitude and longitude columns."""

    # Step 1: Check for combined column e.g. "[12.34, 56.78]"
    for col in cols:
        if _is_pair_column(df, col):
            print(f"[spotmap] Found combined coordinate column: '{col}'")
            split = (
                df[col].astype(str)
                .str.replace(r'[\[\]()]', '', regex=True)
                .str.split(',', expand=True)
            )
            v1 = pd.to_numeric(split[0].str.strip(), errors='coerce')
            v2 = pd.to_numeric(split[1].str.strip(), errors='coerce')

            if v1.abs().max() > 90 and v2.abs().max() <= 90:
                df['_auto_lon'] = v1
                df['_auto_lat'] = v2
            elif v2.abs().max() > 90 and v1.abs().max() <= 90:
                df['_auto_lat'] = v1
                df['_auto_lon'] = v2
            else:
                df['_auto_lon'] = np.where(v1.abs() > v2.abs(), v1, v2)
                df['_auto_lat'] = np.where(v1.abs() > v2.abs(), v2, v1)

            return '_auto_lat', '_auto_lon'

    # Step 2: Look for separate lat/lon columns by name
    numeric_cols = [c for c in cols if _is_float_column(df, c)]

    lat_keywords = ["lat", "latitude", "y", "northing"]
    lon_keywords = ["lon", "long", "longitude", "lng", "x", "easting"]

    detected_lat = lat_col
    detected_lon = lon_col

    for c in numeric_cols:
        c_lower = c.lower()
        if detected_lat is None and any(k in c_lower for k in lat_keywords):
            detected_lat = c
        if detected_lon is None and any(k in c_lower for k in lon_keywords):
            detected_lon = c

    # Step 3: If still not found and exactly 2 numeric columns, guess
    if (detected_lat is None or detected_lon is None) and len(numeric_cols) == 2:
        print("[spotmap] Guessing lat/lon from 2 numeric columns...")
        detected_lat = detected_lat or numeric_cols[0]
        detected_lon = detected_lon or numeric_cols[1]

    if detected_lat is None or detected_lon is None:
        raise ColumnDetectionError(
            "Could not automatically detect latitude and longitude columns.\n"
            f"Available columns: {cols}\n"
            "Please specify them manually:\n"
            "  spotmap.build('data.csv', lat_col='my_lat', lon_col='my_lon')"
        )

    return detected_lat, detected_lon


def _detect_outcome_col(cols):
    """Auto-detect the outcome/case-control column."""
    candidates = ["outcome", "case_control", "status", "class", "target", "casecontrol"]
    for cand in candidates:
        matches = [c for c in cols if cand in c.lower()]
        if matches:
            return matches[0]

    raise ColumnDetectionError(
        "Could not automatically detect the outcome (case/control) column.\n"
        f"Available columns: {cols}\n"
        "Please specify it manually:\n"
        "  spotmap.build('data.csv', outcome_col='my_outcome_column')"
    )


def _detect_case_value(outcome_series):
    """Auto-detect which value in the outcome column represents a case."""
    common_case_values = ["case", "cases", "1", "yes", "true", "positive", "present"]
    values = outcome_series.dropna().unique()

    detected = next((v for v in values if v in common_case_values), None)

    if detected is None:
        if len(values) > 0:
            detected = values[0]
            print(f"[spotmap] Could not detect case value. Using: '{detected}'")
            print(f"[spotmap] If wrong, pass: case_value='your_value'")
        else:
            raise NoDataError("Outcome column has no valid values.")

    return detected


def _check_column_exists(col, cols, label):
    if col not in cols:
        raise ColumnDetectionError(
            f"Column '{col}' not found in CSV for {label}.\n"
            f"Available columns: {cols}"
        )