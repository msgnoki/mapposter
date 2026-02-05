# Backend - Spécifications Techniques

## 🏗️ Architecture

### Stack Technique
- **Framework**: Flask 3.x
- **Python**: 3.10+
- **Géospatial**: OSMnx, GeoPandas, Shapely
- **Rendu**: Matplotlib
- **Geocoding**: Geopy (Nominatim)

### Structure du Projet
```
maptoposter/
├── create_map_poster.py        # Module principal de génération
├── performance_optimizations.py # Cache et optimisations
├── font_management.py           # Gestion des polices
├── web_interface/
│   ├── app.py                  # Application Flask
│   ├── templates/
│   │   └── index.html          # Interface web
│   └── static/                 # Assets statiques
├── themes/                     # Fichiers JSON des thèmes
├── fonts/                      # Polices Google Fonts
└── cache/                      # Cache OSM (pickle)
```

---

## 📡 API Flask

### Routes

#### `GET /`
Affiche l'interface web principale.

**Réponse**: HTML page avec carte interactive

**Données transmises au template**:
```python
{
    'themes': ['autumn', 'blueprint', ...],  # 17 thèmes disponibles
    'format_presets': {
        'A3': {'width': 11.7, 'height': 16.5, 'name': '...'},
        'A4': {...},
        ...
    }
}
```

---

#### `POST /api/geocode`
Reverse geocoding pour obtenir ville/pays depuis coordonnées.

**Request Body**:
```json
{
    "lat": 43.4255,
    "lng": 6.7694
}
```

**Response Success (200)**:
```json
{
    "success": true,
    "city": "Saint-Raphaël",
    "country": "France",
    "full_address": "Saint-Raphaël, Var, Provence-Alpes-Côte d'Azur..."
}
```

**Response Error (400/404)**:
```json
{
    "success": false,
    "error": "Location not found"
}
```

**Implémentation**:
```python
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="maptoposter_web")
location = geolocator.reverse(f"{lat}, {lng}", language='fr')
```

---

#### `POST /api/generate`
Génère un ou plusieurs posters.

**Request Body**:
```json
{
    "city": "Saint-Raphaël",
    "country": "France",
    "lat": 43.4255,
    "lng": 6.7694,
    "distance": 8523,
    "themes": ["terracotta", "ocean", "blueprint"],
    "format_preset": "A3",
    "orientation": "portrait",
    "output_format": "pdf",
    "dpi": 300,
    "country_label": "French Riviera"
}
```

**Response Success (200)**:
```json
{
    "success": true,
    "files": [
        {
            "theme": "terracotta",
            "filename": "saint-raphaël_terracotta_8523m_20260205_213045.pdf",
            "path": "/absolute/path/to/file.pdf"
        },
        ...
    ],
    "message": "3 poster(s) généré(s) avec succès!"
}
```

**Response Error (500)**:
```json
{
    "success": false,
    "error": "Error message",
    "traceback": "Full Python traceback..."
}
```

**Implémentation**:
- Utilise `load_theme_cached()` et `load_fonts_cached()` pour optimisation
- Génération séquentielle avec logs de progression
- Temps estimé: ~3-5s par poster (après cache OSM)

---

#### `GET /api/download/<filename>`
Télécharge un fichier généré.

**Response**: Fichier PDF/PNG/SVG en téléchargement

---

## 🗺️ Module de Génération (`create_map_poster.py`)

### Pipeline de Génération

```python
def create_poster(city, country, point, dist, output_file,
                  output_format, width, height, country_label, fonts):
    """
    Pipeline complet de génération de poster.

    Étapes:
    1. Fetch OSM data (routes, eau marine, eau continentale, parcs)
    2. Setup plot (matplotlib figure)
    3. Project to metric CRS
    4. Plot layers (ordre z-order)
    5. Add gradients
    6. Add typography
    7. Save to file
    """
```

### 1. Récupération des Données OSM

#### Street Network
```python
G = ox.graph_from_point(
    point,
    dist=compensated_dist,
    network_type='all',
    simplify=True
)
```
**Tags OSM récupérés**: Tous les `highway=*`

#### Marine Water (z-order: -1)
```python
tags = {
    "natural": ["bay", "strait"],
    "place": ["sea", "ocean"]
}
```
**Résultat**: GeoDataFrame de polygones (baies, détroits, mers si disponibles)

#### Inland Water (z-order: 2)
```python
tags = {
    "natural": "water",      # Lacs, étangs
    "waterway": "riverbank"  # Rivières
}
```

#### Parks (z-order: 0.8)
```python
tags = {
    "leisure": "park",
    "landuse": "grass"
}
```

### 2. Système de Cache

**Format**: Pickle (`.pkl`)

**Clés de cache**:
```python
cache_key = f"{city}_{country}_{feature_type}_{dist}m"
# Exemple: "saint-raphaël_france_marine_water_8523m.pkl"
```

**Fonctions**:
```python
cache_get(key)  # Récupère depuis cache
cache_set(key, data)  # Sauvegarde dans cache
```

**Emplacement**: `cache/` directory

### 3. Projection CRS

Toutes les données sont projetées dans un CRS métrique (UTM) pour:
- Distances précises
- Aspect ratio correct
- Cropping précis

```python
g_proj = ox.project_graph(G)
crs = g_proj.graph['crs']  # Exemple: "EPSG:32632" (UTM zone 32N)
```

### 4. Hiérarchie Routière

**Classification OSM → Couleur**:

| OSM highway tag | Couleur theme | Largeur |
|-----------------|---------------|---------|
| `motorway`, `motorway_link` | `road_motorway` | 1.2 |
| `trunk`, `primary`, `*_link` | `road_primary` | 1.0 |
| `secondary`, `secondary_link` | `road_secondary` | 0.8 |
| `tertiary`, `tertiary_link` | `road_tertiary` | 0.6 |
| `residential`, `living_street` | `road_residential` | 0.4 |
| Autres | `road_default` | 0.4 |

**Implémentation**:
```python
def get_edge_colors_by_type(g):
    edge_colors = []
    for u, v, data in g.edges(data=True):
        highway = data.get('highway', 'unclassified')
        if isinstance(highway, list):
            highway = highway[0]

        if highway in ["motorway", "motorway_link"]:
            color = THEME["road_motorway"]
        elif highway in ["trunk", "primary", ...]:
            color = THEME["road_primary"]
        ...
```

### 5. Ordre des Layers (z-order)

```
Background: THEME['bg']
├─ -1: Marine water (baies, mers, détroits)
├─  0: Routes (ox.plot_graph)
├─ 0.8: Parks
├─  2: Inland water (rivières, lacs)
├─ 10: Gradients (top/bottom fade)
└─ 11: Typography (texte, lignes, attributions)
```

### 6. Crop Limits

**Objectif**: Maintenir l'aspect ratio du poster tout en garantissant la couverture complète du rayon demandé.

```python
def get_crop_limits(g_proj, center_lat_lon, fig, dist):
    """
    Calcule les limites de crop pour préserver l'aspect ratio.

    Logique:
    - Portrait: dist = rayon VERTICAL, crop horizontal
    - Landscape: dist = rayon HORIZONTAL, crop vertical
    """
    aspect = fig_width / fig_height
    half_x = dist
    half_y = dist

    if aspect > 1:  # Landscape
        half_y = half_x / aspect
    else:  # Portrait
        half_x = half_y * aspect

    return (
        (center_x - half_x, center_x + half_x),
        (center_y - half_y, center_y + half_y)
    )
```

### 7. Typography

**Polices chargées**:
```python
fonts = {
    'main': 'Montserrat-Bold',      # Nom de ville
    'sub': 'Montserrat-Regular',    # Nom de pays
    'coords': 'RobotoMono-Regular', # Coordonnées
    'attr': 'Roboto-Regular'        # Attribution
}
```

**Échelle dynamique**:
```python
scale_factor = min(width, height) / 12  # Référence: 12 inches
font_size_main = 72 * scale_factor
```

**Letter spacing** pour scripts latins:
```python
if is_latin_script(city):
    text_with_spacing = '  '.join(city.upper())
```

---

## ⚡ Optimisations

### Cache en Mémoire

```python
# performance_optimizations.py
_THEME_CACHE = {}
_FONTS_CACHE = {}

def load_theme_cached(theme_name):
    if theme_name not in _THEME_CACHE:
        _THEME_CACHE[theme_name] = load_theme(theme_name)
    return _THEME_CACHE[theme_name]
```

**Gain**: Évite de recharger les JSON et polices à chaque génération

### Génération Séquentielle Optimisée

```python
fonts = load_fonts_cached()  # Une seule fois

for theme in themes:
    cmp.THEME = load_theme_cached(theme)  # Cache
    create_poster(...)
```

**Performance**:
- Premier poster: ~80-90s (download OSM + génération)
- Posters suivants: ~3-5s (cache OSM utilisé)
- Moyenne pour 17 thèmes: ~8s par poster

---

## 🎨 Système de Thèmes

### Format JSON

```json
{
  "name": "Terracotta",
  "description": "Mediterranean warmth - burnt orange and clay tones on cream",
  "bg": "#F5EDE4",
  "text": "#8B4513",
  "gradient_color": "#F5EDE4",
  "water": "#A8C4C4",
  "parks": "#E8E0D0",
  "road_motorway": "#A0522D",
  "road_primary": "#B8653A",
  "road_secondary": "#C9865E",
  "road_tertiary": "#D4A574",
  "road_residential": "#E0C9A8",
  "road_default": "#E5D5BD"
}
```

### Chargement

```python
def load_theme(theme_name):
    with open(f"themes/{theme_name}.json") as f:
        return json.load(f)

# Variable globale utilisée par create_poster
THEME = load_theme("terracotta")
```

---

## 🔧 Configuration

### Variables d'Environnement

Aucune requise - tout configuré par défaut.

### Répertoires

```python
OUTPUT_DIR = Path('posters/')       # Posters générés
THEMES_DIR = "themes"               # Thèmes JSON
CACHE_DIR = "cache"                 # Cache OSM
FONTS_DIR = "fonts"                 # Google Fonts
```

### Presets de Formats

```python
FORMAT_PRESETS = {
    'A3': {'width': 11.7, 'height': 16.5},
    'A4': {'width': 8.3, 'height': 11.7},
    'A5': {'width': 5.8, 'height': 8.3},
    'ultrawide': {'width': 11.47, 'height': 4.8},  # 3440×1440 @ 300 DPI
    'square': {'width': 12, 'height': 12},
    'poster': {'width': 18, 'height': 24}
}
```

---

## 🐛 Gestion des Erreurs

### OSM Data Fetch Failures

```python
try:
    G = ox.graph_from_point(...)
except Exception as e:
    logger.error(f"Failed to fetch OSM data: {e}")
    raise RuntimeError("Failed to retrieve street network data.")
```

### Projection Errors

```python
try:
    water_polys = ox.projection.project_gdf(water_polys)
except Exception:
    # Fallback to manual CRS conversion
    water_polys = water_polys.to_crs(g_proj.graph['crs'])
```

### Font Loading

```python
if not font_path.exists():
    logger.warning(f"Font not found: {font_path}")
    # Matplotlib utilisera une police par défaut
```

---

## 📊 Logs et Monitoring

### Progression Console

```
🚀 GÉNÉRATION LANCÉE
📊 17 thème(s) à générer
📍 Ville: Saint-Raphaël (8523m)
📐 Format: 11.7×16.5 inches → PDF

[1/17] 🎨 AUTUMN...
Generating map for Saint-Raphaël, France...
Fetching map data: 100%|██████████| 4/4
✓ All data retrieved successfully!
Rendering map...
  ✓ autumn OK (3.2s) - Reste: ~51s

...

✅ TERMINÉ! 17 poster(s) en 145.2s
📊 Moyenne: 8.5s par poster
```

### Flask Debug Mode

```python
app.run(debug=True, port=5000)
```

Permet:
- Auto-reload on file changes
- Detailed error tracebacks
- Debugger PIN pour console Python

---

## 🔐 Sécurité

### Rate Limiting Geocoding

```python
time.sleep(1)  # Respect Nominatim usage policy
```

### Validation des Entrées

```python
distance = int(data.get('distance', 12000))
if distance < 500 or distance > 50000:
    raise ValueError("Distance must be between 500 and 50000 meters")
```

### Sanitization Filenames

```python
city_slug = city.lower().replace(' ', '_').replace(',', '')
```

---

## 📈 Performance Metrics

### Temps de Génération

| Étape | Temps (première fois) | Temps (avec cache) |
|-------|----------------------|-------------------|
| Geocoding | ~1s | ~0s |
| OSM Download | 15-30s | ~0s |
| Projection | ~2s | ~2s |
| Rendering | ~5s | ~5s |
| Save to file | ~1s | ~1s |
| **TOTAL** | **25-40s** | **~8s** |

### Mémoire

- Base: ~150 MB
- Par génération: +50 MB (libéré après)
- Cache OSM: ~10-50 MB par ville

---

## 🚀 Déploiement

### Production WSGI

```python
# wsgi.py
from web_interface.app import app

if __name__ == "__main__":
    app.run()
```

```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

### Docker (optionnel)

```dockerfile
FROM python:3.10-slim
RUN apt-get update && apt-get install -y \
    libgeos-dev \
    libproj-dev \
    libgdal-dev
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
WORKDIR /app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "wsgi:app"]
```
