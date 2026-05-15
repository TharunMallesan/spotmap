"""Boundary loading and spatial-join utilities."""

import os
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

os.environ.setdefault("SHAPE_RESTORE_SHX", "YES")

_DATA_DIR = Path(__file__).parent / "data"
_STATE_FGB = _DATA_DIR / "state_boundary_lite.fgb"
_DISTRICT_FGB = _DATA_DIR / "district_boundary_lite.fgb"

_STATE_CANDIDATES = ["STATE", "STATE_UT", "ST_NM", "STATE_NAME", "STNAME", "NAME"]
_DISTRICT_CANDIDATES = [
    "DISTRICT", "DIST_NEW", "DISTRICT_N",
    "DT_NAME", "DIST_ROMAN", "dtname", "NAME",
]


def _find_name_col(gdf: gpd.GeoDataFrame, candidates: list, label: str) -> str:
    col = next((c for c in candidates if c in gdf.columns), None)
    if col is None:
        raise ValueError(
            f"No {label} name column found. "
            f"Columns present: {list(gdf.columns)}"
        )
    return col


def _ensure_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    gdf["geometry"] = gdf["geometry"].buffer(0)
    return gdf


def load_boundaries(state_shp: str = None, district_shp: str = None):
    """Load state and district boundary GeoDataFrames.

    Uses bundled FlatGeobuf files by default.  Pass custom shapefile/GeoPackage
    paths to override.

    Returns:
        (states, districts, state_name_col, district_name_col)
    """
    state_path = state_shp or str(_STATE_FGB)
    district_path = district_shp or str(_DISTRICT_FGB)

    states = _ensure_wgs84(gpd.read_file(state_path))
    districts = _ensure_wgs84(gpd.read_file(district_path))

    state_name_col = _find_name_col(states, _STATE_CANDIDATES, "state")
    district_name_col = _find_name_col(districts, _DISTRICT_CANDIDATES, "district")

    return states, districts, state_name_col, district_name_col


def build_india_outline(states: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    geom = states.unary_union
    return gpd.GeoDataFrame({"geometry": [geom]}, crs=states.crs)


def _get_col_safe(joined: gpd.GeoDataFrame, col: str):
    shp_col = f"{col}_shp"
    if shp_col in joined.columns:
        return joined[shp_col].values
    if col in joined.columns:
        return joined[col].values
    return [None] * len(joined)


def spatial_join(
    df,
    lat_col: str,
    lon_col: str,
    states: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    state_name_col: str,
    district_name_col: str,
) -> gpd.GeoDataFrame:
    """Attach state and district names to each point via spatial join."""
    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    points = gpd.GeoDataFrame(df.copy(), geometry=geometry, crs="EPSG:4326")

    joined_district = gpd.sjoin(
        points,
        districts[[district_name_col, "geometry"]],
        how="left",
        predicate="within",
        lsuffix="_csv",
        rsuffix="_shp",
    ).drop(columns=["index_right"], errors="ignore")

    joined_state = gpd.sjoin(
        points,
        states[[state_name_col, "geometry"]],
        how="left",
        predicate="within",
        lsuffix="_csv",
        rsuffix="_shp",
    ).drop(columns=["index_right"], errors="ignore")

    result = points.copy()
    result[district_name_col] = _get_col_safe(joined_district, district_name_col)
    result[state_name_col] = _get_col_safe(joined_state, state_name_col)
    return result


def determine_mode(
    points_cases: gpd.GeoDataFrame,
    district_name_col: str,
    state_name_col: str,
    count_cutoff: int = 2,
):
    """Determine map mode: 'districts', 'states', or 'india'.

    Returns:
        (mode, affected_districts, unique_states, bounds_array)
    """
    affected_districts = points_cases[district_name_col].dropna().unique()
    unique_states = points_cases[state_name_col].dropna().unique()

    num_districts = len(affected_districts)
    num_states = len(unique_states)

    if 0 < num_districts <= count_cutoff:
        mode = "districts"
    elif num_states > count_cutoff:
        mode = "india"
    else:
        mode = "states"

    bounds = np.array(points_cases.total_bounds, dtype=float)
    return mode, affected_districts, unique_states, bounds


def crop_geodataframe(
    gdf: gpd.GeoDataFrame, bounds: np.ndarray, margin: float = 1.0
) -> gpd.GeoDataFrame:
    if gdf is None or gdf.empty:
        return gdf
    if not np.isfinite(bounds).all():
        return gdf
    minx, miny, maxx, maxy = bounds
    sub = gdf.cx[minx - margin : maxx + margin, miny - margin : maxy + margin]
    return sub if not sub.empty else gdf
