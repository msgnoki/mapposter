# Problème de rendu des zones d'eau dans un générateur de poster cartographique

## Résumé du problème

Notre application génère des posters cartographiques à partir de données OpenStreetMap. Nous rencontrons un problème où **des zones terrestres intérieures (inland areas) apparaissent comme de l'eau** (couleur de fond bleue) alors qu'elles devraient être rendues comme de la terre.

### Comportement attendu
- Mer/océan : couleur bleue (background)
- Zones terrestres : couleur de fond terre (beige/crème selon le thème)
- Rivières/lacs : couleur eau (bleu clair)
- Parcs : couleur verte

### Comportement observé
- Mer/océan : ✅ correct (bleu)
- **Zones terrestres sans tag OSM spécifique : ❌ apparaissent en bleu (comme de l'eau)**
- Rivières/lacs : ✅ correct
- Parcs : ✅ correct

## Architecture et fichiers concernés

### Fichier principal : `create_map_poster.py`

**Fonction clé : `create_poster()`** (lignes ~480-650)

Cette fonction télécharge les données OSM par couches (layers) et les rend dans un ordre spécifique (z-order) :

```python
# Ordre de rendu actuel (4 étapes) :
with tqdm(total=4, desc="Fetching map data", ncols=100) as pbar:
    # 1. Streets
    pbar.set_description("Downloading street network")
    g_proj = fetch_graph(point, compensated_dist)

    # 2. Landmass (DÉSACTIVÉ - causait régression)
    # landmass = fetch_features(tags={"boundary": "land_area"})
    landmass = None

    # 3. Water features
    pbar.set_description("Downloading water features")
    water = fetch_features(
        tags={"natural": ["water", "bay", "strait"], "waterway": True}
    )

    # 4. Parks/green spaces
    pbar.set_description("Downloading parks/green spaces")
    parks = fetch_features(
        tags={"leisure": "park", "landuse": "grass"}
    )
```

**Z-order de rendu (lignes ~650-750)** :

```python
# Background (fond de carte)
ax.set_facecolor(THEME["bg"])  # Couleur terre de base

# -1. Sea layer (si activé)
if sea and not sea.empty:
    sea.plot(ax=ax, color=THEME["sea"], zorder=-1)

# -0.5. Landmass layer (DÉSACTIVÉ)
# if landmass and not landmass.empty:
#     landmass.plot(ax=ax, color=THEME["landmass"], zorder=-0.5)

# 0. Named landuse areas
if land_areas and not land_areas.empty:
    land_areas.plot(ax=ax, color=THEME["bg"], zorder=0)

# 0.5. Water features (rivers, lakes)
if water and not water.empty:
    water.plot(ax=ax, color=THEME["water"], zorder=0.5, linewidth=0.3)

# 0.8. Parks
if parks and not parks.empty:
    parks.plot(ax=ax, color=THEME["parks"], zorder=0.8)

# 1+. Roads (selon importance)
```

### Fichiers de thèmes : `themes/*.json`

Chaque thème définit les couleurs (17 thèmes disponibles) :

```json
{
  "name": "Ocean",
  "bg": "#f5f0e8",        // Couleur terre (background)
  "sea": "#1e3a5f",       // Couleur mer
  "water": "#4a90e2",     // Couleur rivières/lacs
  "landmass": "#e3dfd5",  // Couleur landmass (désactivée)
  "parks": "#a8d5a3",     // Couleur parcs
  // ...
}
```

## Ce que nous avons essayé

### ❌ Tentative 1 : Ajouter une couche `boundary=land_area`

**Objectif** : Identifier explicitement les zones terrestres pour les rendre avec la couleur terre.

**Implémentation** :
```python
# Fetch landmass
landmass = fetch_features(tags={"boundary": "land_area"})

# Render at z-order -0.5 (entre mer et objets nommés)
landmass.plot(ax=ax, color=THEME["landmass"], zorder=-0.5)
```

**Résultat** : ❌ **Régression majeure**
- La mer a disparu (couverte par la couche landmass)
- `boundary=land_area` couvre à la fois les zones terrestres ET maritimes

**Action** : Désactivée (voir commit ou ligne ~560 dans `create_map_poster.py`)

### 🤔 Piste envisagée : `boundary=maritime`

**Source** : [OSM Wiki - Tag:boundary=maritime](https://wiki.openstreetmap.org/wiki/Tag:boundary=maritime)

**Idée** : Utiliser `boundary=maritime` pour identifier explicitement les zones maritimes et les exclure de la couche landmass.

**Pas encore testé** : Nous ne savons pas comment combiner ces tags efficacement.

## Difficulté actuelle

### Le problème fondamental

1. **Background par défaut = couleur terre** (`THEME["bg"]`)
2. **Les zones sans tag OSM héritent du background**
3. **Si une zone intérieure n'a pas de tag `landuse`, `natural`, etc. → elle apparaît comme de l'eau**

### Question pour l'expert OSM

**Comment distinguer efficacement les zones terrestres des zones maritimes dans OSM pour le rendu cartographique ?**

Options envisagées :

**A. Utiliser `boundary=maritime` pour exclure la mer**
```python
# Fetch tout sauf maritime ?
landmass = fetch_features(tags={"boundary": "land_area"})
maritime = fetch_features(tags={"boundary": "maritime"})
# Comment exclure maritime de landmass dans GeoPandas ?
```

**B. Utiliser `natural=coastline` différemment**
```python
# Créer des polygones à partir des coastlines ?
coastline = fetch_features(tags={"natural": "coastline"})
# Comment convertir en polygones terre/mer ?
```

**C. Utiliser des requêtes Overpass plus sophistiquées**
- Combinaison de tags pour identifier uniquement les zones terrestres intérieures
- Exclusion explicite des zones maritimes

**D. Accepter la limitation**
- Considérer que les zones sans tag OSM peuvent légitimement apparaître comme "non définies"
- Encourager les utilisateurs à choisir des zones bien cartographiées

### Stack technique utilisé

- **Python 3.x**
- **OSMnx** : téléchargement et traitement des données OSM
- **GeoPandas** : manipulation des données géospatiales
- **Matplotlib** : rendu graphique
- **Shapely** : opérations géométriques

### Code de fetch actuel

```python
def fetch_features(point, dist, tags):
    """
    Télécharge les features OSM avec les tags spécifiés
    """
    try:
        gdf = ox.features_from_point(
            point,
            dist=dist,
            tags=tags
        )
        if not gdf.empty:
            gdf = gdf.to_crs(target_crs)
            return gdf[gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]
    except Exception:
        pass
    return gpd.GeoDataFrame()
```

## Questions spécifiques pour l'expert

1. **Quelle est la meilleure approche OSM pour distinguer terre vs mer dans un rendu cartographique ?**

2. **`boundary=land_area` couvre-t-il vraiment les zones maritimes ou avons-nous fait une erreur d'implémentation ?**

3. **Comment utiliser `boundary=maritime` en combinaison avec d'autres tags pour exclure la mer ?**

4. **Existe-t-il un tag OSM "par défaut" pour les zones terrestres non catégorisées (sans `landuse`, `natural`, etc.) ?**

5. **GeoPandas : comment faire une différence géométrique entre deux GeoDataFrames (landmass MINUS maritime) ?**

6. **Les zones intérieures non taguées : est-ce normal qu'elles n'aient pas de tag OSM, ou devrions-nous les traiter différemment ?**

## Exemples de cas problématiques

Zones observées comme "eau bleue" alors qu'elles sont terrestres :
- Zones agricoles sans tag `landuse=farmland`
- Zones résidentielles sans tag `landuse=residential`
- Terrains vagues sans tag spécifique
- Zones rurales non catégorisées

## Reproduction du problème

1. Cloner le repo
2. Installer les dépendances : `pip install -r requirements.txt`
3. Lancer : `python create_map_poster.py --city "Nom_Ville" --country "Pays" --theme ocean`
4. Observer les zones intérieures en bleu (couleur background au lieu de couleur terre)

## Liens utiles

- [OSM Wiki - Coastline](https://wiki.openstreetmap.org/wiki/Coastline)
- [OSM Wiki - Land use](https://wiki.openstreetmap.org/wiki/Land_use)
- [OSM Wiki - boundary=land_area](https://wiki.openstreetmap.org/wiki/Tag:boundary=land_area)
- [OSM Wiki - boundary=maritime](https://wiki.openstreetmap.org/wiki/Tag:boundary=maritime)

---

**Merci d'avance pour votre aide !** 🙏

Toute suggestion sur l'approche OSM correcte pour gérer ce cas d'usage serait grandement appréciée.
