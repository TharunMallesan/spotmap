"""Main SpotMap class — orchestrates loading, spatial join, and map building."""

import folium
import pandas as pd

from .exceptions import NoCasePointsError
from .layers import add_boundary_layers, add_marker_layers
from .loader import load_csv
from .sidebar import build_sidebar_html
from .spatial import (
    build_india_outline,
    crop_geodataframe,
    determine_mode,
    load_boundaries,
    spatial_join,
)

_DEFAULT_CLUSTER_COLOR = "#E85252"
_DEFAULT_CASE_COLOR = "#D55757"
_DEFAULT_CONTROL_COLOR = "#7676E7"


class SpotMap:
    """Build an interactive epidemiological spot map for India.

    Parameters
    ----------
    data:
        Path to a CSV file **or** a pandas DataFrame containing point data.
    state_shp:
        Optional path to a custom state boundary file (shapefile / GeoPackage /
        FlatGeobuf).  Defaults to the bundled India state boundaries.
    district_shp:
        Optional path to a custom district boundary file.  Defaults to the
        bundled India district boundaries.
    lat_col:
        Column name for latitude.  Auto-detected when omitted.
    long_col:
        Column name for longitude.  Auto-detected when omitted.
    outcome_col:
        Column name for the case/control outcome.  Auto-detected when omitted.
    case_value:
        Value in *outcome_col* that represents a **case**.  Auto-detected when
        omitted.
    count_cutoff:
        If the number of affected districts is ≤ this value, the map zooms to
        district level; otherwise to state or national level.
    margin_deg:
        Padding (degrees) added around the data bounding box when cropping
        boundary layers.
    cluster_color:
        Hex colour for the dot-density cluster bubbles.
    case_color:
        Hex colour for case pins in spot-map mode.
    control_color:
        Hex colour for control pins in spot-map mode.
    """

    def __init__(
        self,
        data,
        *,
        state_shp: str = None,
        district_shp: str = None,
        lat_col: str = None,
        long_col: str = None,
        outcome_col: str = None,
        case_value: str = None,
        count_cutoff: int = 2,
        margin_deg: float = 1.0,
        cluster_color: str = _DEFAULT_CLUSTER_COLOR,
        case_color: str = _DEFAULT_CASE_COLOR,
        control_color: str = _DEFAULT_CONTROL_COLOR,
    ):
        if not isinstance(data, (str, pd.DataFrame)):
            raise TypeError("data must be a file path (str) or a pandas DataFrame.")
        self.data = data
        self.state_shp = state_shp
        self.district_shp = district_shp
        self.lat_col = lat_col
        self.long_col = long_col
        self.outcome_col = outcome_col
        self.case_value = case_value
        self.count_cutoff = count_cutoff
        self.margin_deg = margin_deg
        self.cluster_color = cluster_color
        self.case_color = case_color
        self.control_color = control_color

        self._map: folium.Map = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self) -> "SpotMap":
        """Run the full pipeline and store the Folium map internally.

        Returns *self* so calls can be chained: ``SpotMap(...).build().save(...)``.
        """
        # 1. Load data (path or DataFrame)
        df, lat_col, long_col, outcome_col, case_value = load_csv(
            self.data,
            lat_col=self.lat_col,
            long_col=self.long_col,
            outcome_col=self.outcome_col,
            case_value=self.case_value,
        )

        # 2. Load boundaries
        states, districts, state_name_col, district_name_col = load_boundaries(
            state_shp=self.state_shp,
            district_shp=self.district_shp,
        )

        # 3. Spatial join
        points_joined = spatial_join(
            df, lat_col, long_col, states, districts, state_name_col, district_name_col
        )

        # 4. Split cases / controls
        mask = points_joined["_outcome_norm"] == case_value
        points_cases = points_joined[mask].copy()
        points_controls = points_joined[~mask].copy()

        if points_cases.empty:
            raise NoCasePointsError(
                f"No case points found with outcome value '{case_value}'."
            )

        # 5. Determine mode + crop boundaries
        mode, affected_dist_names, unique_state_names, bounds = determine_mode(
            points_cases, district_name_col, state_name_col, self.count_cutoff
        )

        india_outline = build_india_outline(states)
        affected_states = states[states[state_name_col].isin(unique_state_names)].copy()
        affected_districts = districts[
            districts[district_name_col].isin(affected_dist_names)
        ].copy()

        india_sub = crop_geodataframe(india_outline, bounds, self.margin_deg)
        states_sub = crop_geodataframe(affected_states, bounds, self.margin_deg)
        districts_sub = crop_geodataframe(affected_districts, bounds, self.margin_deg)

        # 6. Init map
        zoom = {"india": 4, "states": 5, "districts": 7}[mode]
        m = folium.Map(
            location=[points_cases.geometry.y.mean(), points_cases.geometry.x.mean()],
            zoom_start=zoom,
            tiles="CartoDB positron",
        )

        # 7. Boundary layers
        add_boundary_layers(m, india_sub, states_sub, districts_sub)

        # 8. Marker layers
        cluster, pins_cases, pins_controls = add_marker_layers(
            m,
            points_cases,
            points_controls,
            state_name_col,
            district_name_col,
            cluster_color=self.cluster_color,
            case_color=self.case_color,
            control_color=self.control_color,
        )

        # 9. Sidebar
        sidebar_html = build_sidebar_html(
            map_id=m.get_name(),
            dots_name=cluster.get_name(),
            pins_cases_name=pins_cases.get_name(),
            pins_controls_name=pins_controls.get_name(),
            mode=mode,
            n_cases=len(points_cases),
            n_controls=len(points_controls),
            cluster_color=self.cluster_color,
            case_color=self.case_color,
            control_color=self.control_color,
        )
        m.get_root().html.add_child(folium.Element(sidebar_html))

        self._map = m
        return self

    def save(self, output_path: str) -> "SpotMap":
        """Save the built map to an HTML file."""
        if self._map is None:
            raise RuntimeError("Call .build() before .save().")
        self._map.save(output_path)
        return self

    @property
    def map(self) -> folium.Map:
        """The underlying Folium map object (after build)."""
        if self._map is None:
            raise RuntimeError("Call .build() first.")
        return self._map
