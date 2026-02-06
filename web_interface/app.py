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
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

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

# Flag pour annuler la génération en cours
generation_cancelled = False

# Presets de formats
FORMAT_PRESETS = {
    'A': {'width': 11.7, 'height': 16.5, 'name': 'Format A (PDF vectoriel)'},
    'square': {'width': 12, 'height': 12, 'name': 'Carré 12" × 12"'},
    'ultrawide': {'width': 11.47, 'height': 4.8, 'name': 'Ultrawide 21:9'},
    'custom': {'width': 12, 'height': 16, 'name': 'Personnalisé'},
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


def generate_single_theme(theme, city, country, lat, lng, distance, output_format,
                          width, height, country_label, gradient_height, output_dir):
    """
    Fonction worker pour générer un seul thème (appelée en parallèle)
    """
    try:
        # Charger le thème et les fonts avec cache
        cmp.THEME = load_theme_cached(theme)
        fonts = load_fonts_cached()

        # Nom de fichier
        city_slug = city.lower().replace(' ', '_').replace(',', '')
        timestamp = time.strftime('%Y%m%d_%H%M%S_%f')  # Ajout microsecondes pour unicité
        filename = f"{city_slug}_{theme}_{distance}m_{timestamp}.{output_format}"
        output_path = output_dir / filename

        print(f"  🎨 {theme.upper()} - Début génération...")

        # Générer
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
            fonts=fonts,
            gradient_height=gradient_height
        )

        print(f"  ✓ {theme.upper()} - Terminé")

        return {
            'success': True,
            'theme': theme,
            'filename': filename,
            'path': str(output_path)
        }
    except Exception as e:
        print(f"  ❌ {theme.upper()} - Erreur: {e}")
        return {
            'success': False,
            'theme': theme,
            'error': str(e)
        }


@app.route('/api/generate', methods=['POST'])
def generate_poster():
    """Génère un ou plusieurs posters selon les paramètres"""
    import json as json_module
    data = request.json

    print("\n" + "="*60)
    print("🚀 GÉNÉRATION LANCÉE")
    print("="*60)
    print("📥 [BACKEND] Données reçues:")
    print(json_module.dumps(data, indent=2, ensure_ascii=False))
    print("="*60)

    try:
        # Paramètres de base
        city = data.get('city')
        country = data.get('country')
        lat = float(data.get('lat'))
        lng = float(data.get('lng'))

        print(f"📍 [BACKEND] Localisation: {city}, {country}")
        print(f"🗺️ [BACKEND] Coordonnées: {lat:.6f}, {lng:.6f}")

        # Distance calculée depuis le cadre (WYSIWYG)
        distance = data.get('distance', 12000)
        print(f"📏 [BACKEND] Distance reçue du frontend: {distance}m")

        # Format et orientation
        format_preset = data.get('format_preset', 'A')
        orientation = data.get('orientation', 'portrait')

        preset = FORMAT_PRESETS.get(format_preset, FORMAT_PRESETS['A'])
        width = preset['width']
        height = preset['height']

        print(f"📐 [BACKEND] Format: {format_preset} ({width}×{height} inches)")
        print(f"🔄 [BACKEND] Orientation: {orientation}")

        # Inverser si paysage
        if orientation == 'landscape':
            width, height = height, width
            print(f"📐 [BACKEND] Après inversion paysage: {width}×{height} inches")

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
        gradient_height = float(data.get('gradient_height', 0.25))  # Default 25%

        # Réinitialiser le flag d'annulation au début de chaque génération
        global generation_cancelled
        generation_cancelled = False

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

        # Déterminer le nombre de workers (max 6 cores utilisables)
        num_workers = min(6, multiprocessing.cpu_count(), total_themes)
        print(f"⚡ Parallélisation: {num_workers} workers")
        print("")

        # Génération PARALLÈLE avec ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Soumettre toutes les tâches
            future_to_theme = {
                executor.submit(
                    generate_single_theme,
                    theme, city, country, lat, lng, distance, output_format,
                    width, height, country_label, gradient_height, app.config['OUTPUT_DIR']
                ): theme
                for theme in themes
            }

            # Traiter les résultats au fur et à mesure
            completed = 0
            for future in as_completed(future_to_theme):
                # Vérifier si l'utilisateur a annulé
                if generation_cancelled:
                    print(f"\n🛑 Génération annulée après {completed}/{total_themes} thème(s)")
                    # Annuler les tâches restantes
                    for f in future_to_theme:
                        f.cancel()
                    executor.shutdown(wait=False, cancel_futures=True)
                    return jsonify({
                        'success': False,
                        'cancelled': True,
                        'files': generated_files,
                        'message': f'Génération annulée. {len(generated_files)} poster(s) généré(s) avant l\'annulation.'
                    })

                theme = future_to_theme[future]
                try:
                    result = future.result()
                    completed += 1

                    if result['success']:
                        generated_files.append({
                            'theme': result['theme'],
                            'filename': result['filename'],
                            'path': result['path']
                        })
                        elapsed = time.time() - start_time
                        avg_time = elapsed / completed if completed > 0 else 0
                        remaining = avg_time * (total_themes - completed)
                        print(f"  [{completed}/{total_themes}] ✓ {theme} OK - Reste: ~{int(remaining)}s")
                    else:
                        print(f"  [{completed}/{total_themes}] ❌ {theme} ERREUR: {result.get('error', 'Unknown')}")

                except Exception as e:
                    completed += 1
                    print(f"  [{completed}/{total_themes}] ❌ {theme} EXCEPTION: {e}")

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


@app.route('/api/cancel', methods=['POST'])
def cancel_generation():
    """Annule la génération en cours"""
    global generation_cancelled
    generation_cancelled = True
    print("\n🛑 [BACKEND] Annulation demandée par l'utilisateur")
    return jsonify({'success': True, 'message': 'Génération annulée'})


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
    print("  • Presets de formats (A, Square, Ultrawide, Custom)")
    print("  • Orientation Portrait/Paysage")
    print("  • Format de sortie (PDF, PNG, SVG)")
    print("  • Configuration DPI")
    print()
    print("=" * 60)
    print()

    app.run(debug=True, port=5000)
