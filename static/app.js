// ─── State ──────────────────────────────────────────────────────
const state = {
  concepts: [],
  edges: [],
  stats: { total: 0, abstract: 0, maxDepth: 0 },
  selected: null,
  searchQuery: "",
  view: { x: 0, y: 0, scale: 1 },
};

const $ = (id) => document.getElementById(id);
const commands = {
  "/teach": "Learn from a single example",
  "/apply": "Apply a concept to new input",
  "/why": "Show reasoning trace",
  "/explain": "Show the rule + metadata",
  "/invent": "Discover new abstractions",
  "/concepts": "List all concepts",
  "/export": "Download concepts as JSON",
  "/import": "Load concepts from JSON",
  "/help": "Show help",
};

// ─── Server calls ───────────────────────────────────────────────
async function api(path, body) {
  const r = await fetch(path, body ? {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  } : {});
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function sendCommand(text) {
  try {
    const data = await api("/api/command", { text });
    addMessage("user", text);
    const isError = /couldn'?t|error|not found|no concept|expects|format/i.test(data.reply);
    addMessage(isError ? "error" : "bot", data.reply);
    applyState(data.state);
  } catch (e) {
    addMessage("error", String(e));
  }
}

async function refreshState() {
  try {
    applyState(await api("/api/state"));
  } catch (e) { /* ignore */ }
}

// ─── Chat ───────────────────────────────────────────────────────
const messagesEl = $("messages");

function addMessage(who, text) {
  const el = document.createElement("div");
  el.className = `message ${who}`;
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const head = document.createElement("div");
  head.className = "message-head";
  head.innerHTML = `<span class="who">${who === "user" ? "You" : who === "error" ? "Error" : "Bot"}</span><span class="time">${time}</span>`;

  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = text;

  el.appendChild(head);
  el.appendChild(body);
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // Hide welcome once a message is sent
  const welcome = messagesEl.querySelector(".welcome");
  if (welcome) welcome.remove();
}

// ─── State application ──────────────────────────────────────────
function applyState(s) {
  state.concepts = s.concepts || [];
  state.edges = s.edges || [];
  state.stats = s.stats || { total: 0, abstract: 0, maxDepth: 0 };

  $("stat-total").textContent = state.stats.total;
  $("stat-abstract").textContent = state.stats.abstract;
  $("stat-depth").textContent = state.stats.maxDepth;
  $("concept-count").textContent = state.stats.total;

  renderConceptList();
  renderDetails();
  renderGraph();
}

// ─── Sidebar ────────────────────────────────────────────────────
function renderConceptList() {
  const list = $("concept-list");
  const q = state.searchQuery.toLowerCase();
  const filtered = state.concepts.filter(c =>
    !q || c.name.toLowerCase().includes(q) || c.program.toLowerCase().includes(q)
  );

  if (state.concepts.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <p>No concepts yet.</p>
        <p class="muted">Use <code>teach "hello" → "OLLEH"</code></p>
      </div>`;
    return;
  }
  if (filtered.length === 0) {
    list.innerHTML = `<div class="empty-state"><p>No matches.</p></div>`;
    return;
  }

  list.innerHTML = "";
  for (const c of filtered) {
    const el = document.createElement("div");
    el.className = "concept-item" +
      (c.isAbstract ? " is-abstract" : "") +
      (state.selected === c.name ? " selected" : "");
    el.innerHTML = `
      <div class="concept-name">
        <span class="dot ${c.isAbstract ? "abstract" : "learned"}"></span>
        ${escapeHtml(c.name)}
      </div>
      <div class="concept-program">${escapeHtml(c.program)}</div>
    `;
    el.addEventListener("click", () => selectConcept(c.name));
    list.appendChild(el);
  }
}

function selectConcept(name) {
  state.selected = state.selected === name ? null : name;
  renderConceptList();
  renderDetails();
  renderGraph();
}

function renderDetails() {
  const box = $("details");
  if (!state.selected) { box.hidden = true; return; }
  const c = state.concepts.find(x => x.name === state.selected);
  if (!c) { box.hidden = true; return; }

  const examples = c.examples.length
    ? c.examples.map(e => `<div class="example">${escapeHtml(JSON.stringify(e.inputs))} → ${escapeHtml(JSON.stringify(e.output))}</div>`).join("")
    : `<div class="muted">(none recorded)</div>`;

  box.innerHTML = `
    <h3>${escapeHtml(c.name)}</h3>
    <div class="row">
      <span class="row-label">Program</span>
      <div class="row-value code">${escapeHtml(c.program)}</div>
    </div>
    <div class="row">
      <span class="row-label">Dependencies</span>
      <div class="row-value">${c.deps.map(escapeHtml).join(", ") || "—"}</div>
    </div>
    <div class="row">
      <span class="row-label">Used by</span>
      <div class="row-value">${c.dependents.map(escapeHtml).join(", ") || "—"}</div>
    </div>
    <div class="row">
      <span class="row-label">Examples</span>
      <div class="examples">${examples}</div>
    </div>
  `;
  box.hidden = false;
}

// ─── Graph rendering ────────────────────────────────────────────
const svg = $("svg");
const viewport = $("viewport");
const graphEmpty = $("graph-empty");

function renderGraph() {
  viewport.innerHTML = "";
  graphEmpty.hidden = state.concepts.length > 0;

  if (state.concepts.length === 0) return;

  const svgRect = svg.getBoundingClientRect();
  const W = svgRect.width || 600;
  const H = svgRect.height || 400;

  const positions = layoutGraph(state.concepts, state.edges, W, H);

  // Draw edges first (behind nodes)
  for (const [from, to] of state.edges) {
    if (!positions[from] || !positions[to]) continue;
    const [x1, y1] = positions[from];
    const [x2, y2] = positions[to];
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    // Slight curve for readability
    const mx = (x1 + x2) / 2;
    path.setAttribute("d", `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`);
    path.setAttribute("class", "graph-edge");
    path.setAttribute("marker-end", "url(#arrow)");
    viewport.appendChild(path);
  }

  // Draw nodes
  const nodeMap = Object.fromEntries(state.concepts.map(c => [c.name, c]));
  for (const [name, [x, y]] of Object.entries(positions)) {
    const c = nodeMap[name];
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", "graph-node " + (c.isAbstract ? "abstract" : "learned") +
                   (state.selected === name ? " selected" : ""));
    g.setAttribute("transform", `translate(${x}, ${y})`);
    const r = c.isAbstract ? 24 : 22;
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("r", r);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.textContent = shorten(name, 8);
    g.appendChild(circle);
    g.appendChild(text);
    g.addEventListener("click", (e) => { e.stopPropagation(); selectConcept(name); });
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${name} = ${c.program}`;
    g.appendChild(title);
    viewport.appendChild(g);
  }

  applyView();
}

// Layered DAG layout with barycenter ordering
function layoutGraph(concepts, edges, W, H) {
  // Group by depth
  const layers = {};
  for (const c of concepts) {
    (layers[c.depth] ||= []).push(c);
  }
  const depths = Object.keys(layers).map(Number).sort((a, b) => a - b);
  const maxD = Math.max(...depths, 0);

  // Barycenter ordering
  const order = {};
  for (const d of depths) layers[d].forEach((c, i) => order[c.name] = i);

  for (let iter = 0; iter < 4; iter++) {
    const dir = iter % 2 === 0 ? 1 : -1;
    const keys = dir > 0 ? depths : [...depths].reverse();
    for (const d of keys) {
      const layer = layers[d];
      const neighborLayer = layers[d - dir];
      if (!neighborLayer) continue;
      const bcs = layer.map(c => {
        const neighbors = edges
          .filter(([a, b]) => dir > 0 ? b === c.name : a === c.name)
          .map(([a, b]) => dir > 0 ? a : b)
          .filter(n => n in order);
        if (!neighbors.length) return order[c.name];
        return neighbors.reduce((s, n) => s + order[n], 0) / neighbors.length;
      });
      const reordered = layer
        .map((c, i) => ({ c, bc: bcs[i] }))
        .sort((a, b) => a.bc - b.bc)
        .map(x => x.c);
      layers[d] = reordered;
      reordered.forEach((c, i) => order[c.name] = i);
    }
  }

  // Compute positions
  const positions = {};
  const padX = 60, padY = 50;
  const availW = W - padX * 2;
  const availH = H - padY * 2;
  for (const d of depths) {
    const layer = layers[d];
    const y = H - padY - (maxD > 0 ? (d / maxD) * availH : availH / 2);
    const count = layer.length;
    for (let i = 0; i < count; i++) {
      const x = count === 1 ? W / 2 : padX + (i / (count - 1)) * availW;
      positions[layer[i].name] = [x, y];
    }
  }
  return positions;
}

// ─── Pan / zoom ─────────────────────────────────────────────────
function applyView() {
  viewport.setAttribute("transform",
    `translate(${state.view.x}, ${state.view.y}) scale(${state.view.scale})`);
}

const graphEl = $("graph");
let dragging = false, dragStart = null;

graphEl.addEventListener("mousedown", (e) => {
  if (e.target.closest(".graph-node")) return;
  dragging = true;
  dragStart = [e.clientX - state.view.x, e.clientY - state.view.y];
});
window.addEventListener("mousemove", (e) => {
  if (!dragging) return;
  state.view.x = e.clientX - dragStart[0];
  state.view.y = e.clientY - dragStart[1];
  applyView();
});
window.addEventListener("mouseup", () => { dragging = false; });

graphEl.addEventListener("wheel", (e) => {
  e.preventDefault();
  const rect = svg.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
  const newScale = Math.max(0.3, Math.min(3, state.view.scale * factor));
  const k = newScale / state.view.scale;
  state.view.x = mx - k * (mx - state.view.x);
  state.view.y = my - k * (my - state.view.y);
  state.view.scale = newScale;
  applyView();
}, { passive: false });

$("zoom-in").onclick = () => { state.view.scale = Math.min(3, state.view.scale * 1.2); applyView(); };
$("zoom-out").onclick = () => { state.view.scale = Math.max(0.3, state.view.scale / 1.2); applyView(); };
$("zoom-fit").onclick = () => { state.view = { x: 0, y: 0, scale: 1 }; renderGraph(); };

// ─── Input ──────────────────────────────────────────────────────
const input = $("input");
const sendBtn = $("send");
const suggestions = $("suggestions");

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 200) + "px";
  updateSuggestions();
});

input.addEventListener("keydown", (e) => {
  const active = suggestions.querySelector(".suggestion.active");
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    if (suggestions.hidden || !suggestions.children.length) return;
    e.preventDefault();
    const list = [...suggestions.querySelectorAll(".suggestion")];
    let idx = list.indexOf(active);
    idx = e.key === "ArrowDown" ? (idx + 1) % list.length : (idx - 1 + list.length) % list.length;
    list.forEach(x => x.classList.remove("active"));
    list[idx].classList.add("active");
    return;
  }
  if (e.key === "Tab" && active) {
    e.preventDefault();
    input.value = active.dataset.cmd;
    updateSuggestions();
    return;
  }
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (active) { input.value = active.dataset.cmd; suggestions.hidden = true; }
    else submitInput();
  }
  if (e.key === "Escape") { suggestions.hidden = true; }
});

sendBtn.onclick = submitInput;

async function submitInput() {
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  input.style.height = "auto";
  suggestions.hidden = true;
  sendBtn.disabled = true;
  try { await sendCommand(text); }
  finally { sendBtn.disabled = false; input.focus(); }
}

function updateSuggestions() {
  const text = input.value;
  let matches = [];

  if (/^\/\S*$/.test(text)) {
    matches = Object.entries(commands)
      .filter(([cmd]) => cmd.startsWith(text))
      .map(([cmd, desc]) => ({ cmd, desc }));
  } else if (/^\/[a-z]+\s+\w*$/.test(text)) {
    const [cmd, prefix] = text.split(/\s+/);
    if (["/apply", "/why", "/explain"].includes(cmd)) {
      matches = state.concepts
        .filter(c => c.name.startsWith(prefix))
        .map(c => ({ cmd: `${cmd} ${c.name}`, desc: c.program }));
    }
  }

  if (!matches.length) { suggestions.hidden = true; return; }
  suggestions.innerHTML = "";
  matches.slice(0, 8).forEach((m, i) => {
    const el = document.createElement("div");
    el.className = "suggestion" + (i === 0 ? " active" : "");
    el.dataset.cmd = m.cmd;
    el.innerHTML = `<span class="s-cmd">${escapeHtml(m.cmd)}</span><span class="s-desc">${escapeHtml(m.desc)}</span>`;
    el.onclick = () => { input.value = m.cmd; updateSuggestions(); input.focus(); };
    suggestions.appendChild(el);
  });
  suggestions.hidden = false;
}

// ─── Sidebar search ─────────────────────────────────────────────
$("search").addEventListener("input", (e) => {
  state.searchQuery = e.target.value;
  renderConceptList();
});

// ─── Welcome chips ──────────────────────────────────────────────
document.querySelectorAll(".chip[data-cmd]").forEach(chip => {
  chip.onclick = () => {
    input.value = chip.dataset.cmd;
    input.focus();
    submitInput();
  };
});

// ─── Export / import ────────────────────────────────────────────
$("btn-export").onclick = async () => {
  const data = await api("/api/export");
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ostl-concepts-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
  toast("Concepts exported", "success");
};

$("btn-import").onclick = () => openModal(`
  <h2>Import concepts</h2>
  <p>Select a JSON file previously exported from OSTL. This <strong>replaces</strong> the current concept set.</p>
  <p style="margin-top:16px"><input type="file" id="import-file" accept=".json,application/json"></p>
  <p style="margin-top:20px;text-align:right">
    <button class="chip" id="import-cancel">Cancel</button>
    <button class="chip" id="import-go" style="background:var(--accent);color:white;border-color:var(--accent)">Import</button>
  </p>
`, () => {
  $("import-cancel").onclick = closeModal;
  $("import-go").onclick = async () => {
    const file = $("import-file").files[0];
    if (!file) return toast("No file selected", "error");
    try {
      const data = JSON.parse(await file.text());
      const res = await api("/api/import", data);
      applyState(res.state);
      closeModal();
      toast(`Imported ${res.imported} concept(s)`, "success");
    } catch (e) {
      toast("Import failed: " + e.message, "error");
    }
  };
});

// ─── Theme ──────────────────────────────────────────────────────
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  localStorage.setItem("ostl-theme", t);
}
$("btn-theme").onclick = () => {
  const cur = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(cur === "dark" ? "light" : "dark");
};
applyTheme(localStorage.getItem("ostl-theme") || "dark");

// ─── Help ───────────────────────────────────────────────────────
$("btn-help").onclick = showHelp;

function showHelp() {
  openModal(`
    <h2>Help</h2>
    <p>OSTL learns a general rule from a single example and applies it to new inputs.</p>
    <h3>Commands</h3>
    <table class="cmd-table">
      <tr><td>teach &lt;in&gt; → &lt;out&gt;</td><td>Learn from a single example</td></tr>
      <tr><td>apply &lt;name&gt; &lt;in&gt;</td><td>Apply a concept</td></tr>
      <tr><td>why &lt;name&gt; &lt;in&gt;</td><td>Show the reasoning trace</td></tr>
      <tr><td>explain &lt;name&gt;</td><td>Show the rule + metadata</td></tr>
      <tr><td>concepts</td><td>List all concepts</td></tr>
      <tr><td>invent</td><td>Discover new abstractions from recurring patterns</td></tr>
    </table>
    <h3>Keyboard</h3>
    <p>
      <span class="kbd">Enter</span> send ·
      <span class="kbd">Shift</span>+<span class="kbd">Enter</span> newline ·
      <span class="kbd">↑</span>/<span class="kbd">↓</span> navigate suggestions ·
      <span class="kbd">Tab</span> accept suggestion ·
      <span class="kbd">?</span> help
    </p>
    <h3>Example session</h3>
    <pre style="background:var(--code-bg);padding:12px;border-radius:6px;font-family:var(--mono);font-size:12px;overflow:auto"><code>teach "hello" -> "OLLEH"
teach "abc" -> "CBA"
invent
concepts
why concept_2 "xyz"</code></pre>
  `);
}

// ─── Modal plumbing ─────────────────────────────────────────────
const modal = $("modal");
const modalBody = $("modal-body");

function openModal(html, onMount) {
  modalBody.innerHTML = html;
  modal.hidden = false;
  if (onMount) onMount();
}
function closeModal() { modal.hidden = true; modalBody.innerHTML = ""; }
$("modal-close").onclick = closeModal;
modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { closeModal(); suggestions.hidden = true; }
  if (e.key === "?" && document.activeElement !== input) {
    e.preventDefault(); showHelp();
  }
});

// ─── Toast ──────────────────────────────────────────────────────
let toastTimer;
function toast(msg, type = "") {
  const el = $("toast");
  el.textContent = msg;
  el.className = `toast show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.className = "toast", 2800);
}

// ─── Utilities ──────────────────────────────────────────────────
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}
function shorten(s, n) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }

// ─── Boot ───────────────────────────────────────────────────────
window.addEventListener("resize", () => { if (state.concepts.length) renderGraph(); });
refreshState().then(() => {
  // Auto-import from localStorage if the server is fresh
});
input.focus();