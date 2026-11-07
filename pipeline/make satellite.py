"""
Derive web/template_satellite.html from web/template.html: same model and panels,
but a full-screen tiled basemap (Esri World Imagery satellite, or a CARTO street map)
with a floating Google-Maps-style panel, area search and a base-layer switch.

Tiles load from the tile providers at view time, so this page needs internet access
and must be opened directly in a browser (or hosted, e.g. GitHub Pages). If tiles
can't load, it falls back to the drawn land shape and says so.
"""
import os, re

ROOT = os.path.join(os.path.dirname(__file__), "..")
src = open(os.path.join(ROOT, "web", "template.html")).read()


def sub(old, new, s, count=1):
    assert old in s, "missing: " + old[:80]
    return s.replace(old, new, count)


CSS_EXTRA = """
/* ---- satellite layout: full-screen map, floating panel (overrides the base layout) ---- */
.app { display: block; height: 100%; }
.mapwrap { position: fixed; inset: 0; }
.panel { position: fixed; z-index: 5; top: calc(12px + env(safe-area-inset-top, 0px)); left: calc(12px + env(safe-area-inset-left, 0px));
  bottom: calc(12px + env(safe-area-inset-bottom, 0px)); width: 408px; border: 0; border-radius: 12px;
  box-shadow: 0 2px 6px rgba(0,0,0,.25), 0 8px 24px rgba(0,0,0,.18); }
.panel.collapsed > section:not(.searchbar), .panel.collapsed > nav { display: none; }
.panel.collapsed { bottom: auto; }
.searchbar { position: sticky; top: 0; z-index: 3; background: var(--panel); flex-direction: row !important; align-items: center; gap: 8px !important; padding: 10px 12px !important; }
.searchbar input { flex: 1; min-width: 0; border: 1px solid var(--line); border-radius: 999px; padding: 10px 14px; font: 500 14px var(--f-body); background: var(--chip); color: var(--fg); }
.searchbar input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.iconbtn { flex: none; width: 38px; height: 38px; border-radius: 50%; border: 1px solid var(--line); background: var(--panel); color: var(--fg); cursor: pointer; font: 600 16px var(--f-body); }
.results { position: absolute; left: 12px; right: 12px; top: 58px; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; box-shadow: 0 6px 18px rgba(0,0,0,.18); max-height: 280px; overflow-y: auto; z-index: 4; }
.results button { display: block; width: 100%; text-align: left; background: none; border: 0; padding: 9px 14px; font: 13.5px var(--f-body); color: var(--fg); cursor: pointer; }
.results button:hover, .results button:focus-visible { background: var(--chip); }
.results small { color: var(--muted); margin-left: 6px; }
.zoom { top: auto; right: calc(12px + env(safe-area-inset-right, 0px)); bottom: calc(34px + env(safe-area-inset-bottom, 0px)); gap: 0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.3); }
.zoom button { border-radius: 0; border: 0; width: 40px; height: 40px; background: #fff; color: #333; }
.zoom button + button { border-top: 1px solid #e3e3e3; }
.basebtn { position: fixed; z-index: 4; left: calc(436px + env(safe-area-inset-left, 0px)); bottom: calc(24px + env(safe-area-inset-bottom, 0px)); width: 76px; height: 76px; border-radius: 10px; border: 2px solid #fff;
  box-shadow: 0 1px 6px rgba(0,0,0,.4); cursor: pointer; padding: 0; overflow: hidden; background: #6b7b8c center/cover; color: #fff; font: 700 12px var(--f-body); display: flex; align-items: flex-end; justify-content: center; }
.basebtn span { width: 100%; padding: 3px 0 5px; background: linear-gradient(transparent, rgba(0,0,0,.65)); }
.legend { left: calc(524px + env(safe-area-inset-left, 0px)); bottom: calc(24px + env(safe-area-inset-bottom, 0px)); box-shadow: 0 1px 6px rgba(0,0,0,.3); }
.attrib { position: fixed; z-index: 4; right: 0; bottom: 0; padding: 2px 8px calc(2px + env(safe-area-inset-bottom, 0px)); font-size: 10.5px; background: rgba(255,255,255,.8); color: #333; }
.hint { top: calc(16px + env(safe-area-inset-top, 0px)); left: calc(50% + 210px); box-shadow: 0 2px 8px rgba(0,0,0,.3); }
.banner { position: fixed; z-index: 6; top: calc(16px + env(safe-area-inset-top, 0px)); right: calc(16px + env(safe-area-inset-right, 0px)); max-width: 340px; background: var(--panel); color: var(--fg); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; font-size: 12.5px; box-shadow: 0 4px 14px rgba(0,0,0,.25); }
@media (max-width: 860px) {
  .app { grid-template-rows: none; height: 100%; }
  html, body { height: 100%; }
  .mapwrap { height: auto; }
  .panel { top: auto; left: 0; right: 0; bottom: 0; width: auto; max-height: 52%; border-radius: 14px 14px 0 0; overflow-y: auto; padding-left: max(0px, env(safe-area-inset-left, 0px)); }
  .panel.collapsed { bottom: 0; }
  .basebtn { left: calc(12px + env(safe-area-inset-left, 0px)); top: calc(12px + env(safe-area-inset-top, 0px)); bottom: auto; width: 60px; height: 60px; }
  .legend { left: calc(80px + env(safe-area-inset-left, 0px)); top: calc(12px + env(safe-area-inset-top, 0px)); bottom: auto; right: 60px; }
  .zoom { top: calc(12px + env(safe-area-inset-top, 0px)); bottom: auto; }
  .hint { left: 50%; top: auto; bottom: calc(54% + 8px); }
  .attrib { bottom: auto; top: 0; right: auto; left: 0; font-size: 9px; display: none; }
}
</style>"""

s = src
s = sub("<title>NYC Crash Risk Forecast</title>", "<title>NYC Crash Risk Map</title>", s)
s = sub("</style>", CSS_EXTRA, s)

# markup: search bar on top of the panel, base switch, attribution, fallback banner
s = sub('<aside class="panel">', '''<aside class="panel" id="panel">
    <section class="searchbar">
      <input id="search" type="search" placeholder="Search an area or subway stop" autocomplete="off" aria-label="Search an area or subway stop">
      <button class="iconbtn" id="collapse" aria-label="Collapse panel" aria-expanded="true">▾</button>
      <div class="results" id="results" hidden></div>
    </section>''', s)
s = sub('<div class="legend" id="legend"></div>', '''<div class="legend" id="legend"></div>
    <button class="basebtn" id="basebtn" aria-label="Switch to street map"><span>Map</span></button>
    <div class="attrib" id="attrib"></div>
    <div class="banner" id="banner" hidden></div>''', s)

# tiles
TILES = r'''
// ---------- tiled basemap ----------
const BASES = {
  satellite: { layers: [
      { url: (z, x, y) => `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`, max: 19 },
      { url: (z, x, y) => `https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/${z}/${y}/${x}`, max: 19, alpha: 0.55 } ],
    labels: { url: (z, x, y) => `https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/${z}/${y}/${x}`, max: 19 },
    attrib: "Imagery © Esri, Maxar, Earthstar Geographics, and the GIS User Community", dark: true },
  map: { layers: [ { url: (z, x, y) => `https://${"abcd"[(x + y) % 4]}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/${z}/${x}/${y}${DPR > 1 ? "@2x" : ""}.png`, max: 20 } ],
    labels: { url: (z, x, y) => `https://${"abcd"[(x + y) % 4]}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/${z}/${x}/${y}${DPR > 1 ? "@2x" : ""}.png`, max: 20 },
    attrib: "© OpenStreetMap contributors © CARTO", dark: false },
};
let base = "satellite";
const tileCache = new Map(); let tilesOk = 0, tilesErr = 0, renderQueued = false;
function queueRender() { if (!renderQueued) { renderQueued = true; requestAnimationFrame(() => { renderQueued = false; render(); }); } }
function getTile(layer, z, x, y) {
  const url = layer.url(z, x, y);
  let t = tileCache.get(url);
  if (!t) {
    const img = new Image(); t = { img, ok: false };
    img.onload = () => { t.ok = true; tilesOk++; queueRender(); };
    img.onerror = () => { tilesErr++; };
    img.src = url; tileCache.set(url, t);
    if (tileCache.size > 900) { const k = tileCache.keys().next().value; tileCache.delete(k); }
  }
  return t;
}
function drawTileLayer(layer) {
  const zf = Math.log2(view.scale * DPR / 256);
  const z = Math.max(1, Math.min(layer.max, Math.round(zf)));
  const N = 2 ** z, ts = view.scale / N;
  const left = view.cx - W / 2 / view.scale, top = view.cy - H / 2 / view.scale;
  const x0 = Math.floor(left * N), x1 = Math.floor((left + W / view.scale) * N), y0 = Math.max(0, Math.floor(top * N)), y1 = Math.min(N - 1, Math.floor((top + H / view.scale) * N));
  ctx.globalAlpha = layer.alpha || 1;
  for (let ty = y0; ty <= y1; ty++) for (let tx = x0; tx <= x1; tx++) {
    const X = Math.floor(sx(tx / N)), Y = Math.floor(sy(ty / N)), S = Math.ceil(ts) + 1;
    const t = getTile(layer, z, ((tx % N) + N) % N, ty);
    if (t.ok) { ctx.drawImage(t.img, X, Y, S, S); continue; }
    // while loading, stretch a loaded ancestor tile
    for (let up = 1; up <= 4 && z - up >= 1; up++) {
      const pz = z - up, k = 2 ** up, px = Math.floor(tx / k), py = Math.floor(ty / k);
      const p = tileCache.get(layer.url(pz, ((px % (N / k)) + N / k) % (N / k), py));
      if (p && p.ok) { const sz = 256 / k * (p.img.naturalWidth / 256); ctx.drawImage(p.img, (tx % k) * sz, (ty % k) * sz, sz, sz, X, Y, S, S); break; }
    }
  }
  ctx.globalAlpha = 1;
}
const tilesFailed = () => tilesOk === 0 && tilesErr > 6;
setTimeout(() => { if (tilesFailed()) { const b = $("banner"); b.hidden = false; b.innerHTML = inFrame ? "<b>Satellite tiles are blocked in this preview.</b> Download <code>satellite.html</code> and open it in Chrome, Edge or Safari. Showing the drawn map meanwhile." : "<b>Map tiles couldn't load.</b> Check the internet connection, or a content blocker. Showing the drawn map meanwhile."; } }, 5000);
'''
s = sub("// ---------- map ----------", TILES + "\n// ---------- map ----------", s)

# render: tiles instead of drawn land; cells translucent; labels on top
s = sub('''  drawLand(); if (land && land.width > 1) ctx.drawImage(land, 0, 0);
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);''', '''  if (tilesFailed()) { drawLand(); if (land && land.width > 1) ctx.drawImage(land, 0, 0); ctx.setTransform(DPR, 0, 0, DPR, 0, 0); }
  else { ctx.setTransform(DPR, 0, 0, DPR, 0, 0); BASES[base].layers.forEach(drawTileLayer); }
  $("attrib").textContent = BASES[base].attrib;''', s)
s = sub('''    ctx.globalAlpha = corridor && !corridor.has(c) ? 0.25 : (k === 0 ? 0.55 : 0.9);
    ctx.fillStyle = riskColor(k);
    const gap = (X1 - X0) > 10 ? 1 : 0;
    ctx.fillRect(X0 + gap, Y0 + gap, X1 - X0 - gap, Y1 - Y0 - gap);''', '''    if (k === 0) continue;
    const dim = corridor && !corridor.has(c);
    ctx.globalAlpha = dim ? 0.15 : (k >= 3 ? 0.6 : 0.42);
    ctx.fillStyle = riskColor(k);
    ctx.fillRect(X0, Y0, X1 - X0, Y1 - Y0);
    if (!dim && k >= 3 && X1 - X0 > 6) { ctx.globalAlpha = 0.95; ctx.strokeStyle = riskColor(k); ctx.lineWidth = 1.5; ctx.strokeRect(X0 + 0.75, Y0 + 0.75, X1 - X0 - 1.5, Y1 - Y0 - 1.5); }''', s)
s = sub('''    ctx.fillStyle = tok("--crash");
    const r = Math.max(1.6, Math.min(3.5, view.scale / 2.2e5 * 1.4));''', '''    ctx.fillStyle = "#ffffff"; ctx.strokeStyle = "#111"; ctx.lineWidth = 1.2;
    const r = Math.max(2.4, Math.min(5, view.scale / 2.2e5 * 1.6));''', s)
s = sub('''      const X = sx(crX[i]), Y = sy(crY[i]); ctx.moveTo(X + r, Y); ctx.arc(X, Y, r, 0, 6.2832);
    }
    ctx.fill();''', '''      const X = sx(crX[i]), Y = sy(crY[i]); ctx.moveTo(X + r, Y); ctx.arc(X, Y, r, 0, 6.2832);
    }
    ctx.fill(); ctx.stroke();''', s)
# street / place labels above the risk layer, before markers
s = sub('''  // rank labels for top 10''', '''  if (!tilesFailed() && BASES[base].labels) drawTileLayer(BASES[base].labels);
  // rank labels for top 10''', s)
s = sub('''      ctx.fillStyle = tok("--fg"); ctx.beginPath(); ctx.arc(X, Y, 9, 0, 6.2832); ctx.fill();
      ctx.fillStyle = tok("--panel"); ctx.fillText(String(i + 1), X, Y + 0.5);''', '''      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(X, Y, 11, 0, 6.2832); ctx.fill();
      ctx.fillStyle = riskColor(riskClass(c)); ctx.beginPath(); ctx.arc(X, Y, 9, 0, 6.2832); ctx.fill();
      ctx.fillStyle = "#fff"; ctx.fillText(String(i + 1), X, Y + 0.5);''', s)
s = sub('''    ctx.fillStyle = tok("--fg"); ctx.textAlign = i === 0 ? "right" : "left";''', '''    const sat = base === "satellite" && !tilesFailed();
    ctx.fillStyle = sat ? "#fff" : "#1b2530"; ctx.strokeStyle = sat ? "rgba(0,0,0,.7)" : "rgba(255,255,255,.9)"; ctx.lineWidth = 2.5; ctx.lineJoin = "round"; ctx.textAlign = i === 0 ? "right" : "left";
    ctx.strokeText(W < 600 ? s.name : `${s.name}: ${["dry", "light rain", "heavy rain"][r]}`, i === 0 ? X - 9 : X + 9, Y);''', s)
s = sub('const ns = Math.max(4e4, Math.min(1.2e7, view.scale * k)); k = ns / view.scale;', 'const ns = Math.max(4e4, Math.min(256 * 2 ** 18.5, view.scale * k)); k = ns / view.scale;', s)
s = sub("view.scale = Math.max(view.scale, 2.2e5 * 4); }", "view.scale = Math.max(view.scale, 256 * 2 ** 14.5); if (innerWidth > 860) view.cx -= 210 / view.scale; else view.cy += H * 0.22 / view.scale; }", s)
s = sub('''  view.scale = Math.min(W / (x1 - x0), H / (y1 - y0)) * 0.94;
  view.cx = (x0 + x1) / 2; view.cy = (y0 + y1) / 2;''', '''  const wide = W > 860, padL = wide ? 430 : 0, padB = wide ? 0 : H * 0.52;
  view.scale = Math.min((W - padL) / (x1 - x0), (H - padB) / (y1 - y0)) * 0.94;
  view.cx = (x0 + x1) / 2 - padL / 2 / view.scale; view.cy = (y0 + y1) / 2 + padB / 2 / view.scale;''', s)
s = sub('''const r = map.parentElement.getBoundingClientRect(); W = r.width; H = r.height;''', '''W = innerWidth; H = innerHeight;''', s)
s = sub('''const r = map.parentElement.getBoundingClientRect(); if (!fitted || Math.abs(r.width - W) > 1 || Math.abs(r.height - H) > 1)''', '''if (!fitted || Math.abs(innerWidth - W) > 1 || Math.abs(innerHeight - H) > 1)''', s)
# rain legend dot label
s = sub('`<span><i class="dot"></i>Real injury crash that day</span>`', '`<span><i class="dot" style="background:#fff;border:1.5px solid #111"></i>Real injury crash that day</span>`', s)
s = sub("(black dots)", "(white dots)", s)

# search, collapse, base switch
UI = r'''
// ---------- search, collapse, base switch ----------
const searchIdx = CE.stops.map(([nm, c]) => [c, nm, (nm + " " + cellBoro(c)).toLowerCase()]);
$("search").addEventListener("input", e => {
  const q = e.target.value.trim().toLowerCase(), box = $("results");
  if (q.length < 2) { box.hidden = true; return; }
  const words = q.split(/\s+/);
  const hits = searchIdx.filter(([, , t]) => words.every(w => t.includes(w))).slice(0, 8);
  box.innerHTML = hits.length ? hits.map(([c, nm]) => `<button data-c="${c}" data-n="${esc(nm)}">${esc(nm)}<small>${cellBoro(c)} · area ranked ${order.indexOf(c) + 1} of ${NC}</small></button>`).join("")
    : `<button disabled>No area matches "${esc(q)}"</button>`;
  box.hidden = false;
  box.querySelectorAll("button[data-c]").forEach(b => b.addEventListener("click", () => { box.hidden = true; $("search").value = b.dataset.n; if (st.tab !== "brief") setTab("brief"); select(+b.dataset.c, true); }));
});
$("search").addEventListener("keydown", e => { if (e.key === "Enter") { const b = $("results").querySelector("button[data-c]"); if (b) b.click(); } if (e.key === "Escape") $("results").hidden = true; });
$("collapse").addEventListener("click", () => {
  const c = $("panel").classList.toggle("collapsed");
  $("collapse").textContent = c ? "▴" : "▾"; $("collapse").setAttribute("aria-expanded", String(!c)); $("collapse").setAttribute("aria-label", c ? "Expand panel" : "Collapse panel");
});
function setBase(b) {
  base = b;
  const other = b === "satellite" ? "map" : "satellite";
  $("basebtn").querySelector("span").textContent = other === "map" ? "Map" : "Satellite";
  $("basebtn").setAttribute("aria-label", other === "map" ? "Switch to street map" : "Switch to satellite");
  $("basebtn").style.background = other === "map" ? "#e8eef3" : "#3a4a3a"; $("basebtn").style.color = other === "map" ? "#222" : "#fff";
  render();
}
$("basebtn").addEventListener("click", () => setBase(base === "satellite" ? "map" : "satellite"));
setBase("satellite");
'''
s = sub("fillSelects(); fit();", UI + "\nfillSelects(); fit();", s)
open(os.path.join(ROOT, "web", "template_satellite.html"), "w").write(s)
print("wrote web/template_satellite.html")

# =====================================================================
# Commuter routing on real roads: Google Routes (with a key) -> OSRM -> street-grid estimate
# =====================================================================
s = open(os.path.join(ROOT, "web", "template_satellite.html")).read()

s = sub('''        <button id="mode-drive" aria-pressed="true">I drive or walk</button>
        <button id="mode-bike" aria-pressed="false">I bike</button>
      </div>
      <p class="note" id="commHint">Tap your start and then your destination on the map.</p>''', '''        <button id="mode-drive" aria-pressed="true">Drive</button>
        <button id="mode-bike" aria-pressed="false">Bike</button>
        <button id="mode-walk" aria-pressed="false">Walk</button>
      </div>
      <div class="odbox">
        <label class="f">From<input id="from" type="search" placeholder="Subway stop or address" autocomplete="off"></label>
        <label class="f">To<input id="to" type="search" placeholder="Subway stop or address" autocomplete="off"></label>
        <div class="results" id="odResults" hidden></div>
      </div>
      <p class="note" id="commHint">Search a start and destination, or tap them on the map.</p>''', s)
s = sub('''    <section id="pane-method" class="method" hidden></section>''', '''    <section id="pane-method" class="method" hidden></section>
    <section class="gbox">
      <details id="gdetails">
        <summary>Google Maps <span id="gstate" class="note">· not connected</span></summary>
        <p class="note">Paste a Google Maps Platform API key with the Maps JavaScript, Routes and Geocoding APIs enabled. The map, routes and address search then come from Google. The key stays in this browser.</p>
        <div class="row"><input id="gkey" type="password" placeholder="API key" autocomplete="off" aria-label="Google Maps API key"><button class="btn" id="gconnect">Connect</button><button class="chip" id="gdisconnect" hidden>Disconnect</button></div>
        <p class="note" id="gmsg"></p>
      </details>
    </section>''', s)
s = sub("</style>", '''.odbox { position: relative; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.odbox input, .gbox input { width: 100%; min-width: 0; border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; font: 500 13.5px var(--f-body); background: var(--chip); color: var(--fg); }
.odbox .results { top: 58px; left: 0; right: 0; }
.gbox .row { flex-wrap: nowrap; } .gbox input { flex: 1; }
.gbox summary { cursor: pointer; font-weight: 600; }
.routes { display: flex; flex-direction: column; gap: 6px; }
.route { text-align: left; background: var(--panel); border: 1px solid var(--line); border-radius: 9px; padding: 10px 12px; cursor: pointer; color: var(--fg); font: 13px var(--f-body); display: grid; grid-template-columns: 1fr auto; gap: 2px 8px; }
.route[aria-pressed="true"] { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.route b { font: 600 15px var(--f-mono); }
.route .meta { color: var(--muted); font-size: 12px; grid-column: 1 / 3; }
.badge { font: 700 10.5px var(--f-body); letter-spacing: .06em; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; background: var(--chip); }
.badge.safe { background: #1f8a4c; color: #fff; } .badge.fast { background: var(--accent); color: #fff; }
.src { font-size: 11.5px; color: var(--muted); }
#gmap { position: fixed; top: 0; right: 0; bottom: 0; left: 0; z-index: 0; }
body.gm .attrib { display: none; }
body.gm .basebtn, body.gm .legend { bottom: calc(44px + env(safe-area-inset-bottom, 0px)); }
</style>''', s)

# rename the straight-line versions; the new ones below replace them
s = sub("function corridorCells() {", "function corridorCells_straight() {", s)
s = sub("function renderComm() {", "function renderComm_straight() {", s)

# draw the road route instead of the straight dashed line
s = sub('''    ctx.strokeStyle = tok("--accent"); ctx.lineWidth = 3; ctx.setLineDash([8, 6]);
    if (pts.length === 2) { ctx.beginPath(); ctx.moveTo(...pts[0]); ctx.lineTo(...pts[1]); ctx.stroke(); }
    ctx.setLineDash([]);''', '''    drawRoutes();''', s)

# transparent canvas over Google, no own tiles
s = sub('''  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = tok("--bg"); ctx.fillRect(0, 0, map.width, map.height);''',
        '''  ctx.setTransform(1, 0, 0, 1, 0, 0);
  if (useGoogle) { syncGoogle(); ctx.clearRect(0, 0, map.width, map.height); } else { ctx.fillStyle = tok("--bg"); ctx.fillRect(0, 0, map.width, map.height); }''', s)
s = sub('''  if (tilesFailed()) { drawLand(); if (land && land.width > 1) ctx.drawImage(land, 0, 0); ctx.setTransform(DPR, 0, 0, DPR, 0, 0); }''',
        '''  if (useGoogle) { ctx.setTransform(DPR, 0, 0, DPR, 0, 0); }
  else if (tilesFailed()) { drawLand(); if (land && land.width > 1) ctx.drawImage(land, 0, 0); ctx.setTransform(DPR, 0, 0, DPR, 0, 0); }''', s)
s = sub('''  if (!tilesFailed() && BASES[base].labels) drawTileLayer(BASES[base].labels);''',
        '''  if (!useGoogle && !tilesFailed() && BASES[base].labels) drawTileLayer(BASES[base].labels);''', s)
s = sub('''const tilesFailed = () => tilesOk === 0 && tilesErr > 6;''', '''let useGoogle = false, gkey = "", gmap = null;
let inFrame = false; try { inFrame = window.self !== window.top; } catch (e) { inFrame = true; }
const tilesFailed = () => !useGoogle && tilesOk === 0 && tilesErr > 6;''', s)
s = sub('''setTimeout(() => { if (tilesFailed()) {''', '''setTimeout(() => { if (tilesFailed() && !useGoogle) {''', s)
# Google raster maps only take whole zoom levels: accumulate and step
s = sub('''function zoomAt(px, py, k) {''', '''let zoomResidual = 0;
function zoomAt(px, py, k) {
  if (useGoogle) { zoomResidual += Math.log2(k); const step = Math.abs(zoomResidual) >= 0.5 ? Math.round(zoomResidual) : 0; if (!step) return; zoomResidual -= step; k = 2 ** step; }''', s)
s = sub('''function setBase(b) {
  base = b;''', '''function setBase(b) {
  base = b;
  if (gmap) gmap.setMapTypeId(b === "satellite" ? "hybrid" : "roadmap");''', s)

ROUTING = r'''
// ---------- commuter routing ----------
// Order of preference: Google Routes API (when a key is connected) -> OSRM on OpenStreetMap roads
// -> street-grid estimate using Manhattan distance along the local street grid.
const SPEED_KMH = { drive: 18, bike: 14, walk: 4.8 };
const OSRM = {
  drive: "https://router.project-osrm.org/route/v1/driving/",
  bike: "https://routing.openstreetmap.de/routed-bike/route/v1/driving/",
  walk: "https://routing.openstreetmap.de/routed-foot/route/v1/driving/",
};
const GRID_DEG = 29;   // Manhattan's avenues run about 29 degrees east of true north
st.routes = null; st.routeKey = ""; st.routeSel = 0; st.routeSrc = ""; st.routeNote = "";
const fromXY = (x, y) => [y / 110540 + 40.45, x / (111320 * Math.cos(40.7 * Math.PI / 180)) - 74.3];
const cellByKey = new Map();
for (let c = 0; c < NC; c++) { const [x, y] = toXY(CE.lat[c], CE.lng[c]); cellByKey.set(Math.floor(x / 1000) * 1000 + Math.floor(y / 1000), c); }
const cellAt = (lat, lng) => { const [x, y] = toXY(lat, lng); return cellByKey.get(Math.floor(x / 1000) * 1000 + Math.floor(y / 1000)); };

function routeCells(coords) {
  const seen = new Set(), out = [];
  for (let i = 0; i + 1 < coords.length; i++) {
    const [ax, ay] = toXY(coords[i][0], coords[i][1]), [bx, by] = toXY(coords[i + 1][0], coords[i + 1][1]);
    const n = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay) / 60));
    for (let k = 0; k <= n; k++) {
      const [la, ln] = fromXY(ax + (bx - ax) * k / n, ay + (by - ay) * k / n);
      const c = cellAt(la, ln);
      if (c != null && !seen.has(c)) { seen.add(c); out.push(c); }
    }
  }
  return out;
}

function withTimeout(p, ms) { return Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), ms))]); }

async function osrmRoutes(A, B, mode) {
  const url = `${OSRM[mode]}${A[1].toFixed(6)},${A[0].toFixed(6)};${B[1].toFixed(6)},${B[0].toFixed(6)}?alternatives=true&overview=full&geometries=geojson`;
  const r = await withTimeout(fetch(url), 7000);
  if (!r.ok) throw new Error("OSRM " + r.status);
  const j = await r.json();
  if (j.code !== "Ok" || !j.routes || !j.routes.length) throw new Error("OSRM no route");
  return j.routes.map(rt => ({ coords: rt.geometry.coordinates.map(([ln, la]) => [la, ln]), dist: rt.distance, dur: rt.duration }));
}

function decodePolyline(str) {
  const out = []; let i = 0, lat = 0, lng = 0;
  while (i < str.length) {
    for (const which of [0, 1]) {
      let b, shift = 0, result = 0;
      do { b = str.charCodeAt(i++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
      const d = (result & 1) ? ~(result >> 1) : (result >> 1);
      if (which === 0) lat += d; else lng += d;
    }
    out.push([lat / 1e5, lng / 1e5]);
  }
  return out;
}

async function googleRoutes(A, B, mode) {
  const body = {
    origin: { location: { latLng: { latitude: A[0], longitude: A[1] } } },
    destination: { location: { latLng: { latitude: B[0], longitude: B[1] } } },
    travelMode: { drive: "DRIVE", bike: "BICYCLE", walk: "WALK" }[mode],
    computeAlternativeRoutes: true,
  };
  if (mode === "drive") body.routingPreference = "TRAFFIC_AWARE";
  const r = await withTimeout(fetch("https://routes.googleapis.com/directions/v2:computeRoutes", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Goog-Api-Key": gkey, "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline" },
    body: JSON.stringify(body),
  }), 8000);
  if (!r.ok) throw new Error("Google Routes " + r.status);
  const j = await r.json();
  if (!j.routes || !j.routes.length) throw new Error("Google: no route");
  return j.routes.map(rt => ({ coords: decodePolyline(rt.polyline.encodedPolyline), dist: rt.distanceMeters, dur: parseFloat(rt.duration) }));
}

// Offline fallback: Manhattan (L1) distance along the street grid, as two L-shaped paths
// (avenue first, or street first). The grid is rotated 29 degrees in Manhattan.
function gridRoutes(A, B, mode) {
  const mid = cellAt((A[0] + B[0]) / 2, (A[1] + B[1]) / 2);
  const th = (mid != null && CE.boro[mid] === "MANHATTAN" ? GRID_DEG : 0) * Math.PI / 180;
  const av = [Math.sin(th), Math.cos(th)], stv = [Math.cos(th), -Math.sin(th)];
  const [ax, ay] = toXY(A[0], A[1]), [bx, by] = toXY(B[0], B[1]);
  const dx = bx - ax, dy = by - ay;
  const u = dx * av[0] + dy * av[1], v = dx * stv[0] + dy * stv[1];
  const dist = Math.abs(u) + Math.abs(v), dur = dist / (SPEED_KMH[mode] / 3.6);
  const k1 = fromXY(ax + u * av[0], ay + u * av[1]), k2 = fromXY(ax + v * stv[0], ay + v * stv[1]);
  return [{ coords: [A, k1, B], dist, dur, label: th ? "avenue first" : "north–south first" },
          { coords: [A, k2, B], dist, dur, label: th ? "street first" : "east–west first" }];
}

async function fetchRoutes(A, B, mode) {
  const notes = [];
  if (useGoogle && gkey) {
    try { return { routes: await googleRoutes(A, B, mode), src: "Google Maps routes", notes }; }
    catch (e) { notes.push("Google routing failed (check the Routes API is enabled for this key); used OpenStreetMap roads instead."); }
  }
  try { return { routes: await osrmRoutes(A, B, mode), src: "Real road routes from OpenStreetMap (OSRM)", notes }; }
  catch (e) { notes.push("The routing service couldn't be reached, so routes are a street-grid estimate: Manhattan distance along the grid (rotated 29° in Manhattan), at typical " + mode + " speed."); }
  return { routes: gridRoutes(A, B, mode), src: "Street-grid estimate (Manhattan distance)", notes };
}

function scoreRoutes() {
  if (!st.routes) return;
  const all = [...Array(NC).keys()].map(commScore).sort((a, b) => b - a);
  const thr = all[Math.floor(NC * 0.10)];
  st.routes.forEach(r => {
    r.cells = routeCells(r.coords);
    r.hot = r.cells.filter(c => commScore(c) >= thr);
    r.risk = r.cells.reduce((a, c) => a + commScore(c), 0);
    r.safe = false; r.fast = false;
  });
  const fast = st.routes.reduce((a, b) => (b.dur < a.dur ? b : a));
  const safe = st.routes.reduce((a, b) => (b.hot.length < a.hot.length || (b.hot.length === a.hot.length && b.risk < a.risk) ? b : a));
  // only call a route "fastest" if it is at least 30 s quicker than every other
  if (st.routes.every(r => r === fast || r.dur - fast.dur >= 30)) fast.fast = true;
  safe.safe = st.routes.length > 1 && st.routes.some(r => r.hot.length > safe.hot.length || r.risk > safe.risk);
}

const fmtDur = s => s < 3600 ? Math.max(1, Math.round(s / 60)) + " min" : Math.floor(s / 3600) + " h " + Math.round((s % 3600) / 60) + " min";
const fmtDist = m => m < 1000 ? Math.round(m) + " m" : (m / 1000).toFixed(1) + " km";

function corridorCells() { return st.routes && st.routes[st.routeSel] ? st.routes[st.routeSel].cells || [] : []; }

function renderComm() {
  const out = $("commOut");
  if (st.route[0] && !$("from").value) $("from").value = "Dropped pin";
  if (st.route[1] && !$("to").value) $("to").value = "Dropped pin";
  if (!st.route.length) { $("from").value = $("from").value === "Dropped pin" ? "" : $("from").value; $("to").value = $("to").value === "Dropped pin" ? "" : $("to").value; }
  if (st.route.length < 2) {
    out.innerHTML = ""; st.routes = null; st.routeKey = "";
    $("commHint").textContent = st.route.length ? "Now set your destination: search it, or tap the map." : "Search a start and destination, or tap them on the map.";
    return;
  }
  const key = JSON.stringify([st.route, st.mode, useGoogle]);
  if (key !== st.routeKey) {
    st.routeKey = key; st.routes = null; st.routeSel = 0;
    out.innerHTML = `<p class="note">Finding routes…</p>`;
    const [A, B] = st.route, mode = st.mode;
    fetchRoutes(A, B, mode).then(res => {
      if (st.routeKey !== key) return;
      st.routes = res.routes; st.routeSrc = res.src; st.routeNote = res.notes.join(" ");
      scoreRoutes();
      // recommend the safest route unless it costs more than 25% extra time
      const quick = st.routes.reduce((a, b) => (b.dur < a.dur ? b : a)), safe = st.routes.find(r => r.safe) || quick;
      st.routeSel = st.routes.indexOf(safe.dur <= quick.dur * 1.25 ? safe : quick);
      renderComm(); render();
    });
    return;
  }
  if (!st.routes) return;
  scoreRoutes();
  $("commHint").innerHTML = `<button class="chip" id="clearRoute">Clear route</button>`;
  $("clearRoute").addEventListener("click", () => { st.route = []; $("from").value = ""; $("to").value = ""; renderComm(); render(); $("hint").textContent = "Tap your start point"; });
  const sel = st.routes[st.routeSel], quick = st.routes.reduce((a, b) => (b.dur < a.dur ? b : a)), safe = st.routes.find(r => r.safe) || sel;
  const winLabel = WINDOWS.find(w => w[0] === st.win)[1];
  const when = winLabel === "All day" ? "today" : winLabel.toLowerCase();
  const rainNow = st.src === "fc" ? Math.max(...st.rain) : (Math.max(...M.prcp[st.rpDay]) >= 10 ? 2 : Math.max(...M.prcp[st.rpDay]) >= 1 ? 1 : 0);
  const wxWord = rainNow === 2 ? "Heavy rain expected. " : rainNow === 1 ? "Rain expected. " : "";
  const tip = { drive: "Slow down and watch for cyclists and pedestrians at intersections.", bike: "Use protected lanes where you can and watch for turning vehicles.", walk: "Cross with the signal and watch for turning vehicles." }[st.mode];
  const names = sel.hot.slice(0, 3).map(c => CE.name[c] ? CE.name[c].replace(/ \(.*\)$/, "") : cellBoro(c));
  let msg = sel.hot.length
    ? `${wxWord}Your route ${when} passes ${sel.hot.length} high-risk crash area${sel.hot.length > 1 ? "s" : ""}, near ${names.join(", ")}. ${tip}`
    : `${wxWord}Your route ${when} avoids the city's highest-risk crash areas.`;
  const other = sel === safe ? quick : safe, dt = Math.abs(other.dur - sel.dur), dh = other.hot.length - sel.hot.length;
  if (other !== sel && dh !== 0) {
    if (dt < 30) msg += dh > 0 ? ` It takes about the same time as the other route and passes ${dh} fewer.` : ` Another route takes about the same time and passes ${-dh} fewer.`;
    else if (dh > 0 && other.dur < sel.dur) msg += ` We picked it over the fastest route, which is ${fmtDur(dt)} quicker but passes ${dh} more.`;
    else if (dh < 0 && other.dur > sel.dur) msg += ` A route ${fmtDur(dt)} longer passes ${-dh} fewer.`;
  }
  out.innerHTML = `<div class="push"><span class="app-name">Safe Commute · alert preview</span><p>${esc(msg)}</p></div>
    <div class="routes">${st.routes.map((r, i) => `<button class="route" data-i="${i}" aria-pressed="${i === st.routeSel}">
      <span><b>${fmtDur(r.dur)}</b> · ${fmtDist(r.dist)}${r.label ? ` · ${r.label}` : ""}</span>
      <span>${r.safe ? '<span class="badge safe">Safest</span> ' : ""}${r.fast ? '<span class="badge fast">Fastest</span>' : ""}</span>
      <span class="meta">${r.hot.length ? `${r.hot.length} high-risk area${r.hot.length > 1 ? "s" : ""}` : "No high-risk areas"} · ${r.cells.length} areas crossed</span></button>`).join("")}</div>
    <p class="src">${esc(st.routeSrc)}.${st.routeNote ? " " + esc(st.routeNote) : ""} Risk is scored on the 1 km forecast areas each route crosses.</p>
    <h2 style="margin-top:6px">High-risk areas on this route</h2>
    <div class="list">${sel.hot.length ? sel.hot.map(c => `<button class="item" data-c="${c}"><span class="rank" style="background:${riskColor(Math.max(2, riskClass(c)))}">!</span>
        <span class="nm">${esc(cellName(c))}<small>${cellBoro(c)} · ${chance(lam[c])} chance of an injury crash${st.mode === "bike" && CE.n_cyc[c] ? ` · ${CE.n_cyc[c]} cyclist injury crashes Aug–Sep` : ""}</small></span>
        <span class="val">High<small>risk</small></span></button>`).join("") : `<div class="note">None on this route for this scenario.</div>`}</div>`;
  out.querySelectorAll(".route").forEach(b => b.addEventListener("click", () => { st.routeSel = +b.dataset.i; renderComm(); render(); }));
  out.querySelectorAll(".item").forEach(b => b.addEventListener("click", () => select(+b.dataset.c, true)));
}

function drawRoutes() {
  if (!st.routes) return;
  const order_ = st.routes.map((_, i) => i).filter(i => i !== st.routeSel).concat([st.routeSel]);
  for (const i of order_) {
    const r = st.routes[i], on = i === st.routeSel;
    ctx.beginPath();
    r.coords.forEach(([la, ln], k) => { const X = sx(mx(ln)), Y = sy(my(la)); k ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); });
    ctx.lineJoin = "round"; ctx.lineCap = "round";
    ctx.strokeStyle = on ? "#0b3d91" : "rgba(80,90,105,.85)"; ctx.lineWidth = on ? 8 : 6; ctx.stroke();
    ctx.strokeStyle = on ? "#4c8dff" : "rgba(190,200,212,.95)"; ctx.lineWidth = on ? 5 : 3.5; ctx.stroke();
  }
}

// origin / destination search: subway stops offline, addresses through Google when connected
const odIdx = CE.stops.map(([nm, c, la, ln]) => [nm, c, la, ln, (nm + " " + cellBoro(c)).toLowerCase()]);
let odField = null;
function odSearch(field) {
  odField = field;
  const q = $(field).value.trim().toLowerCase(), box = $("odResults");
  if (q.length < 2) { box.hidden = true; return; }
  const words = q.split(/\s+/);
  const hits = odIdx.filter(r => words.every(w => r[4].includes(w))).slice(0, 7);
  let html = hits.map(([nm, c, la, ln]) => `<button data-la="${la}" data-ln="${ln}" data-n="${esc(nm)}">${esc(nm)}<small>${cellBoro(c)}</small></button>`).join("");
  if (useGoogle) html += `<button data-geo="1">Search “${esc($(field).value.trim())}” with Google</button>`;
  if (!html) html = `<button disabled>No subway stop matches. Connect Google Maps to search addresses, or tap the map.</button>`;
  box.innerHTML = html; box.style.left = field === "to" ? "50%" : "0"; box.style.right = field === "to" ? "0" : "50%"; box.hidden = false;
  box.querySelectorAll("button[data-la]").forEach(b => b.addEventListener("click", () => setEnd(field, +b.dataset.la, +b.dataset.ln, b.dataset.n)));
  const g = box.querySelector("button[data-geo]"); if (g) g.addEventListener("click", () => geocode(field));
}
function setEnd(field, la, ln, label) {
  $("odResults").hidden = true; $(field).value = label;
  const i = field === "from" ? 0 : 1;
  const r = st.route.slice(0, 2); r[i] = [la, ln];
  st.route = r[0] && r[1] ? [r[0], r[1]] : (r[0] ? [r[0]] : []);
  if (!r[0] && r[1]) { st.route = []; st.pendingTo = [la, ln]; }
  if (r[0] && st.pendingTo && !r[1]) { st.route = [r[0], st.pendingTo]; st.pendingTo = null; }
  if (st.route.length === 2) { const xs = st.route.map(p => mx(p[1])), ys = st.route.map(p => my(p[0])); view.cx = (xs[0] + xs[1]) / 2; view.cy = (ys[0] + ys[1]) / 2;
    const span = Math.max(Math.abs(xs[0] - xs[1]) / (W - (W > 860 ? 460 : 40)), Math.abs(ys[0] - ys[1]) / (H * (W > 860 ? 0.8 : 0.4)));
    view.scale = Math.min(256 * 2 ** 16, 1 / Math.max(span, 1e-9)); if (W > 860) view.cx -= 210 / view.scale; else view.cy += H * 0.22 / view.scale; }
  $("hint").textContent = st.route.length === 2 ? "Tap the map to start a new route" : st.route.length ? "Now set your destination" : "Tap your start point";
  renderComm(); render();
}
function geocode(field) {
  const q = $(field).value.trim();
  if (!window.google || !google.maps.Geocoder) return;
  new google.maps.Geocoder().geocode({ address: q, bounds: { south: 40.49, west: -74.26, north: 40.92, east: -73.70 }, componentRestrictions: { country: "US" } }, (res, status) => {
    if (status !== "OK" || !res.length) { $("odResults").innerHTML = `<button disabled>Google found no match (${esc(status)}). Check the Geocoding API is enabled.</button>`; return; }
    const loc = res[0].geometry.location; setEnd(field, loc.lat(), loc.lng(), res[0].formatted_address.replace(/, USA$/, ""));
  });
}
["from", "to"].forEach(f => {
  $(f).addEventListener("input", () => odSearch(f));
  $(f).addEventListener("focus", () => odSearch(f));
  $(f).addEventListener("keydown", e => { if (e.key === "Enter") { const b = $("odResults").querySelector("button[data-la], button[data-geo]"); if (b) b.click(); } if (e.key === "Escape") $("odResults").hidden = true; });
});
["drive", "bike", "walk"].forEach(m => $("mode-" + m).addEventListener("click", () => {
  st.mode = m; ["drive", "bike", "walk"].forEach(k => $("mode-" + k).setAttribute("aria-pressed", String(k === m))); renderComm(); render();
}));

// ---------- Google Maps (optional, needs an API key) ----------
try { gkey = localStorage.getItem("gmapsKey") || ""; } catch (e) { gkey = ""; }
try { const q = new URLSearchParams(location.search).get("gkey"); if (q) gkey = q; } catch (e) {}
function gEdge() { return W > 860 ? { left: 432, bottom: 0 } : { left: 0, bottom: Math.round(H * 0.52) }; }
function syncGoogle() {
  if (!gmap) return;
  const z = Math.max(2, Math.min(21, Math.round(Math.log2(view.scale / 256))));
  view.scale = 256 * 2 ** z;
  const e = gEdge(), gx = e.left + (W - e.left) / 2, gy = (H - e.bottom) / 2;
  const wx = view.cx + (gx - W / 2) / view.scale, wy = view.cy + (gy - H / 2) / view.scale;
  const lng = wx * 360 - 180, lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * wy))) * 180 / Math.PI;
  gmap.moveCamera({ center: { lat, lng }, zoom: z });
}
function gStatus(msg, ok) {
  $("gstate").textContent = ok ? "· connected" : "· not connected"; $("gmsg").textContent = msg || "";
  $("gdisconnect").hidden = !ok; $("gconnect").hidden = !!ok;
}
function connectGoogle(key) {
  if (!key) { gStatus("Paste a key first.", false); return; }
  gStatus("Connecting…", false);
  window.gm_authFailure = () => { disconnectGoogle(); gStatus("Google rejected this key. Check it is valid, billing is on, the Maps JavaScript API is enabled, and the key allows this page's address.", false); };
  window.__gmInit = () => {
    try {
      let div = $("gmap"); if (!div) { div = document.createElement("div"); div.id = "gmap"; document.querySelector(".mapwrap").prepend(div); }
      const e = gEdge(); div.style.left = e.left + "px"; div.style.bottom = e.bottom + "px";
      gmap = new google.maps.Map(div, { center: { lat: 40.73, lng: -73.95 }, zoom: 11, disableDefaultUI: true, gestureHandling: "none", keyboardShortcuts: false, clickableIcons: false, mapTypeId: base === "satellite" ? "hybrid" : "roadmap" });
      useGoogle = true; gkey = key; document.body.classList.add("gm"); $("banner").hidden = true;
      try { localStorage.setItem("gmapsKey", key); } catch (err) {}
      gStatus("Map, routes and address search now come from Google.", true);
      st.routeKey = ""; renderComm(); render();
    } catch (err) { gStatus("Couldn't start Google Maps: " + err.message, false); }
  };
  const s = document.createElement("script");
  s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&v=weekly&callback=__gmInit`;
  s.async = true; s.onerror = () => gStatus(inFrame
    ? "Google Maps was blocked because this page is open inside a preview (for example Claude's file viewer), which doesn't allow outside scripts. Download satellite.html and open it in Chrome, Edge or Safari."
    : "Couldn't load the Google Maps script. Check the internet connection, and that no ad or script blocker is blocking maps.googleapis.com.", false);
  document.head.appendChild(s);
}
function disconnectGoogle() {
  useGoogle = false; gmap = null; const d = $("gmap"); if (d) d.remove(); document.body.classList.remove("gm");
  try { localStorage.removeItem("gmapsKey"); } catch (e) {}
  gStatus("", false); st.routeKey = ""; renderComm(); render();
}
if (location.protocol === "file:") $("gmsg").textContent = "Tip: if your key is restricted to website addresses, open this page from a local server (python -m http.server, then http://localhost:8000/satellite.html) and add http://localhost:8000/* to the key's allowed referrers. Opened as a file, the page sends no address for Google to check.";
$("gconnect").addEventListener("click", () => connectGoogle($("gkey").value.trim()));
$("gdisconnect").addEventListener("click", () => { disconnectGoogle(); location.reload(); });
if (gkey) { $("gkey").value = gkey; connectGoogle(gkey); }
'''
s = sub("\nfillSelects(); fit();", ROUTING + "\nfillSelects(); fit();", s)
open(os.path.join(ROOT, "web", "template_satellite.html"), "w").write(s)
print("added road routing + Google Maps option")

# =====================================================================
# Split into two audience-specific apps built from the combined page
# =====================================================================
combined = open(os.path.join(ROOT, "web", "template_satellite.html")).read()

# --- agency.html: briefing, replay and method; no commuter tab ---
a = combined
a = sub("<title>NYC Crash Risk Map</title>", "<title>NYC Crash Risk Briefing</title>", a)
a = sub("<h1>NYC Crash Risk Forecast</h1>", "<h1>NYC Crash Risk Briefing</h1>", a)
a = sub('''<p class="lede">Where injury crashes are most likely, given the day, the hour and the weather forecast. Built on NYPD collisions, NOAA weather and 311 DOT requests, Aug–Sep 2025.</p>''',
        '''<p class="lede">Where to put enforcement, EMS units and repair crews, given the day, the hour and the weather forecast. For NYPD, DOT and EMS planners. Built on NYPD collisions, NOAA weather and 311 DOT requests, Aug–Sep 2025.</p>''', a)
a = sub('''<button role="tab" id="tab-comm" aria-selected="false">Commuter app</button>''', '''<button role="tab" id="tab-comm" aria-selected="false" hidden>Commuter app</button>''', a)
a = sub('''<button role="tab" id="tab-brief" aria-selected="true">Agency briefing</button>''', '''<button role="tab" id="tab-brief" aria-selected="true">Briefing</button>''', a)
open(os.path.join(ROOT, "web", "template_agency.html"), "w").write(a)

# --- commuter.html: consumer route check; no agency actions or replay ---
c = combined
c = sub("<title>NYC Crash Risk Map</title>", "<title>Safe Commute NYC</title>", c)
c = sub("<h1>NYC Crash Risk Forecast</h1>", "<h1>Safe Commute NYC</h1>", c)
c = sub('''<p class="lede">Where injury crashes are most likely, given the day, the hour and the weather forecast. Built on NYPD collisions, NOAA weather and 311 DOT requests, Aug–Sep 2025.</p>''',
        '''<p class="lede">Check your route for high-risk crash areas before you leave, based on when you travel and the weather forecast.</p>''', c)
c = sub('''      <div class="seg" role="group" aria-label="Scenario source">''', '''      <div class="seg" role="group" aria-label="Scenario source" hidden>''', c)
c = sub('''<label class="f">Day<select id="dow"></select></label>''', '''<label class="f">When<select id="dow"></select></label>''', c)
c = sub('''<label class="f">&nbsp;<button class="btn" id="simulate">Simulate a forecast</button></label>''', '''<label class="f">&nbsp;<button class="btn" id="simulate">Try a random forecast</button></label>''', c)
c = sub('''<button role="tab" id="tab-brief" aria-selected="true">Agency briefing</button>''', '''<button role="tab" id="tab-brief" aria-selected="false" hidden>Agency briefing</button>''', c)
c = sub('''<button role="tab" id="tab-comm" aria-selected="false">Commuter app</button>''', '''<button role="tab" id="tab-comm" aria-selected="true">Your route</button>''', c)
c = sub('''<button role="tab" id="tab-method" aria-selected="false">Method</button>''', '''<button role="tab" id="tab-method" aria-selected="false">How it works</button>''', c)
c = sub('''<input id="search" type="search" placeholder="Search an area or subway stop"''', '''<input id="search" type="search" placeholder="Look up an area or subway stop"''', c)
# open on the route tab; clicking the map in "How it works" should not jump to the agency briefing
c = sub('''  if (st.tab === "method") setTab("brief");''', '''  if (st.tab === "method") { setTab("comm"); return; }''', c)
c = sub('''  if (st.tab !== "brief" && st.tab !== "comm") setTab("brief");''', '''  if (st.tab !== "comm") setTab("comm");''', c)
c = sub('''$("keydown", e => {''', '''$("keydown", e => {''', c) if '$("keydown"' in c else c
c = c.replace('''if (st.tab !== "brief") setTab("brief"); select(+b.dataset.c, true);''', '''select(+b.dataset.c, true);''')
c = sub('''st.rain = [2, 2, 2]; syncForm();
update();''', '''st.rain = [2, 2, 2]; syncForm();
update();
setTab("comm");''', c)
open(os.path.join(ROOT, "web", "template_commuter.html"), "w").write(c)
print("wrote web/template_agency.html and web/template_commuter.html")

# =====================================================================
# Split into two products: agency.html (briefing) and commuter.html (trip app)
# =====================================================================
full = open(os.path.join(ROOT, "web", "template_satellite.html")).read()

# --- agency briefing: no commuter tab ---
a = full
a = sub("<title>NYC Crash Risk Map</title>", "<title>NYC Crash Risk Briefing</title>", a)
a = sub("<h1>NYC Crash Risk Forecast</h1>", "<h1>NYC Crash Risk Briefing</h1>", a)
a = sub('''<p class="lede">Where injury crashes are most likely, given the day, the hour and the weather forecast.''',
        '''<p class="lede">Where to put enforcement, EMS and repair crews, given the day, the hour and the weather forecast.''', a)
a = sub('''<button role="tab" id="tab-comm" aria-selected="false">Commuter app</button>''',
        '''<button role="tab" id="tab-comm" aria-selected="false" hidden>Commuter app</button>''', a)
open(os.path.join(ROOT, "web", "template_agency.html"), "w").write(a)

# --- commuter app: trip planning first, plain weather choice, no agency views ---
c = full
c = sub("<title>NYC Crash Risk Map</title>", "<title>Safe Commute NYC</title>", c)
c = sub("<h1>NYC Crash Risk Forecast</h1>", "<h1>Safe Commute NYC</h1>", c)
c = sub('''<p class="lede">Where injury crashes are most likely, given the day, the hour and the weather forecast. Built on NYPD collisions, NOAA weather and 311 DOT requests, Aug–Sep 2025.</p>''',
        '''<p class="lede">Plan a trip and see which parts of it pass the city's highest-risk crash areas for when you travel and the weather you expect.</p>''', c)
c = sub('''<div class="seg" role="group" aria-label="Scenario source">''', '''<div class="seg" role="group" aria-label="Scenario source" hidden>''', c)
c = sub('''          <label class="f">Rain · Manhattan/Bronx<select id="rain0"></select></label>
          <label class="f">Rain · north Queens<select id="rain1"></select></label>
          <label class="f">Rain · south Queens/Bklyn<select id="rain2"></select></label>''',
        '''          <label class="f">Weather<select id="wxAll"><option value="0">Dry</option><option value="1">Light rain</option><option value="2">Heavy rain</option></select></label>
          <label class="f" hidden>Rain · Manhattan/Bronx<select id="rain0"></select></label>
          <label class="f" hidden>Rain · north Queens<select id="rain1"></select></label>
          <label class="f" hidden>Rain · south Queens/Bklyn<select id="rain2"></select></label>''', c)
c = sub('''<label class="f">&nbsp;<button class="btn" id="simulate">Simulate a forecast</button></label>''',
        '''<label class="f" hidden>&nbsp;<button class="btn" id="simulate">Simulate a forecast</button></label>''', c)
c = sub('''<button role="tab" id="tab-brief" aria-selected="true">Agency briefing</button>''',
        '''<button role="tab" id="tab-brief" aria-selected="true" hidden>Agency briefing</button>''', c)
c = sub('''<button role="tab" id="tab-comm" aria-selected="false">Commuter app</button>''',
        '''<button role="tab" id="tab-comm" aria-selected="false">Plan a trip</button>''', c)
c = sub('''<button role="tab" id="tab-method" aria-selected="false">Method</button>''',
        '''<button role="tab" id="tab-method" aria-selected="false">How it works</button>''', c)
c = sub('''st.rain = [2, 2, 2]; syncForm();
update();''', '''st.rain = [2, 2, 2]; syncForm();
$("wxAll").value = "2";
$("wxAll").addEventListener("change", e => { const v = +e.target.value; st.rain = [v, v, v]; syncForm(); update(); });
update();
setTab("comm");''', c)
c = sub('''<div class="wx" id="wxLine"></div>''', '''<div class="wx" id="wxLine" hidden></div>''', c)
# clicking a hotspot in the trip app should not jump to the agency briefing
c = sub('''  if (st.tab !== "brief" && st.tab !== "comm") setTab("brief");''', '''  if (st.tab !== "brief" && st.tab !== "comm") setTab("comm");''', c)
c = sub('''  if (st.tab === "method") setTab("brief");''', '''  if (st.tab === "method") setTab("comm");''', c)
open(os.path.join(ROOT, "web", "template_commuter.html"), "w").write(c)
print("wrote web/template_agency.html and web/template_commuter.html")