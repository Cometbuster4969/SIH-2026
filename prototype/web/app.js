// SatQuery AI web frontend — vanilla JS, no CDN/build (offline, design §12).
// Talks to /api/v1/* only. The browser never interprets rasters — all overlay
// geometry/PNGs come pre-projected from the backend (design §5).

const state = {
  requestId: null,
  demo: false,
  lastAnswer: null,
  layers: [],
  inventory: [],
  baseUrls: [],
};

const $ = (sel) => document.querySelector(sel);
const chat = $("#chat");
const stage = $("#stage");

// ---- helpers ----------------------------------------------------------------

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

function confBadge(c) {
  if (c === null || c === undefined) return `<span class="conf">conf: n/a (heuristic)</span>`;
  const n = Math.round((c ?? 0) * 4);
  const dots = "●".repeat(n) + "○".repeat(4 - n);
  const label = c >= 0.75 ? "High" : c >= 0.5 ? "Med" : "Low";
  const col = c >= 0.75 ? "var(--green)" : c >= 0.5 ? "var(--amber)" : "var(--red)";
  return `<span class="conf"><span class="dots" style="color:${col}">${dots}</span> ${c.toFixed(2)} ${label}</span>`;
}

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    let msg = r.statusText;
    try { const j = await r.json(); msg = j.detail || j.message || JSON.stringify(j); } catch (_) {}
    throw new Error(msg);
  }
  return r.json();
}

// ---- inventory + stage ------------------------------------------------------

function renderInventory() {
  const inv = $("#inventory");
  inv.innerHTML = "";
  state.inventory.forEach((f, i) => {
    const card = el("div", "inv-card");
    card.innerHTML =
      `<img src="${f.preview_url}" alt="preview">
       <div class="inv-meta"><b>${f.name}</b>
       <span class="muted">${f.label || ""}<br>
       modality: ${f.modality} · ${f.size_px[0]}×${f.size_px[1]}px<br>
       bands: ${f.bands.slice(0, 6).join(", ")}${f.bands.length > 6 ? "…" : ""}<br>
       CRS: ${f.crs || "none"}</span></div>`;
    inv.appendChild(card);
  });
  renderStage();
}

function renderPairBanner(pair) {
  if (!pair) { $("#pairBanner").classList.add("hidden"); return; }
  const b = $("#pairBanner");
  b.className = `pair-banner ${pair.banner}`;
  b.textContent = pair.message;
}

function renderStage() {
  stage.querySelectorAll(".layer,.legend,.stage-empty").forEach((n) => n.remove());
  if (!state.inventory.length) {
    stage.appendChild(el("div", "stage-empty muted", "Upload imagery or load a demo set to view the image stage."));
    return;
  }
  // base = first image (or switched via baseSwitch)
  const activeBase = state.baseUrls[0];
  const img = el("img", "layer");
  img.src = activeBase;
  stage.appendChild(img);
  // overlay layers stacked on top, respecting toggles
  state.layers.forEach((L, i) => {
    const o = el("img", "layer overlay");
    o.dataset.layerIdx = i;
    o.src = L.url;
    if (!L.on) o.classList.add("hidden");
    stage.appendChild(o);
  });
  const legend = el("div", "legend");
  legend.innerHTML = state.layers.filter((l) => l.on)
    .map((l) => `<span class="swatch" style="background:${l.color}"></span> ${l.legend}`).join(" &nbsp;·&nbsp; ");
  if (state.layers.length) stage.appendChild(legend);
}

function renderLayerToggles() {
  const box = $("#layerToggles");
  box.innerHTML = "";
  state.layers.forEach((L, i) => {
    const lab = el("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = L.on !== false;
    cb.onchange = () => {
      L.on = cb.checked;
      const ov = stage.querySelector(`.overlay[data-layer-idx="${i}"]`);
      if (ov) ov.classList.toggle("hidden", !cb.checked);
      renderStage();
    };
    lab.appendChild(cb);
    lab.innerHTML += `<span class="swatch" style="background:${L.color}"></span> ${L.name}`;
    box.appendChild(lab);
  });
}

// ---- chat + answer card -----------------------------------------------------

function addUserMsg(text) {
  chat.appendChild(el("div", "msg user", text));
  chat.scrollTop = chat.scrollHeight;
}

function addWorking(text) {
  const e = el("div", "msg sys", `<span class="spinner"></span> ${text}`);
  chat.appendChild(e);
  chat.scrollTop = chat.scrollHeight;
  return e;
}

function addAnswerCard(data) {
  state.lastAnswer = data;
  const trainedBadge = data.trained
    ? `<span class="badge trained">🟢 TRAINED MODEL</span>`
    : `<span class="badge heuristic">🟡 HEURISTIC (declared)</span>`;
  const taskBadge = data.task
    ? `<span class="badge task">${data.task}</span>` : "";
  const stCls = data.status === "ok" ? "status-ok"
    : data.status === "abstain" ? "status-abstain" : "status-degraded";

  const facts = [];
  const res = data.result;
  if (res) {
    if (res.extra?.change_pct !== undefined)
      facts.push(`<span class="fact">changed ${res.extra.change_pct}%</span>`);
    if (res.bbox) facts.push(`<span class="fact">bbox [${res.bbox.map((v) => Math.round(v)).join(", ")}]</span>`);
    if (res.labels?.length)
      facts.push(...res.labels.slice(0, 3).map((l) => `<span class="fact">${l.label} ${(l.score ?? 0).toFixed(2)}</span>`));
  }

  const warns = (data.warnings || [])
    .filter((w) => w.severity !== "warning" || true)
    .map((w) => `<div class="warn ${w.severity === "error" ? "err" : ""}">⚠ ${w.step}: ${w.message}</div>`)
    .join("");

  const card = el("div", "msg sys");
  card.innerHTML =
    `<div>${taskBadge}${trainedBadge}
       <span class="badge ${stCls}">${data.status}</span>
       ${confBadge(data.confidence)}
       <span class="conf">${data.elapsed_s}s · tool <code>${data.tool}</code>${data.fallback_used ? " · RuleRouter fallback" : ""}</span>
     </div>
     <div class="answer-text">${data.answer}</div>
     ${facts.length ? `<div class="facts">${facts.join("")}</div>` : ""}
     ${warns}
     <div class="foot">trace rendered in right panel · <a href="#" id="jsonLink">Trace as JSON</a></div>`;
  chat.appendChild(card);
  card.querySelector("#jsonLink").onclick = (e) => { e.preventDefault(); showTraceJson(data.trace); };
  chat.scrollTop = chat.scrollHeight;
}

function renderTrace(trace) {
  const panel = $("#tracePanel");
  panel.innerHTML = "";
  const route = trace.route;
  if (route) {
    const head = el("div", "trow");
    head.innerHTML =
      `<div class="step"><span class="ic ok"></span><b>route</b>
       <span class="muted">→ ${route.task} via ${route.planner}</span>
       <span class="lat">fallback=${route.fallback_used}</span></div>
       <div class="detail">keywords: ${(route.keywords || []).join(", ") || "(default)}${route.notes ? "\n" + route.notes : ""}</div>`;
    head.querySelector(".step").onclick = () => head.classList.toggle("open");
    panel.appendChild(head);
  }
  (trace.events || []).forEach((ev) => {
    const row = el("div", "trow");
    const ic = ev.status === "ok" ? "ok" : ev.status === "error" ? "error" : "warning";
    row.innerHTML =
      `<div class="step"><span class="ic ${ic}"></span><b>${ev.step}</b>
       ${ev.tool ? `<span class="muted"> · ${ev.tool}</span>` : ""}
       <span class="lat">${ev.data?.latency_s ? ev.data.latency_s + "s" : ""}</span></div>
       <div class="detail">${ev.message}${ev.data && Object.keys(ev.data).length ? "\n" + JSON.stringify(ev.data, null, 1) : ""}</div>`;
    row.querySelector(".step").onclick = () => row.classList.toggle("open");
    if (ev.step === "execute" || ev.step === "route") row.classList.add("open");
    panel.appendChild(row);
  });
  $("#traceMeta").textContent = route ? `· ${route.planner}` : "";
  $("#traceJson").disabled = false;
  $("#copyAnswer").disabled = false;
}

function showTraceJson(trace) {
  const w = window.open("", "_blank");
  w.document.write("<pre style='font:12px monospace;background:#0e1116;color:#e6edf3;padding:20px'>" +
    JSON.stringify(trace, null, 2).replace(/</g, "&lt;") + "</pre>");
}

// ---- data flows -------------------------------------------------------------

async function loadDemo(setName) {
  const w = addWorking(`Loading demo set: ${setName}…`);
  try {
    const d = await api(`/api/v1/demo?set=${setName}`, { method: "POST" });
    state.requestId = d.request_id;
    state.demo = true;
    state.inventory = d.inventory;
    state.baseUrls = d.inventory.map((f) => f.preview_url);
    state.layers = [];
    renderInventory();
    renderPairBanner(d.pair);
    renderLayerToggles();
    w.remove();
    chat.appendChild(el("div", "msg sys",
      `<b>Demo set loaded (${setName.replace("_", " ")}).</b> Images are synthetic but spectral-consistent stand-ins; ask anything below.`));
  } catch (e) { w.textContent = "Demo load failed: " + e.message; }
}

async function uploadFiles(files) {
  if (!files.length) return;
  const fd = new FormData();
  [...files].forEach((f) => fd.append("files", f));
  const w = addWorking("Ingesting & validating rasters…");
  try {
    const d = await api("/api/v1/ingest", { method: "POST", body: fd });
    state.requestId = d.request_id;
    state.demo = false;
    state.inventory = d.inventory;
    state.baseUrls = d.inventory.map((f) => f.preview_url);
    state.layers = [];
    renderInventory();
    renderPairBanner(d.pair);
    renderLayerToggles();
    w.remove();
    chat.appendChild(el("div", "msg sys",
      `<b>${d.inventory.length} image(s) ingested.</b> ${(d.warnings || []).map((x) => x.message).join(" ")}`));
  } catch (e) {
    w.innerHTML = `<b>Rejected.</b> ${e.message}<br><span class="muted">Fix: upload GeoTIFF/TIFF; PNG/JPEG only for benchmark datasets.</span>`;
  }
}

async function runQuery(q) {
  if (!q.trim()) return;
  if (!state.requestId) { await loadDemo("single"); }
  addUserMsg(q);
  const w = addWorking("Routing → selecting tool → executing → integrating…");
  try {
    const d = await api("/api/v1/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: state.requestId, query: q, demo: state.demo }),
    });
    w.remove();
    addAnswerCard(d);
    renderTrace(d.trace);
    state.layers = (d.layers || []).map((l) => ({ ...l, on: true }));
    renderLayerToggles();
    renderStage();
    if (d.inventory) { state.inventory = d.inventory; renderInventory(); }
    if (d.pair) renderPairBanner(d.pair);
  } catch (e) {
    w.innerHTML = `<b>Failed.</b> ${e.message}`;
  }
}

// ---- wiring -----------------------------------------------------------------

$("#sendBtn").onclick = () => { runQuery($("#queryInput").value); $("#queryInput").value = ""; };
$("#queryInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { $("#sendBtn").click(); }
});
document.querySelectorAll(".chip[data-q]").forEach((c) =>
  c.onclick = () => runQuery(c.dataset.q));
document.querySelectorAll(".chip[data-demo]").forEach((c) =>
  c.onclick = () => loadDemo(c.dataset.demo));

const dz = $("#dropzone"), fi = $("#fileInput");
dz.onclick = () => fi.click();
fi.onchange = () => uploadFiles(fi.files);
["dragover", "dragenter"].forEach((ev) => dz.addEventListener(ev, (e) => {
  e.preventDefault(); dz.classList.add("over");
}));
["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => {
  e.preventDefault(); dz.classList.remove("over");
}));
dz.addEventListener("drop", (e) => uploadFiles(e.dataTransfer.files));

$("#demoToggle").onclick = () => loadDemo("bi_temporal");
$("#clearBtn").onclick = () => location.reload();
$("#traceJson").onclick = () => state.lastAnswer && showTraceJson(state.lastAnswer.trace);
$("#copyAnswer").onclick = () => {
  if (state.lastAnswer) navigator.clipboard.writeText(state.lastAnswer.answer);
};

$("#toolsBtn").onclick = async () => {
  const d = await api("/api/v1/tools");
  const list = $("#toolsList");
  list.innerHTML = "";
  d.tools.forEach((t) => {
    const row = el("div", "tool-row");
    row.innerHTML =
      `<div><span class="tname">${t.name}</span>
       ${t.trained ? '<span class="badge trained">trained</span>' : '<span class="badge heuristic">heuristic</span>'}
       <span class="muted"> · task ${t.task} · budget ${t.latency_budget_s}s</span></div>
       <div class="muted" style="margin-top:4px">${t.description.trim()}</div>
       ${t.vendor ? `<div class="muted" style="margin-top:4px">weights: ${t.vendor}</div>` : ""}`;
    list.appendChild(row);
  });
  $("#modal").classList.remove("hidden");
};
$("#modalClose").onclick = () => $("#modal").classList.add("hidden");
$("#modal").onclick = (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); };

// One-click full walkthrough: runs all six PS-representative queries in order.
$("#walkthrough").onclick = async () => {
  if (!state.requestId) await loadDemo("bi_temporal");
  const qs = [...document.querySelectorAll(".chip[data-q]")].map((c) => c.dataset.q);
  for (const q of qs) { await runQuery(q); await new Promise((r) => setTimeout(r, 600)); }
};
