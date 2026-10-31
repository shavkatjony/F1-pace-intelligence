// Team DPEC pit wall: linked windows on real data from the read-only API (src/dpec/api).
// Same look and window system as web/prototype/, but every number comes from the warehouse.
// Each window type below has: key(c) = which data it needs for context c, load(c) = fetch it,
// render(i, data, c) = draw it. The shared context c is the weekend, session and two drivers.
import { get, weekendPath as wk } from "./api.js";

const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const fmtLap = s => { if (s == null) return "—"; const m = Math.floor(s / 60); return m + ":" + (s - m * 60).toFixed(3).padStart(6, "0") };
const sgn = (v, d = 3) => (v > 0 ? "+" : v < 0 ? "−" : "±") + Math.abs(v).toFixed(d);
const fmtDate = iso => iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }) : "";
const SESSION_NAMES = { FP1: "Practice 1", FP2: "Practice 2", FP3: "Practice 3", SQ: "Sprint quali", S: "Sprint", Q: "Qualifying", R: "Race" };
const PRACTICE = new Set(["FP1", "FP2", "FP3"]);

/* ================= colours: teams, tyres, lap reasons ================= */
const TEAM_COLOURS = { red_bull: "var(--blue)", ferrari: "var(--red)", mercedes: "var(--teal)", mclaren: "var(--orange)",
  aston_martin: "var(--olive)", alpine: "var(--rose)", williams: "var(--sky)", racing_bulls: "var(--plum)",
  sauber: "var(--brown)", haas: "var(--hard)", cadillac: "var(--mustard)" };
const teamColour = lineage => TEAM_COLOURS[lineage] || "var(--line-strong)";
const chip = lineage => `<span class="teamchip" style="background:${teamColour(lineage)}"></span>`;
const ours = lineage => SETTINGS && lineage === SETTINGS.adopted_lineage ? '<span class="ours">★ OURS</span>' : "";
const TYRES = { SOFT: ["S", "var(--soft)", "Soft"], MEDIUM: ["M", "var(--med)", "Medium"], HARD: ["H", "var(--hard)", "Hard"],
  INTERMEDIATE: ["I", "var(--inter)", "Intermediate"], WET: ["W", "var(--wet)", "Wet"] };
const tyreOf = c => TYRES[c] || ["?", "var(--line-strong)", c || "Unknown"];
const tyre = c => { const t = tyreOf(c); return `<span class="tyre" style="--c:${t[1]}" title="${esc(t[2])}">${t[0]}</span>` };
const REASONS = { clean: "var(--teal)", slow: "var(--mustard)", in_lap: "var(--blue)", out_lap: "var(--sky)", no_time: "var(--hard)",
  yellow: "var(--orange)", safety_car: "var(--red)", vsc: "var(--rose)", red_flag: "var(--red)", deleted: "var(--plum)",
  lap_one: "var(--brown)", wet_tyre: "var(--wet)", inaccurate: "var(--olive)" };

/* ================= state ================= */
let SETTINGS = null, WEEKENDS = [];
const DEF_CTX = { season: null, round: null, session: "Q", primary: null, compare: null, cursor: 0 };
const DEF_SET = { theme: "system", units: "kmh", density: "comfy", cb: false };
let uid = 1; const W = (type, cs, rs) => ({ id: "w" + (uid++), type, cs, rs, pinned: null });
function presets() { uid = 1; return {
  pitwall: { name: "Pit wall", hint: "3 monitors · race weekend", monitors: [
    [W("session", 5, 5), W("results", 7, 3), W("weather", 7, 2), W("quality", 12, 2)],
    [W("telemetry", 8, 3), W("trackmap", 4, 3), W("delta", 7, 2), W("corners", 5, 2)],
    [W("forecast", 12, 4), W("strategy", 6, 5), W("laps", 6, 3), W("standings", 6, 2)]] },
  performance: { name: "Performance", hint: "1 large monitor · driver vs driver", monitors: [[W("telemetry", 8, 3), W("trackmap", 4, 3), W("delta", 7, 2), W("corners", 5, 2), W("debrief", 12, 3)]] },
  strategy: { name: "Strategy", hint: "forecast, record, long runs, stints and weather", monitors: [[W("forecast", 7, 4), W("strategy", 5, 6), W("record", 7, 3), W("laps", 7, 3), W("weather", 5, 2)]] },
  laptop: { name: "Laptop", hint: "one window at a time, as tabs", tabs: true, monitors: [[W("session", 12, 5), W("forecast", 12, 5), W("record", 12, 5), W("debrief", 12, 5), W("telemetry", 12, 5), W("trackmap", 12, 5), W("laps", 12, 5), W("strategy", 12, 5), W("results", 12, 5), W("standings", 12, 5)]] } } }
let st = { ctx: { ...DEF_CTX }, set: { ...DEF_SET }, preset: "pitwall", mon: 0, tab: 0, layouts: presets() };
const KEY = "dpec-pitwall-app-v1";
try { const s = JSON.parse(localStorage.getItem(KEY) || "null"); if (s && s.layouts) { st = { ...st, ...s, ctx: { ...DEF_CTX, ...s.ctx }, set: { ...DEF_SET, ...s.set } }; uid = 1 + Math.max(0, ...Object.values(st.layouts).flatMap(p => p.monitors.flat()).map(w => +w.id.slice(1) || 0)) } } catch (e) { }
function save() { try { localStorage.setItem(KEY, JSON.stringify(st)) } catch (e) { } }

// a link like ?season=2024&round=1&session=Q&a=VER&b=LEC opens that weekend and those drivers
const params = (() => { try { return new URLSearchParams(location.search) } catch (e) { return new URLSearchParams() } })();
const wish = { season: +params.get("season") || st.ctx.season, round: +params.get("round") || st.ctx.round,
  session: params.get("session") || st.ctx.session, primary: params.get("a") || st.ctx.primary, compare: params.get("b") || st.ctx.compare };

let bc = null; try { bc = new BroadcastChannel("dpec-pitwall-app") } catch (e) { }
const inst = new Map(); // id -> {def, el, body, tb, state, w, data, dataKey}
const DATA_KEYS = ["season", "round", "session"];

function setCtx(patch, remote) {
  Object.assign(st.ctx, patch);
  if (!remote && bc) try { bc.postMessage({ ctx: st.ctx }) } catch (e) { }
  const keys = Object.keys(patch);
  if (!keys.every(k => k === "cursor")) { syncHeader(); save() }
  for (const i of inst.values()) { if (i.w.pinned) continue; if (keys.some(k => DATA_KEYS.includes(k) || i.def.deps.includes(k))) schedule(i) }
}
if (bc) bc.onmessage = e => { if (e.data && e.data.ctx) { const p = {}; for (const k in e.data.ctx) if (e.data.ctx[k] !== st.ctx[k]) p[k] = e.data.ctx[k]; if (Object.keys(p).length) setCtx(p, true) } };
const ctxOf = i => i.w.pinned || st.ctx;
const sp = v => st.set.units === "mph" ? v * .6214 : v; const spU = () => st.set.units === "mph" ? "mph" : "km/h";

// A weekend or session change must also pick a session and two drivers that exist there.
async function resolve(season, round, want) {
  const weekend = await get(`/weekends/${season}/${round}`);
  const types = weekend.sessions.map(s => s.session_type);
  const session = types.includes(want.session) ? want.session : types.includes("Q") ? "Q" : types[types.length - 1];
  const codes = (await get(`/weekends/${season}/${round}/pace?session=${session}`)).map(d => d.driver_code);
  const primary = codes.includes(want.primary) ? want.primary : codes[0] || null;
  const compare = codes.includes(want.compare) && want.compare !== primary ? want.compare : codes.find(x => x !== primary) || null;
  return { season, round, session, primary, compare };
}
const go = (season, round, want) => resolve(season, round, want).then(p => setCtx(p)).catch(e => toast(e.message));

/* ================= chart helpers ================= */
const scale = (d0, d1, r0, r1) => { const k = (r1 - r0) / ((d1 - d0) || 1); const f = v => r0 + (v - d0) * k; f.inv = p => d0 + (p - r0) / k; return f };
function nice(x) { const e = Math.pow(10, Math.floor(Math.log10(x))); const f = x / e; return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * e }
function ticks(a, b, n) { const s = nice((b - a) / n || 1); const o = []; for (let v = Math.ceil(a / s) * s; v <= b + 1e-9; v += s) o.push(+v.toFixed(6)); return o }
const pth = (xs, ys, X, Y) => { let s = ""; for (let i = 0; i < xs.length; i++) s += (i ? "L" : "M") + X(xs[i]).toFixed(1) + "," + Y(ys[i]).toFixed(1); return s };
const svg = (w, h, inner) => `<svg class="ch" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img">${inner}</svg>`;
const idxOf = (D, d) => clamp(Math.round(d / (D.distance_m[1] - D.distance_m[0] || 1)), 0, D.distance_m.length - 1);
const minmax = a => { let lo = Infinity, hi = -Infinity; for (const v of a) if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v } return [lo, hi] };
function bar(v, mx) { const p = Math.abs(v) / mx * 50; return `<div style="position:relative;height:10px;background:var(--panel2);border-radius:3px"><div style="position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:var(--line-strong)"></div><div style="position:absolute;top:0;bottom:0;${v <= 0 ? `right:50%` : `left:50%`};width:${p}%;background:${v <= 0 ? "var(--s1)" : "var(--s2)"};border-radius:2px"></div></div>` }

/* ================= window types ================= */
const DEFS = {};
const def = (type, o) => DEFS[type] = { type, deps: [], chart: false, ...o };
const paceKey = c => `${wk(c)}/pace/${c.session}`;
const cmpKey = c => `${wk(c)}/compare/${c.session}/${c.primary}/${c.compare}`;
const cmpLoad = c => get(`${wk(c)}/compare?session=${c.session}&a=${c.primary}&b=${c.compare}`);
const pickRow = (i, attr = "code") => { i.body.onclick = e => { const v = e.target.closest("[data-vs]"); if (v) { setCtx({ compare: v.dataset.vs }); return } const r = e.target.closest(`[data-${attr}]`); if (r && r.dataset[attr] !== ctxOf(i).compare) setCtx({ primary: r.dataset[attr] }) } };

def("session", { title: "Session board", mart: "mart_driver_session_pace", color: "var(--orange)", deps: ["primary", "compare"],
  key: paceKey, load: c => get(`${wk(c)}/pace?session=${c.session}`),
  render(i, D, c) {
    i.tb.innerHTML = `<span>${SESSION_NAMES[c.session]} · best clean lap per driver</span><span>Click a row to drive · <b>VS</b> to compare</span>`;
    if (!D.length) { i.body.innerHTML = `<div class="pad note">No clean laps in this session (wet, or red flags). Pick another session.</div>`; return }
    i.body.innerHTML = `<table class="tt"><thead><tr><th>P</th><th>Driver</th><th class="num">Best</th><th class="num">Gap</th><th class="num">%</th><th>Tyre</th><th class="num">Clean/all</th><th></th></tr></thead><tbody>${
      D.map(d => `<tr class="click ${d.driver_code === c.primary ? "p1" : d.driver_code === c.compare ? "p2" : ""}" data-code="${d.driver_code}">
      <td>${d.pace_rank}</td><td>${chip(d.lineage)}<span class="drv">${d.driver_code}</span>${ours(d.lineage)}</td>
      <td class="num">${fmtLap(d.best_lap_s)}</td><td class="num">${d.gap_s > 0 ? "+" + d.gap_s.toFixed(3) : "—"}</td><td class="num dim">${d.gap_to_best_pct.toFixed(2)}</td>
      <td>${tyre(d.best_compound)}</td><td class="num">${d.clean_laps}/${d.laps}</td><td><button class="vs" data-vs="${d.driver_code}" aria-label="Compare with ${d.driver_code}">VS</button></td></tr>`).join("")}</tbody></table>`;
    pickRow(i) } });

def("telemetry", { title: "Telemetry traces", mart: "car_data · distance grid", color: "var(--blue)", chart: true, deps: ["primary", "compare", "cursor"],
  key: cmpKey, load: cmpLoad,
  render(i, D, c) { const w = i.body.clientWidth, h = i.body.clientHeight; if (w < 50 || h < 50) return;
    const n = D.distance_m.length, L = D.distance_m[n - 1], k = idxOf(D, c.cursor), A = D.a, B = D.b;
    i.tb.innerHTML = `<span class="legend"><span><i style="background:var(--s1)"></i>${A.driver} lap ${A.lap} · ${fmtLap(A.lap_time_s)}</span><span><i style="background:var(--s2)"></i>${B.driver} lap ${B.lap} · ${fmtLap(B.lap_time_s)}</span></span>
      <span>@ <b style="color:var(--ink)">${Math.round(D.distance_m[k]).toLocaleString()} m</b></span>
      <span>${A.driver} ${Math.round(sp(D.speed_a[k]))} · ${B.driver} ${Math.round(sp(D.speed_b[k]))} ${spU()}</span><span>gear ${D.gear_a[k]} / ${D.gear_b[k]}</span>`;
    const [v0, v1] = minmax([...D.speed_a, ...D.speed_b]);
    const pl = 48, pr = 12, top = 20, bot = 22; const X = scale(0, L, pl, w - pr);
    const strips = [["speed", "Speed", .5, [Math.floor(v0 / 20) * 20, Math.ceil(v1 / 20) * 20]], ["throttle", "Throttle", .22, [0, 100]], ["brake", "Brake", .1, [0, 1]], ["gear", "Gear", .18, [1, 8]]];
    const avail = h - top - bot - 3 * 8; let y = top, out = "";
    D.corners.forEach(cn => { out += `<line class="corner" x1="${X(cn.distance_m)}" x2="${X(cn.distance_m)}" y1="${top - 4}" y2="${h - bot}"/><text x="${X(cn.distance_m)}" y="${top - 7}" text-anchor="middle">C${cn.corner}</text>` });
    for (const [key, lab, frac, dom] of strips) { const hh = avail * frac, Y = scale(dom[0], dom[1], y + hh, y);
      out += `<rect x="${pl}" y="${y}" width="${w - pl - pr}" height="${Math.max(0, hh)}" fill="none" class="grid"/>`;
      if (key === "speed") ticks(dom[0], dom[1], 3).forEach(t => { out += `<line class="grid" x1="${pl}" x2="${w - pr}" y1="${Y(t)}" y2="${Y(t)}"/><text x="${pl - 6}" y="${Y(t) + 4}" text-anchor="end">${Math.round(sp(t))}</text>` });
      out += `<text class="lab" x="${pl + 6}" y="${y + 13}">${lab}${key === "speed" ? " " + spU() : ""}</text>`;
      for (const [arr, col, sw] of [[D[key + "_b"], "var(--s2)", 3.4], [D[key + "_a"], "var(--s1)", 1.7]]) out += `<path d="${pth(D.distance_m, arr, X, Y)}" fill="none" stroke="${col}" stroke-width="${sw}" stroke-linejoin="round" opacity="${sw > 3 ? .75 : 1}"/>`;
      y += hh + 8 }
    ticks(0, L, 6).forEach(t => out += `<text x="${X(t)}" y="${h - 6}" text-anchor="middle">${t / 1000}k</text>`);
    out += `<line class="cursor" x1="${X(D.distance_m[k])}" x2="${X(D.distance_m[k])}" y1="${top}" y2="${h - bot}"/>`;
    i.body.innerHTML = svg(w, h, out); i.X = X; i.L = L },
  move(i, x) { if (i.X) setCtx({ cursor: clamp(i.X.inv(x), 0, i.L) }) } });

def("trackmap", { title: "Track map", mart: "pos_data", color: "var(--teal)", chart: true, deps: ["primary", "compare", "cursor"],
  key: cmpKey, load: cmpLoad,
  render(i, D, c) { const w = i.body.clientWidth, h = i.body.clientHeight; if (w < 50 || h < 50) return;
    const mode = i.state.mode || "speed", A = D.a.driver, B = D.b.driver, n = D.x.length;
    i.tb.innerHTML = `<div class="seg" data-seg="mode">${["speed", "delta"].map(m => `<button aria-pressed="${m === mode}" data-v="${m}">${m === "speed" ? "Speed" : "Who's faster"}</button>`).join("")}</div>
      <span class="legend">${mode === "speed" ? `<span><i style="background:var(--blue)"></i>slow</span><span><i style="background:var(--teal)"></i></span><span><i style="background:var(--olive)"></i></span><span><i style="background:var(--mustard)"></i></span><span><i style="background:var(--orange)"></i>fast (${A})</span>` : `<span><i style="background:var(--s1)"></i>${A} faster</span><span><i style="background:var(--s2)"></i>${B} faster</span>`}</span>`;
    const [x0, x1] = minmax(D.x), [y0, y1] = minmax(D.y), ar = (x1 - x0) / ((y1 - y0) || 1);
    const pad = 26; let pw = w - 2 * pad, ph = h - 2 * pad; if (pw / ph > ar) pw = ph * ar; else ph = pw / ar; const ox = (w - pw) / 2, oy = (h - ph) / 2;
    const P = k => [ox + (D.x[k] - x0) / ((x1 - x0) || 1) * pw, oy + (1 - (D.y[k] - y0) / ((y1 - y0) || 1)) * ph];
    const cols = ["var(--blue)", "var(--teal)", "var(--olive)", "var(--mustard)", "var(--orange)"]; const [v0, v1] = minmax(D.speed_a);
    let base = `M${P(0)}`; for (let k = 1; k < n; k++) base += `L${P(k)}`;
    let out = `<path d="${base}" fill="none" stroke="var(--ink)" stroke-width="12" stroke-linejoin="round" opacity=".85"/>`;
    for (let k = 0; k < n - 1; k++) { const col = mode === "speed" ? cols[clamp(Math.floor((D.speed_a[k] - v0) / ((v1 - v0) / 5 || 1)), 0, 4)] : D.a_behind_s[k + 1] - D.a_behind_s[k] <= 0 ? "var(--s1)" : "var(--s2)";
      out += `<line x1="${P(k)[0]}" y1="${P(k)[1]}" x2="${P(k + 1)[0]}" y2="${P(k + 1)[1]}" stroke="${col}" stroke-width="7" stroke-linecap="round"/>` }
    const cx = ox + pw / 2, cy = oy + ph / 2;
    D.corners.forEach(cn => { const [x, y] = P(idxOf(D, cn.distance_m)); const dx = x - cx, dy = y - cy, l = Math.hypot(dx, dy) || 1;
      out += `<text x="${x + dx / l * 17}" y="${y + dy / l * 17 + 4}" text-anchor="middle" class="val">${cn.corner}</text>` });
    const [sx, sy] = P(0); out += `<rect x="${sx - 9}" y="${sy - 2}" width="18" height="4" fill="var(--paper)" stroke="var(--ink)"/>`;
    const [kx, ky] = P(idxOf(D, c.cursor)); out += `<circle cx="${kx}" cy="${ky}" r="9" fill="var(--paper)" stroke="var(--ink)" stroke-width="2"/><circle cx="${kx}" cy="${ky}" r="4.5" fill="var(--s1)"/>`;
    i.body.innerHTML = svg(w, h, out); i.P = P; i.n = n },
  move(i, x, y) { if (!i.P || !i.data) return; let b = 0, bd = 1e9; for (let k = 0; k < i.n; k++) { const p = i.P(k), d = (p[0] - x) ** 2 + (p[1] - y) ** 2; if (d < bd) { bd = d; b = k } } if (bd < 1600) setCtx({ cursor: i.data.distance_m[b] }) },
  seg(i, k, v) { i.state.mode = v; schedule(i) } });

def("delta", { title: "Lap delta", mart: "distance grid", color: "var(--plum)", chart: true, deps: ["primary", "compare", "cursor"],
  key: cmpKey, load: cmpLoad,
  render(i, D, c) { const w = i.body.clientWidth, h = i.body.clientHeight; if (w < 50 || h < 50) return;
    const dl = D.a_behind_s, n = dl.length, k = idxOf(D, c.cursor), A = D.a.driver, B = D.b.driver, L = D.distance_m[n - 1];
    i.tb.innerHTML = `<span>${A} vs ${B} · above 0 = ${A} behind</span><span>@ ${Math.round(D.distance_m[k]).toLocaleString()} m: <b style="color:var(--ink)">${sgn(dl[k])} s</b></span><span>at the line: <b style="color:var(--ink)">${sgn(dl[n - 1])} s</b></span>`;
    const pl = 48, pr = 12, top = 12, bot = 22; const m = Math.max(.15, ...dl.map(Math.abs)) * 1.15; const X = scale(0, L, pl, w - pr), Y = scale(-m, m, h - bot, top);
    let out = ""; ticks(-m, m, 4).forEach(t => out += `<line class="grid" x1="${pl}" x2="${w - pr}" y1="${Y(t)}" y2="${Y(t)}"/><text x="${pl - 6}" y="${Y(t) + 4}" text-anchor="end">${t.toFixed(2)}</text>`);
    const line = pth(D.distance_m, dl, X, Y);
    out += `<clipPath id="cu${i.w.id}"><rect x="0" y="0" width="${w}" height="${Y(0)}"/></clipPath><clipPath id="cd${i.w.id}"><rect x="0" y="${Y(0)}" width="${w}" height="${h}"/></clipPath>`;
    const area = line + `L${X(L)},${Y(0)}L${X(0)},${Y(0)}Z`;
    out += `<path d="${area}" fill="var(--s2)" opacity=".28" clip-path="url(#cu${i.w.id})"/><path d="${area}" fill="var(--s1)" opacity=".28" clip-path="url(#cd${i.w.id})"/>`;
    out += `<line class="axis" x1="${pl}" x2="${w - pr}" y1="${Y(0)}" y2="${Y(0)}"/><path d="${line}" fill="none" stroke="var(--ink)" stroke-width="1.8"/>`;
    D.corners.forEach(cn => out += `<text x="${X(cn.distance_m)}" y="${h - 6}" text-anchor="middle">C${cn.corner}</text>`);
    out += `<line class="cursor" x1="${X(D.distance_m[k])}" x2="${X(D.distance_m[k])}" y1="${top}" y2="${h - bot}"/><circle cx="${X(D.distance_m[k])}" cy="${Y(dl[k])}" r="4" fill="var(--s1)" stroke="var(--ink)"/>`;
    i.body.innerHTML = svg(w, h, out); i.X = X; i.L = L },
  move(i, x) { if (i.X) setCtx({ cursor: clamp(i.X.inv(x), 0, i.L) }) } });

def("corners", { title: "Corner table", mart: "distance grid · apexes", color: "var(--olive)", deps: ["primary", "compare", "cursor"],
  key: cmpKey, load: cmpLoad,
  render(i, D, c) { const A = D.a.driver, B = D.b.driver;
    let near = -1, nd = 1e9; D.corners.forEach((cn, j) => { const d = Math.abs(cn.distance_m - c.cursor); if (d < nd) { nd = d; near = j } });
    i.tb.innerHTML = `<span>Corner = slowest point within 150 m, below 250 km/h (C1 = first after the line). Δ time = ${A} vs ${B}, ±150 m</span>`;
    const mx = Math.max(.01, ...D.corners.map(r => Math.abs(r.a_loses_s)));
    i.body.innerHTML = `<table class="tt"><thead><tr><th>Corner</th><th class="num">Apex</th><th class="num">${A}</th><th class="num">${B}</th><th class="num">Δ min</th><th class="num">Δ time</th><th style="width:28%"></th></tr></thead><tbody>${D.corners.map((r, j) => { const dv = sp(r.min_speed_a_kph) - sp(r.min_speed_b_kph);
      return `<tr class="click ${j === near && nd < 200 ? "hl" : ""}" data-d="${r.distance_m}"><td>C${r.corner}</td><td class="num dim">${Math.round(r.distance_m)} m</td><td class="num">${sp(r.min_speed_a_kph).toFixed(0)}</td><td class="num">${sp(r.min_speed_b_kph).toFixed(0)}</td>
      <td class="num ${dv >= 0 ? "pos" : "neg"}">${sgn(dv, 1)}</td><td class="num ${r.a_loses_s <= 0 ? "pos" : "neg"}">${sgn(r.a_loses_s)}</td><td>${bar(r.a_loses_s, mx)}</td></tr>` }).join("")}</tbody></table>`;
    i.body.onclick = e => { const r = e.target.closest("tr[data-d]"); if (r) setCtx({ cursor: +r.dataset.d }) } } });

def("laps", { title: "Laps & long runs", mart: "core_laps · mart_long_runs", color: "var(--mustard)", chart: true, deps: ["primary", "compare"],
  key: c => `${wk(c)}/laps/${c.session}/${c.primary}/${c.compare}`,
  async load(c) { const lp = d => get(`${wk(c)}/laps?session=${c.session}&driver=${d}`);
    const [a, b] = await Promise.all([lp(c.primary), lp(c.compare)]);
    return { a, b, runs: PRACTICE.has(c.session) ? await get(`${wk(c)}/long-runs?session=${c.session}`) : [] } },
  render(i, D, c) { const w = i.body.clientWidth, h = i.body.clientHeight; if (w < 50 || h < 50) return;
    const fuel = SETTINGS.fuel_effect_s_per_lap, practice = PRACTICE.has(c.session);
    const drivers = [[c.primary, D.a, "var(--s1)"], [c.compare, D.b, "var(--s2)"]];
    const series = []; // {code, col, pts:[[x,y]], run}
    for (const [code, laps, col] of drivers) {
      if (practice) { const byStint = {}; laps.filter(l => l.in_long_run).forEach(l => (byStint[l.stint] ||= []).push(l));
        for (const [stint, ls] of Object.entries(byStint)) { const first = Math.min(...ls.map(l => l.lap_number));
          const run = D.runs.find(r => r.driver_code === code && r.stint === +stint);
          series.push({ code, col, run, pts: ls.map(l => [l.tyre_age_laps, l.lap_time_s + fuel * (l.lap_number - first)]) }) } }
      else { const byStint = {}; laps.filter(l => l.is_clean).forEach(l => (byStint[l.stint] ||= []).push(l));
        for (const ls of Object.values(byStint)) series.push({ code, col, compound: ls[0].compound, pts: ls.map(l => [l.lap_number, l.lap_time_s]) }) } }
    i.tb.innerHTML = practice
      ? `<span>${c.session} long runs · fuel-corrected (${fuel} s per lap of fuel)</span>${series.map(s => s.run ? `<span class="chip" style="--c:${s.col}">${s.code} ${tyre(s.run.compound)} ${s.run.run_laps} laps · ${fmtLap(s.run.run_median_s)} · deg ${sgn(s.run.deg_s_per_lap)} s/lap</span>` : "").join("")}`
      : `<span>${SESSION_NAMES[c.session]} · clean laps only, one line per stint</span><span class="legend"><span><i style="background:var(--s1)"></i>${c.primary}</span><span><i style="background:var(--s2)"></i>${c.compare}</span></span>`;
    const all = series.flatMap(s => s.pts);
    if (!all.length) { i.body.innerHTML = `<div class="pad note">${practice ? `No long runs for ${c.primary} or ${c.compare} in ${c.session}. Long runs are 5+ steady clean laps on one set; try FP2.` : `No clean laps for ${c.primary} or ${c.compare} in this session.`}</div>`; return }
    const [x0, x1] = minmax(all.map(p => p[0])), [ya, yb] = minmax(all.map(p => p[1])), y0 = ya - .3, y1 = yb + .3;
    const pl = 56, pr = 14, top = 14, bot = 26; const X = scale(x0 - .5, x1 + .5, pl, w - pr), Y = scale(y0, y1, h - bot, top); let out = "";
    ticks(y0, y1, 4).forEach(t => out += `<line class="grid" x1="${pl}" x2="${w - pr}" y1="${Y(t)}" y2="${Y(t)}"/><text x="${pl - 6}" y="${Y(t) + 4}" text-anchor="end">${fmtLap(t).slice(0, -2)}</text>`);
    ticks(x0, x1, 6).filter(t => Number.isInteger(t)).forEach(t => out += `<text x="${X(t)}" y="${h - 8}" text-anchor="middle">${practice ? "age " : "L"}${t}</text>`);
    out += `<clipPath id="cl${i.w.id}"><rect x="${pl}" y="${top}" width="${w - pl - pr}" height="${h - top - bot}"/></clipPath><g clip-path="url(#cl${i.w.id})">`;
    for (const s of series) {
      if (s.run) { const mx = s.pts.reduce((a, p) => a + p[0], 0) / s.pts.length, my = s.pts.reduce((a, p) => a + p[1], 0) / s.pts.length, f = x => my + s.run.deg_s_per_lap * (x - mx);
        const xa = Math.min(...s.pts.map(p => p[0])), xb = Math.max(...s.pts.map(p => p[0]));
        out += `<line x1="${X(xa)}" y1="${Y(f(xa))}" x2="${X(xb)}" y2="${Y(f(xb))}" stroke="${s.col}" stroke-width="2"/>` }
      else out += `<path d="${pth(s.pts.map(p => p[0]), s.pts.map(p => p[1]), X, Y)}" fill="none" stroke="${s.col}" stroke-width="1.4" opacity=".7"/>`;
      const ring = tyreOf(s.run ? s.run.compound : s.compound)[1];
      s.pts.forEach(p => out += `<circle cx="${X(p[0])}" cy="${Y(p[1])}" r="3.6" fill="${s.col}" stroke="${ring}" stroke-width="1.6"/>`) }
    i.body.innerHTML = svg(w, h, out + "</g>") } });

def("strategy", { title: "Tyre strategy", mart: "mart_stints", color: "var(--red)", chart: true, deps: ["primary", "compare"],
  key: c => `${wk(c)}/stints/${c.session === "S" ? "S" : "R"}`, load: c => get(`${wk(c)}/stints?session=${c.session === "S" ? "S" : "R"}`),
  render(i, D, c) { const w = i.body.clientWidth, h = i.body.clientHeight; if (w < 50 || h < 50) return;
    const sess = c.session === "S" ? "Sprint" : "Race"; const order = [], by = {};
    D.forEach(s => { if (!by[s.driver_code]) { by[s.driver_code] = []; order.push(s.driver_code) } by[s.driver_code].push(s) });
    i.tb.innerHTML = `<span>${sess} · one bar per set of tyres, in finishing order</span><span class="legend">${["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"].filter(k => D.some(s => s.compound === k)).map(k => `<span><i style="background:${tyreOf(k)[1]}"></i>${tyreOf(k)[2]}</span>`).join("")}</span>`;
    if (!order.length) { i.body.innerHTML = `<div class="pad note">No ${sess.toLowerCase()} stints for this weekend.</div>`; return }
    const laps = Math.max(...D.map(s => s.last_lap)); const pl = 74, pr = 12, top = 6, bot = 22, rh = (h - top - bot) / order.length;
    const X = scale(0, laps, pl, w - pr); let out = "";
    ticks(0, laps, 5).forEach(t => out += `<line class="grid" x1="${X(t)}" x2="${X(t)}" y1="${top}" y2="${h - bot}"/><text x="${X(t)}" y="${h - 6}" text-anchor="middle">L${t}</text>`);
    order.forEach((code, r) => { const y = top + r * rh, first = by[code][0], mark = code === c.primary ? "var(--s1)" : code === c.compare ? "var(--s2)" : null;
      out += `<g data-code="${code}" style="cursor:pointer">${mark ? `<rect x="0" y="${y + 1}" width="4" height="${rh - 2}" fill="${mark}"/>` : ""}<rect x="6" y="${y + rh * .25}" width="4" height="${rh * .5}" fill="${teamColour(first.lineage)}"/>
        <text x="14" y="${y + rh / 2 + 4}" class="${mark ? "val" : ""}">${first.finish_position ?? "–"} ${code}</text>`;
      by[code].forEach(s => { const x = X(s.first_lap - 1), bw = Math.max(1, X(s.last_lap) - x - 1), t = tyreOf(s.compound);
        out += `<rect x="${x}" y="${y + rh * .15}" width="${bw}" height="${rh * .7}" rx="2" fill="${t[1]}" opacity=".85"><title>${code} ${t[2]}, laps ${s.first_lap}–${s.last_lap}${s.fresh_at_start ? " (new set)" : ` (used, ${s.tyre_age_start} laps old)`}${s.deg_s_per_lap != null ? `, deg ${sgn(s.deg_s_per_lap)} s/lap` : ""}</title></rect>`;
        if (bw > 16 && rh > 11) out += `<text x="${x + bw / 2}" y="${y + rh / 2 + 4}" text-anchor="middle" style="fill:var(--ink);font-weight:700">${t[0]}</text>` });
      out += `</g>` });
    i.body.innerHTML = svg(w, h, out); pickRow(i) } });

def("weather", { title: "Weather & track", mart: "mart_session_weather · mart_track_evolution", color: "var(--sky)", chart: true, deps: [],
  key: c => `${wk(c)}/weather`, load: c => get(`${wk(c)}/weather`),
  render(i, D, c) { const w = i.body.clientWidth, h = i.body.clientHeight; if (w < 50 || h < 50) return;
    const cur = D.find(s => s.session_type === c.session) || D[D.length - 1];
    i.tb.innerHTML = cur && cur.track_temp_c != null ? `<span class="chips"><span class="chip" style="--c:var(--orange)">Track ${cur.track_temp_c.toFixed(1)}°C</span><span class="chip" style="--c:var(--sky)">Air ${cur.air_temp_c.toFixed(1)}°C</span><span class="chip" style="--c:var(--teal)">Wind ${cur.wind_speed_ms.toFixed(1)} m/s</span><span class="chip" style="--c:var(--blue)">Rain ${Math.round(100 * cur.rain_share)}% of samples</span>${cur.evo_s_per_10min != null ? `<span class="chip" style="--c:var(--olive)">Track evolution ${sgn(cur.evo_s_per_10min)} s / 10 min${cur.evo_is_reliable ? "" : " (unreliable)"}</span>` : ""}</span>` : `<span>No weather data</span>`;
    const temps = D.flatMap(s => [s.air_temp_c, s.track_temp_min_c, s.track_temp_max_c]).filter(v => v != null);
    if (!temps.length) { i.body.innerHTML = `<div class="pad note">No weather samples for this weekend.</div>`; return }
    const lo = Math.floor(Math.min(...temps) / 5) * 5 - 2, hi = Math.ceil(Math.max(...temps) / 5) * 5 + 2;
    const pl = 36, pr = 12, top = 12, bot = 36; const cw = (w - pl - pr) / D.length; const Y = scale(lo, hi, h - bot, top); let out = "";
    ticks(lo, hi, 4).forEach(t => out += `<line class="grid" x1="${pl}" x2="${w - pr}" y1="${Y(t)}" y2="${Y(t)}"/><text x="${pl - 6}" y="${Y(t) + 4}" text-anchor="end">${t}°</text>`);
    D.forEach((s, k) => { const x = pl + cw * (k + .5), on = s.session_type === c.session;
      if (s.track_temp_c != null) { out += `<rect x="${x - 7}" y="${Y(s.track_temp_max_c)}" width="14" height="${Math.max(2, Y(s.track_temp_min_c) - Y(s.track_temp_max_c))}" rx="3" fill="var(--orange)" opacity="${on ? .9 : .45}"/><circle cx="${x}" cy="${Y(s.track_temp_c)}" r="4" fill="var(--panel)" stroke="var(--orange)" stroke-width="2"/>`;
        out += `<line x1="${x - 13}" x2="${x + 13}" y1="${Y(s.air_temp_c)}" y2="${Y(s.air_temp_c)}" stroke="var(--sky)" stroke-width="3"/>`;
        if (s.had_rain) out += `<text x="${x + 16}" y="${Y(s.track_temp_c) + 4}" style="fill:var(--blue);font-weight:700">rain</text>` }
      out += `<text x="${x}" y="${h - 20}" text-anchor="middle" class="${on ? "val" : ""}">${s.session_type}</text><text x="${x}" y="${h - 6}" text-anchor="middle">${s.evo_s_per_10min != null && s.evo_is_reliable ? sgn(s.evo_s_per_10min, 2) : ""}</text>` });
    out += `<text class="lab" x="${pl + 4}" y="${top + 10}">track min–max (bar) · air (line) · bottom: track evolution, s/10 min</text>`;
    i.body.innerHTML = svg(w, h, out) } });

def("quality", { title: "Data quality", mart: "core_laps · core_files", color: "var(--teal)", deps: [],
  key: c => `${wk(c)}/quality`, load: c => get(`${wk(c)}/quality`),
  render(i, D, c) { const sessions = [...new Set(D.lap_reasons.map(r => r.session_type))].sort((a, b) => ["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"].indexOf(a) - ["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"].indexOf(b));
    const empty = D.files.filter(f => f.is_empty);
    i.tb.innerHTML = `<span>Why laps are not "clean" (clean laps are the only ones used for pace)</span><span>${D.files.length} saved tables · ${empty.length ? `<b class="neg">${empty.length} empty: ${empty.map(f => f.session_type + " " + f.table_name).join(", ")}</b>` : "none empty"}</span>`;
    const used = [...new Set(D.lap_reasons.map(r => r.lap_reason))];
    i.body.innerHTML = `<div class="pad" style="display:grid;gap:4px;padding-block:8px">${sessions.map(s => { const rs = D.lap_reasons.filter(r => r.session_type === s), tot = rs.reduce((a, r) => a + r.laps, 0), clean = (rs.find(r => r.lap_reason === "clean") || { laps: 0 }).laps;
      return `<div style="display:grid;grid-template-columns:34px 1fr 82px;gap:8px;align-items:center" title="${s}: ${clean} clean of ${tot} laps"><b class="${s === c.session ? "" : "note"}">${s}</b><div style="display:flex;height:12px;border-radius:3px;overflow:hidden;border:1px solid var(--line-strong)">${rs.map(r => `<div title="${r.lap_reason}: ${r.laps} laps" style="width:${100 * r.laps / tot}%;background:${REASONS[r.lap_reason] || "var(--line)"}"></div>`).join("")}</div><span class="note" style="white-space:nowrap">${Math.round(100 * clean / tot)}% clean</span></div>` }).join("")}
      <div class="legend note">${used.map(r => `<span><i style="background:${REASONS[r] || "var(--line)"}"></i>${r.replace("_", " ")}</span>`).join("")}</div>
      <div class="note">Fuel, setup, ERS and aero state are not in the public data, so no window shows them as measured.</div></div>` } });

def("standings", { title: "Standings", mart: "mart_standings", color: "var(--olive)", deps: ["primary", "compare"],
  key: c => `/standings/${c.season}/${c.round}`, load: c => get(`/standings/${c.season}/${c.round}`),
  render(i, D, c) { const lead = D.drivers[0];
    i.tb.innerHTML = `<span>After round ${c.round} of ${c.season}</span>${lead ? `<span>Leader ${lead.driver_code}, ${lead.total_points} pts</span>` : ""}`;
    i.body.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:4px 14px"><table class="tt"><thead><tr><th>P</th><th>Driver</th><th class="num">Pts</th><th class="num">Wins</th></tr></thead><tbody>${
      D.drivers.slice(0, 10).map(d => `<tr class="click ${d.driver_code === c.primary ? "p1" : d.driver_code === c.compare ? "p2" : ""}" data-code="${d.driver_code}"><td>${d.championship_position}</td><td>${chip(d.lineage)}<span class="drv">${d.driver_code}</span>${ours(d.lineage)}</td><td class="num">${d.total_points}</td><td class="num">${d.total_wins}</td></tr>`).join("")}</tbody></table>
      <table class="tt"><thead><tr><th>Team</th><th class="num">Pts</th></tr></thead><tbody>${D.teams.map(t => `<tr><td>${chip(t.lineage)}${esc(t.team)}${ours(t.lineage)}</td><td class="num">${t.total_points}</td></tr>`).join("")}</tbody></table></div>`;
    pickRow(i) } });

def("results", { title: "Results", mart: "core_results", color: "var(--brown)", deps: ["primary", "compare"],
  hint: "This address is the one you write in Lesson 12, Part 8.",
  key: c => `${wk(c)}/results/${["Q", "SQ", "S", "R"].includes(c.session) ? c.session : "R"}`,
  load: c => get(`${wk(c)}/results?session=${["Q", "SQ", "S", "R"].includes(c.session) ? c.session : "R"}`),
  render(i, D, c) { const s = ["Q", "SQ", "S", "R"].includes(c.session) ? c.session : "R", race = s === "R" || s === "S";
    i.tb.innerHTML = `<span>${SESSION_NAMES[s]} · official classification</span>`;
    i.body.innerHTML = `<table class="tt"><thead><tr><th>P</th><th>Driver</th><th>Team</th>${race ? `<th class="num">Grid</th><th class="num">+/−</th><th>Status</th><th class="num">Pts</th>` : ""}</tr></thead><tbody>${
      D.map(d => { const gain = d.grid_position && d.finish_position ? d.grid_position - d.finish_position : null;
        return `<tr class="click ${d.driver_code === c.primary ? "p1" : d.driver_code === c.compare ? "p2" : ""}" data-code="${d.driver_code}"><td>${d.finish_position ?? "–"}</td><td>${chip(d.lineage)}<span class="drv">${d.driver_code}</span>${ours(d.lineage)}</td><td class="note">${esc(d.team)}</td>
        ${race ? `<td class="num">${d.grid_position || "pit"}</td><td class="num ${gain > 0 ? "pos" : gain < 0 ? "neg" : ""}">${gain == null ? "" : gain > 0 ? "+" + gain : gain}</td><td class="note">${esc(d.status)}</td><td class="num">${d.points || ""}</td>` : ""}</tr>` }).join("")}</tbody></table>`;
    pickRow(i) } });

const CHECKPOINTS = [["after_practice", "After practice"], ["after_quali", "After quali"]];
const pct = (v, d = 2) => v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "±") + Math.abs(v).toFixed(d) + "%";
const chance = v => v == null ? "—" : Math.round(100 * v) + "%";
def("forecast", { title: "Race pace forecast", mart: "data/forecasts · shared model", color: "var(--plum)", chart: true, deps: ["primary", "compare"],
  hint: "Forecasts are made by: uv run dpec backtest (Lesson 15).",
  key: c => `${wk(c)}/forecast`, load: c => get(`${wk(c)}/forecast`),
  render(i, D, c) { const w = i.body.clientWidth, h = i.body.clientHeight; if (w < 50 || h < 50) return;
    const cp = i.state.cp || "after_quali", rows = D.filter(d => d.checkpoint === cp), ranged = rows.filter(d => d.low != null);
    const inside = ranged.filter(d => d.actual >= d.low && d.actual <= d.high).length;
    i.tb.innerHTML = `<div class="seg" data-seg="cp">${CHECKPOINTS.map(([v, l]) => `<button aria-pressed="${v === cp}" data-v="${v}">${l}</button>`).join("")}</div>
      <span>Race pace, % behind the fastest car · bar = 80% range · ◆ = what happened</span>
      <span>${ranged.length ? `Inside the range: <b>${inside} of ${ranged.length}</b> (aim 80%)` : "No range yet: the first 5 forecast weekends only teach the ranges"}</span>`;
    if (!rows.length) { i.body.innerHTML = `<div class="pad note">No forecast at this checkpoint.</div>`; return }
    const side = w > 620, fw = side ? Math.round(w * .64) : w, pl = 74, pr = 14, top = 8, bot = 24, rh = (h - top - bot) / rows.length;
    const lo = Math.min(0, ...rows.map(d => Math.min(d.low ?? d.predicted, d.actual))) - .1, hi = Math.max(...rows.map(d => Math.max(d.high ?? d.predicted, d.actual))) + .1;
    const X = scale(lo, hi, pl, fw - pr); let out = "";
    ticks(lo, hi, 5).forEach(t => out += `<line class="grid" x1="${X(t)}" x2="${X(t)}" y1="${top}" y2="${h - bot}"/><text x="${X(t)}" y="${h - 8}" text-anchor="middle">${t > 0 ? "+" : ""}${t}%</text>`);
    rows.forEach((d, k) => { const y = top + rh * (k + .5), mine = SETTINGS && d.lineage === SETTINGS.adopted_lineage, out_of = d.low != null && (d.actual < d.low || d.actual > d.high);
      const mark = d.driver_code === c.primary ? "var(--s1)" : d.driver_code === c.compare ? "var(--s2)" : null, r = Math.max(2.5, Math.min(5, rh * .28));
      out += `<g data-code="${d.driver_code}" style="cursor:pointer"><title>${d.driver_code}: forecast ${pct(d.predicted)}${d.low != null ? ` (80% range ${pct(d.low)} to ${pct(d.high)})` : ""}, real ${pct(d.actual)}${d.p_top3 != null ? `, top-3 race pace ${chance(d.p_top3)}` : ""}</title>
        <rect x="0" y="${y - rh / 2}" width="${fw}" height="${rh}" fill="transparent"/>${mark ? `<rect x="0" y="${y - rh / 2 + 1}" width="4" height="${rh - 2}" fill="${mark}"/>` : ""}
        <text x="10" y="${y + 4}" class="${mark || mine ? "val" : ""}">${k + 1}. ${d.driver_code}${mine ? " ★" : ""}</text>`;
      if (d.low != null) out += `<line x1="${X(d.low)}" x2="${X(d.high)}" y1="${y}" y2="${y}" stroke="${teamColour(d.lineage)}" stroke-width="${Math.max(3, Math.min(9, rh * .45))}" stroke-linecap="round" opacity="${mine ? .95 : .55}"/>`;
      out += `<circle cx="${X(d.predicted)}" cy="${y}" r="${r}" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>`;
      out += `<path d="M${X(d.actual)},${y - r - 1}l${r + 1},${r + 1}l-${r + 1},${r + 1}l-${r + 1},-${r + 1}z" fill="${out_of ? "var(--red)" : "var(--ink)"}"/></g>` });
    let card = "";
    const p = rows.find(d => d.driver_code === c.primary);
    if (side && p) { const rank = [...rows].sort((a, b) => a.actual - b.actual).findIndex(d => d === p) + 1;
      const line = (label, value, cls = "") => `<div style="display:flex;justify-content:space-between;gap:8px;border-bottom:1px dotted var(--line);padding:3px 0"><span class="note">${label}</span><b class="${cls}">${value}</b></div>`;
      card = `<div class="pad" style="position:absolute;top:0;right:0;width:${w - fw - 8}px;padding-top:10px">
        <div style="margin-bottom:6px">${chip(p.lineage)}<span class="drv">${p.driver_code}</span>${ours(p.lineage)}</div>
        ${line("Forecast", pct(p.predicted))}${line("80% range", p.low != null ? `${pct(p.low)} to ${pct(p.high)}` : "not yet")}
        ${line("What happened", pct(p.actual), p.low != null && (p.actual < p.low || p.actual > p.high) ? "neg" : "")}
        ${line("Chance of the best race pace", chance(p.p_best))}${line("Chance of a top-3 race pace", chance(p.p_top3))}
        ${line("Chance to beat his teammate", chance(p.p_beats_teammate))}${line("Expected pace rank", p.mean_rank != null ? p.mean_rank.toFixed(1) : "—")}
        ${line("Real pace rank", rank)}${line("Grid → finish", `${p.grid_position || "pit"} → ${p.finish_position ?? "–"}`)}
        <p class="note" style="margin-top:8px">Made before the race with only what was known then (${cp === "after_quali" ? "practice and qualifying" : "practice only"}). Race pace = median clean lap.</p></div>` }
    i.body.innerHTML = svg(fw, h, out) + card; pickRow(i) },
  seg(i, k, v) { i.state.cp = v; schedule(i) } });

const VERDICT = { GOOD: "var(--teal)", OK: "var(--mustard)", MISS: "var(--red)" };
const hm = m => m == null ? "—" : m >= 2880 ? Math.round(m / 1440) + " days" : m >= 120 ? Math.round(m / 60) + " h" : m + " min";
def("record", { title: "Public record", mart: "ledger/ · frozen forecasts and scores", color: "var(--teal)", deps: [],
  hint: "Forecasts are frozen by: uv run dpec freeze (Lesson 17).",
  key: () => "/record", load: () => Promise.all([get("/record"), get("/record?source=dry-runs")]).then(([ledger, dry]) => ({ ledger, "dry-runs": dry })),
  render(i, all, c) { const src = i.state.src || "ledger", D = all[src], scored = D.filter(d => d.verdict);
    const count = v => scored.filter(d => d.verdict === v).length;
    i.tb.innerHTML = `<div class="seg" data-seg="src">${[["ledger", "Live record"], ["dry-runs", "Dry runs"]].map(([v, l]) => `<button aria-pressed="${v === src}" data-v="${v}">${l}</button>`).join("")}</div>
      <span>${src === "ledger" ? "Frozen before the session, pushed to GitHub, never edited" : "Made after the fact, to test the pipeline: not the record"}</span>
      <span>${scored.length ? `<b style="color:${VERDICT.GOOD}">${count("GOOD")} good</b> · <b style="color:${VERDICT.OK}">${count("OK")} ok</b> · <b style="color:${VERDICT.MISS}">${count("MISS")} miss</b>` : "No scores yet"}</span>`;
    if (!D.length) { i.body.innerHTML = `<div class="pad note">${src === "ledger" ? "Nothing frozen yet. Before a race: <b>uv run dpec freeze --season 2026 --round N</b>, then commit and push." : "No dry runs yet: <b>uv run dpec pretend --season 2026</b>."}</div>`; return }
    i.body.innerHTML = `<table class="tt"><thead><tr><th>Weekend</th><th>Frozen</th><th>Our cars: forecast → race</th><th>Tyres and stops</th><th class="num">Error</th><th class="num">Inside</th><th>Verdict</th></tr></thead><tbody>${
      D.map(d => { const f = d.frozen[d.frozen.length - 1], here = d.season === c.season && d.round === c.round;
        const cars = d.ours.map(o => `${o.driver_code} ${pct(o.predicted)}${d.our_actual && d.our_actual[o.driver_code] != null ? ` → ${pct(d.our_actual[o.driver_code])}` : ""}`).join("<br>");
        return `<tr class="click ${here ? "p1" : ""}" data-season="${d.season}" data-round="${d.round}" title="sha256 ${f.sha256.slice(0, 12)}…${d.intact ? " · unchanged since frozen" : " · CHANGED after it was frozen"}">
          <td><b>${d.season} R${d.round}</b> <span class="note">${esc(d.circuit)}</span>${d.intact ? "" : ' <b class="neg">edited!</b>'}</td>
          <td class="note">${f.checkpoint === "after_quali" ? "after quali" : "after practice"}, ${f.minutes_early >= 0 ? hm(f.minutes_early) + " early" : `<span class="neg">${hm(-f.minutes_early)} late</span>`}</td>
          <td class="note">${cars || "—"}</td><td class="note">${esc(d.call || "—")}${d.stops_right == null ? "" : d.stops_right ? ' <span class="pos">✓</span>' : ' <span class="neg">✗</span>'}</td>
          <td class="num">${d.error_pct == null ? "—" : d.error_pct.toFixed(2) + "%"}</td><td class="num">${d.inside_range == null ? "—" : Math.round(100 * d.inside_range) + "%"}</td>
          <td>${d.verdict ? `<b style="color:${VERDICT[d.verdict]}">${d.verdict}</b>` : '<span class="note">waiting for the race</span>'}</td></tr>` }).join("")}</tbody></table>
      <p class="note pad">Error = average distance between forecast and real race pace, % of a lap (backtest: 0.55% after quali). Inside = share of real paces inside the 80% range (aim 80%). Click a row to open that weekend.</p>`;
    i.body.onclick = e => { const r = e.target.closest("[data-round]"); if (r) go(+r.dataset.season, +r.dataset.round, st.ctx) } },
  seg(i, k, v) { i.state.src = v; schedule(i) } });

const PART_LABEL = { pace: "Pace", tyre_age: "Older tyres", tyre_compound: "Harder tyres", a_traffic: "Traffic: A", b_traffic: "Traffic: B" };
function splitBars(rows, label, value, lo, hi, w) { // one row per part: a bar from 0, and the 80% range as a line
  const vals = rows.flatMap(r => [r[value], lo ? r[lo] : null, hi ? r[hi] : null]).filter(v => v != null);
  const m = Math.max(0.05, ...vals.map(Math.abs)), pl = 150, pr = 54, rh = 22, h = rows.length * rh + 22, X = scale(-m, m, pl, w - pr); let out = "";
  ticks(-m, m, 4).forEach(v => out += `<line class="grid" x1="${X(v)}" x2="${X(v)}" y1="4" y2="${h - 16}"/><text x="${X(v)}" y="${h - 3}" text-anchor="middle">${v > 0 ? "+" : ""}${v}</text>`);
  rows.forEach((r, k) => { const y = 6 + k * rh, v = r[value];
    out += `<text x="${pl - 8}" y="${y + 13}" text-anchor="end">${esc(label(r))}</text>`;
    if (v == null) { out += `<text x="${X(0) + 6}" y="${y + 13}" class="note">not measured</text>`; return }
    out += `<rect x="${Math.min(X(0), X(v))}" y="${y + 4}" width="${Math.abs(X(v) - X(0))}" height="${rh - 9}" rx="2" fill="${v > 0 ? "var(--s1)" : "var(--s2)"}" opacity=".85"/>`;
    if (lo && r[lo] != null) out += `<line x1="${X(r[lo])}" x2="${X(r[hi])}" y1="${y + rh / 2}" y2="${y + rh / 2}" stroke="var(--ink)" stroke-width="1.5"/><line x1="${X(r[lo])}" x2="${X(r[lo])}" y1="${y + 6}" y2="${y + rh - 6}" stroke="var(--ink)"/><line x1="${X(r[hi])}" x2="${X(r[hi])}" y1="${y + 6}" y2="${y + rh - 6}" stroke="var(--ink)"/>`;
    out += `<text x="${w - 4}" y="${y + 13}" text-anchor="end" class="val">${sgn(v)}</text>` });
  out += `<line x1="${X(0)}" x2="${X(0)}" y1="2" y2="${h - 16}" stroke="var(--line-strong)"/>`;
  return svg(w, h, out) }
def("debrief", { title: "Debrief", mart: "distance grid · core_laps", color: "var(--rose)", deps: ["primary", "compare"],
  hint: "The debrief is built in Lesson 18.",
  key: c => `${wk(c)}/debrief/${c.session}/${c.primary}/${c.compare}`, load: c => get(`${wk(c)}/debrief?session=${c.session}&a=${c.primary}&b=${c.compare}`),
  render(i, D, c) { const w = Math.max(260, i.body.clientWidth - 16), two = w > 760, cw = two ? Math.floor((w - 16) / 2) : w;
    i.tb.innerHTML = `<span><b style="color:var(--s1)">A ${D.a}</b> against <b style="color:var(--s2)">B ${D.b}</b> · + = A loses time, − = A gains</span>`;
    const lap = D.lap ? `<h4>Best laps of ${SESSION_NAMES[D.session]}: A ${D.lap.gap_s >= 0 ? "slower" : "faster"} by ${Math.abs(D.lap.gap_s).toFixed(3)} s</h4>${splitBars(D.lap.parts, r => `${r.kind} (${Math.round(100 * r.share_of_lap)}%)`, "seconds", null, null, cw)}<p class="note">Each 5 m of the gap goes to what B's car was doing there. The parts add up to the whole gap.</p>`
      : `<h4>Best laps of ${SESSION_NAMES[D.session]}</h4><p class="note">${esc(D.lap_note)}</p>`;
    const race = D.race ? `<h4>Race: A ${D.race.gap_s >= 0 ? "slower" : "faster"} by ${Math.abs(D.race.gap_s).toFixed(3)} s a lap (${D.race.laps} laps both clean)</h4>${splitBars(D.race.parts, r => PART_LABEL[r.part], "seconds_per_lap", "low", "high", cw)}<p class="note">Pace = the gap left on equal tyres in clean air. Same lap numbers, so fuel burnt and track grip cancel. Line = 80% range (bootstrap). A in traffic on ${Math.round(100 * D.race.a_traffic_share)}% of these laps.</p>`
      : `<h4>Race</h4><p class="note">${esc(D.race_note)}</p>`;
    i.body.innerHTML = `<div class="pad" style="display:grid;grid-template-columns:${two ? "1fr 1fr" : "1fr"};gap:16px">${`<div>${lap}</div><div>${race}</div>`}</div>` } });

/* ================= window chrome ================= */
const ICONS = {
  link: '<svg viewBox="0 0 24 24"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/></svg>',
  pin: '<svg viewBox="0 0 24 24"><path d="M12 17v5"/><path d="M8 3h8l-1 6 3 4H6l3-4z"/></svg>',
  wide: '<svg viewBox="0 0 24 24"><path d="M3 12h18M7 8l-4 4 4 4M17 8l4 4-4 4"/></svg>',
  tall: '<svg viewBox="0 0 24 24"><path d="M12 3v18M8 7l4-4 4 4M8 17l4 4 4-4"/></svg>',
  pop: '<svg viewBox="0 0 24 24"><path d="M14 4h6v6M20 4l-8 8"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>' };
let raf = new Set(), rafId = 0;
function schedule(i) { raf.add(i); if (!rafId) rafId = requestAnimationFrame(() => { rafId = 0; const s = [...raf]; raf.clear(); s.forEach(draw) }) }

// Draw with the data we have if it's for this context; otherwise fetch it first.
function draw(i) {
  const c = ctxOf(i); if (c.season == null || !c.primary) return;
  const key = i.def.key(c);
  if (i.dataKey === key) paint(i, c);
  else if (i.errorKey === key) return;
  else if (i.loadingKey !== key) {
    i.loadingKey = key; i.body.classList.add("busy");
    i.def.load(c).then(data => { if (i.loadingKey !== key) return; i.data = data; i.dataKey = key; i.errorKey = i.loadingKey = null; i.body.classList.remove("busy"); paint(i, ctxOf(i)) })
      .catch(err => { if (i.loadingKey !== key) return; i.data = i.dataKey = i.loadingKey = null; i.errorKey = key; i.body.classList.remove("busy");
        i.tb.innerHTML = ""; i.body.innerHTML = `<div class="err">${esc(err.message)}${i.def.hint && err.message.startsWith("404") ? `<small>${esc(i.def.hint)}</small>` : ""}</div>` });
  }
  const ln = i.el.querySelector('[data-act="link"]'); if (ln) { ln.innerHTML = i.w.pinned ? ICONS.pin : ICONS.link; ln.classList.toggle("on", !!i.w.pinned); ln.title = i.w.pinned ? "Pinned: keeps its own weekend, session and drivers. Click to link again." : "Linked: follows the shared context. Click to pin." }
  const pb = i.el.querySelector(".pinned-badge"); if (pb) pb.hidden = !i.w.pinned }
function paint(i, c) { try { i.def.render(i, i.data, c); bindSegs(i) } catch (e) { console.error(e); i.body.innerHTML = `<div class="err">Couldn't draw this window: ${esc(e.message)}</div>` } }
function bindSegs(i) { i.el.querySelectorAll("[data-seg]").forEach(sg => sg.onclick = e => { const b = e.target.closest("button[data-v]"); if (b && i.def.seg) i.def.seg(i, sg.dataset.seg, b.dataset.v) }) }

function curList() { const p = st.layouts[st.preset]; return p.monitors[clamp(st.mon, 0, p.monitors.length - 1)] }
let dragId = null;
function buildWS() {
  const ws = $("#ws"); ws.innerHTML = ""; for (const i of inst.values()) i.ro && i.ro.disconnect(); inst.clear();
  const p = st.layouts[st.preset]; let list = curList().filter(w => DEFS[w.type]);
  const tabs = $("#tabstrip");
  if (SOLO) { list = SOLO }
  if (p.tabs && !SOLO) { tabs.hidden = false; st.tab = clamp(st.tab, 0, list.length - 1);
    tabs.innerHTML = list.map((w, k) => `<button role="tab" aria-selected="${k === st.tab}" data-k="${k}" style="--wc:${DEFS[w.type].color}">${DEFS[w.type].title}</button>`).join("");
    tabs.onclick = e => { const b = e.target.closest("[data-k]"); if (b) { st.tab = +b.dataset.k; save(); buildWS() } }; list = [list[st.tab]] } else tabs.hidden = true;
  for (const w of list) { if (!w) continue; const d = DEFS[w.type]; const el = document.createElement("section"); el.className = "win"; el.style.setProperty("--wc", d.color);
    el.style.setProperty("--cs", SOLO ? 12 : w.cs); el.style.setProperty("--rs", SOLO ? 5 : w.rs); el.dataset.id = w.id; el.dataset.type = w.type;
    el.innerHTML = `<header class="win-h" draggable="true"><span class="tri" aria-hidden="true"></span><h3>${d.title}</h3><span class="pinned-badge" hidden>Pinned</span><span class="mart">${d.mart}</span>
      <div class="tools"><button class="ic" data-act="link"></button><button class="ic" data-act="wide" title="Change width">${ICONS.wide}</button><button class="ic" data-act="tall" title="Change height">${ICONS.tall}</button>
      <button class="ic" data-act="pop" title="Pop out to its own browser window">${ICONS.pop}</button><button class="ic" data-act="close" title="Close window">${ICONS.x}</button></div></header>
      <div class="win-tb"></div><div class="win-b ${d.chart ? "chart" : ""}"></div>`;
    ws.appendChild(el);
    const i = { w, def: d, el, tb: $(".win-tb", el), body: $(".win-b", el), state: (PREV_STATE.get(w.id) || {}) }; inst.set(w.id, i);
    if (d.move) { const mv = e => { const r = i.body.getBoundingClientRect(); const pt = e.touches ? e.touches[0] : e; d.move(i, pt.clientX - r.left, pt.clientY - r.top) }; i.body.addEventListener("mousemove", mv); i.body.addEventListener("touchmove", mv, { passive: true }) }
    i.ro = new ResizeObserver(() => schedule(i)); i.ro.observe(i.body);
    $(".tools", el).onclick = e => { const b = e.target.closest("[data-act]"); if (!b) return; act(i, b.dataset.act) };
    const hd = $(".win-h", el);
    hd.addEventListener("dragstart", e => { dragId = w.id; try { e.dataTransfer.setData("text/plain", w.id) } catch (_) { }; e.dataTransfer.effectAllowed = "move" });
    el.addEventListener("dragover", e => { if (dragId && dragId !== w.id) { e.preventDefault(); el.classList.add("dragover") } });
    el.addEventListener("dragleave", () => el.classList.remove("dragover"));
    el.addEventListener("drop", e => { e.preventDefault(); el.classList.remove("dragover"); if (!dragId || dragId === w.id) return; const L = curList(); const a = L.findIndex(x => x.id === dragId), b = L.findIndex(x => x.id === w.id); if (a >= 0 && b >= 0) { [L[a], L[b]] = [L[b], L[a]]; save(); keepState(); buildWS() } dragId = null });
    schedule(i) }
  syncLayoutBar() }
const PREV_STATE = new Map(); function keepState() { for (const [id, i] of inst) PREV_STATE.set(id, i.state) }
function act(i, a) { const L = curList();
  if (a === "link") { i.w.pinned = i.w.pinned ? null : { ...st.ctx }; schedule(i); save(); toast(i.w.pinned ? `${i.def.title} pinned to ${i.w.pinned.season} round ${i.w.pinned.round}, ${i.w.pinned.session}, ${i.w.pinned.primary} vs ${i.w.pinned.compare}.` : `${i.def.title} follows the shared context again.`) }
  if (a === "wide") { const o = [4, 5, 6, 7, 8, 12]; i.w.cs = o[(o.indexOf(i.w.cs) + 1) % o.length] || 6; i.el.style.setProperty("--cs", i.w.cs); save() }
  if (a === "tall") { const o = [2, 3, 4, 5]; i.w.rs = o[(o.indexOf(i.w.rs) + 1) % o.length] || 3; i.el.style.setProperty("--rs", i.w.rs); save() }
  if (a === "close") { const k = L.indexOf(i.w); if (k >= 0) L.splice(k, 1); save(); keepState(); buildWS(); toast(`${i.def.title} closed. Add it back from “+ Add window”.`) }
  if (a === "pop") popout("win=" + i.w.type) }
function popout(q) { let w = null; try { const u = location.href.split("#")[0].split("?")[0] + "?" + q; w = window.open(u, "_blank", "popup,width=1000,height=640") } catch (e) { }
  if (!w) toast("Your browser blocked the pop-out window. Allow pop-ups for this page and try again.") }

/* ================= header + bars ================= */
function seg(el, items, cur, on) { el.innerHTML = items.map(([v, l]) => `<button aria-pressed="${v === cur}" data-v="${v}">${l}</button>`).join(""); el.onclick = e => { const b = e.target.closest("[data-v]"); if (b) on(b.dataset.v) } }
let headerToken = 0;
async function syncHeader() {
  const c = st.ctx, token = ++headerToken; if (c.season == null) return;
  const seasons = [...new Set(WEEKENDS.map(w => w.season))];
  $("#selSeason").innerHTML = seasons.map(s => `<option value="${s}" ${s === c.season ? "selected" : ""}>${s}</option>`).join("");
  const rounds = WEEKENDS.filter(w => w.season === c.season).sort((a, b) => a.round - b.round);
  $("#selRound").innerHTML = rounds.map(w => `<option value="${w.round}" ${w.round === c.round ? "selected" : ""}>${esc(w.event_name.replace("Grand Prix", "GP"))}</option>`).join("");
  const w = rounds.find(x => x.round === c.round) || {};
  $("#rdNo").textContent = String(c.round).padStart(2, "0");
  $("#evCircuit").textContent = `${w.circuit || ""}${w.is_sprint_weekend ? " · sprint weekend" : ""}${w.is_wet_race ? " · wet race" : ""}`;
  $("#evDate").textContent = `Race ${fmtDate(w.race_date)}${w.winner ? " · won by " + w.winner : ""}`;
  try {
    const weekend = await get(wk(c)); if (token !== headerToken) return;
    seg($("#sessSeg"), weekend.sessions.map(s => [s.session_type, s.session_type]), c.session, v => go(c.season, c.round, { ...st.ctx, session: v }));
    const pace = await get(`${wk(c)}/pace?session=${c.session}`); if (token !== headerToken) return;
    const teams = [...new Set(pace.map(d => d.team))];
    const opts = sel => teams.map(t => `<optgroup label="${esc(t)}">${pace.filter(d => d.team === t).map(d => `<option value="${d.driver_code}" ${d.driver_code === sel ? "selected" : ""}>${d.driver_code}</option>`).join("")}</optgroup>`).join("");
    $("#selP").innerHTML = opts(c.primary); $("#selC").innerHTML = opts(c.compare);
    const D = await cmpLoad(c); if (token !== headerToken) return; drawMiniTrack(D);
  } catch (e) { if (token === headerToken) $("#miniTrack").innerHTML = "" } }
$("#selSeason").onchange = e => { const s = +e.target.value; const last = WEEKENDS.filter(w => w.season === s).sort((a, b) => b.round - a.round)[0]; go(s, last.round, st.ctx) };
$("#selRound").onchange = e => go(st.ctx.season, +e.target.value, st.ctx);
$("#selP").onchange = e => { if (e.target.value === st.ctx.compare) setCtx({ primary: e.target.value, compare: st.ctx.primary }); else setCtx({ primary: e.target.value }) };
$("#selC").onchange = e => { if (e.target.value === st.ctx.primary) setCtx({ compare: e.target.value, primary: st.ctx.compare }); else setCtx({ compare: e.target.value }) };
function drawMiniTrack(D) { const [x0, x1] = minmax(D.x), [y0, y1] = minmax(D.y), s = Math.min(84 / ((x1 - x0) || 1), 54 / ((y1 - y0) || 1));
  let d = ""; for (let k = 0; k < D.x.length; k += 3) d += (k ? "L" : "M") + (8 + (D.x[k] - x0) * s).toFixed(1) + "," + (62 - (D.y[k] - y0) * s).toFixed(1);
  $("#miniTrack").innerHTML = `<path d="${d}Z" fill="none" stroke="var(--orange)" stroke-width="3.5" stroke-linejoin="round"/><path d="${d}Z" fill="none" stroke="var(--ink)" stroke-width="1" stroke-linejoin="round"/>` }
function syncLayoutBar() { const p = st.layouts[st.preset];
  seg($("#presetSeg"), Object.entries(st.layouts).map(([k, v]) => [k, v.name]), st.preset, v => { keepState(); st.preset = v; st.mon = 0; st.tab = 0; save(); buildWS(); toast(`${st.layouts[v].name}: ${st.layouts[v].hint}.`) });
  const multi = p.monitors.length > 1; $("#monSeg").hidden = $("#monLbl").hidden = $("#btnPopMon").hidden = !multi;
  if (multi) seg($("#monSeg"), p.monitors.map((m, k) => [String(k), "Monitor " + (k + 1)]), String(st.mon), v => { keepState(); st.mon = +v; save(); buildWS() }) }
$("#btnPopMon").onclick = () => popout("monitor=" + st.mon + "&preset=" + st.preset);
$("#btnReset").onclick = () => { const fresh = presets(); st.layouts[st.preset] = fresh[st.preset]; let mx = 0; Object.values(st.layouts).forEach(p => p.monitors.flat().forEach(w => mx = Math.max(mx, +w.id.slice(1))));
  st.layouts[st.preset].monitors.forEach(m => m.forEach(w => w.id = "w" + (++mx))); uid = mx + 1; save(); PREV_STATE.clear(); buildWS(); toast(`${st.layouts[st.preset].name} layout reset.`) };
$("#btnAdd").onclick = e => { const m = $("#addMenu"); if (!m.hidden) { m.hidden = true; return }
  m.innerHTML = Object.values(DEFS).map(d => `<button role="menuitem" data-t="${d.type}" style="--wc:${d.color}"><i></i>${d.title}</button>`).join("");
  const r = e.currentTarget.getBoundingClientRect(); m.hidden = false; m.style.top = (r.bottom + 8) + "px"; m.style.left = Math.max(16, Math.min(r.right - m.offsetWidth, innerWidth - m.offsetWidth - 16)) + "px";
  m.onclick = ev => { const b = ev.target.closest("[data-t]"); if (!b) return; const w = W(b.dataset.t, 6, 3); curList().push(w); if (st.layouts[st.preset].tabs) { w.cs = 12; w.rs = 5; st.tab = curList().length - 1 } save(); keepState(); buildWS(); m.hidden = true;
    const el = document.querySelector(`[data-id="${w.id}"]`); el && el.scrollIntoView({ behavior: "smooth", block: "nearest" }) } };
document.addEventListener("click", e => { const m = $("#addMenu"); if (!m.hidden && !m.contains(e.target) && e.target.id !== "btnAdd") m.hidden = true });

/* settings */
function applySet() { const s = st.set, root = document.documentElement;
  if (s.theme === "system") root.removeAttribute("data-theme"); else root.dataset.theme = s.theme;
  root.classList.toggle("cb", s.cb); root.classList.toggle("compact", s.density === "compact");
  seg($("#themeSeg"), [["light", "Day session"], ["dark", "Night session"], ["system", "System"]], s.theme, v => { s.theme = v; applySet(); save() });
  seg($("#unitSeg"), [["kmh", "km/h"], ["mph", "mph"]], s.units, v => { s.units = v; applySet(); save(); inst.forEach(schedule) });
  seg($("#densSeg"), [["comfy", "Comfortable"], ["compact", "Compact"]], s.density, v => { s.density = v; applySet(); save() });
  seg($("#cbSeg"), [["off", "Off"], ["on", "On"]], s.cb ? "on" : "off", v => { s.cb = v === "on"; applySet(); save() }) }
$("#btnSettings").onclick = () => { $("#drawer").hidden = false }; $("#btnClose").onclick = () => { $("#drawer").hidden = true };
document.addEventListener("keydown", e => { if (e.key === "Escape") { $("#drawer").hidden = true; $("#addMenu").hidden = true } });
let tt = 0; function toast(m) { const t = $("#toast"); t.textContent = m; t.hidden = false; clearTimeout(tt); tt = setTimeout(() => t.hidden = true, 3600) }

/* solo / monitor pop-outs */
let SOLO = null;
if (params.get("win") && DEFS[params.get("win")]) { SOLO = [W(params.get("win"), 12, 5)]; document.body.classList.add("solo") }
if (params.get("monitor") !== null && params.get("preset") && st.layouts[params.get("preset")]) { st.preset = params.get("preset"); st.mon = +params.get("monitor") || 0 }

/* ================= start ================= */
async function start() {
  applySet();
  try { [SETTINGS, WEEKENDS] = await Promise.all([get("/settings"), get("/weekends")]) }
  catch (e) { $("#ws").innerHTML = `<div class="err" style="grid-column:1/-1">Can't reach the API: ${esc(e.message)}<small>Start it with "make run" in the project folder, then open http://127.0.0.1:8000</small></div>`; return }
  if (!WEEKENDS.length) { $("#ws").innerHTML = `<div class="err" style="grid-column:1/-1">The warehouse has no weekends yet.<small>Run "make data" first.</small></div>`; return }
  $("#oursNote").textContent = `${SETTINGS.adopted_team} (adopted_team in config/dpec.yaml). Their cars carry ★ OURS.`;
  get("/health").then(hl => { $("#modeNote").textContent = `${hl.mode} · ${hl.sessions} sessions in the warehouse` }).catch(() => { });
  const first = WEEKENDS.find(w => w.season === wish.season && w.round === wish.round) || WEEKENDS[0];
  try { Object.assign(st.ctx, await resolve(first.season, first.round, wish)) } catch (e) { toast(e.message) }
  syncHeader(); buildWS() }
start();
