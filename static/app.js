/* Lucidity: the runs home (goal composer + recent runs) and the live run view.
   Everything here reads /api/runs*; the monitor views live in monitor.js. */
"use strict";

const api = async (path, body) => {
  const opt = body === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)};
  const r = await fetch(path, opt);
  let data = {};
  try { data = await r.json(); } catch (e) {}
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
};
const ago = iso => {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  return s < 60 ? "just now" : s < 3600 ? Math.floor(s / 60) + "m ago" : s < 86400 ? Math.floor(s / 3600) + "h ago" : new Date(iso).toLocaleDateString();
};
const STATE_LABEL = {planning: "Planning", plan_ready: "Plan ready", running: "Running", done: "Done", needs_you: "Needs you",
                     stopped: "Stopped", failed: "Failed", queued: "Queued", skipped: "Skipped", working: "Working",
                     checking: "Checking", merging: "Merging", starting: "Starting"};
const badge = (state, label) => `<span class="badge b-${esc(state)}">${esc(label || STATE_LABEL[state] || state)}</span>`;
const trunc = (s, n) => (s = String(s || ""), s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s);
const pct = (a, b) => b > 0 ? Math.max(0, Math.min(100, 100 * a / b)) : 0;

function toast(msg, bad = true) {
  let t = $("#toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    t.setAttribute("role", "status");
    t.style.cssText = "position:fixed;left:50%;bottom:20px;transform:translateX(-50%);z-index:50;max-width:min(560px,calc(100vw - 32px));padding:10px 16px;border-radius:10px;font-size:13.5px;box-shadow:var(--shadow-lg)";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.background = bad ? "var(--fail)" : "var(--ink)";
  t.style.color = "var(--surface)";
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 5000);
}

/* ================= router ================= */

const MONITOR = ["sessions", "map", "trace", "evals"];
let route = {view: "runs", id: null};
let pollTimer = null;

function go() {
  const h = location.hash.replace(/^#/, "") || "runs";
  const [view, id] = h.split("/");
  route = {view: view === "run" && id ? "run" : (MONITOR.includes(view) ? view : "runs"), id: id || null};
  clearTimeout(pollTimer);
  $$(".view").forEach(v => { v.hidden = v.id !== "view-" + route.view; });
  $$("[data-nav]").forEach(a => a.classList.toggle("on", a.dataset.nav === (route.view === "run" ? "runs" : route.view)));
  if (route.view === "runs") showHome();
  else if (route.view === "run") showRun(route.id);
  else if (window.Monitor) window.Monitor.show(route.view, id);
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", go);

/* ================= home: composer + runs ================= */

let meta = null;          // /api/runs payload
let form = {worker: "demo", demo: null, goal: "", repo: "", evalCmd: "", budget: "1.00", parallel: 3, auto: true};

const STEPS = [
  ["Plan", "var(--accent)", "A model splits the goal into tasks, each with done-when checks and a budget."],
  ["Work", "var(--run)", "Each task gets its own git worktree and an agent: Claude Code, Codex, or built-in."],
  ["Check", "var(--check)", "Tests, eval scores and file checks run in the worktree. A checker decides: pass, fail, or needs you."],
  ["Merge", "var(--done-mark)", "Only passing work merges, into a run branch. Your own branch is never touched."],
];

async function showHome() {
  const el = $("#view-runs");
  if (!el.dataset.built) {
    el.innerHTML = `
      <div class="hero">
        <div class="hero-copy">
          <span class="chip">Agent orchestrator</span>
          <h1>Give it a goal. <em>Watch agents ship it</em>, with checks that decide what merges.</h1>
          <p class="lead">Lucidity plans a goal into tasks, runs a coding agent on each in its own git worktree, and only merges work that passes its checks. You see the task graph, progress, spend against the budget, and where in the repo agents worked, live.</p>
        </div>
        <form class="card composer" id="composer" autocomplete="off">
          <div class="skel" style="height:300px"></div>
        </form>
        <div class="steps">${STEPS.map(([t, c, d], i) => `<div class="step"><b><i style="background:${c}">${i + 1}</i>${t}</b><span>${d}</span></div>`).join("")}</div>
      </div>
      <div class="card" id="recent"><div class="card-h"><h2>Runs</h2></div><div class="card-b"><div class="skel" style="height:44px"></div></div></div>`;
    el.dataset.built = "1";
  }
  try {
    meta = await api("/api/runs");
    $("#offline").hidden = true;
  } catch (e) {
    $("#composer").innerHTML = `<div class="notice err"><span class="ic"><span>!</span></span><div>Couldn't load runs: ${esc(e.message)}</div></div>`;
    return;
  }
  if (!$("#composer").dataset.ready) renderComposer();
  renderRecent();
  if (route.view === "runs" && meta.runs.some(r => ["planning", "running"].includes(r.state)))
    pollTimer = setTimeout(showHome, 3000);
}

function workerOptions() {
  const sub = {demo: "no key needed", builtin: "edits via the API", claude: "claude CLI", codex: "codex CLI"};
  return meta.workers.map(w => {
    let ok = w.ok, why = w.why;
    if (w.name !== "demo" && !meta.has_key) { ok = false; why = "needs OPENAI_API_KEY"; }
    return {...w, ok, why, short: w.name === "demo" ? "Demo" : w.name === "builtin" ? "Built-in" : w.label.replace(" CLI", ""), sub: ok ? sub[w.name] : why};
  });
}

function renderComposer() {
  const f = $("#composer");
  const opts = workerOptions();
  if (!opts.find(o => o.name === form.worker && o.ok)) form.worker = "demo";
  const demo = form.worker === "demo";
  const demos = meta.demos || [];
  if (!demos.find(d => d.name === form.demo)) form.demo = demos.length ? demos[0].name : null;
  const dm = demos.find(d => d.name === form.demo) || {goal: "", repo_name: "", about_repo: "", budget_usd: 1};
  f.innerHTML = `
    <div class="field">
      <label class="f">Who does the work</label>
      <div class="seg" role="radiogroup">${opts.map(o => `
        <button type="button" class="opt ${o.name === form.worker ? "on" : ""}" data-w="${esc(o.name)}" role="radio" aria-checked="${o.name === form.worker}" ${o.ok ? "" : "disabled"} title="${esc(o.ok ? o.label : o.label + ": " + o.why)}">
          <b>${esc(o.short)}</b><span>${esc(o.sub)}</span></button>`).join("")}</div>
    </div>
    ${demo && demos.length > 1 ? `<div class="field">
      <label class="f">Demo</label>
      <div class="demos" role="radiogroup">${demos.map(d => `
        <button type="button" class="opt demo-opt ${d.name === form.demo ? "on" : ""}" data-demo="${esc(d.name)}" role="radio" aria-checked="${d.name === form.demo}">
          <b>${esc(d.title)}</b><span>${esc(d.blurb)}</span></button>`).join("")}</div>
    </div>` : ""}
    <div class="field">
      <label class="f" for="goal">Goal</label>
      ${demo ? `<textarea id="goal" readonly rows="2">${esc(dm.goal)}</textarea>
        <div class="hint">The demo's goal is fixed. Its agent edits are recorded; the evals, tests, checks, budget caps and git merges are real.</div>`
             : `<textarea id="goal" rows="3" placeholder="What should change? e.g. Add a --json flag to the CLI that prints results as JSON, with tests.">${esc(form.goal)}</textarea>`}
    </div>
    <div class="field">
      <label class="f" for="repo">Repository</label>
      ${demo ? `<div class="repo-fixed"><b>${esc(dm.repo_name)}</b><span>${esc(dm.about_repo)}, copied fresh for each run</span></div>`
             : `<input type="text" id="repo" placeholder="C:\\path\\to\\your\\repo or ~/code/repo" value="${esc(form.repo)}">
                <div class="hint">A git repo with at least one commit. Work happens in worktrees on <code>lucidity/*</code> branches.</div>`}
    </div>
    ${demo ? "" : `<div class="field">
      <label class="f" for="evalcmd">Eval command <span class="muted" style="font-weight:500">· optional</span></label>
      <input type="text" id="evalcmd" class="mono" placeholder="python evals/score.py" value="${esc(form.evalCmd)}">
      <div class="hint">A script under <code>evals/</code> that prints its scores as JSON. Tasks can then be done when a score clears a bar, and every merge is scored.</div>
    </div>`}
    <div class="row2 field">
      <div><label class="f" for="budget">Budget</label>
        <div class="money-in"><input type="number" id="budget" min="0.05" step="0.05" max="${meta.max_run_usd}" value="${demo ? dm.budget_usd.toFixed(2) : esc(form.budget)}"></div>
        <div class="hint">Cap ${money(meta.max_run_usd)} per run</div></div>
      <div><label class="f" for="parallel">Agents at once</label>
        <select id="parallel">${[1, 2, 3, 4, 5, 6].map(n => `<option ${n === form.parallel ? "selected" : ""}>${n}</option>`).join("")}</select></div>
    </div>
    <div class="field"><label class="check"><input type="checkbox" id="auto" ${form.auto ? "checked" : ""}> Start as soon as the plan is ready (untick to review the plan first)</label></div>
    ${!meta.has_key ? `<div class="notice info field"><span class="ic" style="color:var(--accent)"><span>i</span></span><div>No <code>OPENAI_API_KEY</code> in <code>.env</code>, so only the demo can run. Add one to plan and check your own goals; agents then run through Claude Code, Codex or the built-in worker.</div></div>` : ""}
    <div class="composer-foot">
      <span class="err-text" id="cerr" role="alert"></span>
      <button class="btn primary lg" type="submit" id="go">${demo ? "Run the demo" : "Plan this goal"} <span aria-hidden="true">→</span></button>
    </div>`;
  f.dataset.ready = "1";
  $$("[data-w]", f).forEach(b => b.onclick = () => { saveForm(); form.worker = b.dataset.w; renderComposer(); });
  $$("[data-demo]", f).forEach(b => b.onclick = () => { saveForm(); form.demo = b.dataset.demo; renderComposer(); });
  f.onsubmit = submit;
}

function saveForm() {
  const g = $("#goal"), r = $("#repo"), b = $("#budget"), ec = $("#evalcmd");
  if (g && !g.readOnly) form.goal = g.value;
  if (r) form.repo = r.value;
  if (ec) form.evalCmd = ec.value.trim();
  if (b && form.worker !== "demo") form.budget = b.value;
  form.parallel = +$("#parallel").value;
  form.auto = $("#auto").checked;
}

async function submit(e) {
  e.preventDefault();
  saveForm();
  const btn = $("#go");
  btn.disabled = true;
  $("#cerr").textContent = "";
  const body = {worker: form.worker, budget_usd: +$("#budget").value, max_parallel: form.parallel, auto_run: form.auto};
  if (form.worker !== "demo") Object.assign(body, {goal: form.goal, repo: form.repo}, form.evalCmd ? {eval_command: form.evalCmd} : {});
  else body.demo = form.demo;
  try {
    const run = await api("/api/runs", body);
    location.hash = "run/" + run.id;
  } catch (err) {
    $("#cerr").textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

function renderRecent() {
  const el = $("#recent");
  const rs = meta.runs;
  if (!rs.length) {
    el.innerHTML = `<div class="card-h"><h2>Runs</h2></div>
      <div class="empty"><div class="art">◇</div><b>No runs yet</b>Start the demo above. It takes about 30 seconds and needs no key.</div>`;
    return;
  }
  el.innerHTML = `<div class="card-h"><h2>Runs</h2><span class="sub">${plural(rs.length, "run")}</span></div>
    <div class="runlist" style="margin-top:12px">${rs.map(r => `
      <a class="runrow" href="#run/${esc(r.id)}">
        <span>${badge(r.state)}</span>
        <span style="min-width:0"><div class="goal">${esc(r.goal)}</div><div class="repo">${esc(r.repo_name)} · ${r.mode === "demo" ? "demo" : esc(r.worker)}</div></span>
        <span class="num">${r.done}/${r.tasks} tasks</span>
        <span class="num">${money(r.spent_usd)} of ${money(r.budget_usd)}</span>
        <span class="num when">${ago(r.created)}</span>
      </a>`).join("")}</div>`;
}

/* ================= run view ================= */

let cur = null;            // latest run view
let sel = null;            // selected task id
let selMod = null;         // selected module in the repo map
let sigs = {};             // last rendered signature per part
let runMap = null, mapAt = 0;
let runDiff = null;        // /diff payload, fetched once the run is over
let narrowGraph = null;

function part(name, sig, render) {
  const s = typeof sig === "string" ? sig : JSON.stringify(sig);
  if (sigs[name] === s) return;
  sigs[name] = s;
  const el = $("#p-" + name);
  if (el) render(el);
}

async function showRun(id) {
  const el = $("#view-run");
  if (!cur || cur.id !== id) {
    cur = null; sel = null; selMod = null; sigs = {}; runMap = null; mapAt = 0; runDiff = null;
    el.innerHTML = `
      <div class="crumbs"><a href="#runs">← All runs</a><span>/</span><span class="mono">${esc(id)}</span></div>
      <div id="p-head"><div class="skel" style="height:64px;max-width:720px"></div></div>
      <div id="p-callout"></div>
      <div id="p-stats" class="stats"></div>
      <div id="p-result"></div>
      <div class="grid-2 scores-row" id="scores-row" hidden>
        <div class="card"><div class="card-h"><h2>Scores</h2><span class="sub" id="scores-sub">the merged branch, over time</span></div><div class="card-b" id="p-scores"></div></div>
        <div class="card"><div class="card-h"><h2>Metrics</h2><span class="sub">start → now, against the bar</span></div><div class="card-b" id="p-fields"></div></div>
      </div>
      <div class="grid-main">
        <div class="col">
          <div class="card"><div class="card-h"><h2>Task graph</h2><span class="sub" id="graph-sub"></span></div><div class="card-b" id="p-graph"></div></div>
          <div class="card"><div class="card-h"><h2>Timeline</h2><span class="sub">agent work, then the check, per round</span></div><div class="card-b" id="p-gantt"></div></div>
        </div>
        <div class="card detail"><div class="card-b" id="p-detail" style="padding-top:16px"></div></div>
      </div>
      <div class="grid-2">
        <div class="card"><div class="card-h"><h2>Progress</h2><span class="sub">tasks by state over time</span></div><div class="card-b" id="p-progress"></div></div>
        <div class="card"><div class="card-h"><h2>Spend</h2><span class="sub" id="spend-sub">against the run budget</span></div><div class="card-b" id="p-spend"></div></div>
      </div>
      <div class="grid-main">
        <div class="card"><div class="card-h"><h2>Repo map</h2><span class="sub" id="map-sub">where agents worked</span></div><div class="card-b" id="p-map"></div></div>
        <div class="card"><div class="card-h"><h2>Activity</h2><span class="sub">newest first</span></div><div class="card-b"><div class="feed" id="p-feed"></div></div></div>
      </div>`;
  }
  try {
    const v = await api("/api/runs/" + encodeURIComponent(id));
    $("#offline").hidden = true;
    cur = v;
    renderRun(v);
  } catch (e) {
    if (!cur) {
      el.innerHTML = `<div class="crumbs"><a href="#runs">← All runs</a></div>
        <div class="card"><div class="empty"><div class="art">?</div><b>${e.message === "no such run" ? "No such run" : "Couldn't load this run"}</b>${esc(e.message === "no such run" ? "It may have been deleted." : e.message)}</div></div>`;
      return;
    }
    if (/fetch/i.test(e.message)) $("#offline").hidden = false;
  }
  if (route.view === "run" && route.id === id) {
    const live = cur && ["planning", "running"].includes(cur.state);
    pollTimer = setTimeout(() => showRun(id), live ? 700 : 4000);
  }
}

function renderRun(v) {
  const live = ["planning", "running"].includes(v.state);
  const nodes = v.nodes;
  part("head", [v.state, v.goal, v.budget_usd, v.reason], renderHead);
  part("callout", [v.state, v.reason, v.needs, v.plan_summary, v.files_changed], renderCallout);
  part("stats", [v.state, nodes.map(n => [n.state, n.checks.length]), v.spent_usd, v.budget_usd, Math.floor(v.elapsed_s)], renderStats);
  const w = $("#p-graph").clientWidth || 800;
  const narrow = w < 640;
  if (narrow !== narrowGraph) { narrowGraph = narrow; delete sigs.graph; }
  part("graph", [v.state, sel, narrow, Math.round(w / 40), nodes.map(n => [n.id, n.state, n.phase, n.round, n.spent_usd, n.budget_usd]),
                 v.state === "planning" ? v.events.length : 0], renderGraph);
  part("detail", detailSig(v), renderDetail);
  const scores = v.scores || [];
  $("#scores-row").hidden = !v.eval_command;
  if (v.eval_command) {
    const sw = Math.round(($("#p-scores").clientWidth || 0) / 40);
    part("scores", [scores.length, v.state, sw, live ? Math.floor(v.elapsed_s / 2) : 0], el => { CW = chartWidth(el); el.innerHTML = scoresChart(v); });
    part("fields", [scores.length, v.state, nodes.map(n => n.checks.length)], el => { el.innerHTML = metricsTable(v); bindActions(el); });
  }
  part("result", [v.state, scores.length, nodes.filter(n => n.merged_commit).length], renderResult);
  part("progress", [v.samples.length, v.state, nodes.length], el => { CW = chartWidth(el); el.innerHTML = progressChart(v); });
  part("spend", [v.samples.length, v.spent_usd, v.budget_usd, v.state], el => { CW = chartWidth(el); el.innerHTML = spendChart(v); });
  part("gantt", [nodes.map(n => [n.state, n.spans.length, n.checks.length]), live ? Math.floor(v.elapsed_s * 2) : v.state, sel], el => { el.innerHTML = gantt(v); bindNodeClicks(el); });
  part("feed", [v.events.length, sel], renderFeed);
  const anyFiles = nodes.some(n => n.files && n.files.length);
  if (v.state !== "planning" && (!runMap || (live && Date.now() - mapAt > 2500) || (!live && !runMap.final))) loadMap(v, !live);
  else if (v.state === "planning") part("map", "planning", el => { el.innerHTML = `<div class="skel" style="height:180px"></div>`; });
  if (!anyFiles && runMap) part("map", [selMod, runMap.modules.length, "none"], renderMap);
}

async function loadMap(v, final) {
  mapAt = Date.now();
  try {
    runMap = await api(`/api/runs/${encodeURIComponent(v.id)}/map`);
    runMap.final = final;
    part("map", [selMod, sel, runMap.modules.map(m => [m.id, m.tasks.map(t => [t.id, t.state, t.files.length])])], renderMap);
  } catch (e) {
    part("map", "err" + e.message, el => { el.innerHTML = `<div class="notice err">Couldn't build the repo map: ${esc(e.message)}</div>`; });
  }
}

async function act(action, node, amount) {
  try {
    cur = await api(`/api/runs/${encodeURIComponent(cur.id)}/action`, {action, node, amount});
    renderRun(cur);
    clearTimeout(pollTimer);
    pollTimer = setTimeout(() => showRun(cur.id), 400);
  } catch (e) { toast(e.message); }
}
window.lucidityAct = act;

/* ---------- head, callouts, stats ---------- */

function renderHead(el) {
  const v = cur;
  const acts = [];
  if (v.state === "plan_ready") acts.push(`<button class="btn primary" data-act="approve">Approve plan and run</button>`);
  if (["planning", "running", "needs_you", "plan_ready"].includes(v.state)) acts.push(`<button class="btn danger" data-act="stop">Stop</button>`);
  if (v.state === "stopped" && v.nodes.length && v.integration) acts.push(`<button class="btn" data-act="resume">Resume</button>`);
  if (!["planning", "running"].includes(v.state)) acts.push(`<button class="btn ghost" data-del="1" title="Delete this run's record and worktrees">Delete</button>`);
  acts.push(`<a class="btn" href="#runs">New run</a>`);
  el.innerHTML = `<div class="runhead">
      <div style="min-width:0;flex:1 1 480px">
        <h1>${esc(v.goal)}</h1>
        <div class="meta">${badge(v.state)}
          <span class="chip">${v.mode === "demo" ? "Demo" : "Live"}</span>
          <span class="chip mono" title="${esc(v.repo)}">${esc(v.repo_name)}</span>
          <span class="chip">${esc(v.worker_label)}</span>
          <span class="chip" title="Plans and checks with this model">${esc(v.mode === "demo" ? "planner recorded" : v.model)}</span>
          ${v.integration ? `<span class="chip mono" title="Passing work merges here">${esc(v.integration.branch)}</span>` : ""}
        </div>
      </div>
      <div class="acts">${acts.join("")}</div>
    </div>`;
  $$("[data-act]", el).forEach(b => b.onclick = () => act(b.dataset.act));
  const del = $("[data-del]", el);
  if (del) del.onclick = async () => {
    if (del.dataset.armed !== "1") { del.dataset.armed = "1"; del.textContent = "Click again to delete"; del.classList.add("danger"); return; }
    try { await api(`/api/runs/${encodeURIComponent(v.id)}/delete`, {}); cur = null; location.hash = "runs"; }
    catch (e) { toast(e.message); }
  };
}

const NEEDS_TITLE = {budget: "hit its budget", run_budget: "is waiting on the run budget", rounds: "kept failing its check",
                     checker: "needs a person to judge", conflict: "passed but couldn't merge", error: "hit an error"};

function actionButton(a, n) {
  const node = n.node ? cur.nodes.find(x => x.id === n.node) : null;
  if (a === "add_budget") {
    const amt = Math.max(0.1, Math.round((node ? node.budget_usd : 0.2) * 100) / 100);
    return `<button class="btn warn sm" data-a="add_budget" data-n="${esc(n.node)}" data-amt="${amt}">Add ${money(amt)} and retry</button>`;
  }
  if (a === "raise_budget") {
    const room = Math.max(0, meta ? meta.max_run_usd - cur.budget_usd : 0.5);
    const amt = Math.min(0.5, Math.round(room * 100) / 100);
    return `<button class="btn warn sm" data-a="raise_budget" data-amt="${amt}" ${amt <= 0 ? "disabled" : ""}>Raise run budget ${money(amt)}</button>`;
  }
  if (a === "retry") return `<button class="btn warn sm" data-a="retry" data-n="${esc(n.node)}">Retry one more round</button>`;
  if (a === "skip") return `<button class="btn sm" data-a="skip" data-n="${esc(n.node)}">Skip task</button>`;
  if (a === "stop") return `<button class="btn sm danger" data-a="stop">Stop run</button>`;
  return "";
}

function bindActions(el) {
  $$("[data-a]", el).forEach(b => b.onclick = e => { e.stopPropagation(); act(b.dataset.a, b.dataset.n || null, +(b.dataset.amt || 0)); });
  $$("[data-sel]", el).forEach(b => b.onclick = () => select(b.dataset.sel));
}

function renderCallout(el) {
  const v = cur;
  let h = "";
  if (v.needs && v.needs.length) {
    h = `<div class="needs" role="alert"><h2>Needs you · ${plural(v.needs.length, "decision")}</h2>${v.needs.map(n => `
      <div class="item"><div class="what">
        <b>${n.node ? `<a href="javascript:void 0" data-sel="${esc(n.node)}" class="mono">${esc(n.node)}</a> ${esc(n.title)} ${esc(NEEDS_TITLE[n.kind] || "needs you")}` : "The run budget is spent"}</b>
        <p>${esc(n.reason)}</p></div>
        <div class="acts">${n.actions.map(a => actionButton(a, n)).join("")}</div></div>`).join("")}
      <p class="small muted" style="margin:10px 0 0">Tasks that don't depend on these keep running. Nothing merges until its check passes.</p></div>`;
  } else if (v.state === "plan_ready") {
    h = `<div class="callout"><div><b>The plan is ready for review.</b><p>${esc(v.plan_summary)} ${plural(v.nodes.length, "task")}, ${money(v.nodes.reduce((a, n) => a + n.budget_usd, 0))} of task budgets. Click a task to read its prompt and done-when checks.</p></div>
      <button class="btn primary" data-a="approve">Approve and run</button></div>`;
  } else if (v.state === "done") {
    const blocked = v.nodes.reduce((a, n) => a + n.checks.filter(c => c.verdict === "fail").length, 0);
    h = `<div class="callout ok"><div><b>Done. Every task passed its checks and merged.</b><p>${plural((v.files_changed || []).length, "file")} changed on <code>${esc(v.integration.branch)}</code>; your own branch was not touched.${blocked ? ` Checks sent back ${plural(blocked, "round")} that would otherwise have merged.` : ""}</p></div>
      <a class="btn" href="javascript:void 0" data-jump="result">See what merged ↓</a></div>`;
  } else if (v.state === "failed") {
    h = `<div class="callout bad"><div><b>This run failed.</b><p>${esc(v.reason)}</p></div><a class="btn" href="#runs">Start another</a></div>`;
  } else if (v.state === "stopped") {
    h = `<div class="callout"><div><b>Stopped.</b><p>${esc(v.reason)} Work that passed its checks stays merged on the run branch.</p></div></div>`;
  }
  el.innerHTML = h;
  bindActions(el);
  const j = $("[data-jump]", el);
  if (j) j.onclick = () => $("#p-result").scrollIntoView({behavior: "smooth", block: "start"});
}

function renderStats(el) {
  const v = cur, ns = v.nodes;
  const done = ns.filter(n => n.state === "done").length;
  const checks = ns.flatMap(n => n.checks);
  const passed = checks.filter(c => c.verdict === "pass").length, failed = checks.filter(c => c.verdict === "fail").length;
  const needs = ns.filter(n => n.state === "needs_you").length + (v.needs_kind === "run_budget" && v.state === "needs_you" ? 1 : 0);
  const over = v.spent_usd >= v.budget_usd;
  el.innerHTML = `
    <div class="card stat"><div class="k">Tasks done</div><div class="v">${done}<small> / ${ns.length || "–"}</small></div><div class="bar"><i style="width:${pct(done, ns.length)}%;background:var(--done-mark)"></i></div></div>
    <div class="card stat"><div class="k">Spent</div><div class="v">${money(v.spent_usd)}<small> / ${money(v.budget_usd)}</small></div><div class="bar ${over ? "over" : ""}"><i style="width:${pct(v.spent_usd, v.budget_usd)}%"></i></div></div>
    <div class="card stat"><div class="k">Checks</div><div class="v">${passed}<small> passed${failed ? ` · ${failed} failed` : ""}</small></div></div>
    <div class="card stat ${needs ? "needs" : ""}"><div class="k">Needs you</div><div class="v">${needs}</div></div>
    <div class="card stat wide"><div class="k">Elapsed</div><div class="v">${dur(v.elapsed_s)}</div></div>`;
}

/* ---------- task graph ---------- */

function depths(nodes) {
  const by = Object.fromEntries(nodes.map(n => [n.id, n])), memo = {};
  const d = id => memo[id] ?? (memo[id] = 0, memo[id] = Math.max(0, ...(by[id]?.deps || []).filter(x => by[x]).map(x => d(x) + 1)));
  nodes.forEach(n => d(n.id));
  return memo;
}

function nodeStatus(n) {
  if (n.state === "running") return `${STATE_LABEL[n.phase] || "Working"} · round ${n.round || 1}`;
  if (n.state === "done") return `Merged · ${plural(n.round, "round")}`;
  if (n.state === "needs_you") return `Needs you · ${({budget: "budget", run_budget: "run budget", rounds: "check failing", checker: "judgement", conflict: "conflict", error: "error"})[n.needs_kind] || ""}`;
  if (n.state === "queued") return n.deps.length ? `Waits on ${n.deps.join(", ")}` : "Queued";
  return STATE_LABEL[n.state] || n.state;
}

function renderGraph(el) {
  const v = cur;
  $("#graph-sub").textContent = v.nodes.length ? `${plural(v.nodes.length, "task")} · up to ${v.max_parallel} at once` : "";
  if (v.state === "planning" || (!v.nodes.length && v.state !== "failed")) {
    const lines = v.events.filter(e => e.kind === "planner" || e.kind === "goal").slice(-6);
    el.innerHTML = `<div style="display:grid;gap:10px">
        <div style="display:flex;gap:10px;align-items:center">${badge("planning", "Planning")}<span class="small muted">${esc(v.mode === "demo" ? "replaying the recorded planner" : v.model + " is reading the repo")}</span></div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px">${[0, 1, 2, 3].map(() => `<div class="skel" style="height:62px"></div>`).join("")}</div>
        <div class="feed">${lines.map(e => `<div class="ev k-activity"><span class="t">${dur(e.s)}</span><span class="n"></span><span class="x">${esc(e.text)}</span></div>`).join("")}</div>
      </div>`;
    return;
  }
  if (!v.nodes.length) { el.innerHTML = `<div class="empty"><b>No plan</b>${esc(v.reason || "")}</div>`; return; }
  const dep = depths(v.nodes);
  const narrow = narrowGraph;
  const ncol = new Set(Object.values(dep)).size, gx = 44, gy = 16, H = 74;
  const W = narrow ? Math.max(260, el.clientWidth) - 34
    : Math.round(Math.min(250, Math.max(170, (el.clientWidth - 8 - (ncol - 1) * gx) / ncol)));
  const pos = {};
  let vw, vh;
  if (narrow) {
    const order = [...v.nodes].sort((a, b) => dep[a.id] - dep[b.id]);
    order.forEach((n, i) => { pos[n.id] = {x: 30, y: i * (H + gy)}; });
    vw = W + 34; vh = order.length * (H + gy) - gy;
  } else {
    const cols = {};
    v.nodes.forEach(n => (cols[dep[n.id]] = cols[dep[n.id]] || []).push(n));
    const nc = Object.keys(cols).length, maxRows = Math.max(...Object.values(cols).map(c => c.length));
    vh = maxRows * (H + gy) - gy;
    Object.entries(cols).forEach(([c, list]) => {
      const off = (vh - (list.length * (H + gy) - gy)) / 2;
      list.forEach((n, i) => { pos[n.id] = {x: c * (W + gx), y: off + i * (H + gy)}; });
    });
    vw = nc * (W + gx) - gx;
  }
  const byId = Object.fromEntries(v.nodes.map(n => [n.id, n]));
  let edges = "";
  v.nodes.forEach(n => n.deps.filter(d => byId[d]).forEach(d => {
    const a = pos[d], b = pos[n.id];
    const cls = n.state === "running" ? "live" : byId[d].state === "done" ? "done" : "";
    if (narrow) {
      const y1 = a.y + H / 2, y2 = b.y + H / 2, bend = 10 + Math.min(18, (y2 - y1) / 12);
      edges += `<path class="gedge ${cls}" d="M${a.x} ${y1} C${a.x - bend} ${y1}, ${b.x - bend} ${y2}, ${b.x} ${y2}" marker-end="url(#arr)"/>`;
    } else {
      const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2, mx = (x1 + x2) / 2;
      edges += `<path class="gedge ${cls}" d="M${x1} ${y1} C${mx} ${y1}, ${mx} ${y2}, ${x2 - 3} ${y2}" marker-end="url(#arr)"/>`;
    }
  }));
  const chars = Math.floor((W - 26) / 7.4);
  const boxes = v.nodes.map(n => {
    const p = pos[n.id], bw = W - 26;
    const spent = Math.min(1, n.budget_usd ? n.spent_usd / n.budget_usd : 0);
    return `<g class="gnode st-${n.state} ${n.phase ? "ph-" + n.phase : ""} ${sel === n.id ? "sel" : ""}" data-node="${esc(n.id)}" transform="translate(${p.x},${p.y})" tabindex="0" role="button" aria-label="${esc(n.id + " " + n.title + ", " + nodeStatus(n))}">
      <rect class="ring" x="-1" y="-1" width="${W + 2}" height="${H + 2}" rx="11"/>
      <rect class="box" width="${W}" height="${H}" rx="10"/>
      <rect class="stripe" x="0" y="10" width="3.5" height="${H - 20}" rx="1.75"/>
      <text class="id" x="13" y="20">${esc(n.id)}</text>
      <text class="money" x="${W - 12}" y="20" text-anchor="end">${money(n.spent_usd)} / ${money(n.budget_usd)}</text>
      <text class="t" x="13" y="39">${esc(trunc(n.title, chars))}</text>
      <text class="s" x="13" y="56">${esc(trunc(nodeStatus(n), chars + 4))}</text>
      <rect class="bg" x="13" y="${H - 10}" width="${bw}" height="3" rx="1.5"/>
      <rect class="fg ${spent >= 1 ? "over" : ""}" x="13" y="${H - 10}" width="${Math.max(0, bw * spent)}" height="3" rx="1.5"/>
    </g>`;
  }).join("");
  el.innerHTML = `<div class="svgwrap"><svg viewBox="-4 -4 ${vw + 8} ${vh + 8}" style="max-height:${narrow ? "none" : Math.max(240, vh + 40) + "px"}" role="img" aria-label="Task graph">
      <defs><marker id="arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L8 4L0 8z" fill="var(--line-strong)"/></marker></defs>
      ${edges}${boxes}</svg></div>
    <div class="legend">${[["queued", "var(--queued)"], ["working", "var(--run)"], ["checking", "var(--check)"], ["needs you", "var(--needs-mark)"], ["done", "var(--done-mark)"]].map(([l, c]) => `<span><i style="background:${c}"></i>${l}</span>`).join("")}<span class="grow"></span><span>Bar: spend against the task's budget</span></div>`;
  bindNodeClicks(el);
}

function bindNodeClicks(el) {
  $$("[data-node]", el).forEach(g => {
    g.onclick = () => select(g.dataset.node);
    g.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(g.dataset.node); } };
  });
}

function select(id) {
  sel = sel === id ? null : id;
  delete sigs.graph; delete sigs.detail; delete sigs.feed; delete sigs.gantt; delete sigs.map;
  renderRun(cur);
  if (runMap) part("map", ["sel", sel, selMod, Date.now()], renderMap);
  if (sel && window.innerWidth < 1080) $("#p-detail").scrollIntoView({behavior: "smooth", block: "start"});
}

/* ---------- detail panel ---------- */

function detailSig(v) {
  if (!sel) return ["run", v.state, v.plan_summary, v.problems, v.files_changed, v.spend_by, v.nodes.map(n => n.state + n.phase)];
  const n = v.nodes.find(x => x.id === sel);
  return n ? ["node", sel, n.state, n.phase, n.round, n.checks.length, n.reports.length, n.files, n.reason, n.spent_usd, n.budget_usd,
              v.events.filter(e => e.node === sel).length] : ["gone", sel];
}

function renderDetail(el) {
  const v = cur;
  const n = sel && v.nodes.find(x => x.id === sel);
  if (!n) {
    const sb = v.spend_by || {};
    el.innerHTML = `<div class="kicker">The run</div>
      <h3>${v.state === "planning" ? "Planning…" : v.nodes.length ? plural(v.nodes.length, "task") + " planned" : "No plan"}</h3>
      ${v.plan_summary ? `<p>${esc(v.plan_summary)}</p>` : v.state === "planning" ? `<div class="skel" style="height:48px;margin-top:8px"></div>` : ""}
      ${(v.problems || []).length ? `<div class="kicker">Planner warnings</div>${v.problems.map(p => `<p class="small" style="color:var(--needs)">• ${esc(p)}</p>`).join("")}` : ""}
      ${v.nodes.length ? `<div class="kicker">Tasks</div>${v.nodes.map(x => `<button class="srow" data-sel="${esc(x.id)}" style="grid-template-columns:auto minmax(0,1fr) auto"><span class="mono small muted">${esc(x.id)}</span><span class="p">${esc(x.title)}</span>${badge(x.state === "running" ? x.phase || "working" : x.state)}</button>`).join("")}` : ""}
      <div class="kicker">Where the money went</div>
      ${["planner", "worker", "checker"].map(k => `<div class="bar2"><span>${k === "worker" ? "Agents" : k === "planner" ? "Planner" : "Checker"}</span><span class="mono">${money(sb[k] || 0)}</span><div class="bar"><i style="width:${pct(sb[k] || 0, v.spent_usd)}%"></i></div></div>`).join("")}
      ${v.files_changed ? `<div class="kicker">Files changed on ${esc(v.integration.branch)}</div><div class="files">${v.files_changed.map(f => `<span>${esc(f)}</span>`).join("")}</div>` : ""}
      ${v.nodes.length ? `<p class="small muted" style="margin-top:16px">Click a task in the graph to see its prompt, done-when checks and every check result.</p>` : ""}`;
    bindActions(el);
    return;
  }
  const last = n.checks[n.checks.length - 1];
  const conds = last ? last.conditions : n.done_when.map(c => ({kind: c.kind, label: c.label || c.text || c.command, met: null, evidence: ""}));
  const need = (v.needs || []).find(x => x.node === n.id);
  const evs = v.events.filter(e => e.node === n.id).slice(-30).reverse();
  el.innerHTML = `
    <button class="back" data-sel="${esc(n.id)}">← The run</button>
    <div class="kicker">Task <span class="mono">${esc(n.id)}</span></div>
    <h3>${esc(n.title)}</h3>
    <div class="line">${badge(n.state === "running" ? n.phase || "working" : n.state)}<span class="chip">${plural(n.round, "round")} of ${n.max_rounds}</span><span class="chip">${money(n.spent_usd)} / ${money(n.budget_usd)}</span>${n.weak ? `<span class="chip" style="color:var(--needs)" title="Every check passed before any work">weak checks</span>` : ""}</div>
    ${n.reason && n.state === "needs_you" ? `<div class="box warn" style="margin-top:12px"><b>${esc(NEEDS_TITLE[n.needs_kind] ? "This task " + NEEDS_TITLE[n.needs_kind] : "Needs you")}</b>${esc(n.reason)}${need ? `<div class="acts">${need.actions.map(a => actionButton(a, need)).join("")}</div>` : ""}</div>` : ""}
    <div class="kicker">What the agent is told</div>
    <p>${esc(n.prompt)}</p>
    ${n.deps.length ? `<p class="small muted">Starts after ${n.deps.map(d => `<a href="javascript:void 0" data-sel="${esc(d)}" class="mono">${esc(d)}</a>`).join(", ")}.</p>` : ""}
    <div class="kicker">Done when${last ? ` · round ${last.round} result` : ""}</div>
    ${conds.map(c => `<div class="cond"><span class="m ${c.met === true ? "y" : c.met === false ? "n" : ""}">${c.met === true ? "✓" : c.met === false ? "×" : "·"}</span><div class="lab"><span class="${c.kind === "test" ? "mono" : ""}">${esc(c.label)}</span>${c.met != null && c.evidence && !/\n/.test(c.evidence) && c.kind !== "test" ? `<span class="small muted"> · ${esc(trunc(c.evidence, 90))}</span>` : ""}</div></div>`).join("")}
    ${n.checks.length ? `<div class="kicker">Rounds · newest first</div>${[...n.checks].reverse().map(c => roundCard(n, c)).join("")}`
      : n.reports.length ? `<div class="kicker">Agent's report</div>${n.reports.slice(-2).map(r => `<p class="small"><span class="muted">Round ${r.round}:</span> ${esc(r.text)}</p>`).join("")}` : ""}
    ${n.files.length ? `<div class="kicker">Files changed</div><div class="files">${n.files.map(f => `<span>${esc(f)}</span>`).join("")}</div>` : ""}
    ${evs.length ? `<div class="kicker">Activity</div><div class="feed">${evs.map(feedRow).join("")}</div>` : ""}`;
  bindActions(el);
}

const VERDICT = {pass: "Passed", fail: "Sent back", needs_you: "Needs you"};
const BY = {program: "the checks", model: "the checker model"};

// One round: what the agent said it did, next to what the check found.
function roundCard(n, c) {
  const rep = n.reports.find(r => r.round === c.round);
  const cs = c.conditions || [];
  const failed = cs.filter(x => x.met === false), met = cs.filter(x => x.met === true);
  const found = failed.map(x => {
    let ev;
    if (x.drops && x.drops.length) ev = `<div class="drops">${x.drops.map(d => `<span><b class="mono">${esc(d.metric)}</b> ${fmtScore(d.before)} → <span class="minus">${d.after == null ? "missing" : fmtScore(d.after)}</span></span>`).join("")}</div>`;
    else if (x.kind === "test" || /\n/.test(x.evidence || "")) ev = x.evidence ? `<pre>${esc(x.evidence.slice(-700))}</pre>` : "";
    else ev = x.evidence ? `<div class="small muted">${esc(x.evidence)}</div>` : "";
    return `<div class="fx"><span class="m n">×</span><div class="lab"><b>${esc(x.label)}</b>${ev}</div></div>`;
  }).join("");
  const why = c.by !== "program" && c.reasons.length ? `<ul>${c.reasons.slice(0, 4).map(r => `<li>${esc(r)}</li>`).join("")}</ul>` : "";
  return `<div class="round r-${esc(c.verdict)}">
    <div class="vh"><span class="v-${esc(c.verdict)}">${esc(VERDICT[c.verdict] || c.verdict)}</span><span class="small muted">round ${c.round} · by ${esc(BY[c.by] || c.by)}${c.usd ? " · " + money(c.usd) : ""}</span></div>
    ${rep ? `<div class="said"><div class="lbl">Agent said</div><p>${esc(trunc(rep.text, 420))}</p></div>` : ""}
    ${failed.length || why ? `<div class="found"><div class="lbl">Check found</div>${found}${why}
      ${met.length ? `<div class="small muted also">Also checked and met: ${met.map(x => esc(x.label)).join(" · ")}</div>` : ""}</div>`
      : met.length ? `<div class="small muted also">${plural(met.length, "check")} met: ${met.map(x => esc(x.label)).join(" · ")}</div>` : ""}
  </div>`;
}

const fmtScore = x => typeof x !== "number" ? "–" : Math.abs(x) <= 1 ? x.toFixed(2) : x.toLocaleString(undefined, {maximumFractionDigits: 2});

/* ---------- scores (runs with an eval) ---------- */

function globRe(p) {
  return new RegExp("^" + p.split("*").map(s => s.replace(/[.+?^${}()|[\]\\]/g, "\\$&")).join(".*") + "$");
}

// The metrics worth charting: the ones a task must raise, plus the ones guarded against drops.
function trackedMetrics(v) {
  const S = (v.scores || []).filter(s => s.metrics);
  const all = S.length ? Object.keys(S[S.length - 1].metrics) : [];
  const pats = [...new Set(v.nodes.flatMap(n => n.done_when).filter(c => c.kind === "no_regression" && c.command === v.eval_command).map(c => c.metric))].map(globRe);
  let keys = all.filter(k => k in v.targets || pats.some(r => r.test(k)));
  if (!keys.length) keys = all.slice(0, 8);
  Object.keys(v.targets).forEach(k => { if (!keys.includes(k)) keys.push(k); });
  return keys.slice(0, 8);
}

// "vendor.f1", "total.f1" → "vendor", "total" with suffix ".f1", so the legend stays short.
function shortNames(keys) {
  const tail = keys.length > 1 && keys.every(k => k.includes(".")) ? keys[0].slice(keys[0].lastIndexOf(".")) : "";
  const same = tail && keys.every(k => k.endsWith(tail));
  return {suffix: same ? tail.slice(1) : "", name: k => same ? k.slice(0, -tail.length) : k};
}

function scoresChart(v) {
  const all = v.scores || [], S = all.filter(s => s.metrics);
  const keys = trackedMetrics(v), sn = shortNames(keys);
  $("#scores-sub").innerHTML = `<code>${esc(v.eval_command)}</code> on the merged branch${sn.suffix ? " · " + esc(sn.suffix.toUpperCase()) : ""}`;
  if (!S.length) {
    const err = all.find(s => s.error);
    return chartEmpty(err ? "Scoring failed: " + err.error
      : ["planning", "plan_ready"].includes(v.state) ? "The merged branch is scored when the run starts, then after every merge." : "Waiting for the first score.");
  }
  const end = Math.max(v.elapsed_s || 0, S[S.length - 1].s, 1);
  const vals = S.flatMap(s => keys.map(k => s.metrics[k]).filter(x => typeof x === "number"));
  const bars = [...new Set(Object.values(v.targets).map(t => t.value))];
  const hi = Math.max(...vals, ...bars, 0);
  const maxY = hi <= 1 ? 1 : Math.ceil(hi * 1.1);
  const {x, y, g} = axes(end, maxY, val => maxY <= 1 ? val.toFixed(2) : Math.round(val), 4);
  let lines = "", dots = "";
  keys.forEach((k, i) => {
    const pts = S.filter(s => typeof s.metrics[k] === "number");
    if (!pts.length) return;
    let d = `M${x(pts[0].s)} ${y(pts[0].metrics[k])}`;
    pts.slice(1).forEach(p => { d += `H${x(p.s)}V${y(p.metrics[k])}`; });
    d += `H${x(end)}`;
    const col = `var(--c${i % 8 + 1})`;
    lines += `<path class="sline" d="${d}" style="stroke:${col}"/>`;
    pts.forEach((p, j) => {
      const prev = j ? pts[j - 1].metrics[k] : null;
      if (j && Math.abs(p.metrics[k] - prev) < 0.005) return;
      dots += `<circle cx="${x(p.s)}" cy="${y(p.metrics[k])}" r="3.2" style="fill:${col}"><title>${esc(p.label)}: ${esc(k)} ${fmtScore(p.metrics[k])}</title></circle>`;
    });
  });
  const barLines = bars.map(b => `<line class="target-line" x1="${PL}" x2="${CW - PR}" y1="${y(b)}" y2="${y(b)}"/>
      <text class="target-label" x="${PL + 4}" y="${y(b) - 5}">bar ${fmtScore(b)}</text>`).join("");
  return `<div class="svgwrap chart"><svg viewBox="0 0 ${CW} ${CH}" role="img" aria-label="Eval scores of the merged branch over time">${g}${barLines}${lines}${dots}</svg></div>
    <div class="legend">${keys.map((k, i) => `<span><i style="background:var(--c${i % 8 + 1})"></i>${esc(sn.name(k))}</span>`).join("")}<span class="grow"></span><span>dashed: the bar tasks must clear</span></div>`;
}

function metricsTable(v) {
  const S = (v.scores || []).filter(s => s.metrics);
  if (!S.length) return chartEmpty("Each metric's start, current value and bar show up here once the run starts.");
  const keys = trackedMetrics(v), first = S[0].metrics, now = S[S.length - 1].metrics, sn = shortNames(keys);
  const rows = keys.map(k => {
    const t = v.targets[k];
    const ok = t && typeof now[k] === "number" ? (t.op === "<=" ? now[k] <= t.value : now[k] >= t.value) : null;
    const moves = [];
    for (let i = 1; i < S.length; i++) {
      const a = S[i - 1].metrics[k], b = S[i].metrics[k];
      if (typeof a === "number" && typeof b === "number" && Math.abs(b - a) >= 0.005 && S[i].node)
        moves.push(`<a href="javascript:void 0" data-sel="${esc(S[i].node)}" class="dchip ${b > a ? "up" : "down"}">${esc(S[i].node)} ${b > a ? "+" : "−"}${Math.abs(b - a).toFixed(2)}</a>`);
    }
    const chips = `<span class="dchips">${moves.join("") || `<span class="muted">–</span>`}</span>`;
    return `<tr><td class="mono" title="${esc(k)}">${esc(sn.name(k))}<div class="mv-in">${moves.length ? chips : ""}</div></td>
      <td class="num">${fmtScore(first[k])}</td>
      <td class="num"><b class="${ok === true ? "okv" : ok === false ? "lowv" : ""}">${fmtScore(now[k])}</b></td>
      <td class="num">${t ? `${t.op === "<=" ? "≤" : "≥"} ${fmtScore(t.value)}` : `<span class="muted">no drop</span>`}</td>
      <td class="mv">${chips}</td></tr>`;
  }).join("");
  const blocked = v.nodes.flatMap(n => n.checks.filter(c => c.verdict === "fail").flatMap(c =>
    (c.conditions || []).filter(x => x.kind === "no_regression" && x.met === false && x.drops).flatMap(x => x.drops.map(d => ({node: n.id, round: c.round, ...d})))));
  return `<table class="t metrics"><thead><tr><th>${sn.suffix ? `Field · ${esc(sn.suffix.toUpperCase())}` : "Metric"}</th><th>Start</th><th>Now</th><th>Bar</th><th class="mv">Moved by</th></tr></thead><tbody>${rows}</tbody></table>
    ${blocked.length ? `<div class="kicker">Stopped before merge</div>${blocked.map(b => `<div class="blocked"><span class="m n">×</span><div><a href="javascript:void 0" data-sel="${esc(b.node)}" class="mono">${esc(b.node)}</a> round ${b.round} would have taken <b class="mono">${esc(b.metric)}</b> from ${fmtScore(b.before)} to <span class="minus">${b.after == null ? "missing" : fmtScore(b.after)}</span>. The agent called it done; the check sent it back.</div></div>`).join("")}` : ""}`;
}

/* ---------- result (once the run is over) ---------- */

async function renderResult(el) {
  const v = cur;
  const merged = v.nodes.filter(n => n.merged_commit);
  if (v.state !== "done" && !(v.state === "stopped" && merged.length)) { el.innerHTML = ""; return; }
  if (!runDiff || runDiff.n !== merged.length) {
    el.innerHTML = `<div class="card result"><div class="card-h"><h2>What merged</h2></div><div class="card-b"><div class="skel" style="height:120px"></div></div></div>`;
    try { runDiff = await api(`/api/runs/${encodeURIComponent(v.id)}/diff`); runDiff.n = merged.length; }
    catch (e) { el.innerHTML = `<div class="notice err">Couldn't load the merged changes: ${esc(e.message)}</div>`; return; }
  }
  const S = (v.scores || []).filter(s => s.metrics);
  const keys = S.length ? trackedMetrics(v) : [];
  const first = S.length ? S[0].metrics : {}, last = S.length ? S[S.length - 1].metrics : {};
  const pm = files => {
    const a = files.reduce((s, f) => s + f.added, 0), r = files.reduce((s, f) => s + f.removed, 0);
    return `<span class="plus">+${a}</span>${r ? ` <span class="minus">−${r}</span>` : ""}`;
  };
  el.innerHTML = `<div class="card result">
    <div class="card-h"><h2>What merged</h2><span class="sub">${plural(runDiff.tasks.length, "task")} on <code>${esc(runDiff.branch || "")}</code> · ${pm(runDiff.tasks.flatMap(t => t.files))} · from <code>${esc((runDiff.base || "").slice(0, 7))}</code> · click a task for its diff</span></div>
    <div class="card-b">
      ${keys.length ? `<div class="finals">${keys.map(k => {
        const t = v.targets[k], ok = t ? (t.op === "<=" ? last[k] <= t.value : last[k] >= t.value) : true;
        return `<div class="final ${ok ? "" : "low"}"><span class="mono">${esc(k)}</span><b>${fmtScore(last[k])}</b><span class="small muted">from ${fmtScore(first[k])}</span></div>`;
      }).join("")}</div>` : ""}
      ${runDiff.tasks.map(t => `<details class="mtask">
        <summary><span class="mono muted">${esc(t.id)}</span> <b>${esc(t.title)}</b>
          <span class="small">${pm(t.files)} · ${plural(t.files.length, "file")}</span></summary>
        <div class="mfiles">${t.files.map(f => `<span class="mono">${esc(f.path)} ${pm([f])}</span>`).join("")}</div>
        <pre class="diff">${diffHtml(t.diff)}${t.cut ? "\n… cut here; run git diff for the rest" : ""}</pre>
      </details>`).join("")}
    </div></div>`;
}

function diffHtml(text) {
  return esc(text || "").split("\n").map(l =>
    /^(\+\+\+|---|diff |index |new file|deleted file)/.test(l) ? `<span class="dh">${l}</span>`
      : l.startsWith("@@") ? `<span class="dhunk">${l}</span>`
      : l.startsWith("+") ? `<span class="dadd">${l}</span>`
      : l.startsWith("-") ? `<span class="ddel">${l}</span>` : l).join("\n");
}

/* ---------- charts ---------- */

let CW = 560;
const CH = 200, PL = 42, PR = 12, PT = 10, PB = 26;
const chartWidth = el => Math.max(280, Math.min(900, Math.round(el.clientWidth) || 560));

function axes(maxX, maxY, fmtY, ticksY = 4) {
  const x = s => PL + (CW - PL - PR) * (maxX ? s / maxX : 0);
  const y = val => PT + (CH - PT - PB) * (1 - (maxY ? val / maxY : 0));
  let g = "";
  for (let i = 0; i <= ticksY; i++) {
    const val = maxY * i / ticksY;
    g += `<line class="grid" x1="${PL}" x2="${CW - PR}" y1="${y(val)}" y2="${y(val)}"/><text x="${PL - 6}" y="${y(val) + 4}" text-anchor="end">${fmtY(val)}</text>`;
  }
  const tx = niceTicks(maxX);
  tx.forEach(t => { g += `<text x="${x(t)}" y="${CH - 8}" text-anchor="middle">${dur(t)}</text>`; });
  return {x, y, g};
}

function niceTicks(max) {
  if (!max) return [0];
  const steps = [5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200];
  const st = steps.find(s => max / s <= 5) || Math.ceil(max / 5);
  const out = [];
  for (let t = 0; t <= max + 0.01; t += st) out.push(t);
  return out;
}

function chartEmpty(msg) {
  return `<div class="empty" style="padding:44px 16px"><div class="art">∿</div>${esc(msg)}</div>`;
}

function progressChart(v) {
  const S = v.samples, total = v.nodes.length;
  if (!total || S.length < 2 || !S.some(s => s.done || s.running || s.needs_you))
    return chartEmpty(v.state === "planning" ? "Fills in once the plan is ready and tasks start." : v.state === "plan_ready" ? "Approve the plan and this fills in as tasks run." : "Fills in as tasks run.");
  const maxX = Math.max(S[S.length - 1].s, 1);
  const {x, y, g} = axes(maxX, total, val => Math.round(val), total <= 6 ? total : total % 4 === 0 ? 4 : total % 3 === 0 ? 3 : total % 2 === 0 ? 2 : 1);
  const layers = [["done", "a-done"], ["running", "a-running"], ["needs_you", "a-needs"], ["queued", "a-queued"]];
  let base = S.map(() => 0), paths = "";
  layers.forEach(([k, cls]) => {
    const top = S.map((s, i) => base[i] + (s[k] || 0));
    let d = `M${x(S[0].s)} ${y(top[0])}`;
    for (let i = 1; i < S.length; i++) d += `H${x(S[i].s)}V${y(top[i])}`;
    d += `L${x(S[S.length - 1].s)} ${y(base[S.length - 1])}`;
    for (let i = S.length - 2; i >= 0; i--) d += `V${y(base[i])}H${x(S[i].s)}`;
    paths += `<path class="${cls}" d="${d}Z"/>`;
    base = top;
  });
  return `<div class="svgwrap chart"><svg viewBox="0 0 ${CW} ${CH}" role="img" aria-label="Tasks by state over time">${g}${paths}</svg></div>
    <div class="legend">${[["done", "var(--done-mark)"], ["running", "var(--run)"], ["needs you", "var(--needs-mark)"], ["queued", "var(--queued)"]].map(([l, c]) => `<span><i style="background:${c}"></i>${l}</span>`).join("")}</div>`;
}

function spendChart(v) {
  const S = v.samples;
  $("#spend-sub").textContent = `${money(v.spent_usd)} of ${money(v.budget_usd)}`;
  if (S.length < 2 || !v.spent_usd) return chartEmpty(v.state === "planning" ? "The planner's cost lands here first." : "Fills in as agents spend.");
  const maxX = Math.max(S[S.length - 1].s, 1), top = Math.max(v.budget_usd, v.spent_usd) * 1.08;
  const step = [0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1, 2, 2.5, 5, 10, 25, 50].find(s => s * 4 >= top) || Math.ceil(top / 4);
  const maxY = step * 4;
  const {x, y, g} = axes(maxX, maxY, val => "$" + val.toFixed(step < 0.1 ? 2 : step < 1 ? 2 : 0));
  let d = `M${x(S[0].s)} ${y(S[0].usd)}`;
  for (let i = 1; i < S.length; i++) d += `H${x(S[i].s)}V${y(S[i].usd)}`;
  const area = d + `V${y(0)}H${x(S[0].s)}Z`;
  const by = y(v.budget_usd);
  const sb = v.spend_by || {};
  return `<div class="svgwrap chart"><svg viewBox="0 0 ${CW} ${CH}" role="img" aria-label="Spend over time against the budget">${g}
      <path class="spend-area" d="${area}"/><path class="spend-line" d="${d}"/>
      <line class="budget-line" x1="${PL}" x2="${CW - PR}" y1="${by}" y2="${by}"/>
      <text class="budget-label" x="${CW - PR}" y="${by - 6}" text-anchor="end">budget ${money(v.budget_usd)}</text></svg></div>
    <div class="legend"><span><i style="background:var(--accent)"></i>spent</span><span><i style="background:var(--fail)"></i>run budget</span><span class="grow"></span>
      <span>planner ${money(sb.planner || 0)} · agents ${money(sb.worker || 0)} · checker ${money(sb.checker || 0)}</span></div>`;
}

function gantt(v) {
  const ns = v.nodes.filter(n => n.spans.length || n.state !== "queued");
  if (!v.nodes.length || !ns.length) return chartEmpty(v.state === "plan_ready" ? "Approve the plan to start the agents." : "Each task's rounds show up here as agents work and checks run.");
  const end = Math.max(v.elapsed_s, ...ns.flatMap(n => n.spans.map(s => s.end || 0)), 1);
  const narrow = $("#p-gantt").clientWidth < 600;
  const GW = Math.max(300, Math.round($("#p-gantt").clientWidth) || 1000), LW = narrow ? 40 : 210, RH = 26, top = 4;
  const x = s => LW + (GW - LW - 10) * s / end;
  let rows = "";
  ns.forEach((n, i) => {
    const yy = top + i * RH;
    rows += `<g data-node="${esc(n.id)}" style="cursor:pointer" class="${sel && sel !== n.id ? "dimrow" : ""}" opacity="${sel && sel !== n.id ? .45 : 1}">
      <rect class="lane" x="${LW}" y="${yy + 4}" width="${GW - LW - 10}" height="${RH - 8}" rx="4"/>
      <text class="lab id" x="0" y="${yy + 17}">${esc(n.id)}</text>
      ${narrow ? "" : `<text class="lab" x="30" y="${yy + 17}">${esc(trunc(n.title, 28))}</text>`}
      ${n.spans.map(s => {
        const e = s.end ?? v.elapsed_s;
        const cls = s.kind === "work" ? "sp-work" : "sp-check " + (s.end == null ? "" : s.ok ? "ok" : "bad");
        return `<rect class="${cls} ${s.end == null ? "sp-open" : ""}" x="${x(s.start)}" y="${yy + 6}" width="${Math.max(2, x(e) - x(s.start))}" height="${RH - 12}" rx="3"><title>${esc(n.id)} round ${s.round}: ${s.kind === "work" ? "agent working" : "check " + (s.end == null ? "running" : s.ok ? "passed" : "failed")} (${dur(e - s.start)})</title></rect>`;
      }).join("")}
      ${n.state === "needs_you" ? `<circle class="mark-needs" cx="${x(n.spans.length ? n.spans[n.spans.length - 1].end || v.elapsed_s : 0) + 8}" cy="${yy + RH / 2}" r="4.5"><title>needs you</title></circle>` : ""}
    </g>`;
  });
  const H = top + ns.length * RH + 22;
  const ticks = niceTicks(end).map(t => `<text x="${x(t)}" y="${H - 6}" text-anchor="middle">${dur(t)}</text>`).join("");
  return `<div class="svgwrap chart gantt"><svg viewBox="0 0 ${GW} ${H}" role="img" aria-label="Timeline of agent work and checks">${rows}${ticks}</svg></div>
    <div class="legend"><span><i style="background:var(--run)"></i>agent working</span><span><i style="background:var(--done-mark)"></i>check passed</span><span><i style="background:var(--fail)"></i>check failed</span><span><i style="background:var(--needs-mark);border-radius:50%"></i>needs you</span></div>`;
}

/* ---------- repo map ---------- */

function renderMap(el) {
  const m = runMap;
  if (!m) return;
  if (m.error && !m.modules.length) { el.innerHTML = `<div class="notice err">${esc(m.error)}</div>`; return; }
  const touched = m.modules.filter(x => x.tasks.length);
  $("#map-sub").textContent = `${m.name} · ${plural(m.file_count || 0, "file")} · ${touched.length} of ${plural(m.modules.length, "module")} changed`;
  if (!m.modules.length) { el.innerHTML = `<div class="empty"><b>Empty repo</b>No source files to map.</div>`; return; }
  const layers = {};
  m.modules.forEach(x => (layers[x.layer] = layers[x.layer] || []).push(x));
  const maxT = Math.max(1, ...m.modules.map(x => x.tasks.reduce((a, t) => a + t.files.length, 0)));
  const names = ["Entry points", "Middle", "Foundations"];
  const keys = Object.keys(layers).sort((a, b) => b - a);
  const labelFor = (k, i) => keys.length === 1 ? "Modules" : i === 0 ? "Entry points" : i === keys.length - 1 ? "Foundations" : keys.length > 3 ? "Middle · " + i : "Middle";
  const selNodeMods = sel ? new Set(m.modules.filter(x => x.tasks.some(t => t.id === sel)).map(x => x.id)) : null;
  let h = `<div class="layers">${keys.map((k, i) => `<div class="layer-label">${labelFor(k, i)}</div><div class="layer">${layers[k].sort((a, b) => b.tasks.length - a.tasks.length || b.lines - a.lines).map(x => {
    const nf = x.tasks.reduce((a, t) => a + t.files.length, 0);
    const dim = selNodeMods && !selNodeMods.has(x.id);
    return `<button class="mod ${x.tasks.length ? "hot" : ""} ${selMod === x.id ? "sel" : ""} ${dim ? "dim" : ""}" data-mod="${esc(x.id)}" title="${esc(x.id)}">
      ${nf ? `<span class="heat" style="opacity:${(0.05 + 0.13 * nf / maxT).toFixed(3)}"></span>` : ""}
      <span class="nm">${esc(x.id)}</span><span class="sz">${plural(x.files, "file")} · ${x.lines.toLocaleString()} lines</span>
      <span class="tk">${x.tasks.length ? x.tasks.map(t => `<span class="tchip st-${esc(t.state)}" title="${esc(t.id)}: ${esc(t.files.join(", "))}">${esc(t.id)}</span>`).join("") : `<span class="small muted">untouched</span>`}</span></button>`;
  }).join("")}</div>`).join("")}</div>`;
  const sm = selMod && m.modules.find(x => x.id === selMod);
  if (sm) {
    h += `<div class="mapside"><b class="mono">${esc(sm.id)}</b>${sm.tasks.length ? sm.tasks.map(t => `<div class="touch"><a href="javascript:void 0" data-sel="${esc(t.id)}" class="mono">${esc(t.id)}</a> ${esc((cur.nodes.find(n => n.id === t.id) || {}).title || "")} ${badge(t.state)}<div class="files" style="margin-top:4px">${t.files.map(f => `<span>${esc(f)}</span>`).join("")}</div></div>`).join("")
      : `<p class="small muted">No task changed this module. Biggest files: ${sm.top_files.map(f => `<code>${esc(f)}</code>`).join(" ")}</p>`}</div>`;
  } else {
    h += `<div class="key"><span><i class="swatch"></i>shade: how many files agents changed there</span><span>chips: the tasks that changed it</span><span>click a module for its files</span></div>`;
  }
  el.innerHTML = h;
  $$("[data-mod]", el).forEach(b => b.onclick = () => { selMod = selMod === b.dataset.mod ? null : b.dataset.mod; part("map", ["mod", selMod, Date.now()], renderMap); });
  bindActions(el);
}

/* ---------- activity ---------- */

const EV_ICON = {goal: "◎", planner: "·", plan: "▣", plan_problem: "!", run: "▶", worktree: "⑂", round: "↻", activity: "·",
                 check: "✓", merge: "⇥", needs_you: "!", you: "☺", stopped: "■", error: "×", weak_contract: "!"};

function feedRow(e) {
  return `<div class="ev ${esc(e.level)} k-${esc(e.kind)}"><span class="t">${dur(e.s)}</span><span class="n">${esc(e.node || "")}</span><span class="x" title="${e.text.length > 200 ? esc(e.text) : ""}">${esc(trunc(e.text, 200))}</span></div>`;
}

function renderFeed(el) {
  const evs = cur.events.filter(e => !sel || e.node === sel || !e.node).slice(-150).reverse();
  el.innerHTML = evs.length ? evs.map(feedRow).join("") : `<div class="empty">Nothing yet.</div>`;
}

window.addEventListener("resize", () => {
  if (route.view !== "run" || !cur) return;
  clearTimeout(window.__rz);
  window.__rz = setTimeout(() => { delete sigs.graph; delete sigs.gantt; renderRun(cur); }, 150);
});

go();
