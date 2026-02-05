#!/bin/bash
# Génération optimisée des 17 fonds d'écran Lauris Ultrawide 3440×1440

echo "🖼️  Génération des fonds d'écran Lauris Ultrawide"
echo "Résolution: 3440×1440 (21:9)"
echo "Format: 11.47 × 4.8 inches @ 300 DPI"
echo "Thèmes: 17"
echo ""

source .venv/bin/activate

# Liste des 17 thèmes
themes=(
  "autumn"
  "blueprint"
  "contrast_zones"
  "copper_patina"
  "emerald"
  "forest"
  "gradient_roads"
  "japanese_ink"
  "midnight_blue"
  "monochrome_blue"
  "neon_cyberpunk"
  "noir"
  "ocean"
  "pastel_dream"
  "sunset"
  "terracotta"
  "warm_beige"
)

# Génération séquentielle pour garantir la qualité
for theme in "${themes[@]}"; do
  echo "Génération: $theme..."
  python create_map_poster.py \
    -c "Lauris" \
    -C "France" \
    --country-label "France" \
    -t "$theme" \
    -d 12000 \
    -W 11.47 \
    -H 4.8 \
    -f png
done

echo ""
echo "✅ Tous les fonds d'écran générés!"
echo "📁 Dossier: posters/lauris_*_12000m_*.png"
