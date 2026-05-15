"""
spotmap/spatial.py
==================
Handles:
  - Spatial join of points with district and state boundaries
  - Map mode detection (district / state / india view)
  - Boundary cropping to the area of interest
"""

import numpy as np
import geopandas as gpd

from spotmap.exceptions import NoDataError

# =========================================================
# PUBLIC: SPATIAL JOIN
# =========================================================

def join_with_boundaries(
    points_gdf: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    states: gpd.GeoDataFrame,
    district_name_col: str,
    state_name_col: str,
) -> gpd.GeoDataFrame:
    """
    Spatially join points with district and state boundaries.

    Adds district and state name columns to each point.

    Parameters
    ----------
    points_gdf : GeoDataFrame
        All points (cases + controls).
    districts : GeoDataFrame
        District boundary GeoDataFrame.
    states : GeoDataFrame
        State boundary GeoDataFrame.
    district_name_col : str
        Column name for district names in districts GeoDataFrame.
    state_name_col : str
        Column name for state names in states GeoDataFrame.

    Returns
    -------
    GeoDataFrame with added district and state name columns.
    """

    print("[spotmap] Performing spatial join...")

    # Join with districts
    points_district = gpd.sjoin(
        points_gdf,
        districts[[district_name_col, "geometry"]],
        how="left",
        predicate="within",
        lsuffix="_csv",
        rsuffix="_shp",
    ).drop(columns=["index_right"], errors="ignore")

    # Join with states
    points_state = gpd.sjoin(
        points_gdf,
        states[[state_name_col, "geometry"]],
        how="left",
        predicate="within",
        lsuffix="_csv",
        rsuffix="_shp",
    ).drop(columns=["index_right"], errors="ignore")

    # Merge results back into one GeoDataFrame
    result = points_gdf.copy()
    result[district_name_col] = _get_joined_column(points_district, district_name_col)
    result[state_name_col]    = _get_joined_column(points_state, state_name_col)

    print("[spotmap] Spatial join complete.")
    return result


# =========================================================
# PUBLIC: SPLIT CASES / CONTROLS
# =========================================================

def split_cases_controls(
    points_gdf: gpd.GeoDataFrame,
) -> tuple:
    """
    Split joined GeoDataFrame into cases and controls.

    Parameters
    ----------
    points_gdf : GeoDataFrame
        Joined GeoDataFrame with _is_case column.

    Returns
    -------
    tuple: (cases GeoDataFrame, controls GeoDataFrame)
    """
    cases    = points_gdf[points_gdf["_is_case"]].copy()
    controls = points_gdf[~points_gdf["_is_case"]].copy()

    if cases.empty:
        raise NoDataError(
            "No case points found after spatial join. "
            "Check that your coordinates fall within India boundaries."
        )

    return cases, controls


# =========================================================
# PUBLIC: MAP MODE DETECTION
# =========================================================

def detect_map_mode(
    points_cases: gpd.GeoDataFrame,
    district_name_col: str,
    state_name_col: str,
    count_cutoff: int = 5,
) -> str:
    """
    Detect the appropriate map mode based on how many
    districts and states are affected.

    Modes:
      - 'districts' → few districts affected (zooms to district level)
      - 'states'    → multiple states affected (zooms to state level)
      - 'india'     → many states affected (national view)

    Parameters
    ----------
    points_cases : GeoDataFrame
        Case points only.
    district_name_col : str
        Column name for district names.
    state_name_col : str
        Column name for state names.
    count_cutoff : int
        Threshold for switching between modes.

    Returns
    -------
    str: 'districts', 'states', or 'india'
    """

    num_districts = points_cases[district_name_col].nunique()
    num_states    = points_cases[state_name_col].nunique()

    if 0 < num_districts <= count_cutoff:
        mode = "districts"
    elif num_states > count_cutoff:
        mode = "india"
    else:
        mode = "states"

    print(f"[spotmap] Mode: {mode} | Districts: {num_districts} | States: {num_states}")
    return mode


# =========================================================
# PUBLIC: BOUNDARY PREPARATION
# =========================================================

def prepare_boundaries(
    points_cases: gpd.GeoDataFrame,
    districts: gpd.GeoDataFrame,
    states: gpd.GeoDataFrame,
    district_name_col: str,
    state_name_col: str,
    margin_deg: float = 1.0,
):
    """
    Prepare cropped boundary layers for rendering.

    Returns only the boundaries relevant to the affected area,
    cropped with a margin for cleaner map display.

    Parameters
    ----------
    points_cases : GeoDataFrame
        Case points only.
    districts : GeoDataFrame
        Full district boundary GeoDataFrame.
    states : GeoDataFrame
        Full state boundary GeoDataFrame.
    district_name_col : str
        Column name for district names.
    state_name_col : str
        Column name for state names.
    margin_deg : float
        Margin in degrees to add around the bounding box.

    Returns
    -------
    dict with keys:
        india_outline, affected_states, affected_districts,
        bounds, unique_states_count, unique_districts_count
    """

    affected_district_names = points_cases[district_name_col].dropna().unique()
    affected_state_names    = points_cases[state_name_col].dropna().unique()

    affected_states    = states[states[state_name_col].isin(affected_state_names)].copy()
    affected_districts = districts[districts[district_name_col].isin(affected_district_names)].copy()

    # India outline
    india_geom    = states.unary_union
    india_outline = gpd.GeoDataFrame({"geometry": [india_geom]}, crs=states.crs)

    # Bounding box of cases
    bounds = np.array(points_cases.total_bounds, dtype=float)

    def crop(gdf):
        if gdf is None or gdf.empty or not np.isfinite(bounds).all():
            return gdf
        minx, miny, maxx, maxy = bounds
        sub = gdf.cx[
            minx - margin_deg : maxx + margin_deg,
            miny - margin_deg : maxy + margin_deg,
        ]
        return sub if not sub.empty else gdf

    return {
        "india_outline":       crop(india_outline),
        "affected_states":     crop(affected_states),
        "affected_districts":  crop(affected_districts),
        "bounds":              bounds,
        "unique_states_count":    points_cases[state_name_col].nunique(),
        "unique_districts_count": points_cases[district_name_col].nunique(),
    }


# =========================================================
# INTERNAL HELPERS
# =========================================================

def _get_joined_column(joined_df, col_name):
    """Safely extract joined column, handling _shp suffix."""
    shp_col = f"{col_name}_shp"
    if shp_col in joined_df.columns:
        return joined_df[shp_col].values
    if col_name in joined_df.columns:
        return joined_df[col_name].values
    return [None] * len(joined_df)