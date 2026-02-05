# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

City Map Poster Generator - A Python CLI tool that generates beautiful, minimalist map posters for any city in the world using OpenStreetMap data via OSMnx. The tool creates high-quality, poster-ready images with customizable themes, multilingual support, and various output formats.

## Development Setup

### With uv (Recommended)
```bash
# Dependencies auto-install on first run
uv run ./create_map_poster.py --city "Paris" --country "France"

# Or explicitly sync dependencies first (using locked versions)
uv sync --locked
```

### With pip + venv
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Common Commands

### Run the Tool
```bash
# With uv
uv run ./create_map_poster.py -c "Tokyo" -C "Japan" -t noir

# With pip/venv
python create_map_poster.py -c "Tokyo" -C "Japan" -t noir
```

### Testing & Validation
```bash
# Test CLI help
python create_map_poster.py --help

# List available themes
python create_map_poster.py --list-themes

# Validate Python syntax
python -m compileall . -q

# Run comprehensive test script (generates all variations)
./test/all_variations.sh
```

### Linting & Type Checking
```bash
# Install dev dependencies
pip install flake8 pylint mypy

# Flake8 (max line length: 160 for CI, 120 for local .flake8)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --statistics --max-line-length=160

# Pylint
pylint . --max-line-length=160

# Type checking with mypy
mypy . --ignore-missing-imports --no-strict-optional
```

## Architecture

### Data Flow Pipeline
```
CLI Args → Geocoding (Nominatim) → OSM Data Fetch (OSMnx) → Rendering (Matplotlib) → Output (PNG/SVG/PDF)
         → Theme Loading ────────────────────────────────┘
         → Font Management ──────────────────────────────┘
```

### Core Modules

**create_map_poster.py** - Main entry point and rendering logic
- CLI argument parsing (argparse)
- Data fetching from OpenStreetMap (via OSMnx)
- Map rendering with matplotlib
- Typography and text overlay
- Theme application

**font_management.py** - Font loading and Google Fonts integration
- Downloads and caches Google Fonts from their API
- Parses CSS to extract font URLs for different weights
- Handles font fallbacks (Roboto as default)
- Script detection for Latin vs non-Latin typography

### Key Functions & Their Purpose

| Function | Location | Purpose |
|----------|----------|---------|
| `create_poster()` | create_map_poster.py:482 | Main rendering pipeline - orchestrates data fetching, layer plotting, and text overlay |
| `fetch_graph()` | create_map_poster.py:409 | Fetches OSM street network via OSMnx with caching |
| `fetch_features()` | create_map_poster.py:444 | Fetches OSM features (water, parks) with caching |
| `get_edge_colors_by_type()` | create_map_poster.py:255 | Maps OSM highway types to theme colors for road hierarchy |
| `get_edge_widths_by_type()` | create_map_poster.py:289 | Maps OSM highway types to line widths for visual hierarchy |
| `get_coordinates()` | create_map_poster.py:319 | Geocoding via Nominatim API with caching |
| `get_crop_limits()` | create_map_poster.py:373 | Calculates viewport crop for desired aspect ratio |
| `create_gradient_fade()` | create_map_poster.py:214 | Creates top/bottom gradient overlay for aesthetic fade |
| `load_theme()` | create_map_poster.py:177 | Loads theme JSON from themes/ directory |
| `is_latin_script()` | create_map_poster.py:114 | Detects script for typography (enables letter-spacing for Latin only) |
| `load_fonts()` | font_management.py:137 | Loads local fonts or downloads from Google Fonts |
| `download_google_font()` | font_management.py:17 | Downloads and caches Google Fonts (woff2/ttf) |

### Rendering Layers (z-order, bottom to top)
```
z=0     Background color (theme.bg)
z=0.5   Water features (polygons)
z=0.8   Parks (polygons)
z=3     Roads (via ox.plot_graph, colored by hierarchy)
z=10    Gradient fades (top & bottom aesthetic overlay)
z=11    Text labels (city, country, coordinates)
```

### OSM Highway Hierarchy → Visual Styling

The tool maps OpenStreetMap highway types to visual weights:

```python
# In get_edge_colors_by_type() and get_edge_widths_by_type()
motorway, motorway_link     → Thickest (1.2×), theme['road_motorway']
trunk, primary              → Thick (1.0×), theme['road_primary']
secondary                   → Medium (0.8×), theme['road_secondary']
tertiary                    → Thin (0.6×), theme['road_tertiary']
residential, living_street  → Thinnest (0.4×), theme['road_residential']
```

## Themes System

Themes are JSON files in `themes/` directory with this structure:
```json
{
  "name": "Theme Name",
  "description": "Theme description",
  "bg": "#FFFFFF",              // Background color
  "text": "#000000",            // Text color
  "gradient_color": "#FFFFFF",  // Gradient fade color (matches bg for subtle fade)
  "water": "#C0C0C0",          // Water features
  "parks": "#F0F0F0",          // Parks/green spaces
  "road_motorway": "#0A0A0A",   // Highways
  "road_primary": "#1A1A1A",    // Primary roads
  "road_secondary": "#2A2A2A",  // Secondary roads
  "road_tertiary": "#3A3A3A",   // Tertiary roads
  "road_residential": "#4A4A4A", // Residential streets
  "road_default": "#3A3A3A"     // Fallback for unclassified roads
}
```

17 themes available: noir, midnight_blue, blueprint, neon_cyberpunk, warm_beige, pastel_dream, japanese_ink, emerald, forest, ocean, terracotta, sunset, autumn, copper_patina, monochrome_blue, gradient_roads, contrast_zones

## Typography & i18n

### Script Detection
- **Latin scripts** (English, French, Spanish, etc.): Letter spacing applied for elegant "P  A  R  I  S" effect
- **Non-Latin scripts** (Japanese, Arabic, Thai, Korean, etc.): Natural spacing for "東京" (no gaps)

Detection logic in `is_latin_script()`:
- Uses Unicode ranges U+0000-U+024F for Latin
- If >80% of alphabetic characters are Latin, spacing is applied
- Applied in text rendering for city names

### Font Loading Priority
1. If `--font-family` specified: Download from Google Fonts API → cache in `fonts/cache/`
2. Fallback: Local Roboto fonts in `fonts/` directory (Bold, Regular, Light)

### Text Positioning (in ax.transAxes normalized coordinates)
```
y=0.14   City name (with letter-spacing if Latin script)
y=0.125  Decorative separator line
y=0.10   Country name
y=0.07   Coordinates (lat, lon)
y=0.02   Attribution text (bottom-right)
```

## Caching System

All network-fetched data is cached using pickle in `cache/` directory (configurable via `CACHE_DIR` env var):
- Geocoding results (city → lat/lon)
- OSM street networks
- OSM features (water, parks)

Cache keys are generated from query parameters. Delete `cache/` directory to force refresh.

## CI/CD (GitHub Actions)

### `.github/workflows/pr-checks.yml`
- **Lint and Validate**: Runs on Ubuntu + Windows, Python 3.11-3.14
  - Validates Python syntax (`compileall`)
  - Tests CLI (`--help`, `--list-themes`)
  - flake8 (max line length: 160)
  - pylint (max line length: 160)
  - mypy type checking
- **Security**: pip-audit for dependency vulnerabilities

### `.github/workflows/conflicts.yml`
- Checks for merge conflicts in PRs

## Project Constraints

From the README "Contributors Guide":
- Bug fixes are welcomed
- **DO NOT** submit user interface (web/desktop) - CLI only
- **DO NOT** Dockerize for now
- If fixing bugs, test before/after poster output
- For big features, ask in Discussions/Issue first before implementing

## Common Modification Patterns

### Adding a New Map Layer (e.g., railways)
```python
# In create_poster(), after parks fetch in the progress bar:
pbar.set_description("Downloading railways")
railways = fetch_features(
    point,
    compensated_dist,
    tags={'railway': 'rail'},
    name="railways"
)
pbar.update(1)

# Then plot before roads (adjust zorder as needed):
if railways is not None and not railways.empty:
    railways_polys = railways[railways.geometry.type.isin(["Polygon", "MultiPolygon"])]
    if not railways_polys.empty:
        railways_polys = ox.projection.project_gdf(railways_polys)
        railways_polys.plot(ax=ax, color=THEME['railways'], linewidth=0.5, zorder=2.5)
```

### Adding a New Theme Property
1. Add key to theme JSON files: `"railways": "#FF0000"`
2. Use in rendering code: `THEME['railways']`
3. Add fallback in `load_theme()` default theme dict

### Useful OSMnx Query Patterns
```python
# Buildings
buildings = ox.features_from_point(point, tags={'building': True}, dist=dist)

# Specific amenities
cafes = ox.features_from_point(point, tags={'amenity': 'cafe'}, dist=dist)

# Different network types
G = ox.graph_from_point(point, dist=dist, network_type='drive')  # roads only
G = ox.graph_from_point(point, dist=dist, network_type='bike')   # bike paths
G = ox.graph_from_point(point, dist=dist, network_type='walk')   # pedestrian
```

## Performance Considerations

- Large `dist` values (>20km) = slow downloads + memory heavy
- Caching is critical to avoid Nominatim rate limits
- `network_type='drive'` is faster than `'all'` for street networks
- Reduce `dpi` from 300 to 150 for quick previews during development
- The `compensated_dist` calculation (line 534) accounts for viewport cropping to ensure the visible area matches the requested distance

## Dependencies

Python 3.11+ required. Key dependencies:
- **osmnx** 2.0.7: OpenStreetMap data fetching
- **matplotlib** 3.10.8: Rendering and plotting
- **geopandas** 1.1.2: Geospatial data handling
- **geopy** 2.4.1: Geocoding (Nominatim)
- **requests** 2.32.5: HTTP requests (Google Fonts)

All locked in `pyproject.toml` and `uv.lock`.
