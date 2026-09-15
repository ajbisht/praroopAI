const $ = (id) => document.getElementById(id);
const FORM_IDS = ["request", "project_cost", "duration_months", "num_milestones", "storage"];
const STEP_ORDER = ["intake", "derive", "draft", "compliance", "reviewer", "score"];

/* ── health badges ──────────────────────────────────── */
fetch("/api/health").then(r => r.json()).then(d => {
  const eb = $("engineBadge");
  eb.classList.add("ok");
  eb.querySelector("span").textContent = d.engine || "LangGraph";
  const llm = d.llm || {};
  const lb = $("llmBadge");
  lb.classList.add(llm.ok ? "ok" : "off");
  lb.querySelector("span").textContent = `${llm.provider || "llm"} · ${llm.model || "?"}`;
  lb.title = llm.detail || "";
  if (!llm.ok) { logLine(`LLM not ready: ${llm.detail}`, "warn"); showTab("log"); }
}).catch(() => {});

/* ── cost helper ────────────────────────────────────── */
function inWords(n) {
  n = Number(n) || 0;
  if (n >= 1e7) return `≈ ₹${(n / 1e7).toFixed(2)} crore`;
  if (n >= 1e5) return `≈ ₹${(n / 1e5).toFixed(2)} lakh`;
  return n > 0 ? `₹${n.toLocaleString("en-IN")}` : "";
}
$("project_cost").addEventListener("input", e =>
  $("costWords").textContent = inWords(e.target.value));
$("costWords").textContent = inWords($("project_cost").value);

/* ── doc type + tabs ────────────────────────────────── */
document.querySelectorAll("#docTypeSeg .seg-btn").forEach(b =>
  b.addEventListener("click", () => {
    document.querySelectorAll("#docTypeSeg .seg-btn").forEach(x => x.classList.remove("active"));
    b.classList.add("active");
    $("doc_type").value = b.dataset.val;
  }));

function showTab(name) {
  document.querySelectorAll("#tabs .tab").forEach(t =>
    t.classList.toggle("active", t.dataset.tab === name));
  ["doc", "trace", "log"].forEach(k => $("pane-" + k).hidden = k !== name);
}
document.querySelectorAll("#tabs .tab").forEach(t =>
  t.addEventListener("click", () => showTab(t.dataset.tab)));

function setTabCount(tab, n) {
  const el = document.querySelector(`#tabs .tab[data-tab="${tab}"]`);
  let c = el.querySelector(".cnt");
  if (!c) { c = document.createElement("span"); c.className = "cnt"; el.appendChild(c); }
  c.textContent = n;
}

/* ── stepper ────────────────────────────────────────── */
const resetStepper = () =>
  document.querySelectorAll(".step").forEach(s => s.classList.remove("active", "done"));
function markStep(node) {
  const el = document.querySelector(`.step[data-step="${node}"]`);
  if (!el) return;
  const i = STEP_ORDER.indexOf(node);
  document.querySelectorAll(".step").forEach(s => {
    const j = STEP_ORDER.indexOf(s.dataset.step);
    s.classList.remove("active");
    if (j > -1 && j < i) s.classList.add("done");
  });
  el.classList.remove("done"); el.classList.add("active");
}
const stepperAllDone = () => document.querySelectorAll(".step").forEach(s => {
  s.classList.remove("active"); s.classList.add("done");
});

/* ── progress + live log ────────────────────────────── */
let t0 = 0, timer = null, logCount = 0;
function startTimer() {
  t0 = Date.now();
  timer = setInterval(() => {
    const s = Math.round((Date.now() - t0) / 1000);
    $("progressTime").textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }, 1000);
}
const stopTimer = () => { if (timer) clearInterval(timer); timer = null; };
function setProgress(pct, text) {
  if (pct != null) $("progressFill").style.width = `${pct}%`;
  if (text) $("progressText").textContent = text;
}
function logLine(text, cls = "") {
  if (logCount === 0) $("log").innerHTML = "";
  const el = document.createElement("div");
  el.className = `log-line ${cls}`;
  const t = t0 ? ((Date.now() - t0) / 1000).toFixed(1).padStart(5) : "  0.0";
  el.innerHTML = `<span class="t">${t}s</span><span>${esc(text)}</span>`;
  $("log").appendChild(el);
  $("log").scrollTop = $("log").scrollHeight;
  setTabCount("log", ++logCount);
}

/* ── lock inputs ────────────────────────────────────── */
function setLocked(locked) {
  $("intakeForm").classList.toggle("locked", locked);
  FORM_IDS.forEach(id => { const el = $(id); if (el) el.disabled = locked; });
  document.querySelectorAll("#docTypeSeg .seg-btn").forEach(b => b.disabled = locked);
  const b = $("runBtn");
  b.disabled = locked;
  b.querySelector(".btn-ico").textContent = locked ? "⏳" : "⚡";
  b.querySelector(".btn-label").textContent =
    locked ? "Agents working…" : "Generate & Check Compliance";
}

/* ── trace ──────────────────────────────────────────── */
let traceCount = 0;
const kindClass = k => ["ai", "code", "done"].includes(k) ? k : "done";
function addTraceStep(s) {
  if (traceCount === 0) $("trace").innerHTML = "";
  const el = document.createElement("div");
  el.className = "trace-item live";
  el.innerHTML = `<span class="n">${s.n}</span><span class="ag">${esc(s.agent)}</span>
    <span class="kind ${kindClass(s.kind)}">${esc(s.kind)}</span>
    <span class="dt">${esc(s.detail)}</span>`;
  $("trace").appendChild(el);
  const live = $("trace").querySelectorAll(".trace-item.live");
  if (live.length > 1) live[live.length - 2].classList.remove("live");
  setTabCount("trace", ++traceCount);
}

/* ── run ────────────────────────────────────────────── */
async function runPipeline() {
  setLocked(true); resetStepper();
  traceCount = 0; logCount = 0;
  $("trace").innerHTML = ""; $("log").innerHTML = "";
  $("derivedBox").hidden = true; $("findings").innerHTML = "";
  $("exportNote").textContent = ""; $("docMeta").textContent = "";
  $("exportBtn").disabled = true;
  $("exportBtn").querySelector(".btn-ico").textContent = "🔒";
  $("progressWrap").hidden = false;
  setProgress(2, "Starting…");
  startTimer();
  $("sections").innerHTML =
    '<div class="placeholder"><div class="spinner"></div><p>Drafting in progress…</p></div>';
  $("scorecard").innerHTML =
    '<div class="working"><div class="spinner"></div>Agents are working live…</div>';

  const payload = {
    request: $("request").value,
    doc_type: $("doc_type").value,
    title: "",
    project_cost: Number($("project_cost").value),
    duration_months: Number($("duration_months").value),
    storage: $("storage").value,
    num_milestones: Number($("num_milestones").value),
  };

  try {
    const res = await fetch("/api/run/stream", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok || !res.body) throw new Error(await res.text());
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "", final = null;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split("\n\n"); buf = parts.pop();
      for (const p of parts) {
        const line = p.trim();
        if (!line.startsWith("data:")) continue;
        const evt = JSON.parse(line.slice(5).trim());
        handleEvent(evt);
        if (evt.type === "complete") final = evt.result;
        if (evt.type === "error") throw new Error(evt.message);
      }
    }
    $("trace").querySelectorAll(".trace-item.live").forEach(e => e.classList.remove("live"));
    stepperAllDone();
    setProgress(100, "Complete");
    if (final) render(final);
  } catch (e) {
    logLine(`ERROR: ${e.message}`, "warn");
    showTab("log");
    $("scorecard").innerHTML = `<div class="placeholder"><p>⚠️ ${esc(e.message)}</p></div>`;
    $("sections").innerHTML = `<div class="placeholder"><p>⚠️ Generation failed — see Live Log.</p></div>`;
    setProgress(100, "Failed");
    resetStepper();
  } finally {
    stopTimer(); setLocked(false);
  }
}

function handleEvent(evt) {
  switch (evt.type) {
    case "progress": {
      const d = evt.detail || "";
      if (evt.stage && STEP_ORDER.includes(evt.stage)) markStep(evt.stage);
      if (evt.current && evt.total) setProgress(25 + Math.round(50 * evt.current / evt.total), d);
      else setProgress(null, d);
      logLine(d, d.startsWith("✓") ? "ok" : d.startsWith("⚠") ? "warn" : "work");
      break;
    }
    case "step":
      addTraceStep(evt.step);
      logLine(`[${evt.step.agent}] ${evt.step.detail}`);
      break;
    case "node":
      if (STEP_ORDER.includes(evt.name)) {
        markStep(evt.name);
        const base = { intake: 10, derive: 22, draft: 76, compliance: 84, reviewer: 90, score: 98 };
        setProgress(base[evt.name] ?? null, null);
      }
      break;
    case "ping": setProgress(null, `Still working… (${evt.elapsed}s)`); break;
    case "error": logLine(`ERROR: ${evt.message}`, "warn"); break;
  }
}

/* ── render ─────────────────────────────────────────── */
function render(data) {
  const brief = data.brief || {}, money = (data.derived || {}).money || {};
  $("docMeta").textContent =
    `${brief.doc_type || ""} · ${money.project_cost || ""} · ${brief.duration_months || 0} months`;

  const rows = [
    ["Total cost", money.project_cost], ["EMD (2%)", money.emd_amount],
    ["PBG (5%)", money.pbg_amount], ["LD cap (10%)", money.ld_cap_amount],
    ["Tender mode", (data.derived || {}).tender_mode],
  ].filter(r => r[1]);
  if (rows.length) {
    $("derivedList").innerHTML = rows.map(([k, v]) =>
      `<div class="row"><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");
    $("derivedBox").hidden = false;
  }

  const secs = Object.values(data.sections || {});
  setTabCount("doc", secs.length);
  $("sections").innerHTML = secs.length
    ? secs.map(s => `<article class="section"><h4>${esc(s.title)}</h4>
        <div class="body">${fmtBody(s.body)}</div></article>`).join("")
    : '<div class="placeholder"><p>No sections generated — see Live Log.</p></div>';

  const sc = data.scorecard || {};
  const ready = !!sc.can_finalize;
  const cls = ready ? "green" : (sc.mandatory_open ? "red" : "amber");
  let html = `<div class="overall"><span class="big ${cls}">${sc.overall_percent ?? 0}%</span>
      <span class="lbl">Overall compliance</span>
      <span class="verdict ${ready ? "ready" : "blocked"}">
        ${ready ? "✓ Ready to export" : "✕ " + (sc.mandatory_open || 0) + " mandatory issue(s)"}
      </span></div>`;
  (sc.rows || []).forEach(r => {
    html += `<div class="fw-row"><div class="lbl">
        <span><span class="dot bg-${r.status}"></span>${esc(r.framework)}</span>
        <span class="val ${r.status}">${r.percent}% · ${r.passed}/${r.total}</span></div>
      <div class="bar"><span class="bg-${r.status}" style="width:${r.percent}%"></span></div></div>`;
  });
  $("scorecard").innerHTML = html;

  $("findings").innerHTML = (data.findings || []).map(f =>
    `<div class="finding ${f.severity === "mandatory" ? "" : "rec"}">
      <span class="rid">${esc(f.rule_id)}</span> · ${esc(f.framework)}<br>${esc(f.message)}
      ${f.citation ? `<div class="cite">📖 ${esc(f.citation)}</div>` : ""}</div>`).join("");

  const eb = $("exportBtn");
  eb.disabled = !ready;
  eb.querySelector(".btn-ico").textContent = ready ? "🔓" : "🔒";
  eb.querySelector(".btn-label").textContent =
    ready ? `Export ${brief.doc_type || "document"} (.docx)` : "Export locked";
  $("exportNote").textContent = ready
    ? "All mandatory checks pass — export unlocked."
    : `${sc.mandatory_open || 0} mandatory issue(s) block export.`;
}

/* body renderer: paragraphs, bullets, bold, highlighted amounts */
function fmtBody(text) {
  const lines = String(text || "").split("\n");
  let html = "", inList = false;
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (/^[-*•]\s+/.test(line)) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${rich(line.replace(/^[-*•]\s+/, ""))}</li>`;
    } else {
      if (inList) { html += "</ul>"; inList = false; }
      html += `<p>${rich(line)}</p>`;
    }
  }
  if (inList) html += "</ul>";
  return html;
}

/* escape first, then apply inline formatting on the safe string */
function rich(s) {
  let out = esc(s);
  // **bold** -> <strong> (safety net; bodies are normally stripped server-side)
  out = out.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // highlight a whole money token, including its "(₹2.00 crore)" suffix,
  // so a composite amount is never split across two chips
  out = out.replace(
    /₹\s?[\d][\d,]*(?:\.\d+)?(?:\s*(?:crore|lakh))?(?:\s*\(₹\s?[\d][\d,]*(?:\.\d+)?\s*(?:crore|lakh)\))?/gi,
    m => `<span class="amt">${m}</span>`);
  return out;
}

const esc = s => String(s ?? "").replace(/[&<>"]/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function doExport() {
  const res = await fetch("/api/export", { method: "POST" });
  if (!res.ok) { alert("Export blocked: " + (await res.text())); return; }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `PraroopAI_${$("doc_type").value}.docx`; a.click();
  URL.revokeObjectURL(url);
}

$("runBtn").addEventListener("click", runPipeline);
$("exportBtn").addEventListener("click", doExport);
