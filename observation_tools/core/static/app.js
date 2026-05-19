// EVA Black Box —— V0 前端 (vanilla JS，无 CDN).
//
// 职责（V0-d 范围）：
//   - 启动加载 /api/run_info + /api/turns
//   - 渲染左侧 turn 列表（支持 life_state / advisory 筛选）
//   - 5 秒轮询 /api/run_info 监听 counts 变化；变化则重新拉 turns
//   - 点击 turn 卡片选中、占位渲染右侧详情（V0-e 才完整填充）
//
// V0-e 会在 renderDetail() 里填入完整链路展开。
// V0-f 会在 renderTimeline() 里填入顶部时间轴 + drive 折线。

(function () {
  "use strict";

  // ========= 全局状态 =========
  const state = {
    runInfo: null,        // { run_name, runtime_dir, counts: {...} }
    turns: [],            // ChainView.to_dict() 列表（全量缓存）
    selectedTurnIdx: null,
    filterLifeState: "",
    filterAdvisory: "",
    lastCounts: null,     // 上一次 counts 字符串化，用于增量判断
    lastFetchOk: null,    // 时间戳（ms）
  };

  // ========= 工具函数 =========

  async function fetchJson(path) {
    const resp = await fetch(path);
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status} on ${path}`);
    }
    return await resp.json();
  }

  function formatTimeShort(iso) {
    // 2026-05-19T17:47:27.855060Z -> 17:47:27
    if (!iso) return "—";
    const m = iso.match(/T(\d{2}:\d{2}:\d{2})/);
    return m ? m[1] : iso.slice(0, 19);
  }

  function lifeStateBadge(lifeState) {
    const ls = (lifeState || "").toUpperCase();
    const cls = `badge life-${ls.toLowerCase() || "unknown"}`;
    return `<span class="${cls}">${ls || "UNKNOWN"}</span>`;
  }

  function advisoryBadge(outcome) {
    if (!outcome) return `<span class="badge advisory-none">无 advisory</span>`;
    if (outcome === "advisory_attached") return `<span class="badge advisory-ok">advisory</span>`;
    if (outcome === "fallback_local") return `<span class="badge advisory-fallback">fallback</span>`;
    return `<span class="badge advisory-none">${outcome}</span>`;
  }

  // ========= 数据加载 =========

  async function loadRunInfo() {
    state.runInfo = await fetchJson("/api/run_info");
    document.getElementById("run-name").textContent = state.runInfo.run_name || "—";
    document.getElementById("turn-count").textContent =
      state.runInfo.counts.deliberation_audit;
  }

  async function loadTurns() {
    const data = await fetchJson("/api/turns");
    state.turns = data.turns || [];
    renderTurnList();
    refreshLifeStateFilterOptions();
    if (state.selectedTurnIdx !== null && state.selectedTurnIdx >= state.turns.length) {
      state.selectedTurnIdx = null;
      renderDetail(null);
    }
  }

  function countsKey(counts) {
    if (!counts) return "";
    return Object.entries(counts)
      .map(([k, v]) => `${k}=${v}`)
      .join(",");
  }

  // ========= 渲染 =========

  function refreshLifeStateFilterOptions() {
    const select = document.getElementById("filter-life-state");
    const seen = new Set();
    for (const turn of state.turns) {
      const ls = (turn.response && turn.response.life_state) || "UNKNOWN";
      seen.add(ls);
    }
    const current = state.filterLifeState;
    // 保留 "全部"，重新填充已知 life_state
    select.innerHTML = `<option value="">全部</option>` +
      [...seen]
        .sort()
        .map((ls) => `<option value="${ls}">${ls}</option>`)
        .join("");
    select.value = current;
  }

  function turnPassesFilter(turn) {
    if (state.filterLifeState) {
      const ls = (turn.response && turn.response.life_state) || "UNKNOWN";
      if (ls !== state.filterLifeState) return false;
    }
    if (state.filterAdvisory) {
      const outcome = (turn.advisory && turn.advisory.outcome) || "";
      if (state.filterAdvisory === "no_advisory") {
        if (outcome) return false;
      } else if (outcome !== state.filterAdvisory) {
        return false;
      }
    }
    return true;
  }

  function renderTurnList() {
    const container = document.getElementById("turn-list");
    if (state.turns.length === 0) {
      container.innerHTML = `<div class="placeholder">尚未载入 turn 数据</div>`;
      return;
    }
    // 倒序：最新在上
    const visible = state.turns.filter(turnPassesFilter).slice().reverse();
    if (visible.length === 0) {
      container.innerHTML = `<div class="placeholder">无 turn 匹配当前筛选</div>`;
      return;
    }
    container.innerHTML = visible.map(renderTurnCard).join("");
    // 绑定点击事件
    for (const node of container.querySelectorAll(".turn-card")) {
      node.addEventListener("click", () => {
        const idx = parseInt(node.dataset.turnIdx, 10);
        selectTurn(idx);
      });
    }
  }

  function renderTurnCard(turn) {
    const lifeState = (turn.response && turn.response.life_state) || "UNKNOWN";
    const advisoryOutcome = (turn.advisory && turn.advisory.outcome) || "";
    const topDrive =
      (turn.deliberation &&
        turn.deliberation.deliberation_input &&
        turn.deliberation.deliberation_input.drive_broadcast &&
        turn.deliberation.deliberation_input.drive_broadcast.top_drive) || "—";
    const selectedAction =
      (turn.response && turn.response.selected_action) || "—";
    const selectedCls =
      state.selectedTurnIdx === turn.turn_idx ? " selected" : "";
    return `
      <div class="turn-card${selectedCls}" data-turn-idx="${turn.turn_idx}">
        <div class="head">
          <span class="turn-idx">#${turn.turn_idx}</span>
          <span class="recorded-at">${formatTimeShort(turn.recorded_at)}</span>
        </div>
        <div class="body">
          ${lifeStateBadge(lifeState)}
          <span>drive: ${topDrive}</span>
          <span>act: ${selectedAction}</span>
          ${advisoryBadge(advisoryOutcome)}
        </div>
      </div>
    `;
  }

  function selectTurn(idx) {
    state.selectedTurnIdx = idx;
    const turn = state.turns[idx];
    if (!turn) return;
    document.getElementById("selected-turn").textContent = `#${idx}`;
    document.getElementById("selected-life-state").textContent =
      (turn.response && turn.response.life_state) || "UNKNOWN";
    renderTurnList(); // 重画以更新 selected 类
    renderDetail(turn);
    // 重画 timeline 以更新选中指示线
    if (state.timeline) {
      renderTimelineStrip();
    }
  }

  // ========= 详情视图（V0-e 链路全展开） =========

  function renderDetail(turn) {
    const body = document.getElementById("detail-body");
    if (turn === null || turn === undefined) {
      body.innerHTML = `<div class="placeholder">选择左侧任一 turn 查看链路（L1 → L2 → L3 → 动作）。</div>`;
      return;
    }
    const sections = [
      renderL1Section(turn.deliberation),
      renderL2Section(turn.deliberation),
      renderL3Section(turn.deliberation),
      renderAdvisorySection(turn.advisory),
      renderActionSection(turn.response),
      renderOutcomeMemorySection(turn.outcome, turn.habit),
    ];
    body.innerHTML = sections.join("");
    bindSectionToggles(body);
  }

  // ----- 节通用辅助 -----

  function section(title, summary, bodyHtml, opts) {
    const collapsed = opts && opts.collapsed ? " collapsed" : "";
    return `
      <div class="chain-section${collapsed}">
        <div class="section-header">
          <span>${escapeHtml(title)}</span>
          <span class="summary">${summary || ""}</span>
        </div>
        <div class="section-body">${bodyHtml}</div>
      </div>
    `;
  }

  function bindSectionToggles(root) {
    for (const header of root.querySelectorAll(".chain-section .section-header")) {
      header.addEventListener("click", () => {
        header.parentElement.classList.toggle("collapsed");
      });
    }
  }

  function kvTable(pairs) {
    // pairs: [[label, value], ...]; value 可以是字符串或 HTML 片段（已转义）
    if (!pairs || pairs.length === 0) return "";
    return `<div class="kv-table">${pairs
      .map(([k, v]) => `<div class="k">${escapeHtml(k)}</div><div class="v">${v}</div>`)
      .join("")}</div>`;
  }

  function rawJsonBlock(obj) {
    return `<details style="margin-top:8px">
      <summary style="cursor:pointer;color:#6e7681;font-size:11px">原始 JSON</summary>
      <pre class="raw-json">${escapeHtml(JSON.stringify(obj, null, 2))}</pre>
    </details>`;
  }

  function fmtNum(value, decimals) {
    if (value === null || value === undefined || isNaN(value)) return "—";
    const d = decimals === undefined ? 3 : decimals;
    return Number(value).toFixed(d);
  }

  function missingNote(label) {
    return `<div style="color:#6e7681;font-size:12px">本 turn 没有 ${escapeHtml(label)} 数据</div>`;
  }

  // ----- L1 感知 -----

  function renderL1Section(deliberation) {
    if (!deliberation) {
      return section("L1 感知 signal_batch", "—", missingNote("deliberation_audit"));
    }
    const signalBatch = (deliberation.deliberation_input || {}).signal_batch || {};
    const signals = signalBatch.signals || [];

    // 按 class 分组计数
    const classCounts = {};
    for (const sig of signals) {
      const cls = sig.class || "unknown";
      classCounts[cls] = (classCounts[cls] || 0) + 1;
    }
    const summary = Object.entries(classCounts)
      .map(([c, n]) => `<span class="badge">${escapeHtml(c)} × ${n}</span>`)
      .join(" ");

    // 按 class 分组渲染
    const grouped = {};
    for (const sig of signals) {
      const cls = sig.class || "unknown";
      (grouped[cls] = grouped[cls] || []).push(sig);
    }
    const classOrder = ["threat", "pressure", "status", "background", "unknown"];
    const groupHtml = classOrder
      .filter((c) => grouped[c])
      .map((c) => {
        const items = grouped[c].map((sig) => renderSignalLine(sig)).join("");
        return `<div style="margin-bottom:8px"><div style="color:#58a6ff;font-size:12px;font-weight:600;margin-bottom:4px">${escapeHtml(c)}</div>${items}</div>`;
      })
      .join("");

    const body = (groupHtml || `<div style="color:#6e7681">无 signal</div>`) +
      rawJsonBlock(signalBatch);
    return section("L1 感知 signal_batch", summary || "—", body);
  }

  function renderSignalLine(sig) {
    const source = sig.source || "—";
    const payload = sig.payload || {};
    let highlight = "";
    if (payload.dimensions) {
      // status 信号：列出 dimension 名 + 状态
      const dims = Object.entries(payload.dimensions)
        .map(([name, info]) => `${name}=${(info && info.status) || "—"}`)
        .join(", ");
      highlight = escapeHtml(dims);
    } else if (payload.pressure_type) {
      highlight = `${escapeHtml(payload.pressure_type)}/${escapeHtml(payload.pressure_severity || "—")} (${escapeHtml(payload.pressure_reason || "—")})`;
    } else if (payload.reason) {
      highlight = escapeHtml(payload.reason);
    }
    return `<div style="font-size:11px;padding:2px 0;color:#c9d1d9">
      <span style="color:#8b949e">[${escapeHtml(source)}]</span> ${highlight}
    </div>`;
  }

  // ----- L2 drive 广播 -----

  function renderL2Section(deliberation) {
    if (!deliberation) {
      return section("L2 drive_broadcast", "—", missingNote("deliberation_audit"));
    }
    const drive = (deliberation.deliberation_input || {}).drive_broadcast || {};
    const top = drive.top_drive || "—";
    const topLevel = drive.top_level;
    const levels = drive.drive_levels || {};
    const trends = drive.drive_trends || {};
    const summary = `<span class="badge">top: ${escapeHtml(top)}${topLevel !== undefined ? " (" + fmtNum(topLevel, 2) + ")" : ""}</span>`;

    const drivesTable = Object.keys(levels)
      .sort()
      .map((name) => {
        const lvl = fmtNum(levels[name], 3);
        const trend = trends[name] || "stable";
        const isTop = name === top;
        const nameHtml = isTop
          ? `<strong style="color:#58a6ff">${escapeHtml(name)}</strong>`
          : escapeHtml(name);
        return `<div class="k">${nameHtml}</div><div class="v">${lvl} (${escapeHtml(trend)})</div>`;
      })
      .join("");
    const body = `<div class="kv-table">${drivesTable}</div>` + rawJsonBlock(drive);
    return section("L2 drive_broadcast", summary, body);
  }

  // ----- L3 deliberation -----

  function renderL3Section(deliberation) {
    if (!deliberation) {
      return section("L3 deliberation", "—", missingNote("deliberation_audit"));
    }
    const wm = (deliberation.deliberation_input || {}).working_memory_context || {};
    const candidates = deliberation.candidates || [];
    const assessments = deliberation.assessments || [];
    const release = deliberation.release_decision || {};
    const releaseOutcome = release.outcome || "—";

    // Working memory summary
    const wmRows = [
      ["situation_key", escapeHtml(wm.situation_key || "—")],
      ["bias_summaries 数量", String((wm.bias_summaries || []).length)],
      ["habit_skills 数量", String((wm.habit_skills || []).length)],
      ["inherited_priors 数量", String((wm.inherited_priors || []).length)],
      ["semantic_patterns 数量", String((wm.semantic_patterns || []).length)],
      ["recent_outcomes 数量", String((wm.recent_relevant_outcomes || []).length)],
      ["local_confidence", fmtNum(wm.local_confidence, 3)],
    ];
    if (wm.advisory_context && Object.keys(wm.advisory_context).length > 0) {
      const adv = wm.advisory_context;
      wmRows.push([
        "advisory_context",
        escapeHtml(JSON.stringify({
          candidate_suggestions: adv.candidate_suggestions,
          confidence: adv.confidence,
        })),
      ]);
    }
    const wmHtml = `<div style="font-weight:600;color:#58a6ff;margin-bottom:4px">Working Memory</div>${kvTable(wmRows)}`;

    // Candidates + assessments
    const assessmentByProfile = {};
    for (const a of assessments) {
      if (a && a.candidate_profile) {
        assessmentByProfile[a.candidate_profile] = a;
      }
    }
    let candidatesHtml = "";
    if (candidates.length === 0) {
      candidatesHtml = `<div style="color:#6e7681">无 candidate</div>`;
    } else {
      candidatesHtml = candidates
        .map((c) => {
          const profile = c.candidate_profile || "—";
          const action = c.selected_action || c.action || "—";
          const a = assessmentByProfile[profile] || {};
          const score = fmtNum(a.aggregated_score !== undefined ? a.aggregated_score : a.score, 3);
          return `<div style="font-size:12px;padding:2px 0">
            <span style="color:#58a6ff">${escapeHtml(profile)}</span>
            → ${escapeHtml(String(action))}
            <span style="color:#8b949e">score=${score}</span>
          </div>`;
        })
        .join("");
    }
    const candidatesSection = `<div style="margin-top:10px;font-weight:600;color:#58a6ff;margin-bottom:4px">Candidates / Assessments (${candidates.length})</div>${candidatesHtml}`;

    // Mediator release_decision
    const releaseHtml = kvTable([
      ["outcome", escapeHtml(releaseOutcome)],
      ["rationale", escapeHtml(release.rationale || "—")],
      ["expected_outcome", escapeHtml(JSON.stringify(release.expected_outcome || {}))],
    ]);
    const mediatorSection = `<div style="margin-top:10px;font-weight:600;color:#58a6ff;margin-bottom:4px">Mediator release_decision</div>${releaseHtml}`;

    const summary = `<span class="badge">${escapeHtml(releaseOutcome)}</span> · ${candidates.length} candidates`;
    const body = wmHtml + candidatesSection + mediatorSection +
      rawJsonBlock({ working_memory_context: wm, candidates, assessments, release_decision: release });
    return section("L3 deliberation", summary, body);
  }

  // ----- LLM advisory -----

  function renderAdvisorySection(advisory) {
    if (!advisory) {
      return section("LLM Advisory", "无（heuristic / inert / 未启用）", missingNote("llm_advisory_audit"), { collapsed: true });
    }
    const outcome = advisory.outcome || "—";
    const cls = outcome === "advisory_attached" ? "advisory-ok"
      : outcome === "fallback_local" ? "advisory-fallback"
      : "advisory-none";
    const summary = `<span class="badge ${cls}">${escapeHtml(outcome)}</span> · ${escapeHtml(advisory.model || "—")}`;

    const response = advisory.response || {};
    const rows = [
      ["provider", escapeHtml(advisory.provider || "—")],
      ["model", escapeHtml(advisory.model || "—")],
      ["advisory_source", escapeHtml(advisory.advisory_source || "—")],
      ["request_timeout_sec", fmtNum(advisory.request_timeout_sec, 2)],
      ["outcome", escapeHtml(outcome)],
    ];
    if (advisory.error) rows.push(["error", escapeHtml(String(advisory.error))]);
    rows.push([
      "response.candidate_suggestions",
      escapeHtml(JSON.stringify(response.candidate_suggestions || [])),
    ]);
    rows.push(["response.confidence", fmtNum(response.confidence, 3)]);
    if (response.reasoning_trace) {
      rows.push(["response.reasoning_trace", escapeHtml(JSON.stringify(response.reasoning_trace))]);
    }
    const body = kvTable(rows) + rawJsonBlock(advisory);
    return section("LLM Advisory", summary, body);
  }

  // ----- 动作执行 -----

  function renderActionSection(response) {
    if (!response) {
      return section("动作执行", "—", missingNote("response_history"));
    }
    const action = response.selected_action || "—";
    const status = response.execution_status || "—";
    const pressure = response.pressure_outcome || "—";
    const summary = `<span class="badge">${escapeHtml(action)}</span> · ${escapeHtml(status)} · ${escapeHtml(pressure)}`;

    const coreRows = [
      ["selected_action", escapeHtml(action)],
      ["selected_posture", escapeHtml(response.selected_posture || "—")],
      ["selected_action_reason", escapeHtml(response.selected_action_reason || "—")],
      ["execution_status", escapeHtml(status)],
      ["pressure_id", escapeHtml(response.pressure_id || "—")],
      ["pressure_type/severity", `${escapeHtml(response.pressure_type || "—")}/${escapeHtml(response.pressure_severity || "—")}`],
      ["pressure_reason", escapeHtml(response.pressure_reason || "—")],
      ["pressure_outcome", escapeHtml(pressure)],
      ["filter_result", escapeHtml(response.filter_result || "—")],
    ];
    if ((response.denied_actions || []).length > 0) {
      coreRows.push(["denied_actions", escapeHtml(JSON.stringify(response.denied_actions))]);
    }
    if ((response.discouraged_actions || []).length > 0) {
      coreRows.push(["discouraged_actions", escapeHtml(JSON.stringify(response.discouraged_actions))]);
    }
    if ((response.side_effects || []).length > 0) {
      coreRows.push(["side_effects", escapeHtml(JSON.stringify(response.side_effects))]);
    }
    coreRows.push(["uncertainty_after_action", escapeHtml(response.uncertainty_after_action || "—")]);

    // 场景特定 deltas（V1 plugin 阶段会专属渲染）
    const sceneRows = [];
    if (response.achievement_delta) sceneRows.push(["achievement_delta", escapeHtml(JSON.stringify(response.achievement_delta))]);
    if (response.inventory_delta) sceneRows.push(["inventory_delta", escapeHtml(JSON.stringify(response.inventory_delta))]);
    if (response.life_delta) sceneRows.push(["life_delta", escapeHtml(JSON.stringify(response.life_delta))]);
    if (response.visible_threat_count !== undefined) sceneRows.push(["visible_threat_count", String(response.visible_threat_count)]);

    let body = kvTable(coreRows);
    if (sceneRows.length > 0) {
      body += `<div style="margin-top:10px;font-weight:600;color:#58a6ff;margin-bottom:4px">场景观察（待 plugin 渲染）</div>${kvTable(sceneRows)}`;
    }
    body += rawJsonBlock(response);
    return section("动作执行", summary, body);
  }

  // ----- Outcome + Memory -----

  function renderOutcomeMemorySection(outcome, habit) {
    const haveOutcome = outcome !== null && outcome !== undefined;
    const haveHabit = habit !== null && habit !== undefined;
    if (!haveOutcome && !haveHabit) {
      return section("Outcome / Memory", "—", missingNote("learning_outcomes / habit_bias"), { collapsed: true });
    }

    let body = "";
    let summaryParts = [];

    if (haveOutcome) {
      const ov = outcome.outcome_vector || {};
      const odeltaRaw = outcome.outcome_delta;
      const odelta = odeltaRaw !== undefined ? fmtNum(odeltaRaw, 3) : "—";
      summaryParts.push(`outcome_delta=${odelta}`);
      body += `<div style="font-weight:600;color:#58a6ff;margin-bottom:4px">Learning Outcome</div>`;
      body += kvTable([
        ["outcome_delta", odelta],
        ["candidate_profile", escapeHtml(outcome.candidate_profile || "—")],
        ["selected_action", escapeHtml(outcome.selected_action || "—")],
        ["outcome_vector", escapeHtml(JSON.stringify(ov))],
      ]);
      body += rawJsonBlock(outcome);
    }
    if (haveHabit) {
      summaryParts.push("habit_bias 新增");
      body += `<div style="margin-top:10px;font-weight:600;color:#58a6ff;margin-bottom:4px">Habit Bias</div>`;
      body += kvTable([
        ["situation_key", escapeHtml((habit.content && habit.content.situation_key) || habit.situation_key || "—")],
        ["candidate_profile", escapeHtml(habit.candidate_profile || "—")],
        ["selected_action", escapeHtml(habit.selected_action || "—")],
        ["outcome_delta", fmtNum(habit.outcome_delta, 3)],
      ]);
      body += rawJsonBlock(habit);
    }

    return section("Outcome / Memory", summaryParts.join(" · ") || "—", body);
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // ========= Live 指示器 =========

  function setLive(state_label) {
    const node = document.getElementById("live-indicator");
    const text = node.querySelector(".text");
    node.classList.remove("live", "stale", "error");
    if (state_label === "live") {
      node.classList.add("live");
      text.textContent = "已连接";
    } else if (state_label === "stale") {
      node.classList.add("stale");
      text.textContent = "等待新数据";
    } else if (state_label === "error") {
      node.classList.add("error");
      text.textContent = "加载失败";
    } else {
      text.textContent = state_label || "—";
    }
  }

  // ========= 顶部时间轴 + drive 折线 (V0-f) =========

  // drive 颜色编码（手挑）。未识别的 drive 会用 fallback 灰色。
  const DRIVE_COLORS = {
    metabolic:   "#f85149",  // 红
    safety:      "#d29922",  // 橙
    recovery:    "#3fb950",  // 绿
    acquisition: "#58a6ff",  // 蓝
    capability:  "#a371f7",  // 紫
    exploration: "#ff7b72",  // 粉橙
  };
  const DRIVE_COLOR_FALLBACK = "#8b949e";

  // life_state 标记颜色
  const LIFE_STATE_COLORS = {
    STABLE:     "#3fb950",
    RECOVERING: "#d29922",
    CRITICAL:   "#f85149",
    UNKNOWN:    "#6e7681",
  };

  async function loadTimeline() {
    state.timeline = await fetchJson("/api/timeline");
    renderTimelineStrip();
  }

  function renderTimelineStrip() {
    const strip = document.getElementById("timeline-strip");
    const t = state.timeline;
    if (!t || !t.n_turns || t.n_turns === 0) {
      strip.innerHTML = `<div class="placeholder">尚无 turn 数据</div>`;
      return;
    }

    // SVG 尺寸：根据可视区宽度自适应；高度固定 80
    const padding = 8;
    const width = Math.max(strip.clientWidth - padding * 2, 400);
    const height = 80;
    const lifeBandHeight = 12;
    const driveAreaTop = lifeBandHeight + 4;
    const driveAreaHeight = height - driveAreaTop - 4;
    const n = t.n_turns;

    const xOf = (i) => (n <= 1 ? width / 2 : (i / (n - 1)) * width);
    const yOf = (v) => driveAreaTop + driveAreaHeight - clamp01(v) * driveAreaHeight;

    // life_state 标记带（按相邻变化点画段）
    let lifeBand = "";
    let segStart = 0;
    for (let i = 1; i <= n; i++) {
      if (i === n || t.life_state[i] !== t.life_state[segStart]) {
        const x0 = xOf(segStart);
        const x1 = xOf(i - 1);
        const ls = t.life_state[segStart] || "UNKNOWN";
        const fill = LIFE_STATE_COLORS[ls] || DRIVE_COLOR_FALLBACK;
        lifeBand += `<rect x="${x0}" y="0" width="${Math.max(x1 - x0, 1)}" height="${lifeBandHeight}" fill="${fill}" opacity="0.55"><title>${ls} (turns ${segStart}-${i - 1})</title></rect>`;
        segStart = i;
      }
    }

    // 6 条 drive 折线
    let driveLines = "";
    let legend = "";
    const driveNames = Object.keys(t.drive_levels).sort();
    for (const name of driveNames) {
      const values = t.drive_levels[name] || [];
      const color = DRIVE_COLORS[name] || DRIVE_COLOR_FALLBACK;
      const pathData = values.map((v, i) => `${i === 0 ? "M" : "L"} ${xOf(i).toFixed(2)} ${yOf(v).toFixed(2)}`).join(" ");
      driveLines += `<path d="${pathData}" fill="none" stroke="${color}" stroke-width="1.2" opacity="0.85"><title>${name}</title></path>`;
      legend += `<span style="display:inline-flex;align-items:center;gap:4px;margin-right:10px;color:#8b949e">
        <span style="width:10px;height:2px;background:${color}"></span>
        <span>${name}</span>
      </span>`;
    }

    // 0 / 0.5 / 1 horizontal guides
    const guideY0 = yOf(0);
    const guideY50 = yOf(0.5);
    const guideY100 = yOf(1.0);
    const guides = [guideY0, guideY50, guideY100]
      .map((y) => `<line x1="0" y1="${y}" x2="${width}" y2="${y}" stroke="#30363d" stroke-width="0.5" stroke-dasharray="2,3"/>`)
      .join("");

    // 选中 turn 指示线
    let selectedIndicator = "";
    if (state.selectedTurnIdx !== null && state.selectedTurnIdx < n) {
      const sx = xOf(state.selectedTurnIdx);
      selectedIndicator = `<line x1="${sx}" y1="0" x2="${sx}" y2="${height}" stroke="#58a6ff" stroke-width="1.2"/>`;
    }

    strip.innerHTML = `
      <div style="width:100%;padding:6px ${padding}px 0">
        <svg id="timeline-svg" width="${width}" height="${height}" style="display:block;cursor:crosshair">
          ${guides}
          ${lifeBand}
          ${driveLines}
          ${selectedIndicator}
        </svg>
        <div style="font-size:10px;padding:4px 0">
          ${legend}
          <span style="color:#6e7681">· 点击跳转到对应 turn</span>
        </div>
      </div>
    `;

    // 点击跳转：根据 X 坐标推算 turn idx
    const svg = document.getElementById("timeline-svg");
    svg.addEventListener("click", (e) => {
      const rect = svg.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const idx = Math.min(n - 1, Math.max(0, Math.round((x / width) * (n - 1))));
      selectTurn(idx);
    });
  }

  function clamp01(v) {
    const n = Number(v);
    if (isNaN(n)) return 0;
    if (n < 0) return 0;
    if (n > 1) return 1;
    return n;
  }

  // ========= 轮询 =========

  async function poll() {
    try {
      await loadRunInfo();
      const newKey = countsKey(state.runInfo.counts);
      if (newKey !== state.lastCounts) {
        await loadTurns();
        await loadTimeline();
        state.lastCounts = newKey;
      }
      state.lastFetchOk = Date.now();
      // 60 秒无新数据则标 stale
      if (Date.now() - state.lastFetchOk > 60_000) {
        setLive("stale");
      } else {
        setLive("live");
      }
    } catch (exc) {
      console.error(exc);
      setLive("error");
    }
  }

  // ========= 事件绑定 =========

  function bindFilters() {
    document.getElementById("filter-life-state").addEventListener("change", (e) => {
      state.filterLifeState = e.target.value;
      renderTurnList();
    });
    document.getElementById("filter-advisory").addEventListener("change", (e) => {
      state.filterAdvisory = e.target.value;
      renderTurnList();
    });
  }

  // ========= 启动 =========

  async function start() {
    bindFilters();
    setLive("初始化");
    await poll();
    // 5 秒间隔
    setInterval(poll, 5000);
  }

  // DOM 已 parse 完后启动
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
