#!/usr/bin/env python3
"""
Benchmark de génération de poster pour identifier les goulots d'étranglement
"""
import time
import sys
sys.path.insert(0, '.')

def benchmark_generation():
    print("🔍 Benchmark de génération de poster\n")
    
    from create_map_poster import (
        get_coordinates, load_theme, load_fonts,
        create_poster
    )
    import create_map_poster as cmp
    
    city = "Lauris"
    country = "France"
    theme = "terracotta"
    distance = 12000
    
    # 1. Géocodage
    start = time.time()
    coords = get_coordinates(city, country)
    geocoding_time = time.time() - start
    print(f"1. Géocodage: {geocoding_time:.2f}s")
    
    # 2. Chargement du thème
    start = time.time()
    cmp.THEME = load_theme(theme)
    theme_time = time.time() - start
    print(f"2. Chargement thème: {theme_time:.2f}s")
    
    # 3. Chargement des polices
    start = time.time()
    fonts = load_fonts()
    fonts_time = time.time() - start
    print(f"3. Chargement polices: {fonts_time:.2f}s")
    
    # 4. Génération complète
    start = time.time()
    create_poster(
        city=city,
        country=country,
        point=coords,
        dist=distance,
        output_file="test_benchmark.png",
        output_format="png",
        width=12,
        height=16,
        fonts=fonts
    )
    generation_time = time.time() - start
    print(f"4. Génération poster: {generation_time:.2f}s")
    
    total = geocoding_time + theme_time + fonts_time + generation_time
    print(f"\n⏱️  TOTAL: {total:.2f}s")
    
    # Breakdown
    print(f"\n📊 Répartition:")
    print(f"   - Géocodage: {geocoding_time/total*100:.1f}%")
    print(f"   - Génération: {generation_time/total*100:.1f}%")
    print(f"   - Autres: {(theme_time+fonts_time)/total*100:.1f}%")

if __name__ == '__main__':
    benchmark_generation()
