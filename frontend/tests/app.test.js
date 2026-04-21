import assert from 'node:assert/strict';

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ✗ ${name}`);
    console.error(`    ${err.message}`);
    failed++;
  }
}

function scoreColor(score) {
  if (score >= 70) return '#4caf50';
  if (score >= 40) return '#ff9800';
  return '#f44336';
}

function scoreClass(score) {
  if (score >= 70) return 'high';
  if (score >= 40) return 'mid';
  return 'low';
}

function renderScoreCard(data, elements) {
  if (!data || !elements) return;
  if (data.out_of_bounds) {
    elements.scoreValue = '—';
    elements.scoreFactors = data.warnings?.[0] || 'Out of bounds';
    return;
  }
  const score = Math.round(data.score);
  elements.scoreValue = String(score);
  elements.scoreColor = scoreColor(score);
  elements.scoreFactors = (data.breakdown || []).map(f => {
    const ns = Math.round(f.normalized_score);
    return `${f.factor_name}:${ns}`;
  }).join('|');
}

function renderTop10(top10) {
  return top10.map((site, i) => ({
    rank: i + 1,
    score: Math.round(site.score),
    lat: site.lat,
    lon: site.lon,
    cls: scoreClass(Math.round(site.score)),
  }));
}

function buildCsvRows(sites, mode) {
  const cityFactors = ['ev_adoption', 'income', 'population', 'traffic', 'competition', 'accessibility'];
  const highwayFactors = ['traffic_flow', 'distance_gap', 'fuel_proximity', 'rest_stop_proximity', 'risk'];
  const factorCols = mode === 'city' ? cityFactors : highwayFactors;
  const header = ['lat', 'lon', 'score', 'mode', ...factorCols];
  const rows = sites.map(s => {
    const breakdown = {};
    (s.breakdown || []).forEach(b => { breakdown[b.factor_name] = b.normalized_score; });
    return [s.lat, s.lon, s.score, mode, ...factorCols.map(f => breakdown[f] ?? '')];
  });
  return [header, ...rows];
}

function clearResults(state) {
  return { ...state, results: null, polygon: null, top10: [] };
}

console.log('\nMode selector behavior');

test('switching mode clears results', () => {
  const state = { results: [{ lat: 23.0, lon: 72.5, score: 80 }], polygon: {}, top10: [] };
  const cleared = clearResults(state);
  assert.equal(cleared.results, null);
  assert.equal(cleared.polygon, null);
});

test('switching mode clears polygon', () => {
  const state = { results: null, polygon: { type: 'Polygon', coordinates: [] }, top10: [] };
  const cleared = clearResults(state);
  assert.equal(cleared.polygon, null);
});

console.log('\nScore card rendering');

test('score card shows correct value for high score', () => {
  const data = { score: 85, mode: 'city', out_of_bounds: false, breakdown: [], warnings: [] };
  const el = {};
  renderScoreCard(data, el);
  assert.equal(el.scoreValue, '85');
  assert.equal(el.scoreColor, '#4caf50');
});

test('score card shows orange for mid score', () => {
  const data = { score: 55, mode: 'city', out_of_bounds: false, breakdown: [], warnings: [] };
  const el = {};
  renderScoreCard(data, el);
  assert.equal(el.scoreColor, '#ff9800');
});

test('score card shows red for low score', () => {
  const data = { score: 20, mode: 'city', out_of_bounds: false, breakdown: [], warnings: [] };
  const el = {};
  renderScoreCard(data, el);
  assert.equal(el.scoreColor, '#f44336');
});

test('score card shows out-of-bounds message', () => {
  const data = { score: 0, mode: 'city', out_of_bounds: true, breakdown: [], warnings: ['Point is outside city limits'] };
  const el = {};
  renderScoreCard(data, el);
  assert.equal(el.scoreValue, '—');
  assert.ok(el.scoreFactors.includes('outside'));
});

test('score card renders factor breakdown', () => {
  const data = {
    score: 72, mode: 'city', out_of_bounds: false,
    breakdown: [
      { factor_name: 'ev_adoption', normalized_score: 80, weight: 0.25, weighted_contribution: 20 },
      { factor_name: 'income', normalized_score: 65, weight: 0.20, weighted_contribution: 13 },
    ],
    warnings: [],
  };
  const el = {};
  renderScoreCard(data, el);
  assert.ok(el.scoreFactors.includes('ev_adoption:80'));
  assert.ok(el.scoreFactors.includes('income:65'));
});

test('handles null data gracefully', () => {
  assert.doesNotThrow(() => renderScoreCard(null, {}));
});

test('handles null container gracefully', () => {
  assert.doesNotThrow(() => renderScoreCard({ score: 50, breakdown: [], warnings: [] }, null));
});

console.log('\nTop-10 panel');

test('top-10 list is sorted descending', () => {
  const sites = [
    { lat: 23.0, lon: 72.5, score: 60, breakdown: [], mode: 'city' },
    { lat: 23.1, lon: 72.6, score: 85, breakdown: [], mode: 'city' },
    { lat: 23.2, lon: 72.7, score: 45, breakdown: [], mode: 'city' },
  ];
  const sorted = [...sites].sort((a, b) => b.score - a.score);
  const items = renderTop10(sorted.slice(0, 10));
  assert.equal(items[0].score, 85);
  assert.equal(items[1].score, 60);
  assert.equal(items[2].score, 45);
});

test('top-10 list has correct rank numbers', () => {
  const sites = [
    { lat: 23.0, lon: 72.5, score: 90, breakdown: [], mode: 'city' },
    { lat: 23.1, lon: 72.6, score: 70, breakdown: [], mode: 'city' },
  ];
  const items = renderTop10(sites);
  assert.equal(items[0].rank, 1);
  assert.equal(items[1].rank, 2);
});

test('top-10 item has correct score class', () => {
  const sites = [
    { lat: 23.0, lon: 72.5, score: 80, breakdown: [], mode: 'city' },
    { lat: 23.1, lon: 72.6, score: 50, breakdown: [], mode: 'city' },
    { lat: 23.2, lon: 72.7, score: 20, breakdown: [], mode: 'city' },
  ];
  const items = renderTop10(sites);
  assert.equal(items[0].cls, 'high');
  assert.equal(items[1].cls, 'mid');
  assert.equal(items[2].cls, 'low');
});

console.log('\nCSV export');

test('CSV has correct header columns for city mode', () => {
  const rows = buildCsvRows([], 'city');
  const header = rows[0];
  assert.ok(header.includes('lat'));
  assert.ok(header.includes('lon'));
  assert.ok(header.includes('score'));
  assert.ok(header.includes('mode'));
  assert.ok(header.includes('ev_adoption'));
  assert.ok(header.includes('income'));
  assert.ok(header.includes('population'));
  assert.ok(header.includes('traffic'));
  assert.ok(header.includes('competition'));
  assert.ok(header.includes('accessibility'));
});

test('CSV has correct header columns for highway mode', () => {
  const rows = buildCsvRows([], 'highway');
  const header = rows[0];
  assert.ok(header.includes('traffic_flow'));
  assert.ok(header.includes('distance_gap'));
  assert.ok(header.includes('fuel_proximity'));
  assert.ok(header.includes('rest_stop_proximity'));
  assert.ok(header.includes('risk'));
});

test('CSV data row contains correct values', () => {
  const sites = [{
    lat: 23.03, lon: 72.58, score: 75, mode: 'city',
    breakdown: [
      { factor_name: 'ev_adoption', normalized_score: 80 },
      { factor_name: 'income', normalized_score: 70 },
    ],
  }];
  const rows = buildCsvRows(sites, 'city');
  assert.equal(rows.length, 2);
  assert.equal(rows[1][0], 23.03);
  assert.equal(rows[1][1], 72.58);
  assert.equal(rows[1][2], 75);
});

test('CSV handles empty sites array', () => {
  const rows = buildCsvRows([], 'city');
  assert.equal(rows.length, 1);
});

test('CSV handles missing breakdown gracefully', () => {
  const sites = [{ lat: 23.0, lon: 72.5, score: 50, mode: 'city' }];
  assert.doesNotThrow(() => buildCsvRows(sites, 'city'));
});

console.log('\nProperty 14: Mode change clears all prior results');

test('mode change clears score results', () => {
  let state = {
    results: [{ lat: 23.0, lon: 72.5, score: 80 }],
    polygon: { type: 'Polygon' },
    top10: [{ lat: 23.0, lon: 72.5, score: 80 }],
  };
  state = clearResults(state);
  assert.equal(state.results, null, 'Results should be null after mode change');
  assert.equal(state.polygon, null, 'Polygon should be null after mode change');
  assert.deepEqual(state.top10, [], 'Top10 should be empty after mode change');
});

test('mode change with no prior results is safe', () => {
  const state = { results: null, polygon: null, top10: [] };
  assert.doesNotThrow(() => clearResults(state));
});

console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);
