// EVA viz-p2 — 三层 Viewer 前端（vanilla JS，无框架，无 CDN）
// PR-V1 范围：L1 游戏视图 + timeline scrubber + L2/L3 基础骨架
(function () {
  "use strict";

  // =========================================================
  // 全局状态
  // =========================================================
  const state = {
    runInfo: null,       // /api/v2/run_info
    timeline: null,      // /api/v2/timeline → {n_turns, turns:[...]}
    turnData: null,      // /api/v2/turn/<idx> 当前 turn 完整数据
    selectedTurn: null,  // 当前选中的 turn_index
    selectedNode: null,  // 当前选中的 L2 pipeline node key
  };

  // =========================================================
  // Tile emoji 映射（L1 游戏视图）
  // =========================================================
  const TILE_EMOJI = {
    grass:    "🌿",
    tree:     "🌲",
    stone:    "🪨",
    path:     "  ",
    coal:     "⬛",
    iron:     "🟫",
    diamond:  "💎",
    water:    "💧",
    lava:     "🔥",
    sand:     "🟡",
    cow:      "🐄",
    zombie:   "💀",
    skeleton: "☠️",
    plant:    "🌱",
    table:    "🪵",
    furnace:  "🏭",
    fence:    "🚧",
    unknown:  "❓",
  };

  const TILE_BG = {
    grass:   "#1a2e1a",
    tree:    "#0d1f0d",
    stone:   "#2a2a2a",
    path:    "#1e1e28",
    coal:    "#111111",
    iron:    "#2a1a0a",
    diamond: "#0a1a2a",
    water:   "#0a1a2e",
    lava:    "#2e0a0a",
    sand:    "#2e2a10",
    cow:     "#1a2a0a",
    zombie:  "#1a0a0a",
    table:   "#1a1510",
    furnace: "#1a1208",
  };

  // =========================================================
  // 工具函数
  // =========================================================
  async function fetchJson(path) {
    const resp = await fetch(path);
    if (!resp.ok) throw new Error(`HTTP ${resp.status} on ${path}`);
    return resp.json();
  }

  function esc(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatJson(obj) {
    if (obj == null) return "null";
    return JSON.stringify(obj, null, 2);
  }

  // =========================================================
  // 初始化
  // =========================================================
  async function init() {
    try {
      state.runInfo = await fetchJson("/api/v2/run_info");
      state.timeline = await fetchJson("/api/v2/timeline");

      document.getElementById("run-name").textContent = state.runInfo.run_name || "—";
      document.getElementById("total-turns").textContent = state.timeline.n_turns;

      renderTimeline();
      setupNavButtons();

      // 默认选第一个非 warmup turn
      const firstReal = state.timeline.turns.find(t => !t.is_warmup);
      const defaultIdx = firstReal ? firstReal.turn_index : 0;
      await selectTurn(defaultIdx);
    } catch (err) {
      console.error("init failed:", err);
    }
  }

  // =========================================================
  // Timeline 渲染
  // =========================================================
  function renderTimeline() {
    const strip = document.getElementById("timeline-steps");
    strip.innerHTML = "";

    const turns = state.timeline.turns;

    // Drive 折线 canvas
    renderDriveChart(turns);

    turns.forEach(t => {
      const el = document.createElement("div");
      el.className = "timeline-step";
      el.dataset.idx = t.turn_index;
      el.title = `Turn ${t.turn_index} | ${t.action ?? "—"} | ${t.top_drive ?? "—"}`;

      if (t.is_warmup) {
        el.classList.add("warmup");
        el.title = `Turn ${t.turn_index} | warmup`;
      } else {
        const act = t.action || "";
        if (act.startsWith("do")) el.classList.add("action-do");
        else if (act.startsWith("move")) el.classList.add("action-move");
        else if (act === "sleep") el.classList.add("action-sleep");
      }

      el.addEventListener("click", () => selectTurn(t.turn_index));
      strip.appendChild(el);
    });
  }

  function renderDriveChart(turns) {
    const canvas = document.getElementById("timeline-drive-chart");
    if (!canvas || !canvas.getContext) return;
    const W = canvas.parentElement.clientWidth || 800;
    canvas.width = W;
    canvas.height = 40;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, W, 40);

    const DRIVE_COLORS = {
      metabolic:   "#e74c3c",
      safety:      "#f39c12",
      acquisition: "#3498db",
      capability:  "#9b59b6",
      recovery:    "#2ecc71",
      exploration: "#1abc9c",
    };

    const validTurns = turns.filter(t => !t.is_warmup && t.drive_levels);
    if (!validTurns.length) return;

    const driveNames = Object.keys(validTurns[0].drive_levels || {});
    const n = turns.length;
    const stepW = W / Math.max(n, 1);

    driveNames.forEach(name => {
      const color = DRIVE_COLORS[name] || "#888";
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.globalAlpha = 0.6;
      ctx.lineWidth = 1;
      let first = true;
      turns.forEach((t, i) => {
        const lvl = (t.drive_levels || {})[name] ?? 0;
        const x = i * stepW + stepW / 2;
        const y = 38 - lvl * 36;
        if (first) { ctx.moveTo(x, y); first = false; }
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.globalAlpha = 1;
    });
  }

  // =========================================================
  // Turn 选择
  // =========================================================
  async function selectTurn(idx) {
    state.selectedTurn = idx;
    state.selectedNode = null;

    // 更新 timeline 高亮
    document.querySelectorAll(".timeline-step").forEach(el => {
      el.classList.toggle("selected", +el.dataset.idx === idx);
    });

    document.getElementById("current-turn").textContent = idx;

    // 更新导航按钮
    const n = state.timeline?.n_turns ?? 0;
    document.getElementById("btn-prev").disabled = idx <= 0;
    document.getElementById("btn-next").disabled = idx >= n - 1;

    // 加载完整 turn 数据
    try {
      state.turnData = await fetchJson(`/api/v2/turn/${idx}`);
    } catch (err) {
      console.error("turn load failed:", err);
      state.turnData = null;
    }

    renderL1();
    renderL2();
    renderL3(null);
  }

  function setupNavButtons() {
    document.getElementById("btn-prev").addEventListener("click", () => {
      if (state.selectedTurn > 0) selectTurn(state.selectedTurn - 1);
    });
    document.getElementById("btn-next").addEventListener("click", () => {
      const n = state.timeline?.n_turns ?? 0;
      if (state.selectedTurn < n - 1) selectTurn(state.selectedTurn + 1);
    });

    // 键盘左右
    document.addEventListener("keydown", e => {
      if (e.key === "ArrowLeft") document.getElementById("btn-prev").click();
      if (e.key === "ArrowRight") document.getElementById("btn-next").click();
    });
  }

  // =========================================================
  // L1 游戏视图渲染
  // =========================================================
  function renderL1() {
    const d = state.turnData;
    if (!d) return;

    const isWarmup = d.is_warmup;
    const banner = document.getElementById("warmup-banner");
    banner.classList.toggle("visible", isWarmup);

    const gs = d.game_state || {};
    const facing = gs.facing || "";

    // 顶部信息
    const action = getPipelineValue(d, "bridge.resolve_action", "selected_action")
      ?? getPipelineValue(d, "l3.decide_release", "selected_action")
      ?? "—";
    const topDrive = getPipelineValue(d, "l2.broadcast", "top_drive") ?? "—";
    document.getElementById("current-action").textContent = action;
    document.getElementById("current-top-drive").textContent = topDrive;

    renderGrid(gs, isWarmup, facing);
    renderLifeBars(gs, isWarmup);
    renderInventory(gs, isWarmup);
  }

  function renderGrid(gs, isWarmup, facing) {
    const grid = document.getElementById("game-grid");

    if (isWarmup || !gs.local_view) {
      grid.innerHTML = `<div style="grid-column:1/-1;grid-row:1/-1;display:flex;align-items:center;justify-content:center;color:var(--warmup);font-size:12px;padding:8px;">warmup</div>`;
      return;
    }

    const lv = gs.local_view;
    const cells = lv.cells || [];
    const rows = lv.height || 7;
    const cols = lv.width || 9;
    const centerRow = (lv.center || {}).row ?? Math.floor(rows / 2);
    const centerCol = (lv.center || {}).col ?? Math.floor(cols / 2);

    // facing arrow overlay
    const FACING_ARROW = { north: "↑", south: "↓", east: "→", west: "←" };
    const facingArrow = FACING_ARROW[facing] || "";

    grid.style.gridTemplateColumns = `repeat(${cols}, 30px)`;
    grid.style.gridTemplateRows = `repeat(${rows}, 30px)`;

    let html = "";
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const tileArr = (cells[r] || [])[c] ?? [];
        // cells[r] may be a flat list of strings per row (each cell = one string)
        const tile = Array.isArray(tileArr) ? tileArr[0] : tileArr;
        const isCenter = r === centerRow && c === centerCol;
        const emoji = TILE_EMOJI[tile] ?? "·";
        const bg = TILE_BG[tile] || "var(--bg2)";
        const cls = isCenter ? "grid-cell center-cell" : "grid-cell";
        const style = `background:${bg}`;
        if (isCenter) {
          html += `<div class="${cls}" style="${style}" title="${esc(tile)} (agent${facingArrow ? ' facing ' + facing : ''})">${facingArrow}</div>`;
        } else {
          html += `<div class="${cls}" style="${style}" title="${esc(tile)}">${emoji}</div>`;
        }
      }
    }
    grid.innerHTML = html;
  }

  function renderLifeBars(gs, isWarmup) {
    const container = document.getElementById("life-bars");
    const lp = gs.life_panel || {};
    const available = lp.available !== false;

    if (isWarmup || !available) {
      container.innerHTML = `<div class="placeholder">—</div>`;
      return;
    }

    const vals = lp.values || {};
    const MAX = 9;
    const ATTRS = ["health", "food", "water", "energy"];
    const LABELS = { health: "Health", food: "Food", water: "Water", energy: "Energy" };

    container.innerHTML = ATTRS.map(attr => {
      const v = vals[attr] ?? 0;
      const pct = Math.round((v / MAX) * 100);
      return `
        <div class="life-bar-row">
          <span class="life-bar-label">${LABELS[attr]}</span>
          <div class="life-bar-track">
            <div class="life-bar-fill ${attr}" style="width:${pct}%"></div>
          </div>
          <span class="life-bar-val">${v}</span>
        </div>`;
    }).join("");
  }

  function renderInventory(gs, isWarmup) {
    const container = document.getElementById("inventory-grid");
    const ip = gs.inventory_panel || {};
    const available = ip.available !== false;

    if (isWarmup || !available) {
      container.innerHTML = `<div class="placeholder">—</div>`;
      return;
    }

    const items = ip.items || {};
    const sorted = Object.entries(items).sort((a, b) => b[1] - a[1]);

    container.innerHTML = sorted.map(([name, count]) => {
      const cls = count > 0 ? "inv-item nonzero" : "inv-item";
      return `<div class="${cls}">
        <span class="item-name">${esc(name)}</span>
        <span class="item-count">${count}</span>
      </div>`;
    }).join("");
  }

  // =========================================================
  // L2 决策 Swimlane 渲染
  // =========================================================

  const PIPELINE_NODES = [
    { key: "l1.signal_publish",    label: "L1 Signals" },
    { key: "l2.broadcast",         label: "L2 Drive" },
    { key: "anchor.admit",         label: "Anchor A'(s)" },
    { key: "l3.candidate_produce", label: "dlPFC" },
    { key: "l3.assess_score",      label: "OFC", ofc: true },
    { key: "mediator.release",     label: "Mediator" },
    { key: "bridge.resolve_action",label: "Action", isAction: true },
  ];

  const DRIVE_COLORS = {
    metabolic:   "#e74c3c",
    safety:      "#f39c12",
    acquisition: "#3498db",
    capability:  "#9b59b6",
    recovery:    "#2ecc71",
    exploration: "#1abc9c",
  };
  const TREND_ICON = { worsening: "↑", improving: "↓", stable: "→" };

  function buildNodeContent(nodeKey, d) {
    const records = (d.pipeline || {})[nodeKey] || [];
    const last = records[records.length - 1] || null;
    let value = "—", sub = "", extra = "";

    switch (nodeKey) {
      case "l1.signal_publish": {
        const summary = last?.outputs?.summary || {};
        const lifeState = last?.inputs?.life_state || "";
        const total = summary.signal_count ?? 0;
        const parts = [];
        if (summary.pressure_signal_count) parts.push(`${summary.pressure_signal_count}p`);
        if (summary.status_signal_count)   parts.push(`${summary.status_signal_count}s`);
        if (summary.threat_signal_count)   parts.push(`${summary.threat_signal_count}⚠`);
        value = total ? `${total} sig${parts.length ? " (" + parts.join(" ") + ")" : ""}` : "0 signals";
        sub   = lifeState ? `life: ${lifeState}` : "";
        if (last?.inputs?.critical_blocked) sub += " 🔴 blocked";
        break;
      }
      case "l2.broadcast": {
        const levels = last?.outputs?.drive_levels || {};
        const trends = last?.outputs?.drive_trends || {};
        const top    = last?.outputs?.top_drive || "";
        value = top ? `${top} ${(levels[top] ?? 0).toFixed(2)}` : "—";
        sub   = top && trends[top] ? `trend: ${TREND_ICON[trends[top]] || trends[top]}` : "";
        // mini drive bars as coloured spans
        const bars = Object.entries(levels).map(([name, lvl]) => {
          const color = DRIVE_COLORS[name] || "#888";
          const pct   = Math.round(lvl * 100);
          const trend = TREND_ICON[trends[name]] || "";
          const bold  = name === top ? "font-weight:700;" : "";
          return `<span title="${name}: ${lvl.toFixed(3)} ${trends[name]||''}" style="display:inline-flex;align-items:center;gap:2px;${bold}">
            <span style="display:inline-block;width:${Math.max(4, pct/5)}px;height:4px;background:${color};border-radius:2px;"></span>
            <span style="font-size:9px;color:${color}">${trend}</span></span>`;
        }).join(" ");
        extra = bars ? `<div class="node-drives" style="margin-top:4px;display:flex;flex-wrap:wrap;gap:3px;">${bars}</div>` : "";
        break;
      }
      case "anchor.admit": {
        const candidates = last?.outputs?.admitted_candidates || [];
        const actions = candidates.map(c => {
          const a = (c.candidate_id || "").replace("candidate-crafter-", "").replace(/-/g, "_");
          return a;
        });
        value = actions.length ? actions.join(", ") : "0 candidates";
        sub   = `${candidates.length} admitted`;
        break;
      }
      case "l3.candidate_produce": {
        // prefer parsed_response from transcript
        const tx = d.transcript;
        const parsed = tx?.parsed_response?.candidates || [];
        const fromTrace = (records || []).map(r => {
          const cid = r?.outputs?.candidate_id || "";
          return cid.replace("candidate-crafter-", "").replace(/-/g, "_");
        }).filter(Boolean);
        const actions = parsed.length
          ? parsed.map(c => c.action)
          : fromTrace;
        value = actions.length ? actions.join(", ") : "—";
        sub   = tx ? `model: ${tx.model || "?"}` : "";
        break;
      }
      case "l3.assess_score": {
        // Phase A: show action:score pairs, highlight winner
        const assessments = last?.outputs?.assessments || [];
        if (assessments.length) {
          const maxScore = Math.max(...assessments.map(a => a.score ?? -Infinity));
          const pairs = assessments.map(a => {
            const isWinner = Math.abs((a.score ?? 0) - maxScore) < 1e-9;
            const scoreStr = (a.score ?? 0).toFixed(3);
            const act = (a.action || "?").replace("_", " ");
            return isWinner
              ? `<span style="color:var(--accent2);font-weight:700">${esc(act)}: ${scoreStr}</span>`
              : `${esc(act)}: ${scoreStr}`;
          });
          value = "";  // use extra for HTML content
          extra = `<div class="node-value" style="font-size:11px;line-height:1.5">${pairs.join("<br>")}</div>`;
        } else {
          value = "—";
        }
        sub = "(Phase A 占位)";
        break;
      }
      case "mediator.release": {
        const outcome = last?.outputs?.outcome || "—";
        const authorized = last?.outputs?.release_authorized;
        value = outcome.replace("_", " ");
        sub   = authorized === false ? "🔴 withheld" : authorized === true ? "✓ released" : "";
        break;
      }
      case "bridge.resolve_action": {
        const action = last?.outputs?.selected_action || "—";
        const reason = (last?.outputs?.selected_action_reason || "").slice(0, 32);
        value = action;
        sub   = reason || "";
        break;
      }
    }
    return { value, sub, extra };
  }

  function renderL2() {
    const d = state.turnData;
    const swimlane = document.getElementById("l2-swimlane");

    if (!d) {
      swimlane.innerHTML = `<div class="placeholder">无数据</div>`;
      return;
    }

    let html = "";
    PIPELINE_NODES.forEach((node, i) => {
      if (i > 0) html += `<span class="pipeline-arrow">→</span>`;

      const { value, sub, extra } = buildNodeContent(node.key, d);

      const nodeClass = [
        "pipeline-node",
        node.ofc ? "ofc-placeholder" : "",
        node.isAction ? "action-node" : "",
        state.selectedNode === node.key ? "selected" : "",
      ].filter(Boolean).join(" ");

      html += `<div class="${nodeClass}" data-node-key="${esc(node.key)}">
        <div class="node-label">${esc(node.label)}</div>
        ${extra || `<div class="node-value">${esc(value)}</div>`}
        ${sub ? `<div class="node-sub">${esc(sub)}</div>` : ""}
      </div>`;
    });

    swimlane.innerHTML = html;

    swimlane.querySelectorAll(".pipeline-node").forEach(el => {
      el.addEventListener("click", () => selectNode(el.dataset.nodeKey));
    });
  }

  // =========================================================
  // L3 深钻面板
  // =========================================================
  function selectNode(nodeKey) {
    state.selectedNode = nodeKey;

    // 更新 L2 高亮
    document.querySelectorAll(".pipeline-node").forEach(el => {
      el.classList.toggle("selected", el.dataset.nodeKey === nodeKey);
    });

    renderL3(nodeKey);
  }

  function renderL3(nodeKey) {
    const labelEl = document.getElementById("l3-node-label");
    const content = document.getElementById("l3-content");

    if (!nodeKey || !state.turnData) {
      labelEl.textContent = "";
      content.innerHTML = `<div class="placeholder">点击 L2 任意节点展开详情</div>`;
      return;
    }

    const d = state.turnData;
    const records = (d.pipeline || {})[nodeKey] || [];
    const nodeDef = PIPELINE_NODES.find(n => n.key === nodeKey);
    labelEl.textContent = nodeDef ? nodeDef.label : nodeKey;

    // Section 1: 节点 raw data
    const rawSection = `
      <div class="l3-section">
        <div class="l3-section-title">节点数据 <span style="color:var(--text-dim)">${esc(nodeKey)}</span></div>
        <pre>${esc(formatJson(records.map(r => ({ inputs: r.inputs, outputs: r.outputs }))))}</pre>
      </div>`;

    // Section 2: advisory
    const adv = d.advisory;
    let advHtml = "";
    if (adv) {
      const req = adv.request || {};
      const resp = adv.response || {};
      advHtml = `
        <div class="l3-section">
          <div class="l3-section-title">Advisory</div>
          <pre>${esc(formatJson({ source: adv.advisory_source, outcome: adv.outcome, request_keys: Object.keys(req), confidence: resp.confidence }))}</pre>
        </div>`;
    }

    // Section 3: transcript（只在 dlPFC / L3 / Bridge 节点显示）
    const isL3Node = nodeKey.startsWith("l3.") || nodeKey.startsWith("bridge.");
    let transcriptHtml = "";
    if (isL3Node) {
      const tx = d.transcript;
      if (tx) {
        transcriptHtml = buildTranscriptSection(tx);
      } else {
        transcriptHtml = `
          <div class="l3-section">
            <div class="l3-section-title">dlPFC Transcript</div>
            <div class="transcript-unavailable">transcript not recorded (run without EVA_LLM_TRANSCRIPT=raw)</div>
          </div>`;
      }
    }

    content.innerHTML = rawSection + advHtml + transcriptHtml;
  }

  // =========================================================
  // Transcript 结构化渲染
  // =========================================================
  function buildTranscriptSection(tx) {
    const model = tx.model || "?";
    const parseStatus = tx.parse_status || "?";
    const statusColor = parseStatus === "ok" ? "var(--accent2)" : "var(--danger)";
    const msgs = tx.messages || [];
    const parsed = tx.parsed_response || {};
    const candidates = parsed.candidates || [];

    // 候选 action + reason 列表
    let candidateHtml = "";
    if (candidates.length) {
      const items = candidates.map(c => {
        const reason = (c.reason || "").slice(0, 200);
        return `<div class="tx-candidate">
          <span class="tx-action">${esc(c.action || "?")}</span>
          <span class="tx-reason">${esc(reason)}${c.reason?.length > 200 ? "…" : ""}</span>
        </div>`;
      }).join("");
      candidateHtml = `<div class="tx-candidates">${items}</div>`;
    } else {
      candidateHtml = `<div class="transcript-unavailable">no parsed candidates</div>`;
    }

    // User message content preview (last user msg = observation)
    const userMsg = [...msgs].reverse().find(m => m.role === "user");
    const userContent = typeof userMsg?.content === "string"
      ? userMsg.content : JSON.stringify(userMsg?.content || "");
    const userPreview = userContent.slice(0, 400) + (userContent.length > 400 ? "…" : "");

    // System prompt size + sections present
    const sysMsg = msgs.find(m => m.role === "system");
    const sysLen = typeof sysMsg?.content === "string" ? sysMsg.content.length : 0;
    const sections = tx.prompt_sections_present || [];
    const sysInfo = sysLen
      ? `${(sysLen / 1000).toFixed(1)}k chars${sections.length ? " | " + sections.join(", ") : ""}`
      : "—";

    return `
      <div class="l3-section" style="min-width:340px">
        <div class="l3-section-title">
          dlPFC Transcript
          <span style="font-size:10px;color:${statusColor};margin-left:8px">${esc(parseStatus)}</span>
          <span style="font-size:10px;color:var(--text-dim);margin-left:8px">${esc(model)}</span>
        </div>
        <div class="tx-block-label">Candidates</div>
        ${candidateHtml}
        <div class="tx-block-label" style="margin-top:8px">Observation (user msg)</div>
        <pre class="tx-pre">${esc(userPreview)}</pre>
        <div class="tx-block-label" style="margin-top:8px">System prompt</div>
        <div class="tx-meta">${esc(sysInfo)}</div>
      </div>`;
  }

  // =========================================================
  // 辅助：从 pipeline 取值
  // =========================================================
  function getPipelineValue(d, nodeKey, outputKey) {
    const records = ((d || {}).pipeline || {})[nodeKey] || [];
    const last = records[records.length - 1];
    return last?.outputs?.[outputKey] ?? null;
  }

  // =========================================================
  // 启动
  // =========================================================
  document.addEventListener("DOMContentLoaded", init);
})();
