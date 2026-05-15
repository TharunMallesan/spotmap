"""
spotmap/layers.py
=================
Handles:
  - Dot density cluster layer (cases)
  - Spot map pin layers (cases + controls)
  - Popup content for each marker
"""

import folium
from folium.plugins import MarkerCluster
import geopandas as gpd

# =========================================================
# PUBLIC: ADD CLUSTER LAYER
# =========================================================

def add_cluster_layer(
    m: folium.Map,
    points_cases: gpd.GeoDataFrame,
    state_name_col: str,
    district_name_col: str,
    cluster_color: str = "#E85252",
) -> MarkerCluster:
    """
    Add a dot density cluster layer for case points.

    Parameters
    ----------
    m : folium.Map
        The map to add the layer to.
    points_cases : GeoDataFrame
        Case points only.
    state_name_col : str
        Column name for state names (for popup).
    district_name_col : str
        Column name for district names (for popup).
    cluster_color : str
        Base hex color for clusters.

    Returns
    -------
    MarkerCluster layer (already added to map)
    """

    total = len(points_cases) or 1

    icon_fn = _build_cluster_icon_fn(total, cluster_color)

    cluster = MarkerCluster(
        name="Dot Density Layer",
        icon_create_function=icon_fn,
        disableClusteringAtZoom=15,
        spiderfyOnMaxZoom=True,
        showCoverageOnHover=False,
        maxClusterRadius=60,
        singleMarkerMode=True,
    )
    m.add_child(cluster)

    for _, row in points_cases.iterrows():
        lat = row.geometry.y
        lon = row.geometry.x
        popup = _make_popup(row, "Case", state_name_col, district_name_col)
        folium.Marker(location=[lat, lon], popup=popup).add_to(cluster)

    return cluster


# =========================================================
# PUBLIC: ADD PIN LAYERS
# =========================================================

def add_pin_layers(
    m: folium.Map,
    points_cases: gpd.GeoDataFrame,
    points_controls: gpd.GeoDataFrame,
    state_name_col: str,
    district_name_col: str,
    case_color: str = "#D55757",
    control_color: str = "#7676E7",
) -> tuple:
    """
    Add spot map pin layers for cases and controls.

    Parameters
    ----------
    m : folium.Map
        The map to add layers to.
    points_cases : GeoDataFrame
        Case points.
    points_controls : GeoDataFrame
        Control points.
    state_name_col : str
        Column name for state names (for popup).
    district_name_col : str
        Column name for district names (for popup).
    case_color : str
        Hex color for case pins.
    control_color : str
        Hex color for control pins.

    Returns
    -------
    tuple: (cases FeatureGroup, controls FeatureGroup)
    """

    pins_cases_layer    = folium.FeatureGroup(name="Spot Map - Cases")
    pins_controls_layer = folium.FeatureGroup(name="Spot Map - Controls")

    m.add_child(pins_cases_layer)
    m.add_child(pins_controls_layer)

    for _, row in points_cases.iterrows():
        lat = row.geometry.y
        lon = row.geometry.x
        popup = _make_popup(row, "Case", state_name_col, district_name_col)
        folium.Marker(
            location=[lat, lon],
            popup=popup,
        ).add_to(pins_cases_layer)

    for _, row in points_controls.iterrows():
        lat = row.geometry.y
        lon = row.geometry.x
        popup = _make_popup(row, "Control", state_name_col, district_name_col)
        folium.Marker(
            location=[lat, lon],
            popup=popup,
        ).add_to(pins_controls_layer)

    return pins_cases_layer, pins_controls_layer


# =========================================================
# INTERNAL HELPERS
# =========================================================

def _make_popup(row, point_type: str, state_col: str, district_col: str) -> str:
    """Build popup HTML for a marker."""
    state    = row.get(state_col, "Unknown")
    district = row.get(district_col, "Unknown")
    return (
        f"<b>Type:</b> {point_type}<br>"
        f"<b>State:</b> {state}<br>"
        f"<b>District:</b> {district}"
    )


def _build_cluster_icon_fn(total: int, cluster_color: str) -> str:
    """Build the JavaScript function for custom cluster icons."""
    return f"""
function(cluster) {{
    var count = cluster.getChildCount();
    var total = {total};

    var frac = count / total;
    if (!isFinite(frac) || frac < 0) frac = 0;
    if (frac > 1) frac = 1;

    var baseHex = window.clusterBaseColor || '{cluster_color}';

    function hexToRgb(hex) {{
        if (!hex) return {{r: 255, g: 0, b: 0}};
        var c = hex.replace('#','');
        if (c.length === 3) c = c[0]+c[0]+c[1]+c[1]+c[2]+c[2];
        var num = parseInt(c, 16);
        return {{
            r: (num >> 16) & 255,
            g: (num >> 8) & 255,
            b: num & 255
        }};
    }}

    function mixWithWhite(rgb, t) {{
        t = Math.max(0, Math.min(1, t));
        return {{
            r: Math.round(255 * (1 - t) + rgb.r * t),
            g: Math.round(255 * (1 - t) + rgb.g * t),
            b: Math.round(255 * (1 - t) + rgb.b * t)
        }};
    }}

    var baseRgb = hexToRgb(baseHex);
    var t = 0.4 + 0.6 * Math.sqrt(frac);
    if (!isFinite(t) || t < 0.4) t = 0.4;
    if (t > 1) t = 1;

    var mixed = mixWithWhite(baseRgb, t);
    var color = 'rgba(' + mixed.r + ',' + mixed.g + ',' + mixed.b + ',0.95)';
    var size  = 30 + Math.min(25, Math.sqrt(count) * 3);

    return new L.DivIcon({{
        html: '<div style="background:' + color +
              '; width:' + size + 'px; height:' + size +
              'px; border-radius:50%; display:flex; align-items:center;' +
              ' justify-content:center; box-shadow:0 0 6px rgba(0,0,0,0.4);' +
              ' font-weight:bold;">' + count + '</div>',
        className: 'cluster-icon',
        iconSize: new L.Point(size, size)
    }});
}}
"""