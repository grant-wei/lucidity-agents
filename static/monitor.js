/* The monitor: Claude Code / Codex sessions you started by hand, read from their logs.
   Sessions (triage + done checks), Session map (which modules they changed), Trace (how a refresh decided)
   and Evals. Reads /api/snapshot (polled in index.html), /api/map, /api/traces, /api/trace, /api/evals. */
(function () {
  "use strict";
  const mins = m => m == null ? "–" : m < 1 ? "just now" : m < 60 ? Math.round(m) + " min ago" : (m / 60).toFixed(1) + " h ago";
  const since = (t, now) => { const m = (now - Date.parse(t)) / 60000; return m >= 2880 ? Math.round(m / 1440) + " days ago" : mins(m); };
  const short = (s, n) => (s = String(s || "")).length > n ? s.slice(0, n - 1) + "…" : s;
  const LABEL = {needs_you: "Needs you", working: "Working", finished: "Finished", unknown: "Unknown"};
  const BADGE = {needs_you: "needs_you", working: "running", finished: "done", unknown: "stopped"};
  const FIELD = {doing_now: "now", done_so_far: "done", needs_from_you: "needs"};
  const PALETTE = ["#4f46e5", "#c2410c", "#16a34a", "#a21caf", "#0e7490", "#b45309", "#be123c", "#65a30d", "#7c3aed", "#0284c7"];
  const WINDOWS = {"24h": 24, "3 days": 72, "7 days": 168};
  let view = null;

  const head = (title, sub) => `<div class="vhead"><h1>${title}</h1><span class="chip">${snap && snap.mode === "local" ? "your sessions" : "sample data"}</span><span class="grow"></span>
    <button class="btn sm" data-refresh title="Read the session logs again now">${snap && snap.refreshing ? "Refreshing…" : "Refresh"}</button></div>${sub || ""}`;

  function banners() {
    if (!snap) return "";
    return (snap.error ? `<div class="banner bad">${esc(snap.error)}</div>` : "") + (snap.banner ? `<div class="banner">${esc(snap.banner)}</div>` : "");
  }

  function bindRefresh(el) {
    $$("[data-refresh]", el).forEach(b => {
      b.disabled = !!(snap && snap.refreshing);
      b.onclick = async () => {
        b.disabled = true; b.textContent = "Refreshing…";
        try { await fetch("/api/refresh", {method: "POST"}); } catch (e) {}
        setTimeout(pollSnapshot, 1500);
        if (view === "map") setTimeout(loadMap, 4000);
      };
    });
  }

  /* ---------- sessions ---------- */

  function renderSessions() {
    const el = $("#view-sessions");
    if (!snap) { el.innerHTML = head("Sessions") + `<div class="skel" style="height:160px"></div>`; return; }
    const rows = snap.sessions || [];
    let h = head("Sessions", `<p class="intro"><b>Agents you started yourself, on one screen.</b> Lucidity reads ${snap.mode === "local" ? "your Claude Code and Codex logs" : "8 sample agent sessions"}, works out which ones are waiting on you, and checks the ones that say they're done. Every claim cites the log line it came from: click a chip like <span class="eid" style="cursor:default">e12</span> to see it.</p>`) + banners();
    if (!rows.length) {
      h += `<div class="card">` + (snap.refreshing || !snap.refresh_id
        ? `<div class="empty"><div class="art">…</div><b>Reading your sessions</b>The first refresh takes 20 to 40 seconds. After that, only sessions that changed are read again.</div>`
        : snap.mode === "local"
        ? `<div class="empty"><div class="art">◇</div><b>No agent sessions from the last 3 days</b>Lucidity looks in <code>~/.claude/projects</code> and <code>~/.codex/sessions</code>. Start a Claude Code or Codex session and press Refresh.</div>`
        : `<div class="empty"><div class="art">◇</div><b>No sample sessions found</b>Rebuild them with <code>python sample_data/generate.py</code>.</div>`) + `</div>`;
      el.innerHTML = h; bindRefresh(el); return;
    }
    const needs = rows.filter(r => r.state === "needs_you");
    const flagged = rows.filter(r => r.flags.length || (r.checker && r.checker.verdict === "not_verified") || r.secrets.length);
    const extra = flagged.filter(r => r.state !== "needs_you");
    if (needs.length || extra.length) {
      h += `<div class="mneeds"><h2>Needs you (${needs.length + extra.length})</h2>
        <div class="why">Agents blocked on an answer or approval, plus anything a rule flagged: runaway spend, a repeating failure, a "done" that didn't check out, a leaked secret.</div><ul>`;
      for (const r of needs) {
        const c = r.claims.find(c => c.field === "needs_from_you") || r.claims[0];
        h += `<li><a href="javascript:void 0" data-jump="${esc(r.id)}"><b>${esc(r.project)}</b></a>: ${esc(c ? c.text : "waiting on you")}</li>`;
      }
      for (const r of extra) {
        const why = r.flags.length ? r.flags[0].kind + ": " + r.flags[0].reason
          : r.secrets.length ? "secret in transcript (" + r.secrets.map(s => s.kind).join(", ") + ")" : "says done, checker could not verify";
        h += `<li><a href="javascript:void 0" data-jump="${esc(r.id)}"><b>${esc(r.project)}</b></a>: ${esc(why)}</li>`;
      }
      h += `</ul></div>`;
    } else h += `<div class="mneeds ok"><h2>Nothing needs you</h2><div class="why" style="margin:0">No agent is waiting on you and no rule fired.</div></div>`;
    h += `<div class="kicker">All sessions (${rows.length})</div><div class="sgrid">` + rows.map(card).join("") + `</div>`;
    el.innerHTML = h;
    bindRefresh(el);
    $$(".eid[data-e]", el).forEach(b => b.onclick = () => showEvent(b.dataset.s, b.dataset.e));
    $$("[data-sact]", el).forEach(b => b.onclick = () => sessionAct(b.dataset.s, b.dataset.sact, b));
    $$("[data-jump]", el).forEach(a => a.onclick = () => { const c = document.getElementById("c-" + a.dataset.jump); if (c) c.scrollIntoView({behavior: "smooth", block: "start"}); });
  }

  function card(r) {
    let h = `<div class="card scard${r.flags.length ? " flagged" : ""}" id="c-${esc(r.id)}">
      <div class="topline"><span class="proj">${esc(r.project)}</span><span class="grow"></span>${badge(BADGE[r.state] || "stopped", LABEL[r.state] || r.state)}</div>
      <div class="sub">${esc(r.tool)} · ${esc(r.model || "")} · ${mins(r.idle_min)} · ${money(r.usd)} so far</div>`;
    if (r.first_prompt) h += `<div class="task">“${esc(short(r.first_prompt, 160))}”</div>`;
    for (const c of r.claims)
      h += `<div class="claim"><span class="f">${FIELD[c.field] || c.field}</span>${esc(c.text)}` +
        c.event_ids.map(e => `<button class="eid" data-s="${esc(r.id)}" data-e="${esc(e)}" title="Show the log line this is based on">${esc(e)}</button>`).join("") + `</div>`;
    if (r.overridden) h += `<div class="note">Marked "needs you" by a rule: ${esc(r.overridden.because)} (${r.overridden.model_said === "unknown" ? "no model result" : "the model said " + esc(r.overridden.model_said)}).</div>`;
    for (const f of r.flags) {
      const x = r.explanation || {};
      h += `<div class="box bad"><b>${f.kind === "runaway" ? "Runaway spend" : "Stalled"}</b><div class="what">${f.kind === "runaway" ? "A plain-code rule saw the agent looping or spending past its cap." : "A plain-code rule saw the same failure repeat with no progress."}</div>${esc(f.reason)}.` +
        (x.why ? `<div style="margin-top:4px">${esc(x.why)}</div>` : "") +
        (x.next_step ? `<div style="margin-top:4px"><i>Suggested:</i> ${esc(x.next_step)}</div>` : "") +
        `<div class="acts">` + ["pause", "stop", "let_it_run"].map(a =>
          `<button class="btn sm ${x.recommendation === a ? "primary" : ""}" data-sact="${a}" data-s="${esc(r.id)}">${a === "let_it_run" ? "Let it run" : a[0].toUpperCase() + a.slice(1)}</button>`).join("") +
        `</div><div class="note">Lucidity doesn't stop hand-started agents itself. Your click is logged; stop it in its terminal.</div></div>`;
    }
    if (r.checker) {
      const ok = r.checker.verdict === "verified";
      h += `<div class="box ${ok ? "ok" : "warn"}"><b>${ok ? "✓ Done, verified" : "× Says done, not verified"}</b><div class="what">The done checker ran the task's tests and graded each done-when condition.</div>` +
        (r.checker.conditions || []).map(c => `<div>${c.met ? "✓" : "×"} ${esc(c.condition)} <span class="note">${esc(c.evidence)}</span></div>`).join("") +
        ((r.checker.missing || []).length ? `<div><i>Missing:</i> ${esc(r.checker.missing.map(m => m.replace(/[.;\s]+$/, "")).join("; "))}</div>` : "") +
        (r.checker.tests_ran || []).map(t => `<div class="note">ran <code>${esc(t.command)}</code> → exit ${esc(t.exit_code ?? (t.refused ? "refused" : "?"))}</div>`).join("") + `</div>`;
    }
    if (r.secrets.length) h += `<div class="box bad"><b>Secret in the transcript</b>${esc(r.secrets.map(s => s.kind + " (" + s.event_ids.join(", ") + ")").join("; "))}. It was redacted before any model saw it. Rotate it.</div>`;
    if (r.warning) h += `<div class="box warn"><b>Heads up</b><div class="what">Something the triage agent noticed that isn't a status.</div>${esc(r.warning)}</div>`;
    h += `<details id="d-${esc(r.id)}"><summary>Log (last ${r.events.length} of ${r.event_count} events)</summary><div class="evlog">` +
      r.events.map(e => `<div data-e="${esc(e.id)}"><b>${esc(e.id)}</b> ${esc(e.kind)}${e.tool ? " " + esc(e.tool) : ""}: <span class="${e.is_error ? "err" : ""}">${esc(e.text.slice(0, 500))}</span></div>`).join("") +
      `</div></details>`;
    return h + `</div>`;
  }

  function showEvent(sid, eid) {
    const d = document.getElementById("d-" + sid); if (!d) return;
    d.open = true;
    $$(".evlog div", d).forEach(x => x.classList.toggle("hl", x.dataset.e === eid));
    const t = d.querySelector(`.evlog div[data-e="${CSS.escape(eid)}"]`);
    if (t) t.scrollIntoView({block: "nearest"});
    else $(".evlog", d).insertAdjacentHTML("afterbegin", `<div class="hl">${esc(eid)} is older than the last ${$$(".evlog div", d).length} events shown.</div>`);
  }

  async function sessionAct(sid, action, btn) {
    try { await fetch("/api/action", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({session_id: sid, action})}); } catch (e) { return; }
    $$("button", btn.parentElement).forEach(b => b.classList.remove("primary"));
    btn.classList.add("primary"); btn.textContent = "✓ " + btn.textContent.replace(/^✓ /, "");
  }

  /* ---------- session map ---------- */

  let mapData = null, repoSel = null, modSel = null, sessSel = null, win = "7 days", mapTimer = null;

  async function loadMap() {
    try { mapData = await (await fetch("/api/map")).json(); } catch (e) { mapData = {error: "Can't reach the Lucidity server."}; }
    if (view === "map") drawMap();
    clearTimeout(mapTimer);
    if (view === "map") mapTimer = setTimeout(loadMap, mapData && mapData.building ? 4000 : 30000);
  }

  function mapView() {
    const repo = (mapData.repos || []).find(r => r.name === repoSel) || (mapData.repos || [])[0];
    if (!repo) return null;
    repoSel = repo.name;
    const now = Date.parse(mapData.now), cut = now - WINDOWS[win] * 3600e3;
    const touches = repo.touches.filter(t => Date.parse(t.t) >= cut);
    const ids = new Set(touches.map(t => t.session));
    const sessions = repo.sessions.filter(s => ids.has(s.id)).sort((a, b) => Date.parse(b.last_edit) - Date.parse(a.last_edit));
    const color = {}; repo.sessions.forEach((s, i) => color[s.id] = PALETTE[i % PALETTE.length]);
    const byMod = {};
    for (const t of touches) {
      const m = byMod[t.module] = byMod[t.module] || {edits: 0, lines: 0, usd: 0, sessions: new Set()};
      m.edits++; m.lines += t.added + t.removed; m.usd += t.usd; m.sessions.add(t.session);
    }
    if (sessSel && !ids.has(sessSel)) sessSel = null;
    return {repo, now, touches, sessions, color, byMod, roles: (repo.architect || {}).roles || {}};
  }

  function drawMap() {
    const el = $("#view-map");
    const top = head("Session map", `<p class="intro"><b>Where your hand-started agents worked.</b> Each box is a part of the repo, shaded by how much agents changed it. Runs have their own map on the run page.</p>`);
    if (mapData && mapData.error && !mapData.repos) { el.innerHTML = top + `<div class="banner bad">${esc(mapData.error)}</div>`; bindRefresh(el); return; }
    if (!mapData || !mapData.repos) {
      el.innerHTML = top + `<div class="card"><div class="empty"><div class="art">…</div><b>Drawing the map</b>Reading which files your agents changed and how the code fits together. The first pass over a big repo takes a minute or two.</div></div>`;
      bindRefresh(el); return;
    }
    const v = mapView();
    if (!v) {
      el.innerHTML = top + `<div class="card"><div class="empty"><div class="art">◇</div><b>No agent edits in the last 7 days</b>The map is built from the files Claude Code and Codex sessions change. Once an agent edits a file in a git repo, the repo shows up here.</div></div>`;
      bindRefresh(el); return;
    }
    const {repo, touches, sessions} = v;
    const usd = sessions.reduce((a, s) => a + s.usd, 0);
    el.innerHTML = top + `<div class="mtool">
        <select id="mrepo" class="repo-pick" aria-label="Repository">${mapData.repos.map(r => `<option value="${esc(r.name)}"${r.name === repo.name ? " selected" : ""}>${esc(r.name)}</option>`).join("")}</select>
        <div class="segb" role="group" aria-label="Time window">${Object.keys(WINDOWS).map(w => `<button data-win="${w}"${w === win ? ' class="on"' : ""}>${w}</button>`).join("")}</div>
        <div class="mstats"><span><b>${sessions.length}</b> ${sessions.length === 1 ? "session" : "sessions"}</span><span><b>${touches.length}</b> file edits</span><span><b>${money(usd)}</b> agent spend</span></div>
      </div>
      ${mapData.banner ? `<div class="banner">${esc(mapData.banner)}</div>` : ""}
      <div class="mapwrap"><div class="card"><div id="msvg" class="svgwrap"></div>
        <div class="key"><span><i class="swatch"></i>more agent changes</span><span><i class="dot" style="background:var(--muted)"></i>one agent session</span><span>arrows show imports; click a part to see them</span></div></div>
        <aside class="card side" style="padding:16px" id="mdetail"></aside></div>`;
    bindRefresh(el);
    $("#mrepo").onchange = e => { repoSel = e.target.value; modSel = sessSel = null; drawMap(); };
    $$("[data-win]", el).forEach(b => b.onclick = () => { win = b.dataset.win; drawMap(); });
    drawModules(v);
    drawModDetail(v);
  }

  function drawModules(v) {
    const {repo, byMod, color, roles} = v;
    const cw = $("#msvg").clientWidth;
    const W = 220, H = 70, GX = 16, GY = 34, PER = cw < 520 ? 2 : cw < 940 ? 3 : 4;
    const rows = {};
    repo.modules.forEach(m => (rows[m.layer] = rows[m.layer] || []).push(m));
    const layersDesc = Object.keys(rows).map(Number).sort((a, b) => b - a);
    layersDesc.forEach(l => rows[l].sort((a, b) => (byMod[b.id] ? 1 : 0) - (byMod[a.id] ? 1 : 0) || a.id.localeCompare(b.id)));
    let lines = [];
    for (const l of layersDesc) for (let i = 0; i < rows[l].length; i += PER) lines.push(rows[l].slice(i, i + PER));
    if (lines.length > 6) {
      lines = [[]];
      for (const l of layersDesc) for (const m of rows[l]) {
        if (lines[lines.length - 1].length >= PER) lines.push([]);
        lines[lines.length - 1].push(m);
      }
    }
    const cols = Math.max(...lines.map(r => r.length));
    const width = cols * W + (cols - 1) * GX + 4, height = lines.length * (H + GY) - GY + 4, pos = {};
    lines.forEach((r, ri) => {
      const off = (width - (r.length * W + (r.length - 1) * GX)) / 2;
      r.forEach((m, i) => pos[m.id] = {x: off + i * (W + GX), y: 2 + ri * (H + GY)});
    });
    const maxLines = Math.max(1, ...Object.values(byMod).map(m => m.lines));
    const sessMods = sessSel ? new Set(v.touches.filter(t => t.session === sessSel).map(t => t.module)) : null;
    const near = id => repo.edges.some(e => (e.from === modSel && e.to === id) || (e.to === modSel && e.from === id));
    const lit = id => sessMods ? sessMods.has(id) : modSel ? id === modSel || near(id) : true;
    let s = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Map of ${esc(repo.name)}">
      <defs><marker id="ma" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0L10,5L0,10z" fill="var(--accent)"/></marker></defs>`;
    for (const e of repo.edges) {
      const a = pos[e.from], b = pos[e.to]; if (!a || !b) continue;
      const hot = modSel && (e.from === modSel || e.to === modSel);
      let x1 = a.x + W / 2, y1 = a.y + H, x2 = b.x + W / 2, y2 = b.y;
      if (b.y <= a.y) { y1 = a.y + H / 2; y2 = b.y + H / 2; x1 = a.x + (b.x > a.x ? W : 0); x2 = b.x + (b.x > a.x ? 0 : W); }
      const my = (y1 + y2) / 2;
      s += `<path class="dep${hot ? " hot" : ""}" d="M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2 - 2}"${hot ? ' marker-end="url(#ma)"' : ""}><title>${esc(e.from)} imports ${esc(e.to)}</title></path>`;
    }
    for (const m of repo.modules) {
      const p = pos[m.id], act = byMod[m.id], role = (roles[m.id] || {}).role || "";
      const heat = act ? 0.07 + 0.38 * Math.sqrt(act.lines / maxLines) : 0;
      const dots = act ? [...act.sessions] : [];
      let r1 = role, r2 = "";
      if (role.length > 32) { const cut = role.lastIndexOf(" ", 32); r1 = role.slice(0, cut > 0 ? cut : 32); r2 = short(role.slice(r1.length).trim(), 33); }
      const nameW = dots.length ? 25 - Math.min(dots.length, 4) * 2 : 27;
      s += `<g class="smod${act ? " hot" : " cold"}${m.id === modSel ? " sel" : ""}${lit(m.id) ? "" : " dim"}${m.gone ? " gone" : ""}" data-m="${esc(m.id)}" tabindex="0" role="button">
        <rect class="b" x="${p.x}" y="${p.y}" width="${W}" height="${H}" rx="9"/>
        ${heat ? `<rect class="h" x="${p.x}" y="${p.y}" width="${W}" height="${H}" rx="9" opacity="${heat.toFixed(2)}"/>` : ""}
        <text class="t" x="${p.x + 12}" y="${p.y + 23}">${esc(short(m.id, nameW))}</text>
        <text class="r" x="${p.x + 12}" y="${p.y + 42}">${esc(r1)}</text>
        <text class="r" x="${p.x + 12}" y="${p.y + 57}">${esc(r2)}</text>
        ${dots.slice(0, 4).map((d, i) => `<circle cx="${p.x + W - 13 - i * 12}" cy="${p.y + 18}" r="4.5" fill="${color[d]}"/>`).join("")}
        <title>${esc(m.id)}${role ? ": " + esc(role) : ""}</title></g>`;
    }
    $("#msvg").innerHTML = s + `</svg>`;
    $$("#msvg .smod").forEach(g => {
      const pick = () => { modSel = modSel === g.dataset.m ? null : g.dataset.m; sessSel = null; drawMap(); };
      g.onclick = pick; g.onkeydown = e => { if (e.key === "Enter") pick(); };
    });
  }

  function sessionRow(s, v, extra) {
    return `<button class="srow${s.id === sessSel ? " on" : ""}" data-sess="${esc(s.id)}" title="${esc(s.first_prompt)}">
      <span class="dot" style="background:${v.color[s.id]}"></span><span class="p">${esc(s.first_prompt || "(no prompt)")}</span><span class="c">${money(s.usd)}</span>
      <span class="m">${esc(s.tool)} · ${since(s.last_edit, v.now)}${extra ? " · " + extra : ""}</span></button>`;
  }

  function drawModDetail(v) {
    const {repo, touches, roles} = v;
    const back = `<button class="back" id="mback">← ${esc(repo.name)}</button>`;
    let h;
    if (sessSel) {
      const s = repo.sessions.find(x => x.id === sessSel), mine = touches.filter(t => t.session === sessSel);
      const mods = [...new Set(mine.map(t => t.module))];
      const add = mine.reduce((a, t) => a + t.added, 0), rem = mine.reduce((a, t) => a + t.removed, 0);
      h = back + `<h3><span class="dot" style="background:${v.color[sessSel]}"></span> ${esc(s.tool)} session</h3>
        <div class="meta">${esc(s.model || "")} · ${money(s.usd)} · last edit ${since(s.last_edit, v.now)} · <span class="plus">+${add}</span> <span class="minus">−${rem}</span></div>
        <p class="role">“${esc(short(s.first_prompt, 280))}”</p>
        <div class="kicker">Changed ${plural(mods.length, "part")}</div>` +
        mods.map(m => `<div class="touch"><b>${esc(m)}</b>${roles[m] ? `<div class="cite">${esc(roles[m].role)}</div>` : ""}` +
          [...new Set(mine.filter(t => t.module === m).map(t => t.file))].slice(0, 8).map(f => `<span class="file">${esc(f)}</span>`).join("") + `</div>`).join("");
    } else if (modSel) {
      const m = repo.modules.find(x => x.id === modSel), r = roles[modSel], mine = touches.filter(t => t.module === modSel);
      const out = repo.edges.filter(e => e.from === modSel).map(e => e.to), inn = repo.edges.filter(e => e.to === modSel).map(e => e.from);
      const ids = [...new Set(mine.map(t => t.session))];
      h = back + `<h3>${esc(m.id)}</h3><div class="meta">${plural(m.files, "file")} · ${m.lines.toLocaleString("en-US")} lines${m.gone ? " · no longer in the repo" : ""}</div>` +
        (r ? `<p class="role">${esc(r.role)}</p><div class="cite">from ${r.cites.map(c => esc(c.split("/").pop())).join(", ")}${repo.architect.stale ? " · update queued" : ""}</div>`
           : `<p class="meta">No description yet. One is written when a model key is set.</p>`) +
        (out.length || inn.length ? `<div class="kicker">Connections</div>` : "") +
        (out.length ? `<div class="meta">uses ${esc(out.join(", "))}</div>` : "") + (inn.length ? `<div class="meta">used by ${esc(inn.join(", "))}</div>` : "") +
        `<div class="kicker">Agent sessions, last ${esc(win)}</div>` +
        (ids.length ? ids.map(id => {
          const list = mine.filter(t => t.session === id);
          const add = list.reduce((a, t) => a + t.added, 0), rem = list.reduce((a, t) => a + t.removed, 0);
          const files = [...new Set(list.map(t => t.file))];
          return sessionRow(repo.sessions.find(x => x.id === id), v, `+${add} −${rem}`) +
            `<div style="padding:0 0 6px 19px">${files.slice(0, 5).map(f => `<span class="file">${esc(f.slice(m.id === "(root)" ? 0 : m.id.length + 1))}</span>`).join("")}${files.length > 5 ? `<span class="cite">and ${files.length - 5} more</span>` : ""}</div>`;
        }).join("") : `<div class="meta">None.</div>`);
    } else {
      const ranked = Object.entries(v.byMod).sort((a, b) => b[1].lines - a[1].lines).slice(0, 6);
      const top = ranked.length ? ranked[0][1].lines : 1;
      h = `<h3>${esc(repo.name)}</h3><div class="meta">${repo.file_count.toLocaleString("en-US")} files</div>` +
        (repo.architect && repo.architect.summary ? `<p class="role">${esc(repo.architect.summary)}</p>` : "") +
        `<div class="kicker">Agent sessions, last ${esc(win)}</div>` +
        (v.sessions.length ? v.sessions.map(s => sessionRow(s, v)).join("") : `<div class="meta">None in this window.</div>`) +
        (ranked.length ? `<div class="kicker">Most changed</div>` + ranked.map(([id, a]) =>
          `<div class="bar2"><span>${esc(id)}</span><span class="meta">${a.lines} lines</span><div class="bar"><i style="width:${(100 * a.lines / top).toFixed(0)}%"></i></div></div>`).join("") : "");
    }
    $("#mdetail").innerHTML = h;
    if ($("#mback")) $("#mback").onclick = () => { modSel = sessSel = null; drawMap(); };
    $$("#mdetail [data-sess]").forEach(b => b.onclick = () => { sessSel = b.dataset.sess; modSel = null; drawMap(); });
  }

  /* ---------- trace ---------- */

  let traceSel = null, traceData = null, nodeSel = null;

  async function loadTraces() {
    const el = $("#view-trace");
    const top = head("Trace", `<p class="intro"><b>How Lucidity reached what's on the Sessions page.</b> One graph per refresh. Most steps are plain code; the model is called only for sessions that changed.</p>`);
    let list;
    try { list = await (await fetch("/api/traces")).json(); } catch (e) { el.innerHTML = top + `<div class="banner bad">Can't reach the Lucidity server.</div>`; return; }
    if (!list.length) {
      el.innerHTML = top + `<div class="card"><div class="empty"><div class="art">⑂</div><b>No refresh has run yet</b>Press Refresh. Each refresh is traced here: which steps were plain code, which were model calls, and what each cost.</div></div>`;
      bindRefresh(el); return;
    }
    if (!traceSel || !list.find(t => t.id === traceSel)) traceSel = (list.find(t => t.agents > 0) || list[0]).id;
    traceData = await (await fetch("/api/trace?id=" + encodeURIComponent(traceSel))).json();
    const opts = list.map(t => `<option value="${esc(t.id)}"${t.id === traceSel ? " selected" : ""}>${esc(t.id)} · ${t.agents} agent call(s) · ${money(t.usd)}</option>`).join("");
    el.innerHTML = top + `<div class="rowline"><label class="f" for="tsel" style="margin:0">Refresh</label><select id="tsel">${opts}</select>
      <span class="note" style="margin:0">${traceData.tokens} tokens · ${money(traceData.usd)} · ${traceData.seconds}s. Grey boxes are plain code, outlined boxes are model calls. Click one.</span></div>
      <div class="flowwrap"><div class="card"><div class="svgwrap" id="fsvg"></div></div><div class="card fdetail" style="padding:16px" id="fdetail"></div></div>`;
    bindRefresh(el);
    $("#tsel").onchange = e => { traceSel = e.target.value; nodeSel = null; loadTraces(); };
    drawFlow();
  }

  function drawFlow() {
    const t = traceData, depth = {}, kids = {};
    t.edges.forEach(([a, b]) => (kids[a] = kids[a] || []).push(b));
    const roots = t.nodes.filter(n => !t.edges.some(e => e[1] === n.id));
    const q = roots.map(n => [n.id, 0]);
    while (q.length) { const [id, d] = q.shift(); if (depth[id] != null) continue; depth[id] = d; (kids[id] || []).forEach(k => q.push([k, d + 1])); }
    const cols = {}; t.nodes.forEach(n => (cols[depth[n.id] ?? 0] = cols[depth[n.id] ?? 0] || []).push(n));
    const W = 170, H = 54, GX = 46, GY = 18, pos = {};
    const ncol = Object.keys(cols).length, maxRows = Math.max(...Object.values(cols).map(c => c.length));
    const width = ncol * W + (ncol - 1) * GX + 20, height = Math.max(1, maxRows) * (H + GY) + 10;
    Object.entries(cols).forEach(([d, ns]) => {
      const off = (height - ns.length * (H + GY)) / 2;
      ns.forEach((n, i) => pos[n.id] = {x: 10 + d * (W + GX), y: off + i * (H + GY) + GY / 2});
    });
    let s = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="How this refresh decided">
      <defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L10,5L0,10z" fill="var(--muted)"/></marker></defs>`;
    t.edges.forEach(([a, b]) => { const p = pos[a], q2 = pos[b]; if (!p || !q2) return;
      const x1 = p.x + W, y1 = p.y + H / 2, x2 = q2.x, y2 = q2.y + H / 2, mx = (x1 + x2) / 2;
      s += `<path class="fedge" d="M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2 - 2},${y2}" marker-end="url(#ar)"/>`; });
    t.nodes.forEach(n => { const p = pos[n.id];
      const sub = n.kind === "agent" ? `${n.tools.length} tool call(s) · ${money(n.usd)}` : "code · $0";
      s += `<g class="fnode ${n.kind}${n.id === nodeSel ? " sel" : ""}" data-n="${esc(n.id)}" tabindex="0" role="button">
        <rect x="${p.x}" y="${p.y}" width="${W}" height="${H}" rx="8"/>
        <text x="${p.x + 10}" y="${p.y + 22}">${esc(short(n.label, 24))}</text>
        <text class="s" x="${p.x + 10}" y="${p.y + 40}">${esc(sub)}</text></g>`; });
    $("#fsvg").innerHTML = s + `</svg>`;
    $$("#fsvg .fnode").forEach(g => { g.onclick = () => { nodeSel = g.dataset.n; drawFlow(); };
      g.onkeydown = e => { if (e.key === "Enter") { nodeSel = g.dataset.n; drawFlow(); } }; });
    const n = t.nodes.find(x => x.id === nodeSel) || t.nodes.find(x => x.kind === "agent") || t.nodes[0];
    $("#fdetail").innerHTML = `<h3>${esc(n.label)}</h3><div class="note">${esc(n.kind === "agent" ? "model call" : "plain code, no model")} · ${n.tokens} tokens · ${money(n.usd)}</div>
      ${n.note ? `<p>${esc(n.note)}</p>` : ""}${n.output && n.kind === "code" ? `<p>${esc(n.output)}</p>` : ""}
      ${n.tools.length ? `<div class="kicker">Tool calls</div>` + n.tools.map(x => `<details><summary>${esc(x.name)} ${esc(x.args)}</summary><pre>${esc(x.result)}</pre></details>`).join("") : ""}
      ${n.input && n.kind === "agent" ? `<details><summary>What it read</summary><pre>${esc(n.input)}</pre></details>` : ""}
      ${n.output && n.kind === "agent" ? `<details open><summary>What it returned</summary><pre>${esc(n.output)}</pre></details>` : ""}`;
  }

  /* ---------- evals ---------- */

  async function loadEvals() {
    const el = $("#view-evals");
    const top = `<div class="vhead"><h1>Evals</h1></div><p class="intro"><b>How often the monitor gets it right, and what that costs.</b> Labeled cases run through the real pipeline under different settings.`;
    let r;
    try { r = await (await fetch("/api/evals")).json(); } catch (e) { el.innerHTML = top + `</p><div class="banner bad">Can't reach the Lucidity server.</div>`; return; }
    if (!r || !r.configs) { el.innerHTML = top + `</p><div class="card"><div class="empty"><div class="art">∑</div><b>No eval results yet</b>Run <code>python evals/run_evals.py</code>.</div></div>`; return; }
    const cols = r.columns || Object.keys(r.configs[0].metrics);
    let h = top + ` ${esc(r.summary || "")}</p><div class="card" style="overflow:hidden"><table class="t stack"><thead><tr><th>Configuration</th>${cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>`;
    for (const c of r.configs) h += `<tr><td data-h="Configuration"><b>${esc(c.name)}</b><div class="note">${esc(c.desc || "")}</div></td>` +
      cols.map(k => `<td class="num" data-h="${esc(k)}">${esc(typeof c.metrics[k] === "number" ? c.metrics[k].toLocaleString("en-US") : c.metrics[k] ?? "")}</td>`).join("") + `</tr>`;
    h += `</tbody></table></div>`;
    if (r.cases) h += `<details style="margin-top:14px"><summary>${r.cases.length} test cases</summary><div class="card" style="overflow:hidden;margin-top:8px"><table class="t stack"><thead><tr><th>Case</th><th>Expected</th><th>Got (default, each run)</th></tr></thead><tbody>` +
      r.cases.map(c => `<tr><td data-h="Case">${esc(c.name)}</td><td data-h="Expected">${esc(c.expected)}</td><td data-h="Got">${esc(c.got)}${c.pass ? " ✓" : " ×"}</td></tr>`).join("") + `</tbody></table></div></details>`;
    el.innerHTML = h;
  }

  window.addEventListener("snapshot", () => {
    if (view === "sessions") renderSessions();
    if (view && view !== "evals") $$(`#view-${view} [data-refresh]`).forEach(b => { b.disabled = !!snap.refreshing; b.textContent = snap.refreshing ? "Refreshing…" : "Refresh"; });
  });
  window.addEventListener("hashchange", () => { if (!["sessions", "map", "trace", "evals"].includes((location.hash.slice(1) || "").split("/")[0])) { view = null; clearTimeout(mapTimer); } });

  window.Monitor = {
    show(v) {
      view = v;
      if (v === "sessions") renderSessions();
      if (v === "map") { drawMap(); loadMap(); }
      if (v === "trace") loadTraces();
      if (v === "evals") loadEvals();
    },
  };
  if (["sessions", "map", "trace", "evals"].includes((location.hash.slice(1) || "").split("/")[0])) window.Monitor.show(location.hash.slice(1).split("/")[0]);
})();
