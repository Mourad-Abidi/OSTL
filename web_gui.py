# web_gui.py
import json, os, webbrowser, mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from bot import Bot

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# ── Embedded defaults — written to static/ on first run ─────────
DEFAULT_INDEX = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OSTL — One-Shot Concept Learner</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header class="header">
  <div class="brand">
    <div class="logo">◆</div>
    <div class="brand-text"><h1>OSTL</h1><span>One-Shot Concept Learner</span></div>
  </div>
  <div class="stats">
    <div class="stat"><span class="stat-value" id="stat-total">0</span><span class="stat-label">concepts</span></div>
    <div class="stat"><span class="stat-value" id="stat-abstract">0</span><span class="stat-label">invented</span></div>
    <div class="stat"><span class="stat-value" id="stat-depth">0</span><span class="stat-label">max depth</span></div>
  </div>
  <div class="actions">
    <button class="icon-btn" id="btn-help" title="Help">?</button>
    <button class="icon-btn" id="btn-export" title="Export">↓</button>
    <button class="icon-btn" id="btn-import" title="Import">↑</button>
    <button class="icon-btn" id="btn-theme" title="Toggle theme">◐</button>
  </div>
</header>
<main class="main">
  <aside class="sidebar">
    <div class="sidebar-head"><h2>Concepts</h2><span class="badge" id="concept-count">0</span></div>
    <div class="search-wrap"><input type="search" id="search" placeholder="Search concepts…" autocomplete="off"></div>
    <div class="concept-list" id="concept-list">
      <div class="empty-state"><p>No concepts yet.</p><p class="muted">Use <code>teach "hello" → "OLLEH"</code></p></div>
    </div>
    <div class="details" id="details" hidden></div>
  </aside>
  <section class="chat">
    <div class="chat-head"><h2>Chat</h2><div class="chat-hint">Enter to send · Shift+Enter for newline</div></div>
    <div class="chat-messages" id="messages">
      <div class="welcome">
        <div class="welcome-icon">◆</div>
        <h3>Welcome to OSTL</h3>
        <p>Teach me a rule from a single example — I'll infer the general program, remember it, and reuse it.</p>
        <div class="welcome-examples">
          <button class="chip" data-cmd='teach "hello" -> "OLLEH"'>teach "hello" → "OLLEH"</button>
          <button class="chip" data-cmd='teach 3 -> 9'>teach 3 → 9</button>
          <button class="chip" data-cmd='invent'>invent</button>
          <button class="chip" data-cmd='help'>help</button>
        </div>
      </div>
    </div>
    <div class="chat-input">
      <div class="suggestions" id="suggestions" hidden></div>
      <div class="input-wrap">
        <textarea id="input" rows="1" placeholder='teach "hello" -> "OLLEH"   ·   /help'></textarea>
        <button class="send-btn" id="send" title="Send">↵</button>
      </div>
    </div>
  </section>
  <aside class="graph-panel">
    <div class="graph-head">
      <h2>Graph</h2>
      <div class="graph-controls">
        <button class="icon-btn" id="zoom-out" title="Zoom out">−</button>
        <button class="icon-btn" id="zoom-fit" title="Fit">⤢</button>
        <button class="icon-btn" id="zoom-in" title="Zoom in">+</button>
      </div>
    </div>
    <div class="graph" id="graph">
      <svg id="svg" xmlns="http://www.w3.org/2000/svg">
        <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--edge)"/></marker></defs>
        <g id="viewport"></g>
      </svg>
      <div class="graph-empty" id="graph-empty"><p>The concept graph will appear here.</p></div>
    </div>
    <div class="legend"><span><i class="dot learned"></i>learned</span><span><i class="dot abstract"></i>invented</span></div>
  </aside>
</main>
<div class="toast" id="toast"></div>
<div class="modal" id="modal" hidden>
  <div class="modal-card"><button class="icon-btn modal-close" id="modal-close">×</button><div class="modal-body" id="modal-body"></div></div>
</div>
<script src="/app.js"></script>
</body>
</html>
"""

DEFAULT_CSS = r""":root, :root[data-theme="dark"] {
  --bg:#0a0a0b; --surface:#121214; --surface-2:#17171a; --surface-3:#1f1f23; --surface-4:#27272d;
  --border:#26262c; --border-strong:#35353d; --text:#f4f4f5; --text-2:#a1a1aa; --text-3:#6b6b75;
  --accent:#4f8cff; --accent-hover:#6b9dff; --accent-soft:rgba(79,140,255,.12);
  --success:#22c55e; --error:#ef4444; --abstract:#a78bfa; --abstract-soft:rgba(167,139,250,.12);
  --code-bg:#0d0d0f; --edge:#3a3a42;
  --shadow-md:0 4px 16px rgba(0,0,0,.5); --shadow-lg:0 12px 40px rgba(0,0,0,.6);
  --radius:8px; --radius-lg:12px;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --sans:-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, system-ui, sans-serif;
}
:root[data-theme="light"] {
  --bg:#fff; --surface:#fafafa; --surface-2:#f4f4f5; --surface-3:#ebebed; --surface-4:#e0e0e3;
  --border:#e5e5e8; --border-strong:#d0d0d5; --text:#0a0a0b; --text-2:#52525b; --text-3:#a1a1aa;
  --accent:#2563eb; --accent-hover:#1d4ed8; --accent-soft:rgba(37,99,235,.10);
  --abstract:#7c3aed; --abstract-soft:rgba(124,58,237,.10); --code-bg:#f6f8fa; --edge:#c8c8cc;
  --shadow-md:0 4px 16px rgba(0,0,0,.08); --shadow-lg:0 12px 40px rgba(0,0,0,.12);
}
*{box-sizing:border-box} html,body{margin:0;height:100vh;overflow:hidden}
body{font-family:var(--sans);font-size:13px;color:var(--text);background:var(--bg);-webkit-font-smoothing:antialiased;display:grid;grid-template-rows:56px 1fr}
button{font-family:inherit;cursor:pointer}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--surface-4);border-radius:10px;border:2px solid var(--bg)}
.header{display:flex;align-items:center;justify-content:space-between;padding:0 20px;background:var(--surface);border-bottom:1px solid var(--border);z-index:10}
.brand{display:flex;align-items:center;gap:12px}
.logo{width:32px;height:32px;display:grid;place-items:center;border-radius:8px;background:linear-gradient(135deg,var(--accent),var(--abstract));color:#fff;font-size:14px}
.brand-text h1{margin:0;font-size:14px;font-weight:600}.brand-text span{font-size:11px;color:var(--text-3)}
.stats{display:flex;gap:24px}.stat{display:flex;align-items:baseline;gap:6px}
.stat-value{font-size:16px;font-weight:600;font-variant-numeric:tabular-nums}
.stat-label{font-size:11px;color:var(--text-3);text-transform:uppercase;letter-spacing:.04em}
.actions{display:flex;gap:6px}
.icon-btn{width:32px;height:32px;display:grid;place-items:center;background:transparent;border:1px solid transparent;border-radius:6px;color:var(--text-2);font-size:14px;font-weight:500;transition:all .15s}
.icon-btn:hover{background:var(--surface-3);color:var(--text);border-color:var(--border)}
.main{display:grid;grid-template-columns:280px 1fr 380px;height:100%;overflow:hidden}
.sidebar{display:flex;flex-direction:column;background:var(--surface);border-right:1px solid var(--border);overflow:hidden}
.sidebar-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px 10px}
.sidebar-head h2{margin:0;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-2)}
.badge{font-size:11px;font-weight:600;padding:2px 8px;background:var(--surface-3);color:var(--text-2);border-radius:10px}
.search-wrap{padding:0 12px 10px}
#search{width:100%;padding:7px 10px;background:var(--surface-2);color:var(--text);border:1px solid var(--border);border-radius:6px;font:inherit;font-size:12px}
#search:focus{outline:none;border-color:var(--accent)}
.concept-list{flex:1;overflow-y:auto;padding:4px 8px 8px}
.concept-item{padding:8px 10px;margin-bottom:2px;border-radius:6px;cursor:pointer;border:1px solid transparent;transition:background .1s}
.concept-item:hover{background:var(--surface-2)}
.concept-item.selected{background:var(--accent-soft);border-color:var(--accent)}
.concept-item.is-abstract.selected{background:var(--abstract-soft);border-color:var(--abstract)}
.concept-name{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:500;color:var(--text)}
.concept-name .dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.dot.learned{background:var(--accent)}.dot.abstract{background:var(--abstract)}
.concept-program{margin-top:3px;font-family:var(--mono);font-size:11px;color:var(--text-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.details{border-top:1px solid var(--border);padding:14px 16px;background:var(--surface-2);max-height:45%;overflow-y:auto;font-size:12px}
.details h3{margin:0 0 10px;font-size:13px;font-weight:600}
.details .row{margin:6px 0;display:flex;flex-direction:column;gap:2px}
.details .row-label{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-3)}
.details .row-value{font-family:var(--mono);font-size:11px;color:var(--text);word-break:break-all}
.details .row-value.code{background:var(--code-bg);padding:4px 8px;border-radius:4px}
.details .example{font-family:var(--mono);font-size:11px;padding:4px 8px;background:var(--code-bg);border-radius:4px;margin-bottom:4px}
.chat{display:flex;flex-direction:column;background:var(--bg);overflow:hidden}
.chat-head{display:flex;align-items:center;justify-content:space-between;padding:14px 20px 10px;border-bottom:1px solid var(--border)}
.chat-head h2{margin:0;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-2)}
.chat-hint{font-size:11px;color:var(--text-3)}
.chat-messages{flex:1;overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:12px;scroll-behavior:smooth}
.welcome{text-align:center;padding:40px 20px;color:var(--text-2)}
.welcome-icon{font-size:40px;margin-bottom:12px;background:linear-gradient(135deg,var(--accent),var(--abstract));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.welcome h3{margin:0 0 8px;font-size:16px;color:var(--text);font-weight:600}
.welcome p{margin:0 0 20px;font-size:13px;max-width:400px;margin-inline:auto}
.welcome-examples{display:flex;flex-wrap:wrap;justify-content:center;gap:6px}
.chip{padding:6px 12px;font-family:var(--mono);font-size:11px;background:var(--surface-2);color:var(--text-2);border:1px solid var(--border);border-radius:6px;transition:all .15s}
.chip:hover{background:var(--surface-3);color:var(--text);border-color:var(--border-strong)}
.message{display:flex;flex-direction:column;gap:4px;animation:slideIn .2s ease-out}
@keyframes slideIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
.message-head{display:flex;align-items:center;gap:8px;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-3)}
.message-head .who{font-weight:600}.message.user .who{color:var(--accent)}.message.bot .who{color:var(--abstract)}
.message-head .time{margin-left:auto;font-variant-numeric:tabular-nums}
.message-body{font-size:13px;line-height:1.6;color:var(--text);white-space:pre-wrap;word-wrap:break-word}
.message.bot .message-body{background:var(--surface-2);padding:10px 14px;border-radius:8px;border-left:2px solid var(--abstract)}
.message.error .message-body{background:rgba(239,68,68,.08);border-left-color:var(--error);color:#fca5a5}
.chat-input{padding:12px 20px 16px;background:var(--surface);border-top:1px solid var(--border);position:relative}
.input-wrap{display:flex;gap:8px;align-items:flex-end;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius);padding:6px 6px 6px 12px;transition:border-color .15s}
.input-wrap:focus-within{border-color:var(--accent)}
#input{flex:1;background:transparent;border:none;outline:none;color:var(--text);font-family:var(--mono);font-size:13px;resize:none;line-height:1.5;padding:6px 0;max-height:200px;overflow-y:auto}
#input::placeholder{color:var(--text-3)}
.send-btn{padding:6px 14px;background:var(--accent);color:#fff;border:none;border-radius:6px;font-weight:600;font-size:13px;transition:background .15s}
.send-btn:hover{background:var(--accent-hover)}.send-btn:disabled{opacity:.5;cursor:not-allowed}
.suggestions{position:absolute;left:20px;right:20px;bottom:calc(100% - 4px);background:var(--surface-2);border:1px solid var(--border-strong);border-radius:var(--radius);box-shadow:var(--shadow-md);max-height:200px;overflow-y:auto;z-index:20}
.suggestion{display:flex;align-items:baseline;gap:12px;padding:8px 12px;cursor:pointer;font-size:12px;transition:background .1s}
.suggestion:hover,.suggestion.active{background:var(--surface-3)}
.suggestion .s-cmd{font-family:var(--mono);color:var(--accent);font-weight:500}
.suggestion .s-desc{color:var(--text-3);font-size:11px;margin-left:auto}
.graph-panel{display:flex;flex-direction:column;background:var(--surface);border-left:1px solid var(--border);overflow:hidden}
.graph-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px 10px;border-bottom:1px solid var(--border)}
.graph-head h2{margin:0;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-2)}
.graph-controls{display:flex;gap:4px}
.graph{flex:1;position:relative;overflow:hidden;background:radial-gradient(circle at 1px 1px,var(--border) 1px,transparent 0) 0 0/24px 24px,var(--bg);cursor:grab}
.graph:active{cursor:grabbing}
#svg{width:100%;height:100%;display:block}
.graph-empty{position:absolute;inset:0;display:grid;place-items:center;color:var(--text-3);font-size:12px;text-align:center;padding:20px;pointer-events:none}
.graph-edge{fill:none;stroke:var(--edge);stroke-width:1.5}
.graph-node{cursor:pointer}
.graph-node circle{stroke:var(--bg);stroke-width:2;transition:filter .15s}
.graph-node.learned circle{fill:var(--accent)}.graph-node.abstract circle{fill:var(--abstract)}
.graph-node text{fill:#fff;font-family:var(--sans);font-size:9px;font-weight:600;text-anchor:middle;dominant-baseline:middle;pointer-events:none;user-select:none}
.graph-node:hover circle{filter:brightness(1.2)}
.graph-node.selected circle{stroke:var(--text);stroke-width:2.5;filter:drop-shadow(0 0 8px currentColor)}
.legend{display:flex;gap:16px;padding:10px 16px;border-top:1px solid var(--border);font-size:11px;color:var(--text-3)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend .dot{width:8px;height:8px;border-radius:50%}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(100px);padding:10px 20px;background:var(--surface-3);color:var(--text);border:1px solid var(--border-strong);border-radius:8px;box-shadow:var(--shadow-lg);font-size:12px;opacity:0;pointer-events:none;transition:all .25s ease;z-index:100}
.toast.show{transform:translateX(-50%) translateY(0);opacity:1}
.toast.success{border-color:var(--success)}.toast.error{border-color:var(--error)}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.6);display:grid;place-items:center;z-index:200}
.modal[hidden]{display:none}
.modal-card{background:var(--surface);border:1px solid var(--border-strong);border-radius:var(--radius-lg);box-shadow:var(--shadow-lg);width:min(560px,calc(100vw - 40px));max-height:80vh;overflow:auto;position:relative;padding:24px}
.modal-close{position:absolute;top:12px;right:12px}
.modal-body h2{margin:0 0 16px;font-size:16px}
.modal-body h3{margin:20px 0 8px;font-size:13px;color:var(--text-2);text-transform:uppercase;letter-spacing:.06em}
.modal-body p,.modal-body li{font-size:13px;color:var(--text-2);line-height:1.6}
.modal-body code{font-family:var(--mono);font-size:12px;background:var(--code-bg);padding:2px 6px;border-radius:3px;color:var(--text)}
.modal-body .kbd{display:inline-block;padding:1px 6px;font-family:var(--mono);font-size:11px;background:var(--surface-3);border:1px solid var(--border-strong);border-bottom-width:2px;border-radius:4px}
.modal-body .cmd-table{width:100%;border-collapse:collapse;margin-top:8px}
.modal-body .cmd-table td{padding:6px 8px;border-bottom:1px solid var(--border);font-size:12px}
.modal-body .cmd-table td:first-child{font-family:var(--mono);color:var(--accent)}
.empty-state{padding:20px;text-align:center;color:var(--text-2);font-size:12px}
.empty-state .muted{color:var(--text-3);font-size:11px}
.empty-state code{font-family:var(--mono);font-size:11px;background:var(--code-bg);padding:2px 6px;border-radius:3px}
"""

DEFAULT_JS = r"""const state={concepts:[],edges:[],stats:{total:0,abstract:0,maxDepth:0},selected:null,searchQuery:"",view:{x:0,y:0,scale:1}};
const $=id=>document.getElementById(id);
const commands={"/teach":"Learn from a single example","/apply":"Apply a concept","/why":"Reasoning trace","/explain":"Show the rule","/invent":"Discover abstractions","/concepts":"List concepts","/export":"Download JSON","/import":"Load JSON","/help":"Help"};
async function api(p,b){const r=await fetch(p,b?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)}:{});if(!r.ok)throw new Error(await r.text());return r.json()}
async function sendCommand(t){try{const d=await api("/api/command",{text:t});addMessage("user",t);const e=/couldn'?t|error|not found|no concept|expects|format/i.test(d.reply);addMessage(e?"error":"bot",d.reply);applyState(d.state)}catch(e){addMessage("error",String(e))}}
async function refreshState(){try{applyState(await api("/api/state"))}catch(e){}}
const messagesEl=$("messages");
function addMessage(who,text){const el=document.createElement("div");el.className="message "+who;const time=new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"});const head=document.createElement("div");head.className="message-head";head.innerHTML=`<span class="who">${who==="user"?"You":who==="error"?"Error":"Bot"}</span><span class="time">${time}</span>`;const body=document.createElement("div");body.className="message-body";body.textContent=text;el.appendChild(head);el.appendChild(body);messagesEl.appendChild(el);messagesEl.scrollTop=messagesEl.scrollHeight;const w=messagesEl.querySelector(".welcome");if(w)w.remove()}
function applyState(s){state.concepts=s.concepts||[];state.edges=s.edges||[];state.stats=s.stats||{total:0,abstract:0,maxDepth:0};$("stat-total").textContent=state.stats.total;$("stat-abstract").textContent=state.stats.abstract;$("stat-depth").textContent=state.stats.maxDepth;$("concept-count").textContent=state.stats.total;renderConceptList();renderDetails();renderGraph()}
function renderConceptList(){const list=$("concept-list");const q=state.searchQuery.toLowerCase();const f=state.concepts.filter(c=>!q||c.name.toLowerCase().includes(q)||c.program.toLowerCase().includes(q));if(state.concepts.length===0){list.innerHTML='<div class="empty-state"><p>No concepts yet.</p><p class="muted">Use <code>teach "hello" → "OLLEH"</code></p></div>';return}if(f.length===0){list.innerHTML='<div class="empty-state"><p>No matches.</p></div>';return}list.innerHTML="";for(const c of f){const el=document.createElement("div");el.className="concept-item"+(c.isAbstract?" is-abstract":"")+(state.selected===c.name?" selected":"");el.innerHTML=`<div class="concept-name"><span class="dot ${c.isAbstract?"abstract":"learned"}"></span>${esc(c.name)}</div><div class="concept-program">${esc(c.program)}</div>`;el.addEventListener("click",()=>selectConcept(c.name));list.appendChild(el)}}
function selectConcept(n){state.selected=state.selected===n?null:n;renderConceptList();renderDetails();renderGraph()}
function renderDetails(){const b=$("details");if(!state.selected){b.hidden=true;return}const c=state.concepts.find(x=>x.name===state.selected);if(!c){b.hidden=true;return}const ex=c.examples.length?c.examples.map(e=>`<div class="example">${esc(JSON.stringify(e.inputs))} → ${esc(JSON.stringify(e.output))}</div>`).join(""):'<div class="muted">(none)</div>';b.innerHTML=`<h3>${esc(c.name)}</h3><div class="row"><span class="row-label">Program</span><div class="row-value code">${esc(c.program)}</div></div><div class="row"><span class="row-label">Dependencies</span><div class="row-value">${c.deps.map(esc).join(", ")||"—"}</div></div><div class="row"><span class="row-label">Used by</span><div class="row-value">${c.dependents.map(esc).join(", ")||"—"}</div></div><div class="row"><span class="row-label">Examples</span><div>${ex}</div></div>`;b.hidden=false}
const svg=$("svg"),viewport=$("viewport"),graphEmpty=$("graph-empty");
function renderGraph(){viewport.innerHTML="";graphEmpty.hidden=state.concepts.length>0;if(state.concepts.length===0)return;const r=svg.getBoundingClientRect();const W=r.width||600,H=r.height||400;const pos=layoutGraph(state.concepts,state.edges,W,H);for(const[a,b]of state.edges){if(!pos[a]||!pos[b])continue;const[x1,y1]=pos[a],[x2,y2]=pos[b];const p=document.createElementNS("http://www.w3.org/2000/svg","path");const mx=(x1+x2)/2;p.setAttribute("d",`M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`);p.setAttribute("class","graph-edge");p.setAttribute("marker-end","url(#arrow)");viewport.appendChild(p)}const nm=Object.fromEntries(state.concepts.map(c=>[c.name,c]));for(const[n,[x,y]]of Object.entries(pos)){const c=nm[n];const g=document.createElementNS("http://www.w3.org/2000/svg","g");g.setAttribute("class","graph-node "+(c.isAbstract?"abstract":"learned")+(state.selected===n?" selected":""));g.setAttribute("transform",`translate(${x}, ${y})`);const circ=document.createElementNS("http://www.w3.org/2000/svg","circle");circ.setAttribute("r",c.isAbstract?24:22);const t=document.createElementNS("http://www.w3.org/2000/svg","text");t.textContent=n.length>8?n.slice(0,7)+"…":n;g.appendChild(circ);g.appendChild(t);g.addEventListener("click",e=>{e.stopPropagation();selectConcept(n)});const tt=document.createElementNS("http://www.w3.org/2000/svg","title");tt.textContent=`${n} = ${c.program}`;g.appendChild(tt);viewport.appendChild(g)}applyView()}
function layoutGraph(concepts,edges,W,H){const layers={};for(const c of concepts)(layers[c.depth]||=[]).push(c);const depths=Object.keys(layers).map(Number).sort((a,b)=>a-b);const maxD=Math.max(...depths,0);const order={};for(const d of depths)layers[d].forEach((c,i)=>order[c.name]=i);for(let iter=0;iter<4;iter++){const dir=iter%2===0?1:-1;const keys=dir>0?depths:[...depths].reverse();for(const d of keys){const layer=layers[d];if(!layers[d-dir])continue;const bcs=layer.map(c=>{const nb=edges.filter(([a,b])=>dir>0?b===c.name:a===c.name).map(([a,b])=>dir>0?a:b).filter(n=>n in order);if(!nb.length)return order[c.name];return nb.reduce((s,n)=>s+order[n],0)/nb.length});const rl=layer.map((c,i)=>({c,bc:bcs[i]})).sort((a,b)=>a.bc-b.bc).map(x=>x.c);layers[d]=rl;rl.forEach((c,i)=>order[c.name]=i)}}const pos={};const padX=60,padY=50;const availW=W-padX*2,availH=H-padY*2;for(const d of depths){const layer=layers[d];const y=H-padY-(maxD>0?(d/maxD)*availH:availH/2);const count=layer.length;for(let i=0;i<count;i++){const x=count===1?W/2:padX+(i/(count-1))*availW;pos[layer[i].name]=[x,y]}}return pos}
function applyView(){viewport.setAttribute("transform",`translate(${state.view.x}, ${state.view.y}) scale(${state.view.scale})`)}
const graphEl=$("graph");let drag=false,ds=null;
graphEl.addEventListener("mousedown",e=>{if(e.target.closest(".graph-node"))return;drag=true;ds=[e.clientX-state.view.x,e.clientY-state.view.y]});
window.addEventListener("mousemove",e=>{if(!drag)return;state.view.x=e.clientX-ds[0];state.view.y=e.clientY-ds[1];applyView()});
window.addEventListener("mouseup",()=>{drag=false});
graphEl.addEventListener("wheel",e=>{e.preventDefault();const r=svg.getBoundingClientRect();const mx=e.clientX-r.left,my=e.clientY-r.top;const f=e.deltaY<0?1.1:1/1.1;const ns=Math.max(.3,Math.min(3,state.view.scale*f));const k=ns/state.view.scale;state.view.x=mx-k*(mx-state.view.x);state.view.y=my-k*(my-state.view.y);state.view.scale=ns;applyView()},{passive:false});
$("zoom-in").onclick=()=>{state.view.scale=Math.min(3,state.view.scale*1.2);applyView()};
$("zoom-out").onclick=()=>{state.view.scale=Math.max(.3,state.view.scale/1.2);applyView()};
$("zoom-fit").onclick=()=>{state.view={x:0,y:0,scale:1};renderGraph()};
const input=$("input"),sendBtn=$("send"),suggestions=$("suggestions");
input.addEventListener("input",()=>{input.style.height="auto";input.style.height=Math.min(input.scrollHeight,200)+"px";updSug()});
input.addEventListener("keydown",e=>{const a=suggestions.querySelector(".suggestion.active");if(e.key==="ArrowDown"||e.key==="ArrowUp"){if(suggestions.hidden||!suggestions.children.length)return;e.preventDefault();const list=[...suggestions.querySelectorAll(".suggestion")];let i=list.indexOf(a);i=e.key==="ArrowDown"?(i+1)%list.length:(i-1+list.length)%list.length;list.forEach(x=>x.classList.remove("active"));list[i].classList.add("active");return}if(e.key==="Tab"&&a){e.preventDefault();input.value=a.dataset.cmd;updSug();return}if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();if(a){input.value=a.dataset.cmd;suggestions.hidden=true}else submitInput()}if(e.key==="Escape")suggestions.hidden=true});
sendBtn.onclick=submitInput;
async function submitInput(){const t=input.value.trim();if(!t)return;input.value="";input.style.height="auto";suggestions.hidden=true;sendBtn.disabled=true;try{await sendCommand(t)}finally{sendBtn.disabled=false;input.focus()}}
function updSug(){const t=input.value;let m=[];if(/^\/\S*$/.test(t)){m=Object.entries(commands).filter(([c])=>c.startsWith(t)).map(([c,d])=>({cmd:c,desc:d}))}else if(/^\/[a-z]+\s+\w*$/.test(t)){const[c,p]=t.split(/\s+/);if(["/apply","/why","/explain"].includes(c)){m=state.concepts.filter(x=>x.name.startsWith(p)).map(x=>({cmd:`${c} ${x.name}`,desc:x.program}))}}if(!m.length){suggestions.hidden=true;return}suggestions.innerHTML="";m.slice(0,8).forEach((x,i)=>{const el=document.createElement("div");el.className="suggestion"+(i===0?" active":"");el.dataset.cmd=x.cmd;el.innerHTML=`<span class="s-cmd">${esc(x.cmd)}</span><span class="s-desc">${esc(x.desc)}</span>`;el.onclick=()=>{input.value=x.cmd;updSug();input.focus()};suggestions.appendChild(el)});suggestions.hidden=false}
$("search").addEventListener("input",e=>{state.searchQuery=e.target.value;renderConceptList()});
document.querySelectorAll(".chip[data-cmd]").forEach(c=>{c.onclick=()=>{input.value=c.dataset.cmd;input.focus();submitInput()}});
$("btn-export").onclick=async()=>{const d=await api("/api/export");const b=new Blob([JSON.stringify(d,null,2)],{type:"application/json"});const u=URL.createObjectURL(b);const a=document.createElement("a");a.href=u;a.download=`ostl-concepts-${Date.now()}.json`;a.click();URL.revokeObjectURL(u);toast("Concepts exported","success")};
$("btn-import").onclick=()=>openModal(`<h2>Import concepts</h2><p>Select a JSON file. This <strong>replaces</strong> the current concept set.</p><p style="margin-top:16px"><input type="file" id="import-file" accept=".json,application/json"></p><p style="margin-top:20px;text-align:right"><button class="chip" id="import-cancel">Cancel</button> <button class="chip" id="import-go" style="background:var(--accent);color:white;border-color:var(--accent)">Import</button></p>`,()=>{$("import-cancel").onclick=closeModal;$("import-go").onclick=async()=>{const f=$("import-file").files[0];if(!f)return toast("No file","error");try{const d=JSON.parse(await f.text());const r=await api("/api/import",d);applyState(r.state);closeModal();toast(`Imported ${r.imported} concept(s)`,"success")}catch(e){toast("Import failed: "+e.message,"error")}}});
function applyTheme(t){document.documentElement.setAttribute("data-theme",t);localStorage.setItem("ostl-theme",t)}
$("btn-theme").onclick=()=>{const c=document.documentElement.getAttribute("data-theme")||"dark";applyTheme(c==="dark"?"light":"dark")};
applyTheme(localStorage.getItem("ostl-theme")||"dark");
$("btn-help").onclick=()=>openModal(`<h2>Help</h2><p>OSTL learns a general rule from a single example and applies it to new inputs.</p><h3>Commands</h3><table class="cmd-table"><tr><td>teach &lt;in&gt; → &lt;out&gt;</td><td>Learn from a single example</td></tr><tr><td>apply &lt;name&gt; &lt;in&gt;</td><td>Apply a concept</td></tr><tr><td>why &lt;name&gt; &lt;in&gt;</td><td>Show the reasoning trace</td></tr><tr><td>explain &lt;name&gt;</td><td>Show the rule + metadata</td></tr><tr><td>concepts</td><td>List all concepts</td></tr><tr><td>invent</td><td>Discover new abstractions</td></tr></table><h3>Keyboard</h3><p><span class="kbd">Enter</span> send · <span class="kbd">Shift</span>+<span class="kbd">Enter</span> newline · <span class="kbd">↑</span>/<span class="kbd">↓</span> navigate · <span class="kbd">Tab</span> accept · <span class="kbd">?</span> help</p><h3>Example</h3><pre style="background:var(--code-bg);padding:12px;border-radius:6px;font-family:var(--mono);font-size:12px;overflow:auto"><code>teach "hello" -> "OLLEH"\nteach "abc" -> "CBA"\ninvent\nconcepts\nwhy concept_2 "xyz"</code></pre>`);
const modal=$("modal"),modalBody=$("modal-body");
function openModal(h,m){modalBody.innerHTML=h;modal.hidden=false;if(m)m()}
function closeModal(){modal.hidden=true;modalBody.innerHTML=""}
$("modal-close").onclick=closeModal;
modal.addEventListener("click",e=>{if(e.target===modal)closeModal()});
document.addEventListener("keydown",e=>{if(e.key==="Escape"){closeModal();suggestions.hidden=true}if(e.key==="?"&&document.activeElement!==input){e.preventDefault();$("btn-help").click()}});
let tt;
function toast(m,t=""){const el=$("toast");el.textContent=m;el.className=`toast show ${t}`;clearTimeout(tt);tt=setTimeout(()=>el.className="toast",2800)}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
window.addEventListener("resize",()=>{if(state.concepts.length)renderGraph()});
refreshState().then(()=>{input.focus()});
"""

def ensure_static():
    os.makedirs(STATIC_DIR, exist_ok=True)
    created = []
    for name, content in (("index.html", DEFAULT_INDEX),
                          ("style.css", DEFAULT_CSS),
                          ("app.js",    DEFAULT_JS)):
        path = os.path.join(STATIC_DIR, name)
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            created.append(path)
    if created:
        print("Initialized static assets:")
        for p in created:
            print(f"  created {p}")


class AppServer:
    def __init__(self, host="127.0.0.1", port=8765, max_size=4):
        from neural import NeuralOracle
        try:
            oracle = NeuralOracle.load("neural_oracle.pt")
            print("Neural oracle loaded.")
        except Exception:
            oracle = None
            print("No neural_oracle.pt — symbolic-only mode.")
        self.bot = Bot(max_size=max_size, neural_oracle=oracle, neural_online=True)
        self.host = host
        self.port = port

    def serve(self, open_browser=True):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a): pass

            def _json(self, code, payload):
                body = json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _file(self, path):
                full = os.path.normpath(os.path.join(STATIC_DIR, path.lstrip("/")))
                if not full.startswith(STATIC_DIR + os.sep) or not os.path.isfile(full):
                    return self._json(404, {"error": "not found", "path": path})
                ctype, _ = mimetypes.guess_type(full)
                with open(full, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ctype or "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                p = urlparse(self.path).path
                if p in ("/", "/index.html"):
                    return self._file("index.html")
                if p == "/api/state":  return self._json(200, app.bot.state())
                if p == "/api/export": return self._json(200, app.bot.export_state())
                return self._file(p)

            def do_POST(self):
                p = urlparse(self.path).path
                n = int(self.headers.get("Content-Length", 0))
                try:
                    body = json.loads(self.rfile.read(n) or b"{}")
                except Exception:
                    return self._json(400, {"error": "bad json"})

                if p == "/api/command":
                    reply = app.bot.handle(body.get("text", ""))
                    if reply == "__EXIT__": reply = "Bye."
                    return self._json(200, {"reply": reply, "state": app.bot.state()})

                if p == "/api/import":
                    try:
                        count = app.bot.import_state(body)
                    except Exception as e:
                        return self._json(400, {"error": str(e)})
                    return self._json(200, {"imported": count, "state": app.bot.state()})

                return self._json(404, {"error": "not found"})

        url = f"http://{self.host}:{self.port}/"
        print(f"OSTL server running at {url}")
        print("Press Ctrl-C to stop.")
        if open_browser:
            try: webbrowser.open(url)
            except Exception: pass
        HTTPServer((self.host, self.port), Handler).serve_forever()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--max-size", type=int, default=4)
    a = p.parse_args()
    ensure_static()
    AppServer(a.host, a.port, a.max_size).serve(open_browser=not a.no_browser)