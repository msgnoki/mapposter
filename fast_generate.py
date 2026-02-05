#!/usr/bin/env python3
"""
Script de génération rapide avec optimisations
Jusqu'à 5x plus rapide pour les previews
"""

import argparse
import time
from performance_optimizations import (
    create_fast_preview,
    generate_multiple_parallel,
    get_optimal_distance,
    load_theme_cached
)
from create_map_poster import get_coordinates


def main():
    parser = argparse.ArgumentParser(description='Génération rapide de posters')

    # Mode
    parser.add_argument('--mode', choices=['fast', 'normal', 'batch'],
                       default='fast', help='Mode de génération')

    # Paramètres de base
    parser.add_argument('-c', '--city', required=True, help='Nom de la ville')
    parser.add_argument('-C', '--country', required=True, help='Nom du pays')
    parser.add_argument('-t', '--theme', default='terracotta', help='Thème')
    parser.add_argument('-d', '--distance', type=int, help='Distance (auto si non spécifié)')
    parser.add_argument('--city-type', choices=['ville', 'town', 'city', 'metro', 'region'],
                       default='city', help='Type de ville (pour distance auto)')

    # Batch mode
    parser.add_argument('--all-themes', action='store_true',
                       help='Générer tous les thèmes')
    parser.add_argument('--workers', type=int, default=4,
                       help='Nombre de workers parallèles (batch mode)')

    args = parser.parse_args()

    # Géocodage
    print(f"🔍 Recherche de {args.city}, {args.country}...")
    coords = get_coordinates(args.city, args.country)
    print(f"✓ Coordonnées: {coords}")

    # Distance optimale
    distance = args.distance or get_optimal_distance(args.city_type)
    print(f"📏 Distance: {distance}m")

    if args.mode == 'fast':
        # Mode rapide - preview basse résolution
        print(f"\n⚡ Mode RAPIDE - Génération preview...")
        output = f"posters/{args.city.lower()}_fast_{args.theme}.png"

        start = time.time()
        create_fast_preview(
            city=args.city,
            country=args.country,
            point=coords,
            dist=distance,
            theme=args.theme,
            output_file=output
        )
        elapsed = time.time() - start

        print(f"✓ Généré en {elapsed:.2f}s: {output}")
        print(f"💡 Gain: ~5x plus rapide qu'une génération normale")

    elif args.mode == 'batch' or args.all_themes:
        # Mode batch - génération parallèle
        from create_map_poster import get_available_themes

        themes = get_available_themes() if args.all_themes else [args.theme]
        print(f"\n🔄 Mode BATCH - {len(themes)} posters en parallèle...")

        # Préparer les configs
        configs = []
        for theme in themes:
            config = {
                'city': args.city,
                'country': args.country,
                'point': coords,
                'dist': distance,
                'theme': theme,
                'output_file': f"posters/{args.city.lower()}_{theme}_{distance}m_fast.pdf",
                'format': 'pdf',
                'width': 11.7,
                'height': 16.5
            }
            configs.append(config)

        start = time.time()
        results = generate_multiple_parallel(configs, max_workers=args.workers)
        elapsed = time.time() - start

        print(f"\n✓ {len(results)} posters générés en {elapsed:.2f}s")
        print(f"   Moyenne: {elapsed/len(results):.2f}s par poster")
        print(f"💡 Gain parallèle: ~{args.workers}x plus rapide")

    else:
        # Mode normal - génération standard
        print(f"\n📄 Mode NORMAL - Génération standard...")
        import create_map_poster as cmp
        from create_map_poster import create_poster, load_fonts

        output = f"posters/{args.city.lower()}_{args.theme}_{distance}m.pdf"

        cmp.THEME = load_theme_cached(args.theme)
        fonts = load_fonts()

        start = time.time()
        create_poster(
            city=args.city,
            country=args.country,
            point=coords,
            dist=distance,
            output_file=output,
            output_format='pdf',
            width=11.7,
            height=16.5,
            fonts=fonts
        )
        elapsed = time.time() - start

        print(f"✓ Généré en {elapsed:.2f}s: {output}")


if __name__ == '__main__':
    print("=" * 60)
    print("⚡ GÉNÉRATEUR RAPIDE DE POSTERS")
    print("=" * 60 + "\n")
    main()
