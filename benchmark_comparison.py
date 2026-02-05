#!/usr/bin/env python3
"""
Benchmark comparatif: génération normale vs optimisée
"""

import time
import os
from create_map_poster import get_available_themes, get_coordinates

# Config pour fond d'écran ultrawide
CITY = "Lauris"
COUNTRY = "France"
WIDTH_INCHES = 3440 / 300  # 11.47 inches
HEIGHT_INCHES = 1440 / 300  # 4.8 inches
DISTANCE = 12000

def benchmark_normal():
    """Génération normale (séquentielle)"""
    print("\n" + "="*60)
    print("🐢 BENCHMARK NORMAL (séquentiel)")
    print("="*60)

    import create_map_poster as cmp
    from create_map_poster import create_poster, load_theme, load_fonts

    coords = get_coordinates(CITY, COUNTRY)
    themes = get_available_themes()

    print(f"Génération de {len(themes)} posters...")
    print(f"Résolution: {int(WIDTH_INCHES*300)}×{int(HEIGHT_INCHES*300)} px")
    print(f"Format: {WIDTH_INCHES:.2f}×{HEIGHT_INCHES:.2f} inches @ 300 DPI\n")

    start_total = time.time()
    times = []

    for i, theme in enumerate(themes, 1):
        print(f"[{i}/{len(themes)}] {theme}...", end=" ", flush=True)

        start = time.time()

        cmp.THEME = load_theme(theme)
        fonts = load_fonts()

        output = f"posters/bench_normal_{CITY.lower()}_{theme}_ultrawide.png"

        create_poster(
            city=CITY,
            country=COUNTRY,
            point=coords,
            dist=DISTANCE,
            output_file=output,
            output_format='png',
            width=WIDTH_INCHES,
            height=HEIGHT_INCHES,
            fonts=fonts
        )

        elapsed = time.time() - start
        times.append(elapsed)
        print(f"{elapsed:.2f}s")

    total = time.time() - start_total
    avg = sum(times) / len(times)

    print(f"\n{'='*60}")
    print(f"⏱️  TOTAL: {total:.2f}s")
    print(f"📊 Moyenne: {avg:.2f}s par poster")
    print(f"{'='*60}\n")

    return total, avg, times


def benchmark_optimized():
    """Génération optimisée (parallèle)"""
    print("\n" + "="*60)
    print("🚀 BENCHMARK OPTIMISÉ (parallèle, 4 workers)")
    print("="*60)

    from performance_optimizations import generate_multiple_parallel

    coords = get_coordinates(CITY, COUNTRY)
    themes = get_available_themes()

    print(f"Génération de {len(themes)} posters en parallèle...")
    print(f"Résolution: {int(WIDTH_INCHES*300)}×{int(HEIGHT_INCHES*300)} px")
    print(f"Format: {WIDTH_INCHES:.2f}×{HEIGHT_INCHES:.2f} inches @ 300 DPI")
    print(f"Workers: 4\n")

    # Préparer configs
    configs = []
    for theme in themes:
        config = {
            'city': CITY,
            'country': COUNTRY,
            'point': coords,
            'dist': DISTANCE,
            'theme': theme,
            'output_file': f"posters/bench_optimized_{CITY.lower()}_{theme}_ultrawide.png",
            'format': 'png',
            'width': WIDTH_INCHES,
            'height': HEIGHT_INCHES
        }
        configs.append(config)

    start_total = time.time()
    results = generate_multiple_parallel(configs, max_workers=4)
    total = time.time() - start_total

    avg = total / len(results)

    print(f"\n{'='*60}")
    print(f"⏱️  TOTAL: {total:.2f}s")
    print(f"📊 Moyenne: {avg:.2f}s par poster")
    print(f"{'='*60}\n")

    return total, avg


def main():
    print("🏁 BENCHMARK COMPARATIF - Génération de posters")
    print(f"Ville: {CITY}, {COUNTRY}")
    print(f"Format: Ultrawide 3440×1440 (21:9)")
    print(f"Thèmes: 17")

    # Benchmark normal
    total_normal, avg_normal, times_normal = benchmark_normal()

    # Benchmark optimisé
    total_optimized, avg_optimized = benchmark_optimized()

    # Comparaison
    print("\n" + "="*60)
    print("📈 RÉSULTATS COMPARATIFS")
    print("="*60)

    print(f"\n{'Méthode':<20} {'Total':<12} {'Moyenne/poster':<20}")
    print("-" * 60)
    print(f"{'Normal (séquentiel)':<20} {total_normal:>6.2f}s     {avg_normal:>6.2f}s")
    print(f"{'Optimisé (4 workers)':<20} {total_optimized:>6.2f}s     {avg_optimized:>6.2f}s")
    print("-" * 60)

    speedup = total_normal / total_optimized
    time_saved = total_normal - total_optimized

    print(f"\n🚀 Accélération: {speedup:.2f}×")
    print(f"⏱️  Temps gagné: {time_saved:.2f}s ({time_saved/60:.1f} minutes)")
    print(f"💡 Efficacité: {(speedup/4)*100:.1f}% (idéal: 100% = 4×)")

    print("\n" + "="*60)
    print("✅ Benchmark terminé!")
    print("="*60)


if __name__ == '__main__':
    main()
