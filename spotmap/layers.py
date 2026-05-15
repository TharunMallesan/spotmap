"""Folium layer builders for dot-density clusters and spot-map pins."""

import folium
import geopandas as gpd
from folium.plugins import MarkerCluster


def _cluster_icon_fn(cluster_color: str, total_cases: int) -> str:
    return f"""
function(cluster) {{
    var count = cluster.getChildCount();
    var total = {total_cases};

    var frac = count / total;
    if (!isFinite(frac) || frac < 0) frac = 0;
    if (frac > 1) frac = 1;

    var baseHex = window.clusterBaseColor || '{cluster_color}';

    function hexToRgb(hex) {{
        if (!hex) return {{r: 255, g: 0, b: 0}};
        var c = hex.replace('#','');
        if (c.length === 3) c = c[0]+c[0]+c[1]+c[1]+c[2]+c[2];
        var num = parseInt(c, 16);
        return {{r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255}};
    }}

    function mixWithWhite(rgb, t) {{
        t = Math.max(0, Math.min(1, t));
        return {{
            r: Math.round(255*(1-t) + rgb.r*t),
            g: Math.round(255*(1-t) + rgb.g*t),
            b: Math.round(255*(1-t) + rgb.b*t)
        }};
    }}

    var baseRgb = hexToRgb(baseHex);
    var t = 0.4 + 0.6 * Math.sqrt(frac);
    if (!isFinite(t) || t < 0.4) t = 0.4;
    if (t > 1) t = 1;

    var mixed = mixWithWhite(baseRgb, t);
    var color = 'rgba('+mixed.r+','+mixed.g+','+mixed.b+',0.95)';
    var size = 30 + Math.min(25, Math.sqrt(count) * 3);

    return new L.DivIcon({{
        html: '<div style="background:'+color+
              '; width:'+size+'px; height:'+size+
              'px; border-radius:50%; display:flex; align-items:center; justify-content:center; '+
              'box-shadow:0 0 6px rgba(0,0,0,0.4); font-weight:bold;">'+count+'</div>',
        className: 'cluster-icon',
        iconSize: new L.Point(size, size)
    }});
}}
"""


def add_boundary_layers(
    m: folium.Map,
    india_outline: gpd.GeoDataFrame,
    affected_states: gpd.GeoDataFrame,
    affected_districts: gpd.GeoDataFrame,
) -> None:
    folium.GeoJson(
        india_outline,
        name="India Border",
        control=False,
        style_function=lambda x: {
            "fillOpacity": 0.0,
            "color": "#000000",
            "weight": 1,
            "opacity": 0.5,
        },
    ).add_to(m)

    folium.GeoJson(
        affected_states,
        name="Affected States",
        control=False,
        style_function=lambda x: {
            "fillOpacity": 0.05,
            "color": "#4B0082",
            "weight": 1.5,
            "opacity": 0.7,
        },
    ).add_to(m)

    folium.GeoJson(
        affected_districts,
        name="Affected Districts",
        control=False,
        style_function=lambda x: {
            "color": "#000000",
            "weight": 1,
            "fillOpacity": 0.01,
            "opacity": 1.0,
        },
    ).add_to(m)


def add_marker_layers(
    m: folium.Map,
    points_cases: gpd.GeoDataFrame,
    points_controls: gpd.GeoDataFrame,
    state_name_col: str,
    district_name_col: str,
    cluster_color: str,
    case_color: str,
    control_color: str,
):
    """Add dot-density cluster and spot-map pin layers.

    Returns:
        (cluster_layer, pins_cases_layer, pins_controls_layer)
    """
    total_cases = len(points_cases) or 1

    cluster = MarkerCluster(
        name="Dot Density Layer",
        icon_create_function=_cluster_icon_fn(cluster_color, total_cases),
        disableClusteringAtZoom=15,
        spiderfyOnMaxZoom=True,
        showCoverageOnHover=False,
        maxClusterRadius=60,
        singleMarkerMode=True,
    )
    m.add_child(cluster)

    pins_cases_layer = folium.FeatureGroup(name="Spot Map - Cases")
    pins_controls_layer = folium.FeatureGroup(name="Spot Map - Controls")
    m.add_child(pins_cases_layer)
    m.add_child(pins_controls_layer)

    for _, row in points_cases.iterrows():
        lat, lon = row.geometry.y, row.geometry.x
        popup = (
            f"<b>Type:</b> Case<br>"
            f"<b>State:</b> {row.get(state_name_col, '')}<br>"
            f"<b>District:</b> {row.get(district_name_col, '')}"
        )
        folium.Marker(location=[lat, lon], popup=popup).add_to(cluster)
        folium.Marker(location=[lat, lon], popup=popup).add_to(pins_cases_layer)

    for _, row in points_controls.iterrows():
        lat, lon = row.geometry.y, row.geometry.x
        popup = (
            f"<b>Type:</b> Control<br>"
            f"<b>State:</b> {row.get(state_name_col, '')}<br>"
            f"<b>District:</b> {row.get(district_name_col, '')}"
        )
        folium.Marker(location=[lat, lon], popup=popup).add_to(pins_controls_layer)

    return cluster, pins_cases_layer, pins_controls_layer
