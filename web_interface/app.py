#!/usr/bin/env python3
"""
Interface web locale pour génération de posters
Design épuré avec focus sur la carte et sélection de zone
"""

from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
from pathlib import Path
import os
import sys
import time

# Ajouter le répertoire parent au path pour importer create_map_poster
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Changer le répertoire de travail vers le parent pour accéder aux fichiers
os.chdir(parent_dir)

from create_map_poster import (
    get_coordinates,
    get_available_themes,
    create_poster
)
import create_map_poster as cmp

# Importer les fonctions optimisées
from performance_optimizations import (
    load_theme_cached,
    load_fonts_cached
)

app = Flask(__name__)
app.config['OUTPUT_DIR'] = Path(__file__).parent.parent / 'posters'

# Presets de formats
FORMAT_PRESETS = {
    'A3': {'width': 11.7, 'height': 16.5, 'name': 'A3 (11.7 × 16.5")'},
    'A4': {'width': 8.3, 'height': 11.7, 'name': 'A4 (8.3 × 11.7")'},
    'A5': {'width': 5.8, 'height': 8.3, 'name': 'A5 (5.8 × 8.3")'},
    'ultrawide': {'width': 11.47, 'height': 4.8, 'name': 'Ultrawide 21:9 (3440×1440)'},
    'square': {'width': 12, 'height': 12, 'name': 'Carré 12" × 12"'},
    'poster': {'width': 18, 'height': 24, 'name': 'Poster 18" × 24"'},
}


@app.route('/')
def index():
    """Page principale avec carte et interface"""
    themes = get_available_themes()
    print(f"DEBUG: Loaded {len(themes)} themes: {themes}")
    return render_template('index.html',
                         themes=themes,
                         format_presets=FORMAT_PRESETS)


@app.route('/api/geocode', methods=['POST'])
def reverse_geocode():
    """Reverse geocoding pour obtenir le nom du lieu"""
    from geopy.geocoders import Nominatim

    data = request.json
    lat = data.get('lat')
    lng = data.get('lng')

    try:
        geolocator = Nominatim(user_agent="maptoposter_web")
        location = geolocator.reverse(f"{lat}, {lng}", language='fr')

        if location:
            address = location.raw.get('address', {})

            # Extraire ville et pays
            city = (address.get('city') or
                   address.get('town') or
                   address.get('village') or
                   address.get('municipality') or
                   'Unknown')

            country = address.get('country', 'Unknown')

            return jsonify({
                'success': True,
                'city': city,
                'country': country,
                'full_address': location.address
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    return jsonify({'success': False, 'error': 'Location not found'}), 404


@app.route('/api/generate', methods=['POST'])
def generate_poster():
    """Génère un ou plusieurs posters selon les paramètres"""
    data = request.json

    print("\n" + "="*60)
    print("🚀 GÉNÉRATION LANCÉE")
    print("="*60)

    try:
        # Paramètres de base
        city = data.get('city')
        country = data.get('country')
        lat = float(data.get('lat'))
        lng = float(data.get('lng'))

        # Distance calculée depuis le cadre (WYSIWYG)
        distance = data.get('distance', 12000)

        # Format et orientation
        format_preset = data.get('format_preset', 'A3')
        orientation = data.get('orientation', 'portrait')

        preset = FORMAT_PRESETS.get(format_preset, FORMAT_PRESETS['A3'])
        width = preset['width']
        height = preset['height']

        # Inverser si paysage
        if orientation == 'landscape':
            width, height = height, width

        # Custom dimensions si spécifiées
        if data.get('custom_width'):
            width = float(data.get('custom_width'))
        if data.get('custom_height'):
            height = float(data.get('custom_height'))

        # Autres paramètres
        dpi = int(data.get('dpi', 300))
        output_format = data.get('output_format', 'pdf')
        themes = data.get('themes', ['terracotta'])
        country_label = data.get('country_label', country)

        # Générer les posters avec optimisation
        generated_files = []
        start_time = time.time()

        # Charger les fonts une seule fois (optimisation)
        print("⚡ Chargement des fonts (cache)...")
        fonts = load_fonts_cached()

        total_themes = len(themes)
        print(f"📊 {total_themes} thème(s) à générer")
        print(f"📍 Ville: {city} ({distance}m)")
        print(f"📐 Format: {width:.1f}×{height:.1f} inches → {output_format.upper()}")
        print("")

        for idx, theme in enumerate(themes, 1):
            theme_start = time.time()

            # Charger le thème avec cache (optimisation)
            cmp.THEME = load_theme_cached(theme)

            # Nom de fichier
            city_slug = city.lower().replace(' ', '_').replace(',', '')
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"{city_slug}_{theme}_{distance}m_{timestamp}.{output_format}"
            output_path = app.config['OUTPUT_DIR'] / filename

            print(f"[{idx}/{total_themes}] 🎨 {theme.upper()}...")

            # Générer
            # Note: DPI est géré automatiquement par matplotlib (300 DPI par défaut)
            create_poster(
                city=city,
                country=country,
                point=(lat, lng),
                dist=distance,
                output_file=str(output_path),
                output_format=output_format,
                width=width,
                height=height,
                country_label=country_label,
                fonts=fonts
            )

            theme_time = time.time() - theme_start
            elapsed = time.time() - start_time
            avg_time = elapsed / idx
            remaining = avg_time * (total_themes - idx)

            generated_files.append({
                'theme': theme,
                'filename': filename,
                'path': str(output_path)
            })

            print(f"  ✓ {theme} OK ({theme_time:.1f}s) - Reste: ~{int(remaining)}s")

        total_time = time.time() - start_time
        print("")
        print("="*60)
        print(f"✅ TERMINÉ! {total_themes} poster(s) en {total_time:.1f}s")
        print(f"📊 Moyenne: {total_time/total_themes:.1f}s par poster")
        print("="*60)

        return jsonify({
            'success': True,
            'files': generated_files,
            'message': f'{len(generated_files)} poster(s) généré(s) avec succès!'
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/download/<filename>')
def download_file(filename):
    """Télécharge un fichier généré"""
    file_path = app.config['OUTPUT_DIR'] / filename
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    print("=" * 60)
    print("🗺️  MAP POSTER GENERATOR - Interface Web Locale")
    print("=" * 60)
    print()
    print("🌐 Ouvrir dans le navigateur: http://localhost:5000")
    print()
    print("Fonctionnalités:")
    print("  • Sélection de zone avec cadre fixe")
    print("  • Choix des thèmes (multi-sélection)")
    print("  • Presets de formats (A3, A4, A5, Ultrawide...)")
    print("  • Orientation Portrait/Paysage")
    print("  • Format de sortie (PDF, PNG, SVG)")
    print("  • Configuration DPI")
    print()
    print("=" * 60)
    print()

    app.run(debug=True, port=5000)
