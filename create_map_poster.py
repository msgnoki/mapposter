#!/usr/bin/env python3
"""
City Map Poster Generator

This module generates beautiful, minimalist map posters for any city in the world.
It fetches OpenStreetMap data using OSMnx, applies customizable themes, and creates
high-quality poster-ready images with roads, water features, and parks.
"""

import argparse
import asyncio
import json
import os
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import cast

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from geopandas import GeoDataFrame
from geopy.geocoders import Nominatim
from lat_lon_parser import parse
from matplotlib.font_manager import FontProperties
from networkx import MultiDiGraph
from shapely.geometry import Point
from tqdm import tqdm

from font_management import load_fonts


class CacheError(Exception):
    """Raised when a cache operation fails."""


CACHE_DIR_PATH = os.environ.get("CACHE_DIR", "cache")
CACHE_DIR = Path(CACHE_DIR_PATH)
CACHE_DIR.mkdir(exist_ok=True)

THEMES_DIR = "themes"
FONTS_DIR = "fonts"
POSTERS_DIR = "posters"

FILE_ENCODING = "utf-8"

FONTS = load_fonts()


def _cache_path(key: str) -> str:
    """
    Generate a safe cache file path from a cache key.

    Args:
        key: Cache key identifier

    Returns:
        Path to cache file with .pkl extension
    """
    safe = key.replace(os.sep, "_")
    return os.path.join(CACHE_DIR, f"{safe}.pkl")


def cache_get(key: str):
    """
    Retrieve a cached object by key.

    Args:
        key: Cache key identifier

    Returns:
        Cached object if found, None otherwise

    Raises:
        CacheError: If cache read operation fails
    """
    try:
        path = _cache_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        raise CacheError(f"Cache read failed: {e}") from e


def cache_set(key: str, value):
    """
    Store an object in the cache.

    Args:
        key: Cache key identifier
        value: Object to cache (must be picklable)

    Raises:
        CacheError: If cache write operation fails
    """
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
        path = _cache_path(key)
        with open(path, "wb") as f:
            pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as e:
        raise CacheError(f"Cache write failed: {e}") from e


# Land Polygons Loading
_LAND_POLYGONS_CACHE = None


def load_land_polygons():
    """
    Load OSM land polygons shapefile (lazy loading with caching).

    Returns GeoDataFrame with land polygons for the entire world.
    The shapefile is loaded once and cached in memory for subsequent calls.
    """
    global _LAND_POLYGONS_CACHE

    if _LAND_POLYGONS_CACHE is not None:
        return _LAND_POLYGONS_CACHE

    import geopandas as gpd
    land_polygons_path = "data/land_polygons/land-polygons-split-4326/land_polygons.shp"

    if not os.path.exists(land_polygons_path):
        print(f"⚠️  WARNING: Land polygons not found at {land_polygons_path}")
        print("   Download from: https://osmdata.openstreetmap.de/data/land-polygons.html")
        return None

    print("📂 Loading land polygons shapefile (one-time load)...")
    _LAND_POLYGONS_CACHE = gpd.read_file(land_polygons_path)
    print(f"✓ Loaded {len(_LAND_POLYGONS_CACHE)} land polygons")
    return _LAND_POLYGONS_CACHE


# Font loading now handled by font_management.py module


def is_latin_script(text):
    """
    Check if text is primarily Latin script.
    Used to determine if letter-spacing should be applied to city names.

    :param text: Text to analyze
    :return: True if text is primarily Latin script, False otherwise
    """
    if not text:
        return True

    latin_count = 0
    total_alpha = 0

    for char in text:
        if char.isalpha():
            total_alpha += 1
            # Latin Unicode ranges:
            # - Basic Latin: U+0000 to U+007F
            # - Latin-1 Supplement: U+0080 to U+00FF
            # - Latin Extended-A: U+0100 to U+017F
            # - Latin Extended-B: U+0180 to U+024F
            if ord(char) < 0x250:
                latin_count += 1

    # If no alphabetic characters, default to Latin (numbers, symbols, etc.)
    if total_alpha == 0:
        return True

    # Consider it Latin if >80% of alphabetic characters are Latin
    return (latin_count / total_alpha) > 0.8


def generate_output_filename(city, theme_name, output_format, dist=None):
    """
    Generate unique output filename with city, theme, distance, and datetime.
    """
    if not os.path.exists(POSTERS_DIR):
        os.makedirs(POSTERS_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city.lower().replace(" ", "_")
    ext = output_format.lower()

    # Include distance in filename if provided
    if dist:
        filename = f"{city_slug}_{theme_name}_{dist}m_{timestamp}.{ext}"
    else:
        filename = f"{city_slug}_{theme_name}_{timestamp}.{ext}"

    return os.path.join(POSTERS_DIR, filename)


def get_available_themes():
    """
    Scans the themes directory and returns a list of available theme names.
    """
    if not os.path.exists(THEMES_DIR):
        os.makedirs(THEMES_DIR)
        return []

    themes = []
    for file in sorted(os.listdir(THEMES_DIR)):
        if file.endswith(".json"):
            theme_name = file[:-5]  # Remove .json extension
            themes.append(theme_name)
    return themes


def load_theme(theme_name="terracotta"):
    """
    Load theme from JSON file in themes directory.
    """
    theme_file = os.path.join(THEMES_DIR, f"{theme_name}.json")

    if not os.path.exists(theme_file):
        print(f"⚠ Theme file '{theme_file}' not found. Using default terracotta theme.")
        # Fallback to embedded terracotta theme
        return {
            "name": "Terracotta",
            "description": "Mediterranean warmth - burnt orange and clay tones on cream",
            "bg": "#F5EDE4",
            "text": "#8B4513",
            "gradient_color": "#F5EDE4",
            "water": "#A8C4C4",
            "parks": "#E8E0D0",
            "road_motorway": "#A0522D",
            "road_primary": "#B8653A",
            "road_secondary": "#C9846A",
            "road_tertiary": "#D9A08A",
            "road_residential": "#E5C4B0",
            "road_default": "#D9A08A",
        }

    with open(theme_file, "r", encoding=FILE_ENCODING) as f:
        theme = json.load(f)
        print(f"✓ Loaded theme: {theme.get('name', theme_name)}")
        if "description" in theme:
            print(f"  {theme['description']}")
        return theme


# Load theme (can be changed via command line or input)
THEME = dict[str, str]()  # Will be loaded later


def create_gradient_fade(ax, color, location="bottom", zorder=10, height=0.25):
    """
    Creates a fade effect at the top or bottom of the map.

    Args:
        height: Gradient height as fraction of image (0.0-0.5). Default 0.25 = 25%.
    """
    vals = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((vals, vals))

    rgb = mcolors.to_rgb(color)
    my_colors = np.zeros((256, 4))
    my_colors[:, 0] = rgb[0]
    my_colors[:, 1] = rgb[1]
    my_colors[:, 2] = rgb[2]

    if location == "bottom":
        my_colors[:, 3] = np.linspace(1, 0, 256)
        extent_y_start = 0
        extent_y_end = height
    else:
        my_colors[:, 3] = np.linspace(0, 1, 256)
        extent_y_start = 1.0 - height
        extent_y_end = 1.0

    custom_cmap = mcolors.ListedColormap(my_colors)

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]

    y_bottom = ylim[0] + y_range * extent_y_start
    y_top = ylim[0] + y_range * extent_y_end

    ax.imshow(
        gradient,
        extent=[xlim[0], xlim[1], y_bottom, y_top],
        aspect="auto",
        cmap=custom_cmap,
        zorder=zorder,
        origin="lower",
    )


def get_edge_colors_by_type(g):
    """
    Assigns colors to edges based on road type hierarchy.
    Returns a list of colors corresponding to each edge in the graph.
    """
    edge_colors = []

    for _u, _v, data in g.edges(data=True):
        # Get the highway type (can be a list or string)
        highway = data.get('highway', 'unclassified')

        # Handle list of highway types (take the first one)
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'

        # Assign color based on road type
        if highway in ["motorway", "motorway_link"]:
            color = THEME["road_motorway"]
        elif highway in ["trunk", "trunk_link", "primary", "primary_link"]:
            color = THEME["road_primary"]
        elif highway in ["secondary", "secondary_link"]:
            color = THEME["road_secondary"]
        elif highway in ["tertiary", "tertiary_link"]:
            color = THEME["road_tertiary"]
        elif highway in ["residential", "living_street", "unclassified"]:
            color = THEME["road_residential"]
        else:
            color = THEME['road_default']

        edge_colors.append(color)

    return edge_colors


def get_edge_widths_by_type(g):
    """
    Assigns line widths to edges based on road type.
    Major roads get thicker lines.
    """
    edge_widths = []

    for _u, _v, data in g.edges(data=True):
        highway = data.get('highway', 'unclassified')

        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'

        # Assign width based on road importance
        if highway in ["motorway", "motorway_link"]:
            width = 1.2
        elif highway in ["trunk", "trunk_link", "primary", "primary_link"]:
            width = 1.0
        elif highway in ["secondary", "secondary_link"]:
            width = 0.8
        elif highway in ["tertiary", "tertiary_link"]:
            width = 0.6
        else:
            width = 0.4

        edge_widths.append(width)

    return edge_widths


def get_coordinates(city, country):
    """
    Fetches coordinates for a given city and country using geopy.
    Includes rate limiting to be respectful to the geocoding service.
    """
    coords = f"coords_{city.lower()}_{country.lower()}"
    cached = cache_get(coords)
    if cached:
        print(f"✓ Using cached coordinates for {city}, {country}")
        return cached

    print("Looking up coordinates...")
    geolocator = Nominatim(user_agent="city_map_poster", timeout=10)

    # Add a small delay to respect Nominatim's usage policy
    time.sleep(1)

    try:
        location = geolocator.geocode(f"{city}, {country}")
    except Exception as e:
        raise ValueError(f"Geocoding failed for {city}, {country}: {e}") from e

    # If geocode returned a coroutine in some environments, run it to get the result.
    if asyncio.iscoroutine(location):
        try:
            location = asyncio.run(location)
        except RuntimeError as exc:
            # If an event loop is already running, try using it to complete the coroutine.
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Running event loop in the same thread; raise a clear error.
                raise RuntimeError(
                    "Geocoder returned a coroutine while an event loop is already running. "
                    "Run this script in a synchronous environment."
                ) from exc
            location = loop.run_until_complete(location)

    if location:
        # Use getattr to safely access address (helps static analyzers)
        addr = getattr(location, "address", None)
        if addr:
            print(f"✓ Found: {addr}")
        else:
            print("✓ Found location (address not available)")
        print(f"✓ Coordinates: {location.latitude}, {location.longitude}")
        try:
            cache_set(coords, (location.latitude, location.longitude))
        except CacheError as e:
            print(e)
        return (location.latitude, location.longitude)

    raise ValueError(f"Could not find coordinates for {city}, {country}")


def get_crop_limits(g_proj, center_lat_lon, fig, dist):
    """
    Crop inward to preserve aspect ratio while guaranteeing
    full coverage of the requested radius.
    """
    lat, lon = center_lat_lon

    # Project center point into graph CRS
    center = (
        ox.projection.project_geometry(
            Point(lon, lat),
            crs="EPSG:4326",
            to_crs=g_proj.graph["crs"]
        )[0]
    )
    center_x, center_y = center.x, center.y

    fig_width, fig_height = fig.get_size_inches()
    aspect = fig_width / fig_height

    # Start from the *requested* radius
    half_x = dist
    half_y = dist

    # Cut inward to match aspect
    if aspect > 1:  # landscape → reduce height
        half_y = half_x / aspect
    else:  # portrait → reduce width
        half_x = half_y * aspect

    return (
        (center_x - half_x, center_x + half_x),
        (center_y - half_y, center_y + half_y),
    )


def fetch_graph(point, dist) -> MultiDiGraph | None:
    """
    Fetch street network graph from OpenStreetMap.

    Uses caching to avoid redundant downloads. Fetches all network types
    within the specified distance from the center point.

    Args:
        point: (latitude, longitude) tuple for center point
        dist: Distance in meters from center point

    Returns:
        MultiDiGraph of street network, or None if fetch fails
    """
    lat, lon = point
    graph = f"graph_{lat}_{lon}_{dist}"
    cached = cache_get(graph)
    if cached is not None:
        print("✓ Using cached street network")
        return cast(MultiDiGraph, cached)

    try:
        g = ox.graph_from_point(point, dist=dist, dist_type='bbox', network_type='all', truncate_by_edge=True)
        # Rate limit between requests
        time.sleep(0.5)
        try:
            cache_set(graph, g)
        except CacheError as e:
            print(e)
        return g
    except Exception as e:
        print(f"OSMnx error while fetching graph: {e}")
        return None


def fetch_features(point, dist, tags, name) -> GeoDataFrame | None:
    """
    Fetch geographic features (water, parks, etc.) from OpenStreetMap.

    Uses caching to avoid redundant downloads. Fetches features matching
    the specified OSM tags within distance from center point.

    Args:
        point: (latitude, longitude) tuple for center point
        dist: Distance in meters from center point
        tags: Dictionary of OSM tags to filter features
        name: Name for this feature type (for caching and logging)

    Returns:
        GeoDataFrame of features, or None if fetch fails
    """
    lat, lon = point
    tag_str = "_".join(tags.keys())
    features = f"{name}_{lat}_{lon}_{dist}_{tag_str}"
    cached = cache_get(features)
    if cached is not None:
        print(f"✓ Using cached {name}")
        return cast(GeoDataFrame, cached)

    try:
        data = ox.features_from_point(point, tags=tags, dist=dist)
        # Rate limit between requests
        time.sleep(0.3)
        try:
            cache_set(features, data)
        except CacheError as e:
            print(e)
        return data
    except Exception as e:
        print(f"OSMnx error while fetching features: {e}")
        return None


def create_poster(
    city,
    country,
    point,
    dist,
    output_file,
    output_format,
    width=12,
    height=16,
    country_label=None,
    name_label=None,
    display_city=None,
    display_country=None,
    fonts=None,
    gradient_height=0.25,
):
    """
    Generate a complete map poster with roads, water, parks, and typography.

    Creates a high-quality poster by fetching OSM data, rendering map layers,
    applying the current theme, and adding text labels with coordinates.

    Args:
        city: City name for display on poster
        country: Country name for display on poster
        point: (latitude, longitude) tuple for map center
        dist: Map radius in meters
        output_file: Path where poster will be saved
        output_format: File format ('png', 'svg', or 'pdf')
        width: Poster width in inches (default: 12)
        height: Poster height in inches (default: 16)
        country_label: Optional override for country text on poster
        _name_label: Optional override for city name (unused, reserved for future use)
        gradient_height: Height of top/bottom gradient fade as fraction (0.0-0.5, default: 0.25 = 25%)

    Raises:
        RuntimeError: If street network data cannot be retrieved
    """
    # Handle display names for i18n support
    # Priority: display_city/display_country > name_label/country_label > city/country
    display_city = display_city or name_label or city
    display_country = display_country or country_label or country

    print(f"\nGenerating map for {city}, {country}...")

    # Progress bar for data fetching
    with tqdm(
        total=6.5,
        desc="Fetching map data",
        unit="step",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
    ) as pbar:
        # 1. Fetch Street Network
        pbar.set_description("Downloading street network")
        compensated_dist = dist * (max(height, width) / min(height, width)) / 4  # To compensate for viewport crop
        g = fetch_graph(point, compensated_dist)
        if g is None:
            raise RuntimeError("Failed to retrieve street network data.")
        pbar.update(1)

        # 1.5 Fetch Administrative Boundaries (limites administratives)
        # Ces polygones couvrent toute la zone administrative (ville/commune)
        # et garantissent que les zones terrestres non-taguées apparaissent
        # comme terre et non comme mer (via le rectangle coastline)
        pbar.set_description("Downloading administrative boundaries")
        admin_boundaries = fetch_features(
            point,
            compensated_dist,
            tags={
                "boundary": "administrative",
                "admin_level": ["4", "5", "6", "7", "8", "9", "10"],  # Niveaux régionaux à locaux
            },
            name="admin_boundaries",
        )
        pbar.update(0.5)  # Demi-étape

        # 2. Fetch Landuse/Landcover (terre)
        pbar.set_description("Downloading land areas")
        landuse = fetch_features(
            point,
            compensated_dist,
            tags={
                # Utiliser True pour capturer TOUS les types de landuse
                # Cela évite que des zones terrestres non-catégorisées
                # apparaissent bleues (couvertes par le rectangle coastline)
                "landuse": True,
                "natural": ["scrub", "grassland", "wood", "heath", "sand", "beach", "bare_rock", "scree", "shingle", "fell"],
                "place": ["island"],
                # Ajouter leisure pour les zones récréatives
                "leisure": True,
            },
            name="landuse",
        )
        pbar.update(1)

        # 3. Fetch Water (mer, océan, rivières, lacs)
        #
        # Historically we requested a very broad set of tags here including
        # ``place=ocean`` and ``water=sea``.  Those queries would return large
        # polygons representing whole seas or bays, which then painted over
        # otherwise untagged land as if it were water.  To avoid this we
        # restrict our query to inland water bodies and riverbanks only.
        #
        # See https://wiki.openstreetmap.org/wiki/Tag:natural%3Dwater for
        # details on the ``natural=water`` tag and
        # https://wiki.openstreetmap.org/wiki/Tag:waterway=riverbank for
        # riverbanks.  We deliberately omit ``place=sea`` and ``water=sea`` as
        # those refer to the open ocean and should be rendered via the
        # coastline/sea background instead.  This change prevents the
        # inadvertent flooding of unclassified land areas reported in
        # OSM_WATER_RENDERING_ISSUE.md.
        pbar.set_description("Downloading water features")
        water_features = fetch_features(
            point,
            compensated_dist,
            tags={
                # ``natural=water`` covers lakes, reservoirs, ponds and other
                # inland water bodies.  We exclude bay/strait here to avoid
                # giant coastal polygons.
                "natural": "water",
                # ``waterway=riverbank`` represents the area occupied by a river.
                "waterway": "riverbank",
                # ``water`` keys enumerate only inland or man‑made water types.
                # We intentionally leave out "sea", "ocean", "bay" and
                # "strait" so that those are handled by the coastline logic.
                "water": ["lake", "river", "pond", "reservoir", "lagoon", "canal"],
            },
            name="water",
        )
        pbar.update(1)

        # 4. Fetch Parks
        pbar.set_description("Downloading parks/green spaces")
        parks = fetch_features(
            point,
            compensated_dist,
            tags={"leisure": "park", "landuse": "grass"},
            name="parks",
        )
        pbar.update(1)

        # 5. Fetch Railways
        pbar.set_description("Downloading railways")
        railways = fetch_features(
            point,
            compensated_dist,
            tags={
                "railway": ["rail", "subway", "light_rail", "tram", "narrow_gauge"],
            },
            name="railways",
        )
        pbar.update(1)

        # 6. Fetch Buildings
        pbar.set_description("Downloading buildings")
        buildings = fetch_features(
            point,
            compensated_dist,
            tags={"building": True},
            name="buildings",
        )
        pbar.update(1)

    print("✓ All data retrieved successfully!")

    # 2. Setup Plot
    print("Rendering map...")
    fig, ax = plt.subplots(figsize=(width, height), facecolor=THEME["bg"])
    ax.set_facecolor(THEME["bg"])
    ax.set_position((0.0, 0.0, 1.0, 1.0))

    # Project graph to a metric CRS so distances and aspect are linear (meters)
    g_proj = ox.project_graph(g)

    # Get crop limits to determine map bounds
    crop_xlim, crop_ylim = get_crop_limits(g_proj, point, fig, compensated_dist)

    # 3. Plot Layers
    # Layer -1: Coastline detection and sea background
    # Télécharger la coastline pour détecter les zones côtières
    coastline = fetch_features(
        point,
        compensated_dist,
        tags={"natural": "coastline"},
        name="coastline"
    )

    # Si on est près d'une côte, ajouter un fond bleu dans la zone viewport
    if coastline is not None and not coastline.empty:
        # Rectangle bleu pour la mer, limité à la zone visible
        from matplotlib.patches import Rectangle
        x_min, x_max = crop_xlim
        y_min, y_max = crop_ylim
        sea_rect = Rectangle(
            (x_min, y_min),
            x_max - x_min,
            y_max - y_min,
            facecolor=THEME['water'],
            edgecolor='none',
            zorder=-1
        )
        ax.add_patch(sea_rect)

    # Layer -0.3: OSM Land Polygons - Zones terrestres officielles
    # Ces polygones proviennent d'OSM et définissent précisément les zones terrestres
    # vs maritimes dans le monde entier. Cela garantit que seules les vraies zones
    # terrestres apparaissent en couleur terre, pas les zones maritimes.
    land_polygons_gdf = load_land_polygons()
    if land_polygons_gdf is not None:
        # Extraire les polygones qui intersectent la zone visible (en WGS84)
        # Convertir crop limits vers WGS84 pour la requête
        import geopandas as gpd
        from shapely.geometry import Point as ShapelyPoint

        # Obtenir la bbox en lat/lon (WGS84)
        # g_proj est en projection métrique, on doit retourner à WGS84
        x_min, x_max = crop_xlim
        y_min, y_max = crop_ylim

        # Créer une bbox légèrement agrandie pour être sûr de tout capturer
        margin = 0.05  # ~5km de marge
        lon_min, lon_max = point[1] - margin, point[1] + margin
        lat_min, lat_max = point[0] - margin, point[0] + margin

        print(f"🌍 Extracting land polygons for bbox ({lat_min:.3f}, {lon_min:.3f}) to ({lat_max:.3f}, {lon_max:.3f})")
        land_subset = land_polygons_gdf.cx[lon_min:lon_max, lat_min:lat_max].copy()

        if not land_subset.empty:
            print(f"✓ {len(land_subset)} land polygons found in area")
            # Projeter dans le CRS de la carte
            try:
                land_subset = land_subset.to_crs(g_proj.graph['crs'])
            except Exception:
                land_subset = ox.projection.project_gdf(land_subset)

            # Dessiner les zones terrestres
            land_subset.plot(ax=ax, facecolor=THEME['bg'], edgecolor='none', zorder=-0.3)
            print(f"🗺️  Rendered {len(land_subset)} land polygons")
        else:
            print(f"⚠️  No land polygons in area (likely inland - drawing fallback rectangle)")
            # Fallback: rectangle terre si pas de land polygons trouvés
            from matplotlib.patches import Rectangle
            land_rect = Rectangle(
                (x_min, y_min),
                x_max - x_min,
                y_max - y_min,
                facecolor=THEME['bg'],
                edgecolor='none',
                zorder=-0.3
            )
            ax.add_patch(land_rect)
    else:
        print(f"⚠️  Land polygons not available, using fallback rectangle")
        # Fallback: rectangle terre simple
        from matplotlib.patches import Rectangle
        x_min, x_max = crop_xlim
        y_min, y_max = crop_ylim
        land_rect = Rectangle(
            (x_min, y_min),
            x_max - x_min,
            y_max - y_min,
            facecolor=THEME['bg'],
            edgecolor='none',
            zorder=-0.3
        )
        ax.add_patch(land_rect)

    # Layer 0.6: Zones maritimes (boundary=maritime)
    # Ces polygones marquent explicitement les zones maritimes dans OSM
    if coastline is not None and not coastline.empty:
        try:
            maritime = fetch_features(
                point,
                compensated_dist,
                tags={"boundary": "maritime"},
                name="maritime_boundaries"
            )
            if maritime is not None and not maritime.empty:
                print(f"🔍 Maritime: {len(maritime)} features, types: {maritime.geometry.type.value_counts().to_dict()}")
                maritime_polys = maritime[maritime.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
                if not maritime_polys.empty:
                    # Projeter
                    try:
                        maritime_polys = ox.projection.project_gdf(maritime_polys)
                    except Exception:
                        maritime_polys = maritime_polys.to_crs(g_proj.graph['crs'])

                    # Dessiner les zones maritimes en bleu
                    maritime_polys.plot(ax=ax, facecolor=THEME['water'], edgecolor='none', zorder=0.6)
                    print(f"🌊  Rendered {len(maritime_polys)} maritime boundary polygons")
                else:
                    print(f"⚠️  Maritime boundaries found but no polygons (likely LineStrings)")
        except Exception as e:
            print(f"⚠️  Could not fetch maritime boundaries: {e}")

    # Layer 0: Landuse/Landcover (terre) - protège le fond bleu
    if landuse is not None and not landuse.empty:
        landuse_polys = landuse[landuse.geometry.type.isin(["Polygon", "MultiPolygon"])]
        if not landuse_polys.empty:
            try:
                landuse_polys = ox.projection.project_gdf(landuse_polys)
            except Exception:
                landuse_polys = landuse_polys.to_crs(g_proj.graph['crs'])
            # Dessiner la terre avec la couleur de fond (bg)
            landuse_polys.plot(ax=ax, facecolor=THEME['bg'], edgecolor='none', zorder=0)

    # Layer 0.4: Buildings (bâtiments)
    # Dessiner les bâtiments avec une couleur légèrement plus claire que le fond
    if buildings is not None and not buildings.empty:
        building_polys = buildings[buildings.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        if not building_polys.empty:
            try:
                building_polys = ox.projection.project_gdf(building_polys)
            except Exception:
                building_polys = building_polys.to_crs(g_proj.graph['crs'])

            buildings_color = THEME.get('buildings', THEME['bg'])
            building_polys.plot(ax=ax, facecolor=buildings_color, edgecolor='none', zorder=0.4)
            print(f"🏢 Rendered {len(building_polys)} buildings")

    # Layer 1: Water (mer, océan, rivières, lacs) - même couleur theme['water']
    if water_features is not None and not water_features.empty:
        # Retain only polygonal geometries
        water_polys = water_features[water_features.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        print(f"🔍 DEBUG: {len(water_polys)} water polygons before filtering")
        print(f"🔍 DEBUG: Columns available: {water_polys.columns.tolist()}")
        if not water_polys.empty:
            # Show some examples of what we have
            for col in ["place", "water", "natural"]:
                if col in water_polys.columns:
                    unique_vals = water_polys[col].dropna().unique()[:10]
                    print(f"🔍 DEBUG: {col} values: {unique_vals.tolist()}")

            # Filter out any large sea/ocean/bay polygons that might have slipped
            # through.  This guards against tag inconsistencies where a
            # multipolygon may still carry an undesired water type.
            for col in ["place", "water", "natural"]:
                if col in water_polys.columns:
                    water_polys = water_polys[~water_polys[col].isin([
                        "sea", "ocean", "bay", "strait"
                    ])]
            print(f"🔍 DEBUG: {len(water_polys)} water polygons after filtering")
            if not water_polys.empty:
                try:
                    water_polys = ox.projection.project_gdf(water_polys)
                except Exception:
                    water_polys = water_polys.to_crs(g_proj.graph['crs'])
                water_polys.plot(ax=ax, facecolor=THEME['water'], edgecolor='none', zorder=0.5)

    if parks is not None and not parks.empty:
        # Filter to only polygon/multipolygon geometries to avoid point features showing as dots
        parks_polys = parks[parks.geometry.type.isin(["Polygon", "MultiPolygon"])]
        if not parks_polys.empty:
            # Project park features in the same CRS as the graph
            try:
                parks_polys = ox.projection.project_gdf(parks_polys)
            except Exception:
                parks_polys = parks_polys.to_crs(g_proj.graph['crs'])
            parks_polys.plot(ax=ax, facecolor=THEME['parks'], edgecolor='none', zorder=0.8)
    # Layer 2: Roads with hierarchy coloring
    print("Applying road hierarchy colors...")
    edge_colors = get_edge_colors_by_type(g_proj)
    edge_widths = get_edge_widths_by_type(g_proj)

    # Determine cropping limits to maintain the poster aspect ratio
    crop_xlim, crop_ylim = get_crop_limits(g_proj, point, fig, compensated_dist)

    # Plot the projected graph and then apply the cropped limits
    ox.plot_graph(
        g_proj, ax=ax, bgcolor=THEME['bg'],
        node_size=0,
        edge_color=edge_colors,
        edge_linewidth=edge_widths,
        show=False,
        close=False,
    )
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(crop_xlim)
    ax.set_ylim(crop_ylim)

    # Layer 3.5: Railways (voies ferrées)
    # Dessiner les voies ferrées avec une ligne plus épaisse que les routes
    if railways is not None and not railways.empty:
        railway_lines = railways[railways.geometry.type.isin(["LineString", "MultiLineString"])].copy()
        if not railway_lines.empty:
            try:
                railway_lines = ox.projection.project_gdf(railway_lines)
            except Exception:
                railway_lines = railway_lines.to_crs(g_proj.graph['crs'])

            # Utiliser la même couleur que les routes primaires, mais plus épais
            railway_color = THEME.get('road_primary', THEME['text'])
            railway_lines.plot(
                ax=ax,
                color=railway_color,
                linewidth=1.8,  # Plus épais que les routes
                zorder=3.5,  # Au-dessus des routes
            )
            print(f"🚂 Rendered {len(railway_lines)} railway lines")

    # Layer 3: Gradients (Top and Bottom)
    create_gradient_fade(ax, THEME['gradient_color'], location='bottom', zorder=10, height=gradient_height)
    create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10, height=gradient_height)

    # Calculate scale factor based on smaller dimension (reference 12 inches)
    # This ensures text scales properly for both portrait and landscape orientations
    scale_factor = min(height, width) / 12.0

    # Base font sizes (at 12 inches width)
    base_main = 60
    base_sub = 22
    base_coords = 14
    base_attr = 8

    # 4. Typography - use custom fonts if provided, otherwise use default FONTS
    active_fonts = fonts or FONTS
    if active_fonts:
        # font_main is calculated dynamically later based on length
        font_sub = FontProperties(
            fname=active_fonts["light"], size=base_sub * scale_factor
        )
        font_coords = FontProperties(
            fname=active_fonts["regular"], size=base_coords * scale_factor
        )
        font_attr = FontProperties(
            fname=active_fonts["light"], size=base_attr * scale_factor
        )
    else:
        # Fallback to system fonts
        font_sub = FontProperties(
            family="monospace", weight="normal", size=base_sub * scale_factor
        )
        font_coords = FontProperties(
            family="monospace", size=base_coords * scale_factor
        )
        font_attr = FontProperties(family="monospace", size=base_attr * scale_factor)

    # Format city name based on script type
    # Latin scripts: apply uppercase and letter spacing for aesthetic
    # Non-Latin scripts (CJK, Thai, Arabic, etc.): no spacing, preserve case structure
    if is_latin_script(display_city):
        # Latin script: uppercase with letter spacing (e.g., "P  A  R  I  S")
        spaced_city = "  ".join(list(display_city.upper()))
    else:
        # Non-Latin script: no spacing, no forced uppercase
        # For scripts like Arabic, Thai, Japanese, etc.
        spaced_city = display_city

    # Dynamically adjust font size based on city name length to prevent truncation
    # We use the already scaled "main" font size as the starting point.
    base_adjusted_main = base_main * scale_factor
    city_char_count = len(display_city)

    # Heuristic: If length is > 10, start reducing.
    if city_char_count > 10:
        length_factor = 10 / city_char_count
        adjusted_font_size = max(base_adjusted_main * length_factor, 10 * scale_factor)
    else:
        adjusted_font_size = base_adjusted_main

    if active_fonts:
        font_main_adjusted = FontProperties(
            fname=active_fonts["bold"], size=adjusted_font_size
        )
    else:
        font_main_adjusted = FontProperties(
            family="monospace", weight="bold", size=adjusted_font_size
        )

    # --- BOTTOM TEXT ---
    ax.text(
        0.5,
        0.14,
        spaced_city,
        transform=ax.transAxes,
        color=THEME["text"],
        ha="center",
        fontproperties=font_main_adjusted,
        zorder=11,
    )

    ax.text(
        0.5,
        0.10,
        display_country.upper(),
        transform=ax.transAxes,
        color=THEME["text"],
        ha="center",
        fontproperties=font_sub,
        zorder=11,
    )

    lat, lon = point
    coords = (
        f"{lat:.4f}° N / {lon:.4f}° E"
        if lat >= 0
        else f"{abs(lat):.4f}° S / {lon:.4f}° E"
    )
    if lon < 0:
        coords = coords.replace("E", "W")

    ax.text(
        0.5,
        0.07,
        coords,
        transform=ax.transAxes,
        color=THEME["text"],
        alpha=0.7,
        ha="center",
        fontproperties=font_coords,
        zorder=11,
    )

    ax.plot(
        [0.4, 0.6],
        [0.125, 0.125],
        transform=ax.transAxes,
        color=THEME["text"],
        linewidth=1 * scale_factor,
        zorder=11,
    )

    # --- ATTRIBUTION (bottom right) ---
    if FONTS:
        font_attr = FontProperties(fname=FONTS["light"], size=8)
    else:
        font_attr = FontProperties(family="monospace", size=8)

    ax.text(
        0.98,
        0.02,
        "© OpenStreetMap contributors",
        transform=ax.transAxes,
        color=THEME["text"],
        alpha=0.5,
        ha="right",
        va="bottom",
        fontproperties=font_attr,
        zorder=11,
    )

    # 5. Save
    print(f"Saving to {output_file}...")

    fmt = output_format.lower()
    save_kwargs = dict(
        facecolor=THEME["bg"],
        bbox_inches="tight",
        pad_inches=0.05,
    )

    # DPI matters mainly for raster formats
    if fmt == "png":
        save_kwargs["dpi"] = 300

    plt.savefig(output_file, format=fmt, **save_kwargs)

    plt.close()
    print(f"✓ Done! Poster saved as {output_file}")


def print_examples():
    """Print usage examples."""
    print("""
City Map Poster Generator
=========================

Usage:
  python create_map_poster.py --city <city> --country <country> [options]

Examples:
  # Iconic grid patterns
  python create_map_poster.py -c "New York" -C "USA" -t noir -d 12000           # Manhattan grid
  python create_map_poster.py -c "Barcelona" -C "Spain" -t warm_beige -d 8000   # Eixample district grid

  # Waterfront & canals
  python create_map_poster.py -c "Venice" -C "Italy" -t blueprint -d 4000       # Canal network
  python create_map_poster.py -c "Amsterdam" -C "Netherlands" -t ocean -d 6000  # Concentric canals
  python create_map_poster.py -c "Dubai" -C "UAE" -t midnight_blue -d 15000     # Palm & coastline

  # Radial patterns
  python create_map_poster.py -c "Paris" -C "France" -t pastel_dream -d 10000   # Haussmann boulevards
  python create_map_poster.py -c "Moscow" -C "Russia" -t noir -d 12000          # Ring roads

  # Organic old cities
  python create_map_poster.py -c "Tokyo" -C "Japan" -t japanese_ink -d 15000    # Dense organic streets
  python create_map_poster.py -c "Marrakech" -C "Morocco" -t terracotta -d 5000 # Medina maze
  python create_map_poster.py -c "Rome" -C "Italy" -t warm_beige -d 8000        # Ancient street layout

  # Coastal cities
  python create_map_poster.py -c "San Francisco" -C "USA" -t sunset -d 10000    # Peninsula grid
  python create_map_poster.py -c "Sydney" -C "Australia" -t ocean -d 12000      # Harbor city
  python create_map_poster.py -c "Mumbai" -C "India" -t contrast_zones -d 18000 # Coastal peninsula

  # River cities
  python create_map_poster.py -c "London" -C "UK" -t noir -d 15000              # Thames curves
  python create_map_poster.py -c "Budapest" -C "Hungary" -t copper_patina -d 8000  # Danube split

  # List themes
  python create_map_poster.py --list-themes

Options:
  --city, -c        City name (required)
  --country, -C     Country name (required)
  --country-label   Override country text displayed on poster
  --theme, -t       Theme name (default: terracotta)
  --all-themes      Generate posters for all themes
  --distance, -d    Map radius in meters (default: 18000)
  --list-themes     List all available themes

Distance guide:
  4000-6000m   Small/dense cities (Venice, Amsterdam old center)
  8000-12000m  Medium cities, focused downtown (Paris, Barcelona)
  15000-20000m Large metros, full city view (Tokyo, Mumbai)

Available themes can be found in the 'themes/' directory.
Generated posters are saved to 'posters/' directory.
""")


def list_themes():
    """List all available themes with descriptions."""
    available_themes = get_available_themes()
    if not available_themes:
        print("No themes found in 'themes/' directory.")
        return

    print("\nAvailable Themes:")
    print("-" * 60)
    for theme_name in available_themes:
        theme_path = os.path.join(THEMES_DIR, f"{theme_name}.json")
        try:
            with open(theme_path, "r", encoding=FILE_ENCODING) as f:
                theme_data = json.load(f)
                display_name = theme_data.get('name', theme_name)
                description = theme_data.get('description', '')
        except (OSError, json.JSONDecodeError):
            display_name = theme_name
            description = ""
        print(f"  {theme_name}")
        print(f"    {display_name}")
        if description:
            print(f"    {description}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate beautiful map posters for any city",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_map_poster.py --city "New York" --country "USA"
  python create_map_poster.py --city "New York" --country "USA" -l 40.776676 -73.971321 --theme neon_cyberpunk
  python create_map_poster.py --city Tokyo --country Japan --theme midnight_blue
  python create_map_poster.py --city Paris --country France --theme noir --distance 15000
  python create_map_poster.py --list-themes
        """,
    )

    parser.add_argument("--city", "-c", type=str, help="City name")
    parser.add_argument("--country", "-C", type=str, help="Country name")
    parser.add_argument(
        "--latitude",
        "-lat",
        dest="latitude",
        type=str,
        help="Override latitude center point",
    )
    parser.add_argument(
        "--longitude",
        "-long",
        dest="longitude",
        type=str,
        help="Override longitude center point",
    )
    parser.add_argument(
        "--country-label",
        dest="country_label",
        type=str,
        help="Override country text displayed on poster",
    )
    parser.add_argument(
        "--theme",
        "-t",
        type=str,
        default="terracotta",
        help="Theme name (default: terracotta)",
    )
    parser.add_argument(
        "--all-themes",
        "--All-themes",
        dest="all_themes",
        action="store_true",
        help="Generate posters for all themes",
    )
    parser.add_argument(
        "--distance",
        "-d",
        type=int,
        default=18000,
        help="Map radius in meters (default: 18000)",
    )
    parser.add_argument(
        "--width",
        "-W",
        type=float,
        default=12,
        help="Image width in inches (default: 12, max: 20 )",
    )
    parser.add_argument(
        "--height",
        "-H",
        type=float,
        default=16,
        help="Image height in inches (default: 16, max: 20)",
    )
    parser.add_argument(
        "--list-themes", action="store_true", help="List all available themes"
    )
    parser.add_argument(
        "--display-city",
        "-dc",
        type=str,
        help="Custom display name for city (for i18n support)",
    )
    parser.add_argument(
        "--display-country",
        "-dC",
        type=str,
        help="Custom display name for country (for i18n support)",
    )
    parser.add_argument(
        "--font-family",
        type=str,
        help='Google Fonts family name (e.g., "Noto Sans JP", "Open Sans"). If not specified, uses local Roboto fonts.',
    )
    parser.add_argument(
        "--format",
        "-f",
        default="png",
        choices=["png", "svg", "pdf"],
        help="Output format for the poster (default: png)",
    )

    args = parser.parse_args()

    # If no arguments provided, show examples
    if len(sys.argv) == 1:
        print_examples()
        sys.exit(0)

    # List themes if requested
    if args.list_themes:
        list_themes()
        sys.exit(0)

    # Validate required arguments
    if not args.city or not args.country:
        print("Error: --city and --country are required.\n")
        print_examples()
        sys.exit(1)

    # Enforce maximum dimensions
    if args.width > 20:
        print(
            f"⚠ Width {args.width} exceeds the maximum allowed limit of 20. It's enforced as max limit 20."
        )
        args.width = 20.0
    if args.height > 20:
        print(
            f"⚠ Height {args.height} exceeds the maximum allowed limit of 20. It's enforced as max limit 20."
        )
        args.height = 20.0

    available_themes = get_available_themes()
    if not available_themes:
        print("No themes found in 'themes/' directory.")
        sys.exit(1)

    if args.all_themes:
        themes_to_generate = available_themes
    else:
        if args.theme not in available_themes:
            print(f"Error: Theme '{args.theme}' not found.")
            print(f"Available themes: {', '.join(available_themes)}")
            sys.exit(1)
        themes_to_generate = [args.theme]

    print("=" * 50)
    print("City Map Poster Generator")
    print("=" * 50)

    # Load custom fonts if specified
    custom_fonts = None
    if args.font_family:
        custom_fonts = load_fonts(args.font_family)
        if not custom_fonts:
            print(f"⚠ Failed to load '{args.font_family}', falling back to Roboto")

    # Get coordinates and generate poster
    try:
        if args.latitude and args.longitude:
            lat = parse(args.latitude)
            lon = parse(args.longitude)
            coords = [lat, lon]
            print(f"✓ Coordinates: {', '.join([str(i) for i in coords])}")
        else:
            coords = get_coordinates(args.city, args.country)

        for theme_name in themes_to_generate:
            THEME = load_theme(theme_name)
            output_file = generate_output_filename(args.city, theme_name, args.format, args.distance)
            create_poster(
                args.city,
                args.country,
                coords,
                args.distance,
                output_file,
                args.format,
                args.width,
                args.height,
                country_label=args.country_label,
                display_city=args.display_city,
                display_country=args.display_country,
                fonts=custom_fonts,
            )

        print("\n" + "=" * 50)
        print("✓ Poster generation complete!")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
