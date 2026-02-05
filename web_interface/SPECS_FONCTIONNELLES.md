# Spécifications Fonctionnelles

## 📋 Vue d'Ensemble

**Map Poster Generator** est une application web permettant de générer des posters de cartes personnalisés pour n'importe quelle ville du monde, avec une interface WYSIWYG intuitive.

### Objectifs Principaux

1. **Simplicité**: Interface épurée avec focus sur la carte
2. **WYSIWYG**: Ce que vous voyez = ce que vous obtenez
3. **Personnalisation**: 17 thèmes, multiples formats, orientations
4. **Performance**: Génération rapide avec cache intelligent
5. **Qualité**: Posters haute résolution (300 DPI) prêts à imprimer

---

## 👥 Personas

### Persona 1: Lisa - Designer Graphique
**Âge**: 28 ans
**Objectif**: Créer des posters muraux pour décoration intérieure

**Besoins**:
- Voir exactement la zone qui sera imprimée
- Tester plusieurs thèmes rapidement
- Formats standards (A3, A4) pour impression
- Haute qualité (PDF vectoriel)

**Frustrations**:
- Les outils existants ne montrent pas la zone exacte
- Génération lente
- Résultats imprévisibles

### Persona 2: Marc - Développeur Nomade
**Âge**: 35 ans
**Objectif**: Créer un fond d'écran ultrawide de sa ville actuelle

**Besoins**:
- Format ultrawide 21:9 (3440×1440)
- Thèmes modernes (neon, cyberpunk)
- PNG pour usage numérique
- Personnalisation du texte

**Frustrations**:
- Pas de format ultrawide dans les outils classiques
- Impossible de modifier les labels

### Persona 3: Sophie - Passionnée de Voyage
**Âge**: 42 ans
**Objectif**: Collection de posters de villes visitées

**Besoins**:
- Générer plusieurs thèmes d'une même ville
- Label personnalisé (ex: "French Riviera" au lieu de "France")
- Tous les formats (A3 à A5)

**Frustrations**:
- Doit générer un par un manuellement
- Pas de personnalisation des textes

---

## 🎯 Fonctionnalités

### F1: Sélection de Zone WYSIWYG

**Description**: L'utilisateur peut naviguer sur une carte interactive avec un cadre fixe au centre représentant exactement la zone qui sera générée.

**User Flow**:
1. La carte s'ouvre centrée sur une ville (défaut: Saint-Raphaël)
2. Un cadre rouge fixe s'affiche au centre
3. L'utilisateur zoome/déplace la carte
4. Le cadre reste fixe, la carte bouge en dessous
5. La zone affichée dans le cadre = zone exacte du poster

**Acceptance Criteria**:
- ✅ Cadre fixe au centre de l'écran
- ✅ Ratio du cadre correspond au format sélectionné (A3, A4, etc.)
- ✅ Distance calculée = rayon exact envoyé au backend
- ✅ Info temps réel affichée (centre, rayon)

**Cas d'usage**:
```
Lisa veut un poster de Paris centré sur la Tour Eiffel.
→ Elle zoome sur Paris
→ Déplace la carte pour mettre la Tour Eiffel au centre du cadre rouge
→ Ajuste le zoom pour avoir le bon niveau de détail
→ Le cadre montre exactement ce qui sera sur le poster
```

---

### F2: Détection Automatique de Ville

**Description**: Quand l'utilisateur déplace la carte, l'application détecte automatiquement la ville et le pays.

**User Flow**:
1. L'utilisateur déplace la carte
2. Quand il s'arrête, un reverse geocoding s'exécute
3. Les champs "Nom de la ville" et "Label pays" se remplissent automatiquement
4. L'utilisateur peut modifier manuellement si besoin

**Acceptance Criteria**:
- ✅ Détection automatique au `moveend`
- ✅ Champs pré-remplis mais éditables
- ✅ Pas de détection pendant le mouvement (performance)
- ✅ Gestion des erreurs si geocoding échoue

**Cas d'usage**:
```
Marc explore la carte du Japon.
→ Il navigue vers Tokyo
→ Quand il s'arrête, les champs se remplissent:
   Ville: "Tokyo"
   Pays: "Japan"
→ Il modifie manuellement "Japan" → "日本"
```

---

### F3: Sélection Multi-Thèmes

**Description**: L'utilisateur peut sélectionner plusieurs thèmes pour générer plusieurs posters d'un seul coup.

**User Flow**:
1. 17 thèmes affichés en grille avec checkboxes
2. Case "Tout sélectionner" en haut
3. L'utilisateur coche les thèmes souhaités
4. Clic sur "Générer" → tous les thèmes sélectionnés sont générés

**Acceptance Criteria**:
- ✅ 17 thèmes disponibles
- ✅ "Tout sélectionner" coche/décoche tous
- ✅ Au moins 1 thème obligatoire
- ✅ Génération séquentielle avec progression

**Cas d'usage**:
```
Sophie veut comparer 5 thèmes pour Lisbonne.
→ Elle décoche "Tout sélectionner"
→ Coche: terracotta, ocean, sunset, pastel_dream, warm_beige
→ Clic "Générer"
→ 5 PDFs sont créés dans posters/
→ Elle peut les comparer et choisir son préféré
```

---

### F4: Presets de Formats

**Description**: Formats pré-configurés pour impression et usage numérique.

**Formats Disponibles**:

| Preset | Dimensions | Usage |
|--------|-----------|-------|
| A3 | 11.7 × 16.5" | Impression grand format |
| A4 | 8.3 × 11.7" | Impression standard |
| A5 | 5.8 × 8.3" | Petit format |
| Ultrawide | 11.47 × 4.8" | Fond d'écran 3440×1440 |
| Carré | 12 × 12" | Instagram, cadre carré |
| Poster | 18 × 24" | Affiche murale |

**User Flow**:
1. L'utilisateur clique sur un preset
2. Le cadre change de ratio immédiatement
3. La distance est recalculée
4. L'orientation (Portrait/Paysage) peut être inversée

**Acceptance Criteria**:
- ✅ 6 presets disponibles
- ✅ Changement de cadre en temps réel
- ✅ Orientation switchable (P/L)
- ✅ Distance WYSIWYG recalculée

**Cas d'usage**:
```
Lisa veut un A3 portrait de Lyon.
→ Sélectionne "A3"
→ Sélectionne "Portrait"
→ Le cadre devient vertical avec ratio 16.5:11.7
→ Elle ajuste le zoom pour que le Vieux Lyon tienne dans le cadre
```

---

### F5: Configuration Sortie

**Description**: Choix du format de fichier et résolution.

**Options**:
- **Format**: PDF (vectoriel), PNG (raster), SVG (vectoriel)
- **DPI**: 150, 300, 600 (note: 300 DPI par défaut, autres pour info)

**User Flow**:
1. L'utilisateur sélectionne le format dans la dropdown
2. Sélectionne le DPI (note: actuellement 300 DPI fixe)
3. Ces paramètres s'appliquent à tous les thèmes générés

**Acceptance Criteria**:
- ✅ 3 formats de sortie
- ✅ DPI sélectionnable (UI only pour le moment)
- ✅ Format défaut: PDF 300 DPI
- ✅ SVG pour web, PDF pour impression

**Cas d'usage**:
```
Marc veut un fond d'écran PNG.
→ Format: Ultrawide
→ Orientation: Paysage
→ Format sortie: PNG
→ DPI: 300
→ Résultat: saint-raphaël_neon_8523m.png (3440×1440)
```

---

### F6: Personnalisation Texte

**Description**: Champs éditables pour ville et pays.

**Champs**:
- **Nom de la ville**: Pré-rempli par geocoding, éditable
- **Label pays**: Pré-rempli, éditable (ex: "French Riviera", "Côte d'Azur")

**User Flow**:
1. L'utilisateur déplace la carte → champs auto-remplis
2. Il modifie manuellement si besoin
3. Le texte modifié apparaît sur le poster

**Acceptance Criteria**:
- ✅ Champs pré-remplis automatiquement
- ✅ Éditables à tout moment
- ✅ Changements reflétés dans le poster généré
- ✅ Support Unicode (日本, Москва, etc.)

**Cas d'usage**:
```
Sophie génère un poster de Saint-Raphaël.
→ Champ auto-rempli: "Saint-Raphaël"
→ Label pays: "France"
→ Elle change "France" → "French Riviera"
→ Le poster affiche: "SAINT-RAPHAËL" / "French Riviera"
```

---

### F7: Génération Batch

**Description**: Générer plusieurs posters (multi-thèmes) en une seule opération.

**User Flow**:
1. L'utilisateur sélectionne N thèmes (ex: 5)
2. Clique "Générer les posters"
3. Progression affichée dans le terminal Flask
4. Message de succès: "5 poster(s) généré(s) avec succès!"

**Acceptance Criteria**:
- ✅ Génération séquentielle (pas de parallélisation)
- ✅ Logs détaillés dans terminal Flask
- ✅ Message de succès/erreur dans l'interface
- ✅ Tous les fichiers créés dans `posters/`

**Performance**:
- Premier poster: ~80-90s (download OSM)
- Posters suivants: ~3-5s (cache)
- Exemple: 17 thèmes = ~2-3 minutes total

**Cas d'usage**:
```
Lisa teste tous les thèmes pour Bordeaux.
→ Coche "Tout sélectionner" (17 thèmes)
→ Clic "Générer"
→ Terminal Flask affiche:
   [1/17] 🎨 AUTUMN... ✓ autumn OK (85.3s)
   [2/17] 🎨 BLUEPRINT... ✓ blueprint OK (3.2s)
   ...
→ Message: "✅ 17 poster(s) générés en 145s"
```

---

### F8: Sidebar Collapsible

**Description**: Le panneau latéral peut être réduit pour plus d'espace carte.

**User Flow**:
1. Clic sur le bouton "◀" en haut du sidebar
2. Le sidebar glisse vers la gauche
3. Bouton devient "▶"
4. Clic à nouveau → sidebar réapparaît

**Acceptance Criteria**:
- ✅ Animation smooth (0.3s)
- ✅ Icône change (◀ / ▶)
- ✅ Carte prend tout l'espace
- ✅ État persiste pendant la session

**Cas d'usage**:
```
Marc veut voir la carte en grand.
→ Clic sur "◀"
→ Sidebar disparaît à gauche
→ Carte occupe tout l'écran
→ Il navigue sur la carte
→ Clic sur "▶" pour rouvrir le sidebar
```

---

## 🔄 User Flows Complets

### Flow 1: Générer un Poster Simple

```
1. Ouvrir http://localhost:5000
2. La carte affiche Saint-Raphaël par défaut
3. Naviguer vers la ville souhaitée (ex: Paris)
   → Champs "Paris" / "France" se remplissent auto
4. Ajuster le zoom/position pour cadrer la zone
   → Le cadre rouge montre la zone exacte
5. Sélectionner un thème (ex: "blueprint")
6. Sélectionner format "A3" + "Portrait"
7. Clic "Générer les posters"
   → Message: "⏳ Génération en cours..."
   → Terminal: logs de progression
8. Après ~85s: Message "✅ 1 poster généré!"
9. Fichier créé: posters/paris_blueprint_8523m_*.pdf
```

### Flow 2: Collection Multi-Thèmes

```
1. Naviguer vers Lisbonne
2. Ajuster cadrage (centre ville + Tage)
3. Cliquer "Tout sélectionner" (17 thèmes)
4. Format: A4 Portrait
5. Format sortie: PDF
6. Clic "Générer"
7. Terminal affiche progression de 1/17 à 17/17
8. Après ~2min: 17 PDFs dans posters/
9. Ouvrir les PDFs pour comparer les thèmes
```

### Flow 3: Fond d'Écran Ultrawide

```
1. Naviguer vers Tokyo
2. Format: Ultrawide
3. Orientation: Paysage
4. Ajuster zoom pour ville entière
5. Thème: neon_cyberpunk
6. Format sortie: PNG
7. Modifier label: "Japan" → "東京"
8. Générer
9. Fichier: tokyo_neon_cyberpunk_*.png (3440×1440)
10. Définir comme fond d'écran
```

---

## 🎨 Thèmes Disponibles

### Thèmes Classiques

| Nom | Description | Usage |
|-----|-------------|-------|
| **terracotta** | Chaleur méditerranéenne - orange brûlé sur crème | Villes côtières, sud |
| **blueprint** | Style plan architecte - bleu technique | Villes modernes, grilles |
| **noir** | Monochrome noir et blanc - contraste fort | Minimaliste, moderne |
| **warm_beige** | Beiges chauds sépia - vintage | Villes historiques |

### Thèmes Nature

| Nom | Description | Usage |
|-----|-------------|-------|
| **forest** | Verts profonds et sauge - botanique | Villes vertes, parcs |
| **emerald** | Vert foncé émeraude avec accents menthe | Seattle, Portland |
| **ocean** | Bleus et turquoise | Villes côtières, îles |
| **autumn** | Oranges brûlés, rouges, jaunes | Saison automne |

### Thèmes Modernes

| Nom | Description | Usage |
|-----|-------------|-------|
| **neon_cyberpunk** | Néons roses/bleus sur fond sombre | Tokyo, Seoul, villes tech |
| **midnight_blue** | Bleu nuit profond | Villes de nuit |
| **gradient_roads** | Dégradé centre→bords | Effet artistique |
| **contrast_zones** | Contraste densité urbaine | Métropoles |

### Thèmes Doux

| Nom | Description | Usage |
|-----|-------------|-------|
| **pastel_dream** | Pastels doux rose/bleu | Romantique, doux |
| **sunset** | Oranges/roses sur pêche | Golden hour |
| **copper_patina** | Cuivre oxydé teal-vert | Industriel vintage |

### Thèmes Spéciaux

| Nom | Description | Usage |
|-----|-------------|-------|
| **japanese_ink** | Encre de Chine minimaliste | Asie, zen |
| **monochrome_blue** | Monochrome bleu | Classique, épuré |

---

## 🚫 Limitations Connues

### L1: Mer/Océan Non Colorée

**Description**: La mer ouverte apparaît en couleur de fond (pas de bleu).

**Raison**: OSM ne fournit pas de polygones pour l'océan ouvert.

**Workaround**:
- Baies (`natural=bay`) sont colorées ✅
- Détroits (`natural=strait`) sont colorés ✅
- Mer ouverte = fond (normal pour les posters de cartes)

**Impact**: Faible - c'est le standard des posters de cartes

### L2: Génération Séquentielle

**Description**: Les thèmes sont générés un par un (pas de parallélisation).

**Raison**: Multiprocessing pickle error avec fonctions imbriquées.

**Performance**:
- 1 thème: ~3-5s (avec cache)
- 17 thèmes: ~2-3 minutes
- Acceptable pour usage normal

**Workaround**: Lancer plusieurs instances Flask sur différents ports

### L3: DPI Interface

**Description**: Le sélecteur DPI dans l'interface n'est pas fonctionnel.

**Raison**: Matplotlib utilise 300 DPI fixe.

**Impact**: Minimal - 300 DPI est parfait pour l'impression

**Todo**: Soit retirer le sélecteur, soit implémenter vraiment le DPI variable

### L4: Taille Cache OSM

**Description**: Le cache OSM peut devenir volumineux.

**Taille**: ~10-50 MB par ville

**Workaround**: Nettoyer manuellement `cache/` si besoin:
```bash
rm cache/*.pkl  # Supprime tout le cache
```

---

## 📊 Metrics de Succès

### Performance
- ✅ Premier poster: < 90s
- ✅ Posters suivants: < 5s
- ✅ Interface réactive: < 16ms par frame

### Qualité
- ✅ Résolution: 300 DPI minimum
- ✅ Format vectoriel disponible (PDF, SVG)
- ✅ Toutes les routes visibles selon hiérarchie
- ✅ Texte lisible et bien positionné

### UX
- ✅ WYSIWYG: cadre = zone exacte générée
- ✅ Reverse geocoding automatique
- ✅ Multi-thèmes en un clic
- ✅ Messages clairs (succès/erreur)

### Adoption
- ✅ Interface intuitive sans documentation
- ✅ Résultats prévisibles
- ✅ Génération fiable (cache + error handling)

---

## 🔮 Roadmap Future

### V2.0: Optimisations

- [ ] Génération parallèle (fix pickle error)
- [ ] Streaming de progression (SSE)
- [ ] DPI variable fonctionnel
- [ ] Cache SQLite (plus rapide que pickle)

### V2.1: Features

- [ ] Prévisualisation miniature avant génération
- [ ] Historique des générations
- [ ] Download batch (ZIP de tous les thèmes)
- [ ] Partage de configurations (URL avec params)

### V2.2: Avancé

- [ ] Coastlines rendering (océan coloré)
- [ ] Custom themes (éditeur de couleurs)
- [ ] Layers additionnels (railways, buildings)
- [ ] Export haute résolution (600 DPI +)

### V3.0: Pro

- [ ] Comptes utilisateurs
- [ ] Galerie publique de posters
- [ ] API REST publique
- [ ] Intégration e-commerce (impression)
- [ ] Mode SaaS avec quotas

---

## 📝 Glossaire

**WYSIWYG**: What You See Is What You Get - principe selon lequel l'aperçu = résultat final

**OSM**: OpenStreetMap - base de données géographiques collaborative

**CRS**: Coordinate Reference System - système de coordonnées géographiques

**DPI**: Dots Per Inch - résolution d'impression (300 = qualité standard)

**Reverse Geocoding**: Convertir coordonnées → nom de lieu

**z-order**: Ordre de superposition des layers graphiques

**GeoDataFrame**: Structure de données GeoPandas pour données géospatiales

**Pickle**: Format de sérialisation Python pour le cache

**Multipolygon**: Polygone composé de plusieurs parties (ex: archipel)

**Aspect Ratio**: Rapport largeur/hauteur (ex: A4 = 1:√2)
