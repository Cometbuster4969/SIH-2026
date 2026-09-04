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
  baseIdx: 0,
};

const $ = (sel) => document.querySelector(sel);
const chat = $("#chat");
const stage = $("#stage");

// Per-task accent for answer headers (visual only).
const TASK_COLOR = {
  landcover: "#3fb950", vqa: "#00e5ff", ground: "#00e5ff", caption: "#58a6ff",
  change: "#f4544c", xmodal: "#bc8cff", xmodal_mask: "#bc8cff",
};

// ---- helpers ----------------------------------------------------------------

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function dismissHero() {
  const h = $("#hero");
  if (h) h.remove();
}

function confBadge(c) {
  if (c === null || c === undefined)
    return `<span class="conf" title="No calibrated confidence — declared heuristic tool">conf n/a · heuristic</span>`;
  const pct = Math.round((c ?? 0) * 100);
  const col = c >= 0.75 ? "var(--green)" : c >= 0.5 ? "var(--amber)" : "var(--red)";
  const label = c >= 0.75 ? "High" : c >= 0.5 ? "Med" : "Low";
  return `<span class="conf" title="Model-reported confidence">
    <span class="conf-bar"><span class="conf-fill" style="width:${pct}%;background:${col}"></span></span>
    ${c.toFixed(2)} · ${label}</span>`;
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
      `<div class="inv-thumb"><img src="${f.preview_url}" alt="preview" loading="lazy">
       <span class="inv-mod ${esc(f.modality)}">${esc(f.modality)}</span></div>
       <div class="inv-meta"><b>${esc(f.label || f.name)}</b>
       <span class="muted">${f.name}<br>
       modality: ${esc(f.modality)} · ${f.size_px[0]}×${f.size_px[1]} px<br>
       bands: ${f.bands.slice(0, 6).join(", ")}${f.bands.length > 6 ? "…" : ""}<br>
       CRS: ${esc(f.crs || "none")}</span></div>`;
    inv.appendChild(card);
  });
  renderBaseSwitch();
  renderStage();
}

function renderPairBanner(pair) {
  if (!pair) { $("#pairBanner").classList.add("hidden"); return; }
  const b = $("#pairBanner");
  b.className = `pair-banner ${pair.banner}`;
  b.textContent = pair.message;
}

function renderBaseSwitch() {
  const box = $("#baseSwitch");
  box.innerHTML = "";
  state.inventory.forEach((f, i) => {
    const c = el("div");
    c.className = "base-chip" + (i === state.baseIdx ? " active" : "");
    c.title = f.label || f.name;
    c.innerHTML = `<img src="${f.preview_url}" alt=""><span>${esc((f.label || f.name).split("|")[0].trim().slice(0, 18))}</span>`;
    c.onclick = () => { state.baseIdx = i; renderBaseSwitch(); renderStage(); };
    box.appendChild(c);
  });
}

function renderStage() {
  stage.querySelectorAll(".stage-imgwrap,.stage-empty").forEach((n) => n.remove());
  if (!state.inventory.length) {
    stage.appendChild(el("div", "stage-empty",
      `<div class="stage-empty-ico" aria-hidden="true">🛰</div>
       <p><b>No imagery on stage yet.</b></p>
       <p class="muted">Upload a GeoTIFF pair or load a demo set — base image and evidence
       overlays (boxes · change map · masks · heatmaps) render here, side by side with the trace.</p>`));
    return;
  }
  const wrap = el("div", "stage-imgwrap");
  const img = el("img", "base");
  img.src = state.baseUrls[Math.min(state.baseIdx, state.baseUrls.length - 1)];
  img.alt = "image stage base";
  wrap.appendChild(img);
  state.layers.forEach((L, i) => {
    const o = el("img", "layer overlay");
    o.dataset.layerIdx = i;
    o.src = L.url;
    o.alt = L.name;
    if (!L.on) o.classList.add("hidden");
    wrap.appendChild(o);
  });
  stage.appendChild(wrap);

  const on = state.layers.filter((l) => l.on);
  if (on.length) {
    const legend = el("div", "stage-legend");
    legend.innerHTML = on
      .map((l) => `<span class="swatch" style="background:${l.color}"></span> ${esc(l.legend || l.name)}`)
      .join(" &nbsp;·&nbsp; ");
    stage.appendChild(legend);
  }
  const cap = state.inventory[Math.min(state.baseIdx, state.inventory.length - 1)];
  if (cap) {
    const c = el("div", "stage-cap");
    c.textContent = `${cap.label || cap.name} · ${cap.size_px[0]}×${cap.size_px[1]}px`;
    stage.appendChild(c);
  }
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
      renderStage();
    };
    lab.appendChild(cb);
    lab.insertAdjacentHTML("beforeend",
      `<span class="swatch" style="background:${L.color}"></span> ${esc(L.name)}`);
    box.appendChild(lab);
  });
}

// ---- chat + answer card -----------------------------------------------------

function addUserMsg(text) {
  dismissHero();
  chat.appendChild(el("div", "msg user", esc(text)));
  chat.scrollTop = chat.scrollHeight;
}

function addWorking(text) {
  const e = el("div", "msg sys", `<span class="spinner"></span> ${esc(text)}`);
  chat.appendChild(e);
  chat.scrollTop = chat.scrollHeight;
  return e;
}

function addAnswerCard(data) {
  state.lastAnswer = data;
  const tc = TASK_COLOR[data.task] || "var(--accent)";
  const trainedBadge = data.trained
    ? `<span class="badge trained"><span class="dot"></span>trained</span>`
    : `<span class="badge heuristic"><span class="dot"></span>heuristic · declared</span>`;
  const taskBadge = data.task
    ? `<span class="badge task" style="--tc:${tc}">${esc(data.task)}</span>` : "";
  const stCls = data.status === "ok" ? "status-ok"
    : data.status === "abstain" ? "status-abstain" : "status-degraded";
  const statusBadge = `<span class="badge ${stCls}">${esc(data.status)}</span>`;

  const facts = [];
  const res = data.result;
  if (res) {
    if (res.extra?.change_pct !== undefined)
      facts.push(`<span class="fact">changed <b>${res.extra.change_pct}%</b></span>`);
    if (res.bbox)
      facts.push(`<span class="fact">bbox [${res.bbox.map((v) => Math.round(v)).join(", ")}]</span>`);
    if (res.labels?.length)
      facts.push(...res.labels.slice(0, 3).map((l) =>
        `<span class="fact">${esc(l.label)} <b>${(l.score ?? 0).toFixed(2)}</b></span>`));
  }

  const warns = (data.warnings || [])
    .map((w) => `<div class="warn ${w.severity === "error" ? "err" : ""}">⚠ ${esc(w.step)}: ${esc(w.message)}</div>`)
    .join("");

  const card = el("div", "msg sys");
  card.innerHTML =
    `<div class="ans-head">${taskBadge}${trainedBadge}${statusBadge}
       ${confBadge(data.confidence)}
     </div>
     <div class="answer-text">${esc(data.answer)}</div>
     ${facts.length ? `<div class="facts">${facts.join("")}</div>` : ""}
     ${warns}
     <div class="ans-meta">${data.elapsed_s}s · tool <code>${esc(data.tool)}</code>${data.fallback_used ? " · RuleRouter fallback" : ""} · query ${esc(data.query_id || "")}</div>
     <div class="foot">trace rendered in right panel · <a href="#" id="jsonLink">Trace as JSON ↗</a></div>`;
  chat.appendChild(card);
  card.querySelector("#jsonLink").onclick = (e) => { e.preventDefault(); showTraceJson(data.trace); };
  chat.scrollTop = chat.scrollHeight;
}

function renderTrace(trace) {
  const panel = $("#tracePanel");
  panel.innerHTML = "";
  const route = trace.route;
  const mkRow = (icCls, name, tool, lat, detail, open) => {
    const row = el("div", "trow" + (open ? " open" : ""));
    row.innerHTML =
      `<div class="step"><span class="ic ${icCls}"></span><b>${esc(name)}</b>
       ${tool ? `<span class="muted">· ${esc(tool)}</span>` : ""}
       <span class="lat">${lat ? esc(lat) : ""}</span></div>
       <div class="detail">${esc(detail)}</div>`;
    row.querySelector(".step").onclick = () => row.classList.toggle("open");
    panel.appendChild(row);
    return row;
  };

  if (route) {
    mkRow("route", "route", null,
      `fallback=${route.fallback_used}`,
      `task → ${route.task} via ${route.planner}\nkeywords: ${(route.keywords || []).join(", ") || "(default)"}${route.notes ? "\nnotes: " + route.notes : ""}`,
      true);
  }
  (trace.events || []).forEach((ev) => {
    const ic = ev.status === "ok" ? "ok" : ev.status === "error" ? "error"
      : ev.status === "warning" ? "warning" : "warning";
    const lat = ev.data?.latency_s ? ev.data.latency_s + "s" : "";
    const detail = ev.message +
      (ev.data && Object.keys(ev.data).length ? "\n" + JSON.stringify(ev.data, null, 1) : "");
    mkRow(ic, ev.step, ev.tool || null, lat, detail,
      ev.step === "execute" || ev.step === "route");
  });
  const foot = el("div", "trace-foot",
    "No internal reasoning is stored — only the observable trace (PS P10).");
  panel.appendChild(foot);
  $("#traceMeta").textContent = route ? `· ${route.planner}` : "";
  $("#traceJson").disabled = false;
  $("#copyAnswer").disabled = false;
}

function showTraceJson(trace) {
  const w = window.open("", "_blank");
  w.document.write("<!doctype html><title>SatQuery AI — trace</title>" +
    "<pre style='font:12px ui-monospace,monospace;background:#0e1116;color:#e6edf3;padding:24px;margin:0;min-height:100vh'>" +
    JSON.stringify(trace, null, 2).replace(/</g, "&lt;") + "</pre>");
}

// ---- data flows -------------------------------------------------------------

async function loadDemo(setName) {
  dismissHero();
  const w = addWorking(`Loading demo set: ${esc(setName)}…`);
  try {
    const d = await api(`/api/v1/demo?set=${setName}`, { method: "POST" });
    state.requestId = d.request_id;
    state.demo = true;
    state.inventory = d.inventory;
    state.baseUrls = d.inventory.map((f) => f.preview_url);
    state.baseIdx = 0;
    state.layers = [];
    renderInventory();
    renderPairBanner(d.pair);
    renderLayerToggles();
    w.remove();
    chat.appendChild(el("div", "msg sys",
      `<b>Demo set loaded · ${esc(setName.replace(/_/g, " "))}.</b><br>
       <span class="muted">Synthetic but spectral-consistent stand-ins (labeled on every card); ask anything below.</span>`));
  } catch (e) {
    dismissHero();
    w.textContent = "Demo load failed: " + e.message;
  }
}

async function uploadFiles(files) {
  if (!files.length) return;
  dismissHero();
  const fd = new FormData();
  [...files].forEach((f) => fd.append("files", f));
  const w = addWorking("Ingesting & validating rasters…");
  try {
    const d = await api("/api/v1/ingest", { method: "POST", body: fd });
    state.requestId = d.request_id;
    state.demo = false;
    state.inventory = d.inventory;
    state.baseUrls = d.inventory.map((f) => f.preview_url);
    state.baseIdx = 0;
    state.layers = [];
    renderInventory();
    renderPairBanner(d.pair);
    renderLayerToggles();
    w.remove();
    chat.appendChild(el("div", "msg sys",
      `<b>${d.inventory.length} image(s) ingested.</b> ${(d.warnings || []).map((x) => esc(x.message)).join(" ")}`));
  } catch (e) {
    w.innerHTML = `<b>Rejected.</b> ${esc(e.message)}<br><span class="muted">Fix: upload GeoTIFF/TIFF; PNG/JPEG only for benchmark datasets.</span>`;
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
    w.innerHTML = `<b>Failed.</b> ${esc(e.message)}`;
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
document.querySelectorAll(".hero-card[data-demo]").forEach((c) =>
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
      `<div><span class="tname">${esc(t.name)}</span>
       ${t.trained ? '<span class="badge trained">trained</span>' : '<span class="badge heuristic">heuristic</span>'}
       <span class="muted"> · task ${esc(t.task)} · budget ${t.latency_budget_s}s</span></div>
       <div class="muted" style="margin-top:5px">${esc(t.description.trim())}</div>
       ${t.vendor ? `<div class="muted" style="margin-top:5px;font-family:var(--mono);font-size:11px">weights: ${esc(t.vendor)}</div>` : ""}`;
    list.appendChild(row);
  });
  $("#modal").classList.remove("hidden");
};
$("#modalClose").onclick = () => $("#modal").classList.add("hidden");
$("#modal").onclick = (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); };

$("#archBtn").onclick = () => $("#archModal").classList.remove("hidden");
$("#archClose").onclick = () => $("#archModal").classList.add("hidden");
$("#archModal").onclick = (e) => { if (e.target.id === "archModal") $("#archModal").classList.add("hidden"); };
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    $("#modal").classList.add("hidden");
    $("#archModal").classList.add("hidden");
  }
});

// One-click full walkthrough: runs all six PS-representative queries in order.
$("#walkthrough").onclick = async () => {
  if (!state.requestId) await loadDemo("bi_temporal");
  const qs = [...document.querySelectorAll(".chip[data-q]")].map((c) => c.dataset.q);
  for (const q of qs) { await runQuery(q); await new Promise((r) => setTimeout(r, 600)); }
};
