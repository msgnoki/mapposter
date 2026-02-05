# Frontend - Spécifications Techniques

## 🎨 Architecture

### Stack Technique
- **Framework**: Vanilla JavaScript (ES6+)
- **Carte**: Leaflet.js 1.9.4
- **Tiles**: OpenStreetMap
- **Style**: CSS3 (Grid, Flexbox)
- **Template**: Jinja2 (Flask)

### Structure
```
web_interface/
├── templates/
│   └── index.html          # Single Page Application
└── static/
    ├── css/                # (inline dans index.html)
    ├── js/                 # (inline dans index.html)
    └── images/             # (none actuellement)
```

---

## 🗺️ Carte Interactive (Leaflet)

### Initialisation

```javascript
let map = L.map('map').setView([43.4255, 6.7694], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
}).addTo(map);
```

### Événements

```javascript
map.on('move', updateFrame);      // Mise à jour cadre en temps réel
map.on('zoom', updateFrame);      // Idem au zoom
map.on('moveend', updateLocation); // Reverse geocoding après déplacement
```

---

## 🎯 Cadre de Sélection WYSIWYG

### Principe

Un rectangle **fixe** au centre de la carte qui représente exactement la zone qui sera générée.

### HTML

```html
<div id="frame-overlay"></div>
```

### CSS

```css
#frame-overlay {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    border: 3px solid #e74c3c;
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.3);
    pointer-events: none;
    z-index: 400;
    transition: all 0.3s ease;
}
```

**Clé**: `pointer-events: none` permet de cliquer à travers le cadre sur la carte en dessous.

### Calcul Dynamique des Dimensions

```javascript
function updateFrame() {
    const frame = document.getElementById('frame-overlay');
    const mapSize = map.getSize();

    // Ratio basé sur le format sélectionné
    const ratio = currentOrientation === 'portrait'
        ? currentFormat.height / currentFormat.width
        : currentFormat.width / currentFormat.height;

    let frameWidth, frameHeight;

    if (currentOrientation === 'portrait') {
        frameWidth = Math.min(mapSize.x * 0.3, 300);
        frameHeight = frameWidth * ratio;
    } else {
        frameHeight = Math.min(mapSize.y * 0.4, 250);
        frameWidth = frameHeight * ratio;
    }

    frame.style.width = frameWidth + 'px';
    frame.style.height = frameHeight + 'px';

    updateMapInfo();
}
```

**Logique**:
- Portrait: largeur = 30% de la carte (max 300px), hauteur calculée selon ratio
- Landscape: hauteur = 40% de la carte (max 250px), largeur calculée selon ratio

### Conversion Pixels → Distance Géographique

```javascript
function getFrameBounds() {
    const frame = document.getElementById('frame-overlay');
    const frameRect = frame.getBoundingClientRect();
    const mapContainer = document.getElementById('map');
    const mapRect = mapContainer.getBoundingClientRect();

    // Centre du cadre (centre de la carte)
    const frameCenter = {
        x: mapRect.width / 2,
        y: mapRect.height / 2
    };

    const frameHalfWidth = frameRect.width / 2;
    const frameHalfHeight = frameRect.height / 2;

    // Convertir pixels → lat/lng
    const topLeft = map.containerPointToLatLng([
        frameCenter.x - frameHalfWidth,
        frameCenter.y - frameHalfHeight
    ]);
    const topRight = map.containerPointToLatLng([
        frameCenter.x + frameHalfWidth,
        frameCenter.y - frameHalfHeight
    ]);
    const center = map.getCenter();

    // Calculer distances en mètres
    const distNS = map.distance(center, [topLeft.lat, center.lng]);
    const distEW = map.distance(center, [center.lat, topRight.lng]);

    // create_poster utilise dist comme la PLUS GRANDE dimension
    const distance = currentOrientation === 'portrait'
        ? Math.round(distNS)  // Portrait: rayon vertical
        : Math.round(distEW); // Landscape: rayon horizontal

    return { distance, bounds: { topLeft, topRight, center } };
}
```

**Clé WYSIWYG**:
- Portrait: on envoie le rayon **vertical** (distNS)
- Landscape: on envoie le rayon **horizontal** (distEW)
- Cela correspond exactement à la logique de `get_crop_limits()` du backend

---

## 🎨 Interface Utilisateur

### Sidebar Collapsible

```javascript
document.getElementById('sidebar-toggle').addEventListener('click', function() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    this.textContent = sidebar.classList.contains('collapsed') ? '▶' : '◀';
});
```

**CSS**:
```css
#sidebar.collapsed {
    transform: translateX(-340px);
}
```

### Sélection de Thèmes

#### HTML (Jinja2)

```html
<div class="select-all-themes">
    <input type="checkbox" id="select-all" checked onchange="toggleAllThemes()">
    <label for="select-all">Tout sélectionner</label>
</div>

<div class="theme-grid">
    {% for theme in themes %}
    <label class="theme-checkbox">
        <input type="checkbox" name="theme" value="{{ theme }}" checked>
        <span>{{ theme }}</span>
    </label>
    {% endfor %}
</div>
```

#### JavaScript

```javascript
function toggleAllThemes() {
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('input[name="theme"]');
    checkboxes.forEach(cb => cb.checked = selectAll.checked);
}
```

**Grid CSS**:
```css
.theme-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    max-height: 300px;
    overflow-y: auto;
}
```

### Sélection de Format

#### Presets

```javascript
const formats = {
    'A3': { width: 11.7, height: 16.5 },
    'A4': { width: 8.3, height: 11.7 },
    'ultrawide': { width: 11.47, height: 4.8 },
    ...
};

function selectFormat(format, width, height) {
    // Désélectionner tous
    document.querySelectorAll('.format-btn[data-format]').forEach(btn => {
        btn.classList.remove('active');
    });

    // Sélectionner le nouveau
    document.querySelector(`[data-format="${format}"]`).classList.add('active');

    // Mettre à jour state
    currentFormat = { width, height };
    updateFrame();  // Recalculer le cadre
}
```

#### Orientation Toggle

```javascript
function setOrientation(orientation) {
    document.querySelectorAll('.orientation-toggle .format-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    currentOrientation = orientation;
    updateFrame();  // Recalculer le cadre
}
```

---

## 🔄 Reverse Geocoding

### Trigger

Appelé automatiquement quand la carte s'arrête de bouger (`moveend`).

### Implémentation

```javascript
async function updateLocation() {
    const center = map.getCenter();

    try {
        const response = await fetch('/api/geocode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: center.lat,
                lng: center.lng
            })
        });

        if (response.ok) {
            const data = await response.json();
            currentLocation = {
                lat: center.lat,
                lng: center.lng,
                city: data.city,
                country: data.country
            };

            // Mettre à jour les champs input
            document.getElementById('location-city').value = data.city;
            document.getElementById('location-country').value = data.country;
        }
    } catch (error) {
        console.error('Geocoding error:', error);
    }
}
```

### Debouncing

Le `moveend` event agit comme un debounce naturel - ne s'exécute qu'à la fin du mouvement.

---

## 🚀 Génération de Posters

### Flow

1. Validation des thèmes sélectionnés
2. Récupération des paramètres (format, orientation, distance)
3. Envoi requête POST à `/api/generate`
4. Affichage progression
5. Affichage résultat

### Implémentation

```javascript
async function generatePosters() {
    const btn = document.querySelector('.generate-btn');
    const message = document.getElementById('message');

    // 1. Validation
    const selectedThemes = Array.from(
        document.querySelectorAll('input[name="theme"]:checked')
    ).map(cb => cb.value);

    if (selectedThemes.length === 0) {
        showMessage('Veuillez sélectionner au moins un thème', 'error');
        return;
    }

    // 2. UI Loading State
    btn.disabled = true;
    btn.classList.add('loading');
    btn.textContent = `⏳ Génération ${selectedThemes.length} poster(s)...`;
    showMessage(
        `⏳ Génération en cours (${selectedThemes.length} thèmes). ` +
        `Voir progression dans le terminal Flask!`,
        'success'
    );

    try {
        // 3. Récupérer les paramètres
        const center = map.getCenter();
        const frameBounds = getFrameBounds();
        const cityValue = document.getElementById('location-city').value;
        const countryValue = document.getElementById('location-country').value;

        // 4. Préparer la requête
        const data = {
            city: cityValue,
            country: 'France',
            lat: center.lat,
            lng: center.lng,
            distance: frameBounds.distance,  // Distance WYSIWYG
            themes: selectedThemes,
            format_preset: document.querySelector(
                '.format-btn.active[data-format]'
            )?.dataset.format || 'A3',
            orientation: currentOrientation,
            output_format: document.getElementById('output-format').value,
            dpi: document.getElementById('dpi').value,
            country_label: countryValue
        };

        // 5. Envoyer la requête
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        // 6. Afficher le résultat
        if (result.success) {
            showMessage(`✅ ${result.message}`, 'success');
        } else {
            showMessage(`❌ Erreur: ${result.error}`, 'error');
        }
    } catch (error) {
        showMessage(`❌ Erreur: ${error.message}`, 'error');
    } finally {
        // 7. Reset UI
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.textContent = '🚀 Générer les posters';
    }
}
```

### Messages

```javascript
function showMessage(text, type) {
    const message = document.getElementById('message');
    message.textContent = text;
    message.className = `message ${type}`;  // 'success' ou 'error'
    message.style.display = 'block';
}
```

**CSS**:
```css
.message.success {
    background: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.message.error {
    background: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}
```

---

## 📊 Info Carte Temps Réel

### Affichage

```html
<div class="map-info">
    <div><strong>Zone sélectionnée</strong></div>
    <div id="map-center">Centre: 43.4255, 6.7694</div>
    <div id="map-distance">Rayon: 8523m</div>
</div>
```

### Mise à Jour

```javascript
function updateMapInfo() {
    const center = map.getCenter();
    const frameBounds = getFrameBounds();

    document.getElementById('map-center').textContent =
        `Centre: ${center.lat.toFixed(4)}, ${center.lng.toFixed(4)}`;
    document.getElementById('map-distance').textContent =
        `Rayon: ${frameBounds.distance}m`;
}
```

**Appelé par**: `updateFrame()` qui s'exécute à chaque mouvement de carte.

---

## 🎨 Design System

### Couleurs

```css
:root {
    --primary: #667eea;
    --primary-dark: #764ba2;
    --success: #28a745;
    --error: #dc3545;
    --bg-light: #f8f9fa;
    --border: #ddd;
    --text: #333;
    --text-muted: #666;
}
```

### Typography

```css
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, Oxygen, Ubuntu, sans-serif;
}

h1 { font-size: 20px; font-weight: 600; }
h3 {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
```

### Composants

#### Boutons

```css
.format-btn {
    padding: 12px;
    border: 2px solid #ddd;
    border-radius: 8px;
    background: white;
    cursor: pointer;
    transition: all 0.2s;
}

.format-btn.active {
    border-color: #667eea;
    background: #667eea;
    color: white;
}

.format-btn:hover {
    border-color: #667eea;
    background: #f5f5ff;
}
```

#### Inputs

```css
.control-group input[type="text"],
.control-group select {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 14px;
}

.control-group input[type="text"]:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}
```

### Responsivité

**Breakpoints**:
- Desktop: > 1024px → Sidebar 380px
- Tablet: 768-1024px → Sidebar 320px (collapsible)
- Mobile: < 768px → Sidebar full overlay

```css
@media (max-width: 768px) {
    #sidebar {
        width: 100%;
        transform: translateX(-100%);
    }

    #sidebar:not(.collapsed) {
        transform: translateX(0);
    }
}
```

---

## 🔧 État Global

### Variables

```javascript
let map;  // Instance Leaflet
let currentFormat = { width: 11.7, height: 16.5 };  // Format actuel
let currentOrientation = 'portrait';  // Orientation
let currentLocation = {
    lat: 43.4255,
    lng: 6.7694,
    city: 'Saint-Raphaël',
    country: 'France'
};
```

### Initialisation

```javascript
window.addEventListener('load', function() {
    initMap();
    updateLocation();
});
```

---

## 🐛 Gestion des Erreurs

### Fetch Errors

```javascript
try {
    const response = await fetch('/api/generate', {...});
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const result = await response.json();
} catch (error) {
    console.error('Generation error:', error);
    showMessage(`❌ Erreur de connexion: ${error.message}`, 'error');
}
```

### Validation

```javascript
if (selectedThemes.length === 0) {
    showMessage('Veuillez sélectionner au moins un thème', 'error');
    return;
}

const distance = frameBounds.distance;
if (distance < 500 || distance > 50000) {
    showMessage('Distance invalide (500-50000m)', 'error');
    return;
}
```

---

## 📱 UX Patterns

### Loading States

```javascript
btn.disabled = true;
btn.classList.add('loading');
btn.textContent = '⏳ Génération en cours...';
```

**CSS**:
```css
.generate-btn.loading {
    background: #999;
    cursor: not-allowed;
}
```

### Feedback Visuel

- Hover states sur tous les boutons
- Transitions smooth (0.2-0.3s)
- Focus visible sur inputs
- Messages de succès/erreur colorés

### Accessibility

```html
<label for="location-city">Nom de la ville</label>
<input id="location-city" type="text" aria-label="Nom de la ville">

<button aria-label="Replier le panneau latéral">◀</button>
```

---

## ⚡ Performance

### Optimisations

1. **Debouncing**: `moveend` au lieu de `move` pour geocoding
2. **CSS transforms**: `transform: translateX()` pour animations (GPU)
3. **Inline CSS/JS**: Pas de requêtes HTTP supplémentaires
4. **Leaflet tiles caching**: Automatique par le navigateur

### Metrics

- **First Paint**: < 500ms
- **Interactive**: < 1s
- **Geocoding**: ~200-500ms par requête
- **Frame update**: < 16ms (60 FPS)

---

## 🔒 Sécurité Frontend

### Sanitization

```javascript
const cityValue = document.getElementById('location-city').value
    .trim()
    .substring(0, 100);  // Max length
```

### CORS

Pas de CORS issues - même origine (Flask template)

### XSS Protection

Jinja2 auto-escape:
```html
{{ theme }}  <!-- Automatiquement échappé -->
```

---

## 🧪 Testing

### Manuel

Checklist:
- [ ] Carte se charge correctement
- [ ] Cadre s'adapte au format/orientation
- [ ] Reverse geocoding fonctionne
- [ ] Tous les thèmes se cochent/décochent
- [ ] Génération réussit
- [ ] Messages d'erreur s'affichent
- [ ] Sidebar collapse/expand

### Console Logs

```javascript
console.log('Frame bounds:', frameBounds);
console.log('Selected themes:', selectedThemes);
console.log('Request data:', data);
```

Activer pour debug, désactiver en prod.
