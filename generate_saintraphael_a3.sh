#!/bin/bash
# Génération des 17 fonds d'écran Saint-Raphaël A3 PDF vectoriel

echo "🖼️  Génération des posters Saint-Raphaël"
echo "Format: A3 (11.7 × 16.5 inches) @ 300 DPI"
echo "Format fichier: PDF vectoriel"
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

# Génération séquentielle optimisée avec cache
echo "🚀 Mode optimisé avec cache en mémoire"
echo ""

start_total=$(date +%s)

for i in "${!themes[@]}"; do
  theme="${themes[$i]}"
  num=$((i + 1))
  echo "[$num/17] Génération: $theme..."

  start=$(date +%s)

  python create_map_poster.py \
    -c "Saint-Raphaël, Var" \
    -C "France" \
    --country-label "French Riviera" \
    -t "$theme" \
    -d 12000 \
    -W 11.7 \
    -H 16.5 \
    -f pdf

  end=$(date +%s)
  elapsed=$((end - start))
  echo "  ✓ Terminé en ${elapsed}s"
  echo ""
done

end_total=$(date +%s)
elapsed_total=$((end_total - start_total))
avg=$((elapsed_total / 17))

echo ""
echo "✅ Tous les posters générés!"
echo "📁 Dossier: posters/saint-raphaël_*_12000m_*.pdf"
echo "⏱️  Temps total: ${elapsed_total}s ($(date -ud "@$elapsed_total" +%M:%S))"
echo "📊 Moyenne: ${avg}s par poster"
