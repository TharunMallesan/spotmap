"""Sidebar HTML/JS/CSS generation."""


def build_sidebar_html(
    map_id: str,
    dots_name: str,
    pins_cases_name: str,
    pins_controls_name: str,
    mode: str,
    n_cases: int,
    n_controls: int,
    cluster_color: str,
    case_color: str,
    control_color: str,
) -> str:
    return f"""
<style>
#sidebar-toggle-btn {{
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 10000;
    width: 38px;
    height: 38px;
    background: white;
    border-radius: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 20px;
    user-select: none;
}}
#sidebar-toggle-btn span {{
    display: block;
    width: 20px;
    height: 2px;
    background: #333;
    margin: 3px 0;
}}
#sidebar-toggle-btn:hover {{ background: #f4f4f4; }}

#map-sidebar {{
    position: fixed;
    top: 10px;
    right: 10px;
    bottom: 10px;
    width: 260px;
    z-index: 9999;
    background: white;
    padding: 10px 12px;
    border-radius: 6px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.4);
    font-size: 13px;
    overflow-y: auto;
    transform: translateX(110%);
    transition: transform 0.25s ease-out;
    font-family: sans-serif;
}}
#map-sidebar.open {{ transform: translateX(0); }}
#map-sidebar h4 {{
    margin: 8px 0 6px 0;
    font-size: 14px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 3px;
    color: #333;
}}
#map-sidebar label {{ display: block; margin: 4px 0; cursor: pointer; }}
#map-sidebar .sidebar-section {{ margin-bottom: 12px; }}
#map-sidebar .sidebar-footer {{
    margin-top: 12px;
    font-size: 11px;
    color: #555;
    border-top: 1px solid #eee;
    padding-top: 8px;
}}
#map-sidebar a.download-link {{
    display: block;
    margin: 4px 0;
    color: #0066cc;
    text-decoration: underline;
    cursor: pointer;
    font-weight: 600;
}}
#map-sidebar a.download-link:hover {{ color: #004a99; }}

#map-legend {{
    position: absolute;
    top: 20px;
    left: 60px;
    z-index: 1000;
    background: rgba(255,255,255,0.9);
    padding: 8px 10px;
    border-radius: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    font-size: 12px;
    font-family: sans-serif;
    min-width: 100px;
    border: 1px solid #ccc;
    display: none;
}}
#map-legend h4 {{
    margin: 0 0 6px 0;
    font-size: 13px;
    border-bottom: 1px solid #ccc;
    padding-bottom: 2px;
    text-align: center;
}}
.legend-item {{ display: flex; align-items: center; margin-bottom: 4px; }}
.legend-icon {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
    border: 1px solid rgba(0,0,0,0.2);
    display: inline-block;
}}

@media print {{
    #map-sidebar, #sidebar-toggle-btn {{ display: none !important; }}
    #map-legend {{ display: block !important; position: absolute; top: 10px; left: 10px; }}
    .leaflet-control-zoom {{ display: none !important; }}
}}
</style>

<div id="sidebar-toggle-btn" title="Map Options">
  <div><span></span><span></span><span></span></div>
</div>

<div id="map-legend">
    <h4>Legend</h4>
    <div class="legend-item" id="legend-case-item">
        <span class="legend-icon" id="legend-icon-case" style="background-color:{case_color};"></span>
        <span>Case</span>
    </div>
    <div class="legend-item" id="legend-control-item" style="display:none;">
        <span class="legend-icon" id="legend-icon-control" style="background-color:{control_color};"></span>
        <span>Control</span>
    </div>
</div>

<div id="map-sidebar">
  <div class="sidebar-section">
    <h4>Map Mode</h4>
    <label><input type="radio" name="markerMode" value="dots" checked> Dot Density (Cases)</label>
    <label><input type="radio" name="markerMode" value="pins"> Spot Map (Pins)</label>
  </div>

  <div class="sidebar-section">
    <h4>Spot Map Filter</h4>
    <label><input type="radio" name="spotFilterMode" value="cases" checked> Cases Only</label>
    <label><input type="radio" name="spotFilterMode" value="both"> Cases &amp; Controls</label>
  </div>

  <div class="sidebar-section">
    <h4>Cluster Color (Cases)</h4>
    <label><input type="radio" name="colorMode" value="red"> Red</label>
    <label><input type="radio" name="colorMode" value="blue"> Blue</label>
    <label><input type="radio" name="colorMode" value="green"> Green</label>
    <label>
      <input type="radio" name="colorMode" value="custom" checked> Custom
      <input type="color" id="clusterCustomColor" value="{cluster_color}"
             style="margin-left:6px;vertical-align:middle;width:40px;height:20px;border:none;padding:0;">
    </label>
  </div>

  <div class="sidebar-section">
    <h4>Spot Map Colors</h4>
    <div style="margin-bottom:6px;">
      <b>Cases:</b><br>
      <input type="color" id="caseColorPicker" value="{case_color}"
             style="vertical-align:middle;width:40px;height:20px;border:none;padding:0;">
      <button type="button" id="caseApply" style="font-size:11px;margin-left:4px;">Apply</button>
    </div>
    <div>
      <b>Controls:</b><br>
      <input type="color" id="controlColorPicker" value="{control_color}"
             style="vertical-align:middle;width:40px;height:20px;border:none;padding:0;">
      <button type="button" id="controlApply" style="font-size:11px;margin-left:4px;">Apply</button>
    </div>
  </div>

  <div class="sidebar-section">
    <h4>Pin Size</h4>
    <input type="range" id="pinSizeSlider" min="0.5" max="2.0" step="0.25" value="1.0" style="width:100%;">
  </div>

  <div class="sidebar-section">
    <h4>Export</h4>
    <a id="downloadPrintLink" class="download-link">Print / Save PDF</a>
    <a id="downloadPngLink" class="download-link">Download PNG</a>
  </div>

  <div class="sidebar-footer">
    <div><b>Mode:</b> {mode}</div>
    <div><b>Cases:</b> {n_cases}</div>
    <div><b>Controls:</b> {n_controls}</div>
  </div>
</div>

<script src="https://unpkg.com/leaflet-simple-map-screenshoter"></script>
<script>
window.addEventListener('load', function() {{
  var mapObj            = {map_id};
  var dotsLayer         = {dots_name};
  var pinsCasesLayer    = {pins_cases_name};
  var pinsControlsLayer = {pins_controls_name};

  // Move legend inside map container so screenshoter captures it
  var legendDiv = document.getElementById('map-legend');
  mapObj.getContainer().appendChild(legendDiv);

  var simpleMapScreenshoter = L.simpleMapScreenshoter({{
      hidden: true,
      mimeType: 'image/png'
  }}).addTo(mapObj);

  var sidebar = document.getElementById('map-sidebar');
  var toggleBtn = document.getElementById('sidebar-toggle-btn');
  var sidebarOpen = false;

  toggleBtn.addEventListener('click', function() {{
    sidebarOpen = !sidebarOpen;
    sidebar.classList.toggle('open', sidebarOpen);
  }});

  window.caseColor    = '{case_color}';
  window.controlColor = '{control_color}';
  window.clusterBaseColor = '{cluster_color}';
  window.pinScale = 1.0;

  function updateLegend() {{
    var legendBox = document.getElementById('map-legend');
    var isPins = document.querySelector('input[name="markerMode"]:checked').value === 'pins';
    legendBox.style.display = isPins ? 'block' : 'none';
    if (!isPins) return;
    document.getElementById('legend-icon-case').style.backgroundColor = window.caseColor;
    document.getElementById('legend-icon-control').style.backgroundColor = window.controlColor;
    var isBoth = document.querySelector('input[name="spotFilterMode"]:checked').value === 'both';
    document.getElementById('legend-control-item').style.display = isBoth ? 'flex' : 'none';
  }}

  function makePinIcon(colorHex) {{
    var scale = window.pinScale || 1.0;
    var baseW = 18, baseH = 24;
    var html =
      '<div style="position:relative;width:'+baseW+'px;height:'+baseH+'px;transform:scale('+scale+');transform-origin:50% 100%;">' +
        '<div style="position:absolute;left:3px;top:6px;width:12px;height:12px;border-radius:50% 50% 50% 0;background:'+colorHex+';transform:rotate(-45deg);box-shadow:0 0 2px rgba(0,0,0,0.5);"></div>' +
        '<div style="position:absolute;left:6.5px;top:9.5px;width:5px;height:5px;border-radius:50%;background:white;opacity:0.9;"></div>' +
      '</div>';
    return new L.DivIcon({{ html: html, className: '', iconSize: [baseW, baseH], iconAnchor: [baseW/2, baseH] }});
  }}

  function redrawPins() {{
    if (pinsCasesLayer) {{
      pinsCasesLayer.eachLayer(function(marker) {{
        if (marker.setIcon) marker.setIcon(makePinIcon(window.caseColor));
      }});
    }}
    if (pinsControlsLayer) {{
      pinsControlsLayer.eachLayer(function(marker) {{
        if (marker.setIcon) marker.setIcon(makePinIcon(window.controlColor));
      }});
    }}
    updateLegend();
  }}

  function refreshClusters() {{
    if (mapObj.hasLayer(dotsLayer)) {{
      mapObj.removeLayer(dotsLayer);
      mapObj.addLayer(dotsLayer);
    }}
  }}

  function applyLayerLogic() {{
    var mode = document.querySelector('input[name="markerMode"]:checked').value;
    var filter = document.querySelector('input[name="spotFilterMode"]:checked').value;

    if (mode === 'dots') {{
      if (!mapObj.hasLayer(dotsLayer)) mapObj.addLayer(dotsLayer);
      if (mapObj.hasLayer(pinsCasesLayer)) mapObj.removeLayer(pinsCasesLayer);
      if (mapObj.hasLayer(pinsControlsLayer)) mapObj.removeLayer(pinsControlsLayer);
    }} else {{
      if (mapObj.hasLayer(dotsLayer)) mapObj.removeLayer(dotsLayer);
      if (!mapObj.hasLayer(pinsCasesLayer)) mapObj.addLayer(pinsCasesLayer);
      if (filter === 'both') {{
        if (!mapObj.hasLayer(pinsControlsLayer)) mapObj.addLayer(pinsControlsLayer);
      }} else {{
        if (mapObj.hasLayer(pinsControlsLayer)) mapObj.removeLayer(pinsControlsLayer);
      }}
    }}
    updateLegend();
  }}

  document.querySelectorAll('input[type=radio]').forEach(function(r) {{
    r.addEventListener('change', applyLayerLogic);
  }});

  // Cluster color
  var colorRadios = document.getElementsByName('colorMode');
  var custClust = document.getElementById('clusterCustomColor');

  function updateClusterColor() {{
    var val = document.querySelector('input[name="colorMode"]:checked').value;
    if (val === 'red') window.clusterBaseColor = '#FF0000';
    else if (val === 'blue') window.clusterBaseColor = '#0000FF';
    else if (val === 'green') window.clusterBaseColor = '#00AA00';
    else window.clusterBaseColor = custClust.value;
    refreshClusters();
  }}

  for (var i = 0; i < colorRadios.length; i++) colorRadios[i].addEventListener('change', updateClusterColor);
  if (custClust) custClust.addEventListener('input', function() {{
    document.querySelector('input[name="colorMode"][value="custom"]').checked = true;
    updateClusterColor();
  }});

  // Spot map colors
  document.getElementById('caseApply').addEventListener('click', function() {{
    window.caseColor = document.getElementById('caseColorPicker').value;
    redrawPins();
  }});
  document.getElementById('controlApply').addEventListener('click', function() {{
    window.controlColor = document.getElementById('controlColorPicker').value;
    redrawPins();
  }});

  // Pin size
  document.getElementById('pinSizeSlider').addEventListener('input', function(e) {{
    window.pinScale = parseFloat(e.target.value);
    redrawPins();
  }});

  // Export
  document.getElementById('downloadPrintLink').addEventListener('click', function() {{ window.print(); }});
  document.getElementById('downloadPngLink').addEventListener('click', function() {{
    sidebar.classList.remove('open');
    sidebarOpen = false;
    setTimeout(function() {{
      simpleMapScreenshoter.takeScreen('blob', {{ caption: function() {{ return ''; }} }})
        .then(function(blob) {{
          var link = document.createElement('a');
          link.download = 'map.png';
          link.href = URL.createObjectURL(blob);
          link.click();
        }})
        .catch(function(e) {{ alert(e); }})
        .finally(function() {{
          sidebar.classList.add('open');
          sidebarOpen = true;
        }});
    }}, 500);
  }});

  applyLayerLogic();
  redrawPins();
}});
</script>
"""
