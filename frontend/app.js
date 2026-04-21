const API_BASE = 'http://localhost:8000';

const CITY_FACTORS = ['EV Adoption', 'Income Level', 'Population', 'Traffic', 'Competition', 'Accessibility'];
const HIGHWAY_FACTORS = ['Traffic Flow', 'Distance Gap', 'Fuel Proximity', 'Rest Stop Proximity', 'Risk'];

let currentMode = 'city';
let currentPolygon = null;
let lastResults = null;
let drawMode = false;
let drawCoords = [];
let map = null;

function scoreColor(score) {
  if (score >= 75) return '#4caf50';
  if (score >= 55) return '#ff9800';
  return '#f44336';
}

function scoreClass(score) {
  if (score >= 75) return 'high';
  if (score >= 55) return 'mid';
  return 'low';
}

function el(id) { return document.getElementById(id); }

function updateModeUI() {
  const factors = currentMode === 'city' ? CITY_FACTORS : HIGHWAY_FACTORS;
  el('mode-title').textContent = currentMode === 'city' ? 'City EV Station Mode' : 'Highway EV Station Mode';
  el('mode-description').textContent = currentMode === 'city'
    ? 'Click anywhere within Ahmedabad or Gandhinagar to score a location.'
    : 'Click near a highway corridor to score a location.';
  el('mode-factors').innerHTML = factors.map(f => `<div class="factor-tag">${f}</div>`).join('');
}

function clearResults() {
  el('score-card').classList.add('hidden');
  el('top10-panel').classList.add('hidden');
  el('top10-list').innerHTML = '';
  lastResults = null;
  currentPolygon = null;
  el('btn-hotspots').disabled = false;
  el('btn-export').disabled = true;

  if (!map) return;
  ['batch-points', 'hotspot-fill', 'hotspot-outline', 'competitors-layer',
   'top10-circles', 'top10-labels', 'best-highway-glow', 'best-highway-line'].forEach(id => {
    if (map.getLayer(id)) map.removeLayer(id);
  });
  ['batch-points', 'hotspots', 'competitors', 'top10-markers', 'best-highways'].forEach(id => {
    if (map.getSource(id)) map.removeSource(id);
  });
  el('btn-summary').disabled = true;
  clearDrawLayers();
  cancelDraw();
}

function cancelDraw() {
  drawMode = false;
  drawCoords = [];
  el('btn-draw').classList.remove('active');
  el('btn-draw').textContent = '✏️ Draw Area';
  if (map) map.getCanvas().style.cursor = '';
  clearDrawLayers();
}

function clearDrawLayers() {
  if (!map) return;
  ['draw-polygon-fill', 'draw-polygon-line', 'draw-vertices', 'draw-preview'].forEach(id => {
    if (map.getLayer(id)) map.removeLayer(id);
  });
  ['draw-polygon', 'draw-vertices', 'draw-preview'].forEach(id => {
    if (map.getSource(id)) map.removeSource(id);
  });
}

function initDrawLayers() {
  if (map.getSource('draw-polygon')) return;
  map.addSource('draw-polygon', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
  map.addLayer({ id: 'draw-polygon-fill', type: 'fill', source: 'draw-polygon', paint: { 'fill-color': '#4fc3f7', 'fill-opacity': 0.15 } });
  map.addLayer({ id: 'draw-polygon-line', type: 'line', source: 'draw-polygon', paint: { 'line-color': '#4fc3f7', 'line-width': 2, 'line-dasharray': [3, 2] } });

  map.addSource('draw-vertices', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
  map.addLayer({ id: 'draw-vertices', type: 'circle', source: 'draw-vertices', paint: { 'circle-radius': 5, 'circle-color': '#4fc3f7', 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' } });

  map.addSource('draw-preview', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
  map.addLayer({ id: 'draw-preview', type: 'line', source: 'draw-preview', paint: { 'line-color': '#4fc3f7', 'line-width': 1.5, 'line-dasharray': [2, 2] } });
}

function updateDrawLayers(mousePos) {
  if (!map.getSource('draw-polygon')) return;

  if (drawCoords.length >= 2) {
    const ring = [...drawCoords, drawCoords[0]];
    map.getSource('draw-polygon').setData({ type: 'FeatureCollection', features: [
      { type: 'Feature', geometry: { type: 'Polygon', coordinates: [ring] }, properties: {} }
    ]});
  } else {
    map.getSource('draw-polygon').setData({ type: 'FeatureCollection', features: [] });
  }

  map.getSource('draw-vertices').setData({ type: 'FeatureCollection',
    features: drawCoords.map(c => ({ type: 'Feature', geometry: { type: 'Point', coordinates: c }, properties: {} }))
  });

  if (drawCoords.length >= 1 && mousePos) {
    const last = drawCoords[drawCoords.length - 1];
    map.getSource('draw-preview').setData({ type: 'FeatureCollection', features: [
      { type: 'Feature', geometry: { type: 'LineString', coordinates: [last, mousePos] }, properties: {} }
    ]});
  } else {
    map.getSource('draw-preview').setData({ type: 'FeatureCollection', features: [] });
  }
}

async function finishDraw() {
  if (drawCoords.length < 3) return;
  const ring = [...drawCoords];
  const polygon = { type: 'Polygon', coordinates: [ring] };
  currentPolygon = polygon;
  cancelDraw();
  await runBatchScore(polygon);
}

async function loadModeLayer() {
  ['city-boundary-fill', 'city-boundary-outline', 'highway-layer'].forEach(id => {
    if (map.getLayer(id)) map.removeLayer(id);
  });
  ['city-boundary', 'highways'].forEach(id => {
    if (map.getSource(id)) map.removeSource(id);
  });

  if (currentMode === 'city') {
    try {
      const resp = await fetch(`${API_BASE}/layers/city-boundary`);
      const data = await resp.json();
      if (data.features && data.features.length > 0) {
        map.addSource('city-boundary', { type: 'geojson', data });
        map.addLayer({ id: 'city-boundary-fill', type: 'fill', source: 'city-boundary', paint: { 'fill-color': '#4fc3f7', 'fill-opacity': 0.06 } });
        map.addLayer({ id: 'city-boundary-outline', type: 'line', source: 'city-boundary', paint: { 'line-color': '#4fc3f7', 'line-width': 2, 'line-opacity': 0.5 } });
      }
    } catch (e) { console.warn('City boundary load failed', e); }
  } else {
    try {
      const resp = await fetch(`${API_BASE}/layers/highways`);
      const data = await resp.json();
      if (data.features && data.features.length > 0) {
        map.addSource('highways', { type: 'geojson', data });
        map.addLayer({ id: 'highway-layer', type: 'line', source: 'highways',
          paint: { 'line-color': '#ff9800', 'line-width': 3, 'line-opacity': 0.8 } });
      }
    } catch (e) { console.warn('Highway layer load failed', e); }
  }
}

async function scoreAndShowPoint(lat, lon) {
  const card = el('score-card');
  card.classList.remove('hidden');
  el('score-value').textContent = '…';
  el('score-value').style.color = '#4fc3f7';
  el('score-factors').innerHTML = '';
  el('score-warnings').textContent = '';
  el('score-coords').textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;

  try {
    const resp = await fetch(`${API_BASE}/score/point`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lon, mode: currentMode }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    renderScoreCard(data);
    lastResults = { type: 'point', sites: [data], mode: currentMode };
    el('btn-export').disabled = false;
  } catch (e) {
    el('score-value').textContent = 'Error';
    el('score-factors').innerHTML = `<div style="color:#f44336;font-size:0.8rem">${e.message}</div>`;
    console.error('Score error:', e);
  }
}

function renderScoreCard(data) {
  if (data.out_of_bounds) {
    el('score-value').textContent = '—';
    el('score-value').style.color = '#9e9e9e';
    el('score-factors').innerHTML = `<div class="out-of-bounds-msg">${data.warnings?.[0] || 'Out of bounds'}</div>`;
    return;
  }

  const score = Math.round(data.score);
  el('score-value').textContent = score;
  el('score-value').style.color = scoreColor(score);

  let mlHtml = '';
  if (data.ml_active && data.rule_score != null && data.ml_score != null) {
    const ruleScore = Math.round(data.rule_score);
    const mlScore = Math.round(data.ml_score);
    mlHtml = `
      <div style="margin:8px 0 4px;padding:8px;background:rgba(27,94,32,0.25);border:1px solid #2e7d32;border-radius:6px;font-size:0.75rem">
        <div style="color:#a5d6a7;font-weight:bold;margin-bottom:5px">🤖 ML Model Active (40% blend)</div>
        <div style="display:flex;gap:8px;align-items:center">
          <div style="flex:1;text-align:center">
            <div style="color:#9e9e9e;font-size:0.68rem">Rules</div>
            <div style="font-size:1.1rem;font-weight:bold;color:${scoreColor(ruleScore)}">${ruleScore}</div>
          </div>
          <div style="color:#555;font-size:1rem">+</div>
          <div style="flex:1;text-align:center">
            <div style="color:#9e9e9e;font-size:0.68rem">ML Predict</div>
            <div style="font-size:1.1rem;font-weight:bold;color:${scoreColor(mlScore)}">${mlScore}</div>
          </div>
          <div style="color:#555;font-size:1rem">=</div>
          <div style="flex:1;text-align:center">
            <div style="color:#9e9e9e;font-size:0.68rem">Final</div>
            <div style="font-size:1.1rem;font-weight:bold;color:${scoreColor(score)}">${score}</div>
          </div>
        </div>
        <div style="margin-top:5px">
          <div style="background:rgba(255,255,255,0.08);border-radius:3px;height:5px;overflow:hidden;display:flex">
            <div style="width:60%;background:#4fc3f7;opacity:0.7" title="Rules 60%"></div>
            <div style="width:40%;background:#a5d6a7" title="ML 40%"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:0.62rem;color:#666;margin-top:2px">
            <span>Rules 60%</span><span>ML 40%</span>
          </div>
        </div>
      </div>`;
  }

  el('score-factors').innerHTML = mlHtml + (data.breakdown || []).map(f => {
    const ns = Math.round(f.normalized_score);
    const cls = scoreClass(ns);
    const name = f.factor_name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    return `
      <div class="factor-row">
        <div class="factor-row-header">
          <span class="factor-name">${name}</span>
          <span class="factor-score-num">${ns}</span>
        </div>
        <div class="factor-bar-bg">
          <div class="factor-bar-fill ${cls}" style="width:${ns}%"></div>
        </div>
      </div>`;
  }).join('');

  if (data.warnings?.length) {
    el('score-warnings').textContent = data.warnings.join(' | ');
  }
}

function renderBatchPoints(sites) {
  if (map.getLayer('batch-points')) map.removeLayer('batch-points');
  if (map.getSource('batch-points')) map.removeSource('batch-points');

  const valid = sites.filter(s => !s.out_of_bounds && s.score > 0);
  if (valid.length === 0) return;

  // Compute relative thresholds from actual score distribution
  const scores = valid.map(s => s.score).sort((a, b) => a - b);
  const p33 = scores[Math.floor(scores.length * 0.33)];
  const p66 = scores[Math.floor(scores.length * 0.66)];

  const features = valid.map(s => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [s.lon, s.lat] },
    properties: { score: s.score, lat: s.lat, lon: s.lon },
  }));

  map.addSource('batch-points', { type: 'geojson', data: { type: 'FeatureCollection', features } });
  map.addLayer({
    id: 'batch-points',
    type: 'circle',
    source: 'batch-points',
    paint: {
      'circle-radius': 7,
      'circle-color': [
        'step', ['get', 'score'],
        '#f44336', p33,
        '#ff9800', p66,
        '#4caf50'
      ],
      'circle-opacity': 0.9,
      'circle-stroke-width': 1.5,
      'circle-stroke-color': '#fff',
    },
  });

  map.on('click', 'batch-points', async (e) => {
    const props = e.features[0].properties;
    await scoreAndShowPoint(props.lat, props.lon);
  });
  map.on('mouseenter', 'batch-points', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'batch-points', () => { map.getCanvas().style.cursor = ''; });
}

function renderTop10Markers(top10) {
  if (map.getLayer('top10-circles')) map.removeLayer('top10-circles');
  if (map.getLayer('top10-labels')) map.removeLayer('top10-labels');
  if (map.getSource('top10-markers')) map.removeSource('top10-markers');

  if (!top10 || top10.length === 0) return;

  const features = top10.map((site, i) => {
    const lat = site.center_lat ?? site.lat;
    const lon = site.center_lon ?? site.lon;
    return {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [lon, lat] },
      properties: { rank: String(i + 1), score: Math.round(site.score), lat, lon },
    };
  });

  map.addSource('top10-markers', { type: 'geojson', data: { type: 'FeatureCollection', features } });

  map.addLayer({
    id: 'top10-circles',
    type: 'circle',
    source: 'top10-markers',
    paint: {
      'circle-radius': 16,
      'circle-color': '#1b5e20',
      'circle-stroke-width': 2.5,
      'circle-stroke-color': '#a5d6a7',
      'circle-opacity': 0.95,
    },
  });

  map.addLayer({
    id: 'top10-labels',
    type: 'symbol',
    source: 'top10-markers',
    layout: {
      'text-field': ['get', 'rank'],
      'text-size': 13,
      'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
      'text-allow-overlap': true,
    },
    paint: { 'text-color': '#a5d6a7' },
  });

  map.on('click', 'top10-circles', async (e) => {
    const props = e.features[0].properties;
    map.flyTo({ center: [props.lon, props.lat], zoom: 14 });
    await scoreAndShowPoint(props.lat, props.lon);
  });
  map.on('mouseenter', 'top10-circles', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'top10-circles', () => { map.getCanvas().style.cursor = ''; });
}

function renderTop10(top10) {
  const list = el('top10-list');
  list.innerHTML = '';

  const legend = document.createElement('div');
  legend.style.cssText = 'font-size:0.72rem;color:#e91e63;padding:4px 0 8px;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:6px';
  legend.innerHTML = '● Pink = existing EV stations &nbsp; ● Dark Green = top 10 picks';
  list.appendChild(legend);

  if (!top10 || top10.length === 0) {
    const empty = document.createElement('li');
    empty.style.cssText = 'color:#9e9e9e;font-size:0.8rem;padding:8px;list-style:none';
    empty.textContent = 'No results';
    list.appendChild(empty);
    return;
  }

  renderTop10Markers(top10);

  top10.forEach((site, i) => {
    const lat = site.center_lat ?? site.lat;
    const lon = site.center_lon ?? site.lon;
    const score = Math.round(site.score);
    const cls = scoreClass(score);
    const li = document.createElement('li');
    li.className = 'top10-item';
    li.innerHTML = `
      <span class="top10-rank" style="background:#1b5e20;color:#a5d6a7;border-radius:50%;width:20px;height:20px;display:inline-flex;align-items:center;justify-content:center;font-weight:bold;font-size:0.75rem">${i + 1}</span>
      <span class="top10-score ${cls}">${score}</span>
      <span class="top10-coords">${lat.toFixed(4)}, ${lon.toFixed(4)}</span>`;
    li.addEventListener('click', () => {
      map.flyTo({ center: [lon, lat], zoom: 15, duration: 600 });
      renderScoreCard({ ...site, lat, lon });
      el('score-card').classList.remove('hidden');
      el('score-coords').textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
    });
    list.appendChild(li);
  });
}

async function loadCompetitorLayer() {
  if (map.getLayer('competitors-layer')) map.removeLayer('competitors-layer');
  if (map.getSource('competitors')) map.removeSource('competitors');

  try {
    const resp = await fetch(`${API_BASE}/layers/ev-stations`);
    const data = await resp.json();
    if (!data.features || data.features.length === 0) return;

    map.addSource('competitors', { type: 'geojson', data });
    map.addLayer({
      id: 'competitors-layer',
      type: 'circle',
      source: 'competitors',
      paint: {
        'circle-radius': 9,
        'circle-color': '#e91e63',
        'circle-stroke-width': 2,
        'circle-stroke-color': '#fff',
        'circle-opacity': 0.9,
      },
    });

    map.on('mouseenter', 'competitors-layer', (e) => {
      map.getCanvas().style.cursor = 'pointer';
      const props = e.features[0].properties;
      new maplibregl.Popup({ closeButton: false, offset: 12 })
        .setLngLat(e.lngLat)
        .setHTML(`<div style="font-size:12px;color:#0f3460;padding:4px 6px">
          <b style="color:#e91e63">⚡ Competitor</b><br/>
          ${props.name || 'EV Station'}<br/>
          <span style="color:#666">${props.operator || ''}</span>
        </div>`)
        .addTo(map);
    });
    map.on('mouseleave', 'competitors-layer', () => {
      map.getCanvas().style.cursor = '';
      const popups = document.querySelectorAll('.maplibregl-popup');
      popups.forEach(p => p.remove());
    });
  } catch (e) {
    console.warn('Competitor layer load failed', e);
  }
}

async function highlightBestHighways(top10) {
  if (currentMode !== 'highway') return;
  if (map.getLayer('best-highway-glow')) map.removeLayer('best-highway-glow');
  if (map.getLayer('best-highway-line')) map.removeLayer('best-highway-line');
  if (map.getSource('best-highways')) map.removeSource('best-highways');

  try {
    const resp = await fetch(`${API_BASE}/layers/highways`);
    const data = await resp.json();
    if (!data.features || data.features.length === 0) return;

    const topLons = top10.map(s => (s.center_lon ?? s.lon));
    const topLats = top10.map(s => (s.center_lat ?? s.lat));

    const bestFeatures = data.features.filter(f => {
      const coords = f.geometry.coordinates;
      return coords.some(([lon, lat]) =>
        topLons.some((tl, i) => Math.abs(lon - tl) < 0.08 && Math.abs(lat - topLats[i]) < 0.08)
      );
    });

    const fc = bestFeatures.length > 0 ? { type: 'FeatureCollection', features: bestFeatures } : data;

    map.addSource('best-highways', { type: 'geojson', data: fc });
    map.addLayer({
      id: 'best-highway-glow', type: 'line', source: 'best-highways',
      paint: { 'line-color': '#1b5e20', 'line-width': 10, 'line-opacity': 0.25, 'line-blur': 4 },
    });
    map.addLayer({
      id: 'best-highway-line', type: 'line', source: 'best-highways',
      paint: { 'line-color': '#4caf50', 'line-width': 4, 'line-opacity': 0.9 },
    });
  } catch (e) { console.warn('Highway highlight failed', e); }
}

async function openSummaryModal() {
  if (!lastResults || !lastResults.sites) return;
  const modal = document.getElementById('summary-modal');
  const content = document.getElementById('summary-content');
  modal.classList.remove('hidden');
  content.innerHTML = '<div class="summary-loading"><div class="spinner"></div>Generating analysis report…</div>';

  try {
    const resp = await fetch(`${API_BASE}/summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sites: lastResults.sites, mode: lastResults.mode }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    content.innerHTML = renderSummaryDashboard(data);
  } catch (e) {
    content.innerHTML = `<div style="color:#f44336;padding:20px">Error: ${e.message}</div>`;
  }
}

function profitColor(rate) {
  if (rate >= 80) return '#4caf50';
  if (rate >= 65) return '#8bc34a';
  if (rate >= 50) return '#ff9800';
  if (rate >= 35) return '#ff5722';
  return '#f44336';
}

function profitBg(rate) {
  if (rate >= 80) return 'rgba(76,175,80,0.15)';
  if (rate >= 65) return 'rgba(139,195,74,0.15)';
  if (rate >= 50) return 'rgba(255,152,0,0.15)';
  return 'rgba(244,67,54,0.12)';
}

function renderSummaryDashboard(data) {
  const mode = data.mode === 'city' ? 'City EV Station' : 'Highway EV Station';
  const avgScore = data.summaries.length
    ? Math.round(data.summaries.reduce((s, x) => s + x.score, 0) / data.summaries.length)
    : 0;
  const avgProfit = data.summaries.length
    ? Math.round(data.summaries.reduce((s, x) => s + x.profitability_rate, 0) / data.summaries.length)
    : 0;

  const cards = data.summaries.map((s, i) => {
    const pc = profitColor(s.profitability_rate);
    const pb = profitBg(s.profitability_rate);
    const reasonsHtml = s.reasons.map(r => `<li class="summary-reason">✓ ${r}</li>`).join('');
    const circumference = 2 * Math.PI * 28;
    const dash = (s.profitability_rate / 100) * circumference;

    return `
    <div class="summary-card">
      <div class="summary-card-header">
        <div class="summary-rank-badge">#${s.rank}</div>
        <div class="summary-location">
          <div class="summary-area-name">${s.area_name}</div>
          <div class="summary-coords">${s.lat.toFixed(4)}, ${s.lon.toFixed(4)}</div>
        </div>
        <div class="summary-score-badge" style="background:${pb};border-color:${pc}">
          <span style="color:${pc};font-size:1.4rem;font-weight:800">${Math.round(s.score)}</span>
          <span style="color:${pc};font-size:0.65rem">/ 100</span>
        </div>
      </div>

      <div class="summary-body">
        <div class="summary-reasons-col">
          <div class="summary-section-title">Why This Location?</div>
          <ul class="summary-reasons">${reasonsHtml}</ul>
        </div>

        <div class="summary-profit-col">
          <div class="summary-section-title">Profitability</div>
          <div class="summary-profit-ring">
            <svg width="72" height="72" viewBox="0 0 72 72">
              <circle cx="36" cy="36" r="28" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="8"/>
              <circle cx="36" cy="36" r="28" fill="none" stroke="${pc}" stroke-width="8"
                stroke-dasharray="${dash} ${circumference}"
                stroke-dashoffset="${circumference / 4}"
                stroke-linecap="round"/>
              <text x="36" y="40" text-anchor="middle" fill="${pc}" font-size="13" font-weight="bold">${Math.round(s.profitability_rate)}%</text>
            </svg>
            <div class="summary-profit-label" style="color:${pc}">${s.profitability_label}</div>
          </div>
        </div>
      </div>
    </div>`;
  }).join('');

  return `
    <div class="summary-dashboard">
      <div class="summary-overview">
        <div class="summary-overview-card">
          <div class="summary-ov-label">Mode</div>
          <div class="summary-ov-value">${mode}</div>
        </div>
        <div class="summary-overview-card">
          <div class="summary-ov-label">Locations Analyzed</div>
          <div class="summary-ov-value">${data.total_analyzed}</div>
        </div>
        <div class="summary-overview-card">
          <div class="summary-ov-label">Top Picks</div>
          <div class="summary-ov-value">${data.summaries.length}</div>
        </div>
        <div class="summary-overview-card">
          <div class="summary-ov-label">Avg Score</div>
          <div class="summary-ov-value" style="color:#4caf50">${avgScore}</div>
        </div>
        <div class="summary-overview-card">
          <div class="summary-ov-label">Avg Profitability</div>
          <div class="summary-ov-value" style="color:${profitColor(avgProfit)}">${avgProfit}%</div>
        </div>
      </div>
      <div class="summary-cards-grid">${cards}</div>
    </div>`;
}

async function runBatchScore(polygon) {
  el('top10-panel').classList.remove('hidden');
  el('top10-list').innerHTML = '<li style="color:#9e9e9e;font-size:0.8rem;padding:8px">Scoring area…</li>';

  try {
    const resp = await fetch(`${API_BASE}/score/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ polygon_geojson: polygon, mode: currentMode }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    lastResults = { type: 'batch', sites: data.sites, mode: currentMode };
    renderBatchPoints(data.sites);
    renderTop10(data.top10);
    await loadCompetitorLayer();
    if (currentMode === 'highway') await highlightBestHighways(data.top10);
    el('btn-hotspots').disabled = false;
    el('btn-export').disabled = false;
    el('btn-summary').disabled = false;
  } catch (e) {
    el('top10-list').innerHTML = `<li style="color:#f44336;font-size:0.8rem;padding:8px">Error: ${e.message}</li>`;
    console.error('Batch score error:', e);
  }
}

async function runHotspots() {
  el('top10-panel').classList.remove('hidden');
  el('top10-list').innerHTML = '<li style="color:#9e9e9e;font-size:0.8rem;padding:8px">Analyzing whole city…</li>';

  if (map.getLayer('hotspot-fill')) map.removeLayer('hotspot-fill');
  if (map.getLayer('hotspot-outline')) map.removeLayer('hotspot-outline');
  if (map.getSource('hotspots')) map.removeSource('hotspots');

  try {
    const resp = await fetch(`${API_BASE}/score/hotspots/city`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: currentMode }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const data = await resp.json();

    const mappedSites = data.top10.map(c => ({
      lat: c.center_lat, lon: c.center_lon, score: c.score,
      breakdown: c.breakdown, mode: currentMode,
    }));
    lastResults = { type: 'hotspot', sites: mappedSites, mode: currentMode };

    map.addSource('hotspots', { type: 'geojson', data: data.geojson_features });

    const hScores = data.geojson_features.features.map(f => f.properties.score).sort((a,b) => a-b);
    const hp33 = hScores[Math.floor(hScores.length * 0.33)] || 40;
    const hp66 = hScores[Math.floor(hScores.length * 0.66)] || 70;

    map.addLayer({
      id: 'hotspot-fill', type: 'fill', source: 'hotspots',
      paint: {
        'fill-color': ['step', ['get', 'score'], '#f44336', hp33, '#ff9800', hp66, '#4caf50'],
        'fill-opacity': 0.55,
      },
    });
    map.addLayer({
      id: 'hotspot-outline', type: 'line', source: 'hotspots',
      paint: { 'line-color': '#ffffff', 'line-width': 0.5, 'line-opacity': 0.3 },
    });

    map.on('click', 'hotspot-fill', (e) => {
      const props = e.features[0].properties;
      if (props.center_lat && props.center_lon) {
        map.flyTo({ center: [props.center_lon, props.center_lat], zoom: 13 });
      }
    });

    renderTop10(data.top10);
    await loadCompetitorLayer();
    if (currentMode === 'highway') await highlightBestHighways(data.top10);
    el('btn-export').disabled = false;
    el('btn-summary').disabled = false;
  } catch (e) {
    el('top10-list').innerHTML = `<li style="color:#f44336;font-size:0.8rem;padding:8px">Error: ${e.message}</li>`;
    console.error('Hotspot error:', e);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  map = new maplibregl.Map({
    container: 'map',
    style: {
      version: 8,
      sources: {
        osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '© OpenStreetMap contributors' },
      },
      layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
    },
    center: [72.58, 23.03],
    zoom: 11,
  });

  fetch(`${API_BASE}/ml/status`)
    .then(r => r.json())
    .then(d => {
      if (d.available) {
        const badge = el('ml-badge');
        if (badge) {
          badge.style.display = 'inline';
          badge.title = `${d.model} | Blend: ${Math.round(d.blend_weight * 100)}% ML + ${Math.round((1 - d.blend_weight) * 100)}% Rules`;
        }
      }
    })
    .catch(() => {});

  map.on('load', () => {
    initDrawLayers();
    updateModeUI();
    loadModeLayer();
  });

  map.on('mousemove', (e) => {
    if (!drawMode || drawCoords.length === 0) return;
    updateDrawLayers([e.lngLat.lng, e.lngLat.lat]);
  });

  map.on('click', async (e) => {
    if (drawMode) {
      drawCoords.push([e.lngLat.lng, e.lngLat.lat]);
      updateDrawLayers(null);
      el('btn-draw').textContent = `✏️ ${drawCoords.length} pts — right-click or Enter to finish`;
      return;
    }
    await scoreAndShowPoint(e.lngLat.lat, e.lngLat.lng);
  });

  map.on('contextmenu', async (e) => {
    if (!drawMode || drawCoords.length < 3) return;
    e.preventDefault();
    await finishDraw();
  });

  document.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter' && drawMode && drawCoords.length >= 3) {
      await finishDraw();
    }
    if (e.key === 'Escape' && drawMode) {
      cancelDraw();
    }
  });

  el('mode-selector').addEventListener('change', () => {
    currentMode = el('mode-selector').value;
    clearResults();
    updateModeUI();
    if (map.loaded()) loadModeLayer();
  });

  el('btn-draw').addEventListener('click', () => {
    if (drawMode) {
      cancelDraw();
    } else {
      drawMode = true;
      drawCoords = [];
      el('btn-draw').classList.add('active');
      el('btn-draw').textContent = '✏️ 0 pts — click to add';
      map.getCanvas().style.cursor = 'crosshair';
      if (!map.getSource('draw-polygon')) initDrawLayers();
    }
  });

  el('btn-hotspots').addEventListener('click', async () => {
    await runHotspots();
  });

  el('btn-export').addEventListener('click', async () => {
    if (!lastResults) return;
    try {
      const resp = await fetch(`${API_BASE}/export/csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sites: lastResults.sites, mode: lastResults.mode }),
      });
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ev_sites_${lastResults.mode}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export failed', e);
    }
  });

  el('btn-clear').addEventListener('click', () => {
    clearResults();
  });

  el('btn-summary').addEventListener('click', openSummaryModal);

  document.getElementById('modal-close').addEventListener('click', () => {
    document.getElementById('summary-modal').classList.add('hidden');
  });

  document.getElementById('summary-modal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('summary-modal')) {
      document.getElementById('summary-modal').classList.add('hidden');
    }
  });
});
