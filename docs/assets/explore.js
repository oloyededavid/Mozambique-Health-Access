/* Interactive district map for the study page. Reads data/districts.geojson (outlines) and data/district_values.json
   (district values for each facility list and mode, written by scripts/s05_web.py). No numbers are typed here.
   Uses the vendored Leaflet (docs/vendor/leaflet-1.9.4) without a tile layer, so the page makes no map requests. */
(() => {
    'use strict';
    const box = document.getElementById('explore-map');
    if (!box || !window.L) return;
    const esc = t => String(t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const STOPS = [[251, 233, 211], [246, 183, 122], [229, 119, 46], [182, 67, 14], [94, 31, 6]];
    const ramp = t => {
        const x = Math.max(0, Math.min(1, t)) * (STOPS.length - 1), i = Math.min(STOPS.length - 2, Math.floor(x)), f = x - i;
        return `rgb(${STOPS[i].map((c, k) => Math.round(c + (STOPS[i + 1][k] - c) * f)).join(',')})`;
    };
    const NONE = '#e6e4de';

    Promise.all([fetch('data/districts.geojson').then(r => r.json()), fetch('data/district_values.json').then(r => r.json())])
        .then(([geo, data]) => {
            const D = data.districts;
            const pct = v => `${Math.round(v * 100)}%`;
            const mins = v => (v == null ? 'not reached' : v >= 120 ? `${(v / 60).toFixed(1)} h` : `${Math.round(v)} min`);
            const fmt = (m, v) => (v == null ? 'n/a' : m.kind === 'share' ? pct(v) : mins(v));
            // the colour scale is fixed for each measure, so switching lists or modes compares like with like:
            // shares run 0-100%; median times run from 0 to the largest median in any list and mode
            const allMed = Object.values(data.values).flat().filter(Boolean).map(r => r[data.measures.length - 1]).filter(v => v != null);
            const medMax = Math.max(...allMed);
            const range = m => (m.kind === 'share' ? [0, 1] : [0, medMax]);
            const scen = Object.fromEntries(data.scenarios.map(s => [s.key, s]));
            let sk = data.scenarios[0].key, mode = data.modes[0].key, measure = data.measures[0], selected = null;
            const val = (i, k = sk, md = mode, m = measure) => { const r = data.values[`${k}|${md}`][i]; return r ? r[m.index] : null; };

            const map = L.map(box, { zoomSnap: 0.25, scrollWheelZoom: false, attributionControl: true, zoomControl: true });
            map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
            const layer = L.geoJSON(geo, {
                style: () => ({ color: '#ffffff', weight: 0.8, fillOpacity: 1, fillColor: NONE }),
                onEachFeature: (f, lyr) => {
                    lyr.on('click', () => select(f.properties.id));
                    lyr.on('mouseover', () => { readout.innerHTML = detail(f.properties.id); });
                    lyr.on('mouseout', () => select(selected));
                },
            }).addTo(map);
            map.attributionControl.addAttribution('Districts: <a href="https://www.geoboundaries.org/">geoBoundaries</a>');
            map.fitBounds(layer.getBounds(), { padding: [8, 8] });
            const byId = {};
            layer.eachLayer(l => {
                const id = l.feature.properties.id; byId[id] = l;
                const el = l.getElement();
                if (el) {
                    el.setAttribute('tabindex', '0'); el.setAttribute('role', 'button');
                    el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(id); } });
                    el.addEventListener('focus', () => select(id, true));
                }
            });
            addEventListener('resize', () => map.invalidateSize());

            const readout = document.getElementById('xp-readout');
            const legendBar = document.getElementById('xp-legend-bar');
            const lo = document.getElementById('xp-min'), hi = document.getElementById('xp-max'), unit = document.getElementById('xp-unit');
            const tableBox = document.getElementById('xp-table');
            const picker = document.getElementById('xp-select'), scenPick = document.getElementById('xp-scen');
            picker.append(new Option('Choose a district', ''));
            [...D].sort((a, b) => a.name.localeCompare(b.name)).forEach(d => picker.append(new Option(`${d.name} (${d.province})`, d.id)));
            picker.addEventListener('change', () => select(picker.value === '' ? null : Number(picker.value)));
            data.scenarios.forEach(s => scenPick.append(new Option(s.label, s.key)));
            scenPick.addEventListener('change', () => { sk = scenPick.value; paint(); select(selected); });

            const peers = () => (scen[sk].herams ? ['H_all', 'H_func', 'H_fully'] : ['A', 'B', 'AB']);   // shown side by side
            const detail = id => {
                const d = D[id];
                if (!d) return '';
                const head = `<b>${esc(d.name)}</b>, ${esc(d.province)}`;
                if (!d.compared) return `${head}: too few residents to compare.`;
                const v = val(id);
                if (v == null && scen[sk].herams) return `${head}: outside the HeRAMS provinces.`;
                const others = data.measures.filter(m => m !== measure).map(m => `${esc(m.label)}: ${fmt(m, val(id, sk, mode, m))}`).join(' · ');
                const across = peers().map(k => `${esc(scen[k].label)}: ${fmt(measure, val(id, k))}`).join('<br>');
                return `${head}, ${Number(d.population).toLocaleString('en-GB')} modelled residents<br>`
                    + `<span class="xp-main">${esc(measure.label)} ${fmt(measure, v)}</span><br>${others}`
                    + `<span class="xp-across">${across}</span>`;
            };
            const select = (id, keepFocus) => {
                selected = id;
                layer.eachLayer(l => {
                    const on = l.feature.properties.id === id;
                    l.setStyle({ color: on ? '#111111' : '#ffffff', weight: on ? 2.6 : 0.8 });
                    if (on && !keepFocus) l.bringToFront();   // moving the node would drop keyboard focus
                });
                picker.value = id == null ? '' : String(id);
                readout.innerHTML = id == null ? 'Select a district on the map, on the list above it, or use Tab and Enter.' : detail(id);
            };
            const paint = () => {
                const [a, b] = range(measure);
                layer.eachLayer(l => {
                    const id = l.feature.properties.id, v = val(id);
                    l.setStyle({ fillColor: v == null ? NONE : ramp((v - a) / (b - a || 1)) });
                    const el = l.getElement();
                    if (el) el.setAttribute('aria-label', `${D[id].name}: ${fmt(measure, v)}`);
                });
                lo.textContent = fmt(measure, a); hi.textContent = fmt(measure, b);
                unit.textContent = `${measure.label}, ${data.modes.find(m => m.key === mode).label.toLowerCase()}, ${scen[sk].label}. Grey: no value.`;
                legendBar.style.background = `linear-gradient(90deg, ${[0, 0.25, 0.5, 0.75, 1].map(ramp).join(',')})`;
                const keys = peers();
                const rows = D.filter(d => val(d.id) != null).sort((x, y) => (val(y.id) ?? -1) - (val(x.id) ?? -1));
                tableBox.innerHTML = `<table><thead><tr><th scope="col">District</th><th scope="col">Province</th>${keys.map(k => `<th scope="col">${esc(scen[k].label)}</th>`).join('')}</tr></thead>`
                    + `<tbody>${rows.map(d => `<tr><th scope="row">${esc(d.name)}</th><td>${esc(d.province)}</td>${keys.map(k => `<td>${fmt(measure, val(d.id, k))}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
            };
            const group = (boxId, items, current, label, onPick) => {
                const bar = document.getElementById(boxId);
                items.forEach(it => {
                    const b = document.createElement('button');
                    b.type = 'button'; b.className = 'xp-btn'; b.textContent = label(it); b.setAttribute('aria-pressed', String(it === current));
                    b.addEventListener('click', () => {
                        bar.querySelectorAll('.xp-btn').forEach(x => x.setAttribute('aria-pressed', 'false'));
                        b.setAttribute('aria-pressed', 'true'); onPick(it); paint(); select(selected);
                    });
                    bar.append(b);
                });
            };
            group('xp-modes', data.modes, data.modes[0], m => m.label, m => { mode = m.key; });
            group('xp-buttons', data.measures, measure, m => m.label, m => { measure = m; });
            paint(); select(null);
        })
        .catch(() => { box.textContent = 'The map data did not load.'; });
})();
