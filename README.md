# SpotMap

**Interactive epidemiological spot maps for India**

SpotMap turns a CSV of case/control coordinates into a publication-ready interactive HTML map with:

- **Dot density** clustering (cases only)
- **Spot map** pins (cases and/or controls) with custom colours
- Automatic state/district boundary overlays (bundled data — no shapefile setup needed)
- Sidebar with mode toggle, colour pickers, pin size slider, and PNG/PDF export
- Smart auto-detection of latitude, longitude, and outcome columns

---

## Installation

```bash
pip install spotmap
```

---

## Quick start

### Python API

```python
from spotmap import SpotMap

SpotMap("my_data.csv").build().save("map.html")
```

### Command line

```bash
spotmap my_data.csv -o map.html
```

---

## CSV format

SpotMap auto-detects columns — no strict naming required.

| Requirement | Details |
|---|---|
| **Coordinates** | Separate `lat` / `lon` columns **or** a combined `"lat,lon"` column |
| **Outcome** | A column named `outcome`, `status`, `case_control`, etc. with values like `case` / `control` |

Example:

```csv
latitude,longitude,outcome
28.6,77.2,case
19.0,72.8,control
13.0,80.2,case
```

---

## Python API reference

```python
SpotMap(
    csv_path,                       # required
    state_shp=None,                 # custom state boundary (shapefile/GeoPackage)
    district_shp=None,              # custom district boundary
    lat_col=None,                   # override auto-detection
    lon_col=None,
    outcome_col=None,
    case_value=None,                # value that means "case" in outcome_col
    count_cutoff=2,                 # districts ≤ cutoff → district zoom
    margin_deg=1.0,                 # boundary crop padding
    cluster_color="#E85252",        # dot-density bubble colour
    case_color="#D55757",           # case pin colour
    control_color="#7676E7",        # control pin colour
)
```

Chain calls:

```python
sm = SpotMap("data.csv", case_color="#FF0000").build()
sm.save("map.html")

# Access the raw Folium map for further customisation
folium_map = sm.map
```

---

## CLI reference

```
usage: spotmap [-h] [-o OUTPUT] [--state-shp STATE_SHP]
               [--district-shp DISTRICT_SHP] [--lat-col LAT_COL]
               [--lon-col LON_COL] [--outcome-col OUTCOME_COL]
               [--case-value CASE_VALUE] [--count-cutoff COUNT_CUTOFF]
               [--cluster-color CLUSTER_COLOR] [--case-color CASE_COLOR]
               [--control-color CONTROL_COLOR]
               csv
```

---

## License

MIT © Tharun Mallesan
