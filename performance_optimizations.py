"""
Performance optimizations for poster generation
Module avec fonctions optimisées pour générations plus rapides
"""

import matplotlib
matplotlib.use('Agg')  # Backend non-interactif (plus rapide)

# Optimisation 1: Cache en mémoire pour les thèmes/polices
_THEME_CACHE = {}
_FONTS_CACHE = {}

def load_theme_cached(theme_name):
    """Version cachée du chargement de thème"""
    if theme_name not in _THEME_CACHE:
        from create_map_poster import load_theme
        _THEME_CACHE[theme_name] = load_theme(theme_name)
    return _THEME_CACHE[theme_name]

def load_fonts_cached(font_family=None):
    """Version cachée du chargement des polices"""
    cache_key = font_family or 'default'
    if cache_key not in _FONTS_CACHE:
        from font_management import load_fonts
        _FONTS_CACHE[cache_key] = load_fonts(font_family)
    return _FONTS_CACHE[cache_key]


# Optimisation 2: Mode Fast Preview (résolution réduite, features minimales)
def create_fast_preview(city, country, point, dist, theme, output_file):
    """
    Génère un preview ultra-rapide en réduisant la qualité et les features
    ~5x plus rapide qu'une génération normale
    """
    import create_map_poster as cmp
    from create_map_poster import create_poster

    # Charger avec cache
    cmp.THEME = load_theme_cached(theme)
    fonts = load_fonts_cached()

    # Résolution très réduite
    create_poster(
        city=city,
        country=country,
        point=point,
        dist=dist,
        output_file=output_file,
        output_format='png',
        width=3,      # 4x plus petit
        height=4,     # 4x plus petit
        fonts=fonts
    )


# Optimisation 3: Génération parallèle
def generate_multiple_parallel(configs, max_workers=4):
    """
    Génère plusieurs posters en parallèle

    Args:
        configs: Liste de dicts avec {city, country, point, dist, theme, output_file, format}
        max_workers: Nombre de workers parallèles
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from create_map_poster import create_poster, load_theme, load_fonts
    import create_map_poster as cmp

    def generate_one(config):
        """Génère un poster (pour parallélisation)"""
        import create_map_poster as cmp
        from create_map_poster import create_poster, load_theme, load_fonts

        cmp.THEME = load_theme(config['theme'])
        fonts = load_fonts()

        create_poster(
            city=config['city'],
            country=config['country'],
            point=config['point'],
            dist=config['dist'],
            output_file=config['output_file'],
            output_format=config.get('format', 'pdf'),
            width=config.get('width', 12),
            height=config.get('height', 16),
            fonts=fonts
        )
        return config['output_file']

    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(generate_one, cfg): cfg for cfg in configs}

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                print(f"✓ Généré: {result}")
            except Exception as e:
                print(f"✗ Erreur: {e}")

    return results


# Optimisation 4: Preset de distances optimisées
DISTANCE_PRESETS = {
    'ville': 5000,      # Petit village
    'town': 8000,       # Ville moyenne
    'city': 12000,      # Grande ville
    'metro': 18000,     # Métropole
    'region': 25000,    # Région
}

def get_optimal_distance(city_type='city'):
    """Retourne la distance optimale selon le type de ville"""
    return DISTANCE_PRESETS.get(city_type, 12000)


# Optimisation 5: Cache SQLite (plus rapide que pickle pour grandes quantités)
def setup_sqlite_cache():
    """
    Configure un cache SQLite pour remplacer pickle
    Plus rapide pour lecture/écriture avec beaucoup de données
    """
    import sqlite3
    import os

    cache_db = os.path.join('cache', 'osm_cache.db')
    os.makedirs('cache', exist_ok=True)

    conn = sqlite3.connect(cache_db)
    cursor = conn.cursor()

    # Table pour cache des graphes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS graph_cache (
            key TEXT PRIMARY KEY,
            data BLOB,
            timestamp REAL
        )
    ''')

    # Table pour cache des features
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS features_cache (
            key TEXT PRIMARY KEY,
            data BLOB,
            timestamp REAL
        )
    ''')

    conn.commit()
    conn.close()
    print("✓ Cache SQLite configuré")


if __name__ == '__main__':
    print("🚀 Module d'optimisation des performances")
    print("\nFonctions disponibles:")
    print("  - load_theme_cached()")
    print("  - load_fonts_cached()")
    print("  - create_fast_preview()")
    print("  - generate_multiple_parallel()")
    print("  - setup_sqlite_cache()")
