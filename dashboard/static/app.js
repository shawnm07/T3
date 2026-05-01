const COLORS = {
  green: "#58d68d",
  red: "#ff6b7a",
  amber: "#f6c85f",
  cyan: "#55d6be",
  blue: "#7aa7ff",
  pink: "#ff8cc6",
  muted: "#6f7885",
  text: "#f3f5f7",
  grid: "#242a33"
};

const state = {
  data: null,
  selectedSymbol: null,
  search: "",
  chartMeta: new WeakMap()
};

const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  $("refreshBtn").addEventListener("click", () => loadDashboard(false));
  $("liveBtn").addEventListener("click", () => loadDashboard(true));
  $("drawerClose").addEventListener("click", closeDrawer);
  $("watchlistAllBtn").addEventListener("click", showFullWatchlist);
  $("symbolSearch").addEventListener("input", (event) => {
    state.search = event.target.value.trim().toUpperCase();
    renderStockDecisions();
  });
  window.addEventListener("resize", debounce(drawAllCharts, 160));
  document.body.addEventListener("click", (event) => {
    if (event.target.closest("[data-no-symbol-click]")) return;
    const row = event.target.closest("[data-symbol]");
    if (row && row.dataset.symbol) {
      showSymbol(row.dataset.symbol);
    }
  });
  loadDashboard(false).then(() => {
    fetchLiveInBackground();
  });
});

async function loadDashboard(live) {
  try {
    setToast(live ? "Refreshing live snapshot..." : "Refreshing dashboard...");
    const response = await fetch(`/api/dashboard${live ? "?live=1" : ""}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    render();
    setToast(live && !state.data.live.ok ? `Live snapshot failed: ${state.data.live.error}` : "Dashboard refreshed.");
  } catch (error) {
    setToast(`Dashboard error: ${error.message}`, true);
  }
}

async function fetchLiveInBackground() {
  try {
    const response = await fetch("/api/dashboard?live=1", { cache: "no-store" });
    if (!response.ok) return;
    const liveData = await response.json();
    if (!state.data) return;
    state.data.live = liveData.live;
    state.data.status = liveData.status;
    render();
  } catch (_) {
    // The archived dashboard remains useful even when live APIs are unavailable.
  }
}

function render() {
  if (!state.data) return;
  renderHeader();
  renderMetrics();
  renderPerformance();
  renderAllocation();
  renderBalance();
  renderPortfolioPlan();
  renderPositions();
  renderCapitalPlan();
  renderMacroRisk();
  renderWatchlist();
  renderStockDecisions();
  renderEvents();
  renderBlocked();
  renderDataHealth();
  drawAllCharts();
}

function renderHeader() {
  const data = state.data;
  const mode = data.status.mode || data.config.mode || "unknown";
  const badge = $("modeBadge");
  const live = data.live || {};
  const marketOpen = live.ok && live.clock && live.clock.is_open === true;
  const marketClosed = live.ok && live.clock && live.clock.is_open === false;
  badge.textContent = `${mode.toUpperCase()}${marketOpen ? " | Market Open" : marketClosed ? " | Market Closed" : ""}`;
  badge.className = `badge ${marketOpen ? "good" : marketClosed ? "neutral" : "warn"}`;
}

function renderMetrics() {
  const status = state.data.status || {};
  const latestPerf = state.data.performance.latest || {};
  $("metricEquity").textContent = fmtMoney(status.equity);
  $("metricEquityMeta").textContent = state.data.live && state.data.live.ok ? "Live valued snapshot" : fallbackSource();
  $("metricCash").textContent = fmtMoney(status.cash);
  $("metricCashMeta").textContent = status.schedule && status.schedule.timezone ? `Schedule: ${status.schedule.timezone}` : "Cash from latest snapshot";
  $("metricPositions").textContent = fmtInt(status.positions_count);
  $("metricPositionsMeta").textContent = `${fmtInt(state.data.latest_scan.selector.pool_size)} symbols in latest scan pool`;
  $("metricRelative").textContent = fmtPct(status.relative_return_pct, 2);
  $("metricRelative").className = classFor(status.relative_return_pct);
  $("metricRelativeMeta").textContent = latestPerf.timestamp_utc ? `Latest point: ${formatDateTime(latestPerf.timestamp_utc)}` : "Waiting for scheduled points";
  $("metricLastScan").textContent = status.last_scan_timestamp ? formatDateTime(status.last_scan_timestamp) : "--";
  $("metricLastScanMeta").textContent = status.last_scan_file || "No scan report found";
  $("metricTrades").textContent = fmtInt((state.data.journals.trades || []).length);
  $("metricTradesMeta").textContent = status.recent_failed_trade_count ? `${status.recent_failed_trade_count} recent failures` : "Recent journal rows loaded";
}

function fallbackSource() {
  const perf = state.data.performance;
  if (perf.latest) return "Scheduled performance history";
  if (state.data.eod.latest) return `EOD ${state.data.eod.latest.date}`;
  return "Latest scan summary";
}

function renderPerformance() {
  const perf = state.data.performance;
  const source = perf.file || {};
  $("performanceSource").textContent = `${perf.source_path} | ${perf.point_count} point${perf.point_count === 1 ? "" : "s"} | Twelve Data price source`;
  $("performanceEmpty").textContent = perf.empty_reason || "";
  $("performanceEmpty").classList.toggle("hidden", !!perf.point_count);
  $("perfLegend").innerHTML = [
    legendItem("Portfolio", COLORS.cyan),
    legendItem("SPY", COLORS.amber)
  ].join("");
  if (!source.exists) {
    $("performanceSource").textContent = `${perf.source_path} | file not present yet`;
  }
}

function renderAllocation() {
  const list = $("allocationList");
  const slices = allocationSlices();
  if (!slices.length) {
    list.innerHTML = `<div class="empty-state">No allocation data available.</div>`;
    return;
  }
  list.innerHTML = slices.map((slice) => `
    <div class="allocation-row" data-symbol="${escapeAttr(slice.symbol)}">
      <strong>${escapeHtml(slice.symbol)}</strong>
      <div class="bar"><span style="width:${clamp(slice.weight * 100, 1, 100)}%; background:${slice.color}"></span></div>
      <span class="num">${fmtPct(slice.weight, 1, true)}</span>
    </div>
  `).join("");
}

function renderBalance() {
  const hasHistory = (state.data.eod.history || []).length > 0;
  $("balanceEmpty").textContent = hasHistory ? "" : "No EOD balance reports found.";
  $("balanceEmpty").classList.toggle("hidden", hasHistory);
}

function renderPortfolioPlan() {
  const scan = state.data.latest_scan;
  $("portfolioThesis").textContent = scan.portfolio_thesis || "No portfolio thesis found in the latest scan.";
  const weights = targetWeightRows();
  $("targetWeights").innerHTML = weights.length ? weights.map((row) => `
    <div class="target-row" data-symbol="${escapeAttr(row.symbol)}">
      <strong>${escapeHtml(row.symbol)}</strong>
      <div class="bar"><span style="width:${clamp(row.weight * 100, 1, 100)}%; background:${row.color}"></span></div>
      <span class="num">${fmtPct(row.weight, 1, true)}</span>
    </div>
  `).join("") : `<div class="empty-state">No target weights in latest scan.</div>`;
}

function renderPositions() {
  const source = positionSource();
  const rows = currentPositions();
  $("positionsSource").textContent = source.label;
  $("positionsSource").className = `badge ${source.live ? "good" : "neutral"}`;
  $("positionsBody").innerHTML = rows.length ? rows.map((pos) => `
    <tr data-symbol="${escapeAttr(pos.symbol)}">
      <td>${escapeHtml(formatDateTime(pos.as_of || pos.ts))}</td>
      <td><strong>${escapeHtml(pos.symbol)}</strong></td>
      <td>${escapeHtml(pos.side || "--")}</td>
      <td class="num">${fmtNum(pos.qty, 4)}</td>
      <td class="num">${fmtMoney(pos.avg_entry)}</td>
      <td class="num">${fmtMoney(pos.current_price)}</td>
      <td class="num">${fmtMoney(pos.market_value)}</td>
      <td class="num">${fmtPct(pos.weight_pct, 1, true)}</td>
      <td class="num ${classFor(pos.pnl_pct)}">${fmtPct(pos.pnl_pct, 2, true)} ${fmtMoneySigned(pos.pnl_dollars)}</td>
      <td>${escapeHtml(pos.price_source || "--")}</td>
    </tr>
  `).join("") : `<tr><td colspan="10" class="muted">No current positions found.</td></tr>`;
}

function renderCapitalPlan() {
  const plan = state.data.latest_scan.capital_movement_plan || [];
  const fallback = state.data.latest_scan.executions || [];
  const rows = plan.length ? plan : fallback;
  $("capitalPlanBody").innerHTML = rows.length ? rows.map((row) => {
    const action = row.action || row.side || row.ai_action || "--";
    const delta = row.delta_usd ?? row.delta_notional;
    const pnl = row.exit_pnl || null;
    return `
      <tr data-symbol="${escapeAttr(row.symbol)}">
        <td>${escapeHtml(formatDateTime(row.ts || row.scan_ts))}</td>
        <td><strong>${escapeHtml(row.symbol || "--")}</strong></td>
        <td>${actionBadge(action)}</td>
        <td class="num">${fmtMoneySigned(delta)}</td>
        <td class="num">${fmtPct(row.target_pct, 1, true)}</td>
        <td class="num">${fmtMoney(pnl && pnl.avg_entry_price)}</td>
        <td class="num">${fmtMoney(pnl && pnl.avg_exit_price)}</td>
        <td class="num ${classFor(pnl && pnl.pnl_value)}">${formatExitPnl(pnl)}</td>
        <td>${escapeHtml(row.reason || row.one_sentence_reason || "--")}</td>
      </tr>
    `;
  }).join("") : `<tr><td colspan="9" class="muted">No capital movement plan in latest scan.</td></tr>`;
}

function renderMacroRisk() {
  const macro = state.data.latest_scan.macro || {};
  const risk = state.data.config.risk || {};
  const selector = state.data.latest_scan.selector || {};
  $("macroGrid").innerHTML = [
    infoTile("Regime", macro.regime || "--"),
    infoTile("Macro Score", fmtNum(macro.score, 3)),
    infoTile("VIX", fmtNum(macro.vix_level, 2)),
    infoTile("Breadth", fmtPct(macro.breadth_pct_above_50, 1, true)),
    infoTile("SPY Trend", fmtNum(macro.spy_trend, 3)),
    infoTile("Pool Size", fmtInt(selector.pool_size))
  ].join("");
  $("riskGrid").innerHTML = [
    infoTile("Max Positions", fmtInt(risk.max_positions)),
    infoTile("Max Position", fmtPct(risk.max_position_pct, 0, true)),
    infoTile("Cash Reserve", fmtPct(risk.cash_reserve_pct, 0, true)),
    infoTile("Hard Stop", fmtPct(risk.hard_stop_loss_pct, 0, true))
  ].join("");
}

function renderWatchlist() {
  const rows = (state.data.watchlist.symbols || []).slice(0, 10);
  $("watchlistLeaders").innerHTML = rows.length ? rows.map((row) => `
    <div class="stack-item" data-symbol="${escapeAttr(row.symbol)}">
      <div class="stack-title">
        <strong>${escapeHtml(row.symbol)}</strong>
        <span class="num">${fmtNum(row.score, 2)}</span>
      </div>
      <p>${escapeHtml(formatDateTime(row.last_seen))}</p>
      <p>${escapeHtml(row.momentum_grade || "--")} | ${escapeHtml(row.last_reason || "--")}</p>
    </div>
  `).join("") : `<div class="empty-state">No dynamic watchlist found.</div>`;
}

function renderStockDecisions() {
  if (!state.data) return;
  const body = $("stockDecisionsBody");
  const all = state.data.latest_scan.all_symbol_decisions || [];
  const search = state.search;
  const rows = all
    .filter((row) => !search || String(row.symbol || "").toUpperCase().includes(search))
    .sort((a, b) => numberOr(b.candidate_priority_score, -999) - numberOr(a.candidate_priority_score, -999));
  body.innerHTML = rows.length ? rows.map((row) => `
    <tr data-symbol="${escapeAttr(row.symbol)}">
      <td><strong>${escapeHtml(row.symbol || "--")}</strong></td>
      <td>${escapeHtml(formatDateTime(row.ts || row.scan_ts))}</td>
      <td>${actionBadge(row.final_action || row.selector_action || "--")}</td>
      <td class="num">${fmtNum(row.opportunity_score, 1)}</td>
      <td class="num">${fmtNum(row.candidate_priority_score, 1)}</td>
      <td>${momentumBadge(row.momentum_grade)}</td>
      <td class="num">${fmtPct(row.target_pct, 1, true)}</td>
      <td class="num">${fmtMoneySigned(row.delta_usd)}</td>
      <td>${escapeHtml(row.reason || "--")}</td>
    </tr>
  `).join("") : `<tr><td colspan="9" class="muted">No symbol decisions match.</td></tr>`;
}

function renderEvents() {
  const trades = (state.data.journals.trades || []).slice(-12).reverse();
  $("tradesList").innerHTML = trades.length ? trades.map((row) => eventItem(row)).join("") : `<div class="empty-state">No trade journal rows found.</div>`;
  const decisions = (state.data.journals.decisions || []).slice(-12).reverse();
  $("decisionsList").innerHTML = decisions.length ? decisions.map((row) => eventItem(row)).join("") : `<div class="empty-state">No decision journal rows found.</div>`;
}

function renderBlocked() {
  const scan = state.data.latest_scan;
  const missed = scan.selector.missed_breakouts || [];
  const blocked = scan.selector.blocked_new_entries || [];
  const rows = [
    ...blocked.map((row) => ({ ...row, type: "Blocked" })),
    ...missed.slice(0, 10).map((row) => ({ ...row, type: "Missed" }))
  ];
  $("blockedList").innerHTML = rows.length ? rows.map((row) => `
    <div class="stack-item" data-symbol="${escapeAttr(row.symbol)}">
      <div class="stack-title">
        <strong>${escapeHtml(row.symbol || "--")}</strong>
        <span class="badge ${row.type === "Blocked" ? "warn" : "neutral"}">${escapeHtml(row.type)}</span>
      </div>
      <p>${escapeHtml(formatDateTime(row.ts || row.scan_ts))}</p>
      <p>${escapeHtml(row.reason || row.selector_reason || "--")}</p>
    </div>
  `).join("") : `<div class="empty-state">No blocked entries or missed breakouts.</div>`;
}

function renderDataHealth() {
  const sources = state.data.sources || {};
  const files = [
    ["Performance history", sources.performance_history],
    ["Latest scan", sources.latest_scan],
    ["Trade journal", state.data.journals.files.trades],
    ["Decision journal", state.data.journals.files.decisions],
    ["Dynamic watchlist", state.data.watchlist.file],
    ["Config", state.data.config.file]
  ];
  const counts = sources.counts || {};
  $("dataHealth").innerHTML = files.map(([label, file]) => sourceItem(label, file)).join("") + `
    <div class="source-item">
      <span>Report counts</span>
      <strong>${fmtInt(counts.scan_reports)} scans | ${fmtInt(counts.eod_reports)} EOD | ${fmtInt(counts.trade_journal_rows)} trades | ${fmtInt(counts.decision_journal_rows)} decisions</strong>
    </div>
  `;
}

function drawAllCharts() {
  if (!state.data) return;
  drawPerformanceChart();
  drawAllocationChart();
  drawBalanceChart();
  drawOpportunityChart();
}

function drawPerformanceChart() {
  const points = state.data.performance.points || [];
  const canvas = $("performanceChart");
  const portfolio = points
    .filter((p) => p.portfolio_return_pct !== null && p.portfolio_return_pct !== undefined)
    .map((p, idx) => ({ x: idx, y: p.portfolio_return_pct, label: shortDate(p.timestamp_utc), raw: p }));
  const spy = points
    .filter((p) => p.spy_return_pct !== null && p.spy_return_pct !== undefined)
    .map((p, idx) => ({ x: idx, y: p.spy_return_pct, label: shortDate(p.timestamp_utc), raw: p }));
  drawLineChart(canvas, [
    { label: "Portfolio", color: COLORS.cyan, points: portfolio },
    { label: "SPY", color: COLORS.amber, points: spy }
  ], {
    yFormat: (v) => fmtPct(v, 1),
    xLabels: points.map((p) => shortDate(p.timestamp_utc)),
    tooltipForPoint: (point, seriesItem) => {
      const raw = point.raw || {};
      const value = seriesItem.label === "Portfolio" ? raw.portfolio_value : raw.spy_price;
      return [
        `${seriesItem.label}: ${fmtPct(point.y, 3)}`,
        `Value: ${seriesItem.label === "Portfolio" ? fmtMoney(value) : fmtNum(value, 4)}`,
        `Time: ${formatDateTime(raw.timestamp_utc || point.label)}`
      ];
    }
  });
}

function drawAllocationChart() {
  drawDonutChart($("allocationChart"), allocationSlices());
}

function drawBalanceChart() {
  const rows = state.data.eod.history || [];
  const points = rows
    .filter((row) => row.equity !== null && row.equity !== undefined)
    .map((row, idx) => ({ x: idx, y: row.equity, label: row.date }));
  drawLineChart($("balanceChart"), [
    { label: "Equity", color: COLORS.green, points }
  ], {
    yFormat: fmtMoneyCompact,
    xLabels: rows.map((row) => row.date),
    tooltipForPoint: (point) => [`Equity: ${fmtMoney(point.y)}`, `Date: ${formatDateTime(point.label)}`]
  });
}

function drawOpportunityChart() {
  const rows = (state.data.latest_scan.all_symbol_decisions || [])
    .slice()
    .sort((a, b) => numberOr(b.candidate_priority_score, -999) - numberOr(a.candidate_priority_score, -999))
    .slice(0, 12)
    .map((row) => ({
      label: row.symbol,
      value: numberOr(row.candidate_priority_score, row.opportunity_score || 0),
      color: actionColor(row.final_action || row.selector_action)
    }));
  drawBarChart($("opportunityChart"), rows);
}

function drawLineChart(canvas, series, options = {}) {
  const { ctx, width, height } = canvasContext(canvas);
  ctx.clearRect(0, 0, width, height);
  const plot = { left: 56, top: 18, right: 18, bottom: 34 };
  const innerW = Math.max(1, width - plot.left - plot.right);
  const innerH = Math.max(1, height - plot.top - plot.bottom);
  const allPoints = series.flatMap((s) => s.points || []);
  if (!allPoints.length) {
    drawEmptyCanvas(ctx, width, height);
    registerTooltip(canvas, []);
    return;
  }
  let minY = Math.min(...allPoints.map((p) => p.y));
  let maxY = Math.max(...allPoints.map((p) => p.y));
  if (minY === maxY) {
    minY -= Math.abs(minY || 1) * 0.05;
    maxY += Math.abs(maxY || 1) * 0.05;
  }
  const pad = (maxY - minY) * 0.12;
  minY -= pad;
  maxY += pad;
  const maxIndex = Math.max(...allPoints.map((p) => p.x), 1);
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  ctx.fillStyle = COLORS.muted;
  ctx.font = "12px system-ui, sans-serif";
  for (let i = 0; i <= 4; i += 1) {
    const y = plot.top + (innerH * i) / 4;
    ctx.beginPath();
    ctx.moveTo(plot.left, y);
    ctx.lineTo(width - plot.right, y);
    ctx.stroke();
    const value = maxY - ((maxY - minY) * i) / 4;
    ctx.fillText(options.yFormat ? options.yFormat(value) : fmtNum(value, 2), 6, y + 4);
  }
  const labels = options.xLabels || [];
  if (labels.length) {
    const leftLabel = labels[0] || "";
    const rightLabel = labels[labels.length - 1] || "";
    ctx.fillText(leftLabel, plot.left, height - 10);
    const measure = ctx.measureText(rightLabel).width;
    ctx.fillText(rightLabel, Math.max(plot.left, width - plot.right - measure), height - 10);
  }
  const mapX = (x) => plot.left + (innerW * x) / maxIndex;
  const mapY = (y) => plot.top + innerH - ((y - minY) / (maxY - minY)) * innerH;
  const tooltipItems = [];
  series.forEach((s) => {
    if (!s.points || !s.points.length) return;
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    s.points.forEach((p, idx) => {
      const x = mapX(p.x);
      const y = mapY(p.y);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    s.points.forEach((p) => {
      const x = mapX(p.x);
      const y = mapY(p.y);
      ctx.fillStyle = s.color;
      ctx.beginPath();
      ctx.arc(x, y, s.points.length === 1 ? 4 : 2.5, 0, Math.PI * 2);
      ctx.fill();
      tooltipItems.push({
        kind: "point",
        x,
        y,
        radius: 12,
        color: s.color,
        title: `${s.label} | ${p.label || ""}`,
        lines: options.tooltipForPoint
          ? options.tooltipForPoint(p, s)
          : [`${s.label}: ${options.yFormat ? options.yFormat(p.y) : fmtNum(p.y, 4)}`, p.label ? `Time: ${formatDateTime(p.label)}` : ""].filter(Boolean)
      });
    });
  });
  registerTooltip(canvas, tooltipItems);
}

function drawBarChart(canvas, rows) {
  const { ctx, width, height } = canvasContext(canvas);
  ctx.clearRect(0, 0, width, height);
  if (!rows.length) {
    drawEmptyCanvas(ctx, width, height);
    registerTooltip(canvas, []);
    return;
  }
  const left = 54;
  const right = 44;
  const top = 12;
  const rowH = Math.max(18, Math.min(28, (height - 24) / rows.length));
  const max = Math.max(...rows.map((row) => row.value), 1);
  ctx.font = "12px system-ui, sans-serif";
  const tooltipItems = [];
  rows.forEach((row, idx) => {
    const y = top + idx * rowH;
    const barW = ((width - left - right) * row.value) / max;
    ctx.fillStyle = COLORS.muted;
    ctx.fillText(row.label || "--", 6, y + rowH * 0.67);
    ctx.fillStyle = "#252a33";
    roundRect(ctx, left, y + 5, width - left - right, rowH - 10, 4);
    ctx.fill();
    ctx.fillStyle = row.color || COLORS.cyan;
    roundRect(ctx, left, y + 5, barW, rowH - 10, 4);
    ctx.fill();
    ctx.fillStyle = COLORS.text;
    ctx.fillText(fmtNum(row.value, 1), width - right + 8, y + rowH * 0.67);
    tooltipItems.push({
      kind: "rect",
      x: left,
      y: y + 5,
      w: Math.max(2, barW),
      h: rowH - 10,
      color: row.color || COLORS.cyan,
      title: row.label || "--",
      lines: [`Score: ${fmtNum(row.value, 4)}`]
    });
  });
  registerTooltip(canvas, tooltipItems);
}

function drawDonutChart(canvas, slices) {
  const { ctx, width, height } = canvasContext(canvas);
  ctx.clearRect(0, 0, width, height);
  if (!slices.length) {
    drawEmptyCanvas(ctx, width, height);
    registerTooltip(canvas, []);
    return;
  }
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.max(42, Math.min(width, height) * 0.36);
  const inner = radius * 0.62;
  const total = slices.reduce((sum, s) => sum + Math.max(0, s.weight), 0) || 1;
  let angle = -Math.PI / 2;
  const tooltipItems = [];
  slices.forEach((slice) => {
    const next = angle + (Math.max(0, slice.weight) / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, angle, next);
    ctx.closePath();
    ctx.fillStyle = slice.color;
    ctx.fill();
    tooltipItems.push({
      kind: "arc",
      cx,
      cy,
      radius,
      inner,
      start: angle,
      end: next,
      color: slice.color,
      title: slice.symbol,
      lines: [`Weight: ${fmtPct(slice.weight, 3, true)}`]
    });
    angle = next;
  });
  ctx.globalCompositeOperation = "destination-out";
  ctx.beginPath();
  ctx.arc(cx, cy, inner, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = COLORS.text;
  ctx.font = "700 18px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(`${slices.length}`, cx, cy - 2);
  ctx.fillStyle = COLORS.muted;
  ctx.font = "12px system-ui, sans-serif";
  ctx.fillText("allocations", cx, cy + 16);
  ctx.textAlign = "left";
  registerTooltip(canvas, tooltipItems);
}

function drawEmptyCanvas(ctx, width, height) {
  ctx.fillStyle = COLORS.muted;
  ctx.font = "13px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("No chart data", width / 2, height / 2);
  ctx.textAlign = "left";
}

function registerTooltip(canvas, items) {
  state.chartMeta.set(canvas, items || []);
  if (canvas.dataset.tooltipBound) return;
  canvas.dataset.tooltipBound = "1";
  canvas.addEventListener("mousemove", handleChartHover);
  canvas.addEventListener("mouseleave", hideChartTooltip);
}

function handleChartHover(event) {
  const canvas = event.currentTarget;
  const items = state.chartMeta.get(canvas) || [];
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const item = findTooltipItem(items, x, y);
  if (!item) {
    hideChartTooltip();
    return;
  }
  showChartTooltip(item, event.clientX, event.clientY);
}

function findTooltipItem(items, x, y) {
  let nearest = null;
  let nearestDistance = Infinity;
  for (const item of items) {
    if (item.kind === "point") {
      const distance = Math.hypot(x - item.x, y - item.y);
      if (distance <= item.radius && distance < nearestDistance) {
        nearest = item;
        nearestDistance = distance;
      }
      continue;
    }
    if (item.kind === "rect") {
      if (x >= item.x && x <= item.x + item.w && y >= item.y && y <= item.y + item.h) return item;
      continue;
    }
    if (item.kind === "arc") {
      const dx = x - item.cx;
      const dy = y - item.cy;
      const radius = Math.hypot(dx, dy);
      if (radius < item.inner || radius > item.radius) continue;
      let angle = Math.atan2(dy, dx);
      if (angle < -Math.PI / 2) angle += Math.PI * 2;
      const start = item.start < -Math.PI / 2 ? item.start + Math.PI * 2 : item.start;
      const end = item.end < -Math.PI / 2 ? item.end + Math.PI * 2 : item.end;
      if (angle >= start && angle <= end) return item;
    }
  }
  return nearest;
}

function showChartTooltip(item, clientX, clientY) {
  const tooltip = $("chartTooltip");
  tooltip.innerHTML = `
    <strong>${escapeHtml(item.title || "")}</strong>
    ${(item.lines || []).map((line) => `<span>${escapeHtml(line)}</span>`).join("")}
  `;
  tooltip.classList.remove("hidden");
  const pad = 14;
  const width = tooltip.offsetWidth || 180;
  const height = tooltip.offsetHeight || 80;
  let left = clientX + pad;
  let top = clientY + pad;
  if (left + width + 12 > window.innerWidth) left = clientX - width - pad;
  if (top + height + 12 > window.innerHeight) top = clientY - height - pad;
  tooltip.style.left = `${Math.max(8, left)}px`;
  tooltip.style.top = `${Math.max(8, top)}px`;
}

function hideChartTooltip() {
  $("chartTooltip").classList.add("hidden");
}

function canvasContext(canvas) {
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(260, rect.width || canvas.parentElement.clientWidth || 400);
  const height = Math.max(180, rect.height || canvas.parentElement.clientHeight || 260);
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { ctx, width, height };
}

function roundRect(ctx, x, y, w, h, r) {
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + w, y, x + w, y + h, radius);
  ctx.arcTo(x + w, y + h, x, y + h, radius);
  ctx.arcTo(x, y + h, x, y, radius);
  ctx.arcTo(x, y, x + w, y, radius);
  ctx.closePath();
}

function showSymbol(symbol) {
  const normalized = String(symbol || "").toUpperCase();
  state.selectedSymbol = normalized;
  const data = state.data;
  const position = currentPositions().find((row) => String(row.symbol || "").toUpperCase() === normalized);
  const decision = (data.latest_scan.all_symbol_decisions || []).find((row) => String(row.symbol || "").toUpperCase() === normalized);
  const history = (data.eod.position_history || {})[normalized] || [];
  const trades = (data.journals.trades || []).filter((row) => String(row.symbol || "").toUpperCase() === normalized).slice(-6).reverse();
  const decisions = (data.journals.decisions || []).filter((row) => String(row.symbol || "").toUpperCase() === normalized).slice(-6).reverse();
  $("drawerTitle").textContent = normalized;
  $("drawerBody").innerHTML = `
    ${detailOverview(position, decision)}
    <section class="detail-section live-chart-section">
      <div class="section-head-inline">
        <h3>Live Chart</h3>
        <span class="badge warn">Extended hours requested</span>
      </div>
      <p>Intraday TradingView chart with pre-market and post-market display requested where the symbol/data feed supports it.</p>
      <div id="tradingViewChart" class="tradingview-chart"></div>
    </section>
    <section class="detail-section">
      <h3>Position History</h3>
      <div class="mini-chart"><canvas id="symbolHistoryChart"></canvas></div>
    </section>
    <section class="detail-section">
      <h3>Latest Reason</h3>
      <p>${escapeHtml((decision && decision.reason) || (position && position.reason) || "No symbol-specific reason found.")}</p>
    </section>
    <section class="detail-section">
      <h3>Recent Trades</h3>
      ${trades.length ? trades.map((row) => eventItem(row)).join("") : `<p>No recent trades for this symbol.</p>`}
    </section>
    <section class="detail-section">
      <h3>Recent Decisions</h3>
      ${decisions.length ? decisions.map((row) => eventItem(row)).join("") : `<p>No recent decisions for this symbol.</p>`}
    </section>
  `;
  $("detailDrawer").classList.add("open");
  $("detailDrawer").setAttribute("aria-hidden", "false");
  setTimeout(() => {
    renderTradingViewChart(normalized);
    const points = history.map((row, idx) => ({ x: idx, y: row.market_value || 0, label: row.date }));
    drawLineChart($("symbolHistoryChart"), [{ label: normalized, color: COLORS.cyan, points }], {
      yFormat: fmtMoneyCompact,
      xLabels: history.map((row) => row.date),
      tooltipForPoint: (point) => [`Market value: ${fmtMoney(point.y)}`, `Date: ${formatDateTime(point.label)}`]
    });
  }, 0);
}

function showFullWatchlist() {
  const rows = state.data && state.data.watchlist ? state.data.watchlist.symbols || [] : [];
  $("drawerTitle").textContent = "Dynamic Watchlist";
  $("drawerBody").innerHTML = `
    <section class="detail-section">
      <div class="detail-kv">
        <div><span>Active Symbols</span><strong>${fmtInt(rows.length)}</strong></div>
        <div><span>Updated</span><strong>${escapeHtml(formatDateTime(state.data.watchlist.updated_at))}</strong></div>
      </div>
      <p>${escapeHtml(state.data.watchlist.notes || "")}</p>
    </section>
    <section class="detail-section">
      <h3>All Dynamic Watchlist Symbols</h3>
      <div class="table-wrap compact-table">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Score</th>
              <th>Last Seen</th>
              <th>Momentum</th>
              <th>Reason</th>
              <th>Sources</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map((row) => `
              <tr data-symbol="${escapeAttr(row.symbol)}">
                <td><strong>${escapeHtml(row.symbol)}</strong></td>
                <td class="num">${fmtNum(row.score, 2)}</td>
                <td>${escapeHtml(formatDateTime(row.last_seen))}</td>
                <td>${momentumBadge(row.momentum_grade)}</td>
                <td>${escapeHtml(row.last_reason || "--")}</td>
                <td>${escapeHtml((row.sources || []).join(", ") || "--")}</td>
              </tr>
            `).join("") || `<tr><td colspan="6" class="muted">No dynamic watchlist rows found.</td></tr>`}
          </tbody>
        </table>
      </div>
    </section>
  `;
  $("detailDrawer").classList.add("open");
  $("detailDrawer").setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  $("detailDrawer").classList.remove("open");
  $("detailDrawer").setAttribute("aria-hidden", "true");
}

function renderTradingViewChart(symbol) {
  const host = $("tradingViewChart");
  if (!host) return;
  const tvSymbol = tradingViewSymbol(symbol);
  host.innerHTML = `<div class="tradingview-widget-container__widget"></div>`;
  const script = document.createElement("script");
  script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
  script.async = true;
  script.text = JSON.stringify({
    autosize: true,
    symbol: tvSymbol,
    interval: "5",
    timezone: "America/New_York",
    theme: "dark",
    style: "1",
    locale: "en",
    enable_publishing: false,
    allow_symbol_change: true,
    save_image: false,
    calendar: false,
    hide_side_toolbar: false,
    withdateranges: true,
    hide_volume: false,
    support_host: "https://www.tradingview.com",
    enabled_features: ["pre_post_market_sessions"],
    overrides: {
      "mainSeriesProperties.sessionId": "extended",
      "backgrounds.preMarket.color": "rgba(85,214,190,0.08)",
      "backgrounds.postMarket.color": "rgba(246,200,95,0.08)"
    }
  });
  host.appendChild(script);
}

function tradingViewSymbol(symbol) {
  const cleaned = String(symbol || "").toUpperCase().replace(/[^A-Z0-9.-]/g, "");
  const mapped = {
    SPY: "AMEX:SPY",
    BITO: "AMEX:BITO",
    SOXS: "AMEX:SOXS",
    SOFX: "NASDAQ:SOFX"
  };
  return mapped[cleaned] || cleaned;
}

function detailOverview(position, decision) {
  return `
    <section class="detail-section">
      <h3>Overview</h3>
      <div class="detail-kv">
        <div><span>Market Value</span><strong>${fmtMoney(position && position.market_value)}</strong></div>
        <div><span>Weight</span><strong>${fmtPct(position && position.weight_pct, 1, true)}</strong></div>
        <div><span>Opportunity</span><strong>${fmtNum(decision && decision.opportunity_score, 1)}</strong></div>
        <div><span>Priority</span><strong>${fmtNum(decision && decision.candidate_priority_score, 1)}</strong></div>
        <div><span>Action</span><strong>${escapeHtml((decision && (decision.final_action || decision.selector_action)) || "--")}</strong></div>
        <div><span>Momentum</span><strong>${escapeHtml((decision && decision.momentum_grade) || "--")}</strong></div>
      </div>
    </section>
  `;
}

function currentPositions() {
  const live = state.data.live || {};
  if (live.ok && live.positions && live.positions.length) return live.positions;
  const eodPositions = state.data.eod.latest && state.data.eod.latest.positions;
  if (eodPositions && eodPositions.length) return eodPositions;
  return (state.data.latest_scan.current_portfolio.positions || []).map((row) => ({
    symbol: row.symbol,
    side: "long",
    qty: row.current_qty,
    current_price: row.current_price,
    market_value: row.current_notional_usd,
    weight_pct: row.current_weight_pct,
    pnl_pct: null,
    pnl_dollars: null,
    price_source: "latest_scan",
    as_of: state.data.latest_scan.ts
  }));
}

function positionSource() {
  const live = state.data.live || {};
  if (live.ok && live.positions && live.positions.length) return { label: "Live valued", live: true };
  if (state.data.eod.latest && state.data.eod.latest.positions && state.data.eod.latest.positions.length) {
    return { label: `EOD ${state.data.eod.latest.date}`, live: false };
  }
  return { label: "Latest scan", live: false };
}

function allocationSlices() {
  const positions = currentPositions();
  const total = positions.reduce((sum, p) => sum + Math.max(0, numberOr(p.market_value, 0)), 0);
  const rows = positions
    .map((p, idx) => {
      const weight = p.weight_pct !== null && p.weight_pct !== undefined ? Number(p.weight_pct) : (total ? numberOr(p.market_value, 0) / total : 0);
      return { symbol: p.symbol || "--", weight: Math.max(0, weight), color: palette(idx) };
    })
    .filter((p) => p.weight > 0);
  const cash = state.data.status.cash;
  const equity = state.data.status.equity;
  if (cash && equity && cash > 0) {
    rows.push({ symbol: "Cash", weight: cash / equity, color: COLORS.amber });
  }
  return rows.sort((a, b) => b.weight - a.weight).slice(0, 12);
}

function targetWeightRows() {
  const weights = state.data.latest_scan.selector.execution_target_weights || state.data.latest_scan.selector.target_weights || {};
  return Object.entries(weights)
    .map(([symbol, weight], idx) => ({ symbol, weight: Number(weight) || 0, color: palette(idx) }))
    .sort((a, b) => b.weight - a.weight);
}

function eventItem(row) {
  const symbol = row.symbol ? `<span class="event-symbol" data-symbol="${escapeAttr(row.symbol)}">${escapeHtml(row.symbol)}</span>` : `<span class="event-symbol">System</span>`;
  const badgeClass = String(row.event || "").toLowerCase().includes("fail") ? "bad" : String(row.action || row.event || "").toLowerCase().includes("buy") ? "good" : "neutral";
  return `
    <div class="event-item">
      <div class="event-top">
        <div>${symbol} <span class="faint">${escapeHtml(formatDateTime(row.ts))}</span></div>
        <span class="badge ${badgeClass}">${escapeHtml(row.action || row.event || "--")}</span>
      </div>
      <div class="event-detail">${escapeHtml(row.detail || row.status || row.error || "--")}</div>
    </div>
  `;
}

function sourceItem(label, file) {
  const exists = file && file.exists;
  const path = file && file.path ? file.path : "--";
  const meta = exists ? `${fmtBytes(file.bytes)} | ${formatDateTime(file.modified_at_utc)}` : "Not found";
  return `
    <div class="source-item">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(path)}</strong>
      <span>${escapeHtml(meta)}</span>
    </div>
  `;
}

function infoTile(label, value) {
  return `<div class="info-tile"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value ?? "--")}</strong></div>`;
}

function legendItem(label, color) {
  return `<span><i style="background:${color}"></i>${escapeHtml(label)}</span>`;
}

function actionBadge(action) {
  const text = String(action || "--");
  return `<span class="badge ${badgeClassForAction(text)}">${escapeHtml(text)}</span>`;
}

function momentumBadge(grade) {
  const text = String(grade || "--");
  const cls = text.includes("strong") ? "good" : text.includes("fading") ? "bad" : text.includes("acceptable") ? "warn" : "neutral";
  return `<span class="badge ${cls}">${escapeHtml(text)}</span>`;
}

function badgeClassForAction(action) {
  const text = String(action || "").toLowerCase();
  if (text.includes("buy") || text.includes("enter") || text.includes("add")) return "good";
  if (text.includes("sell") || text.includes("exit") || text.includes("blocked")) return "bad";
  if (text.includes("trim") || text.includes("reduce")) return "warn";
  return "neutral";
}

function actionColor(action) {
  const cls = badgeClassForAction(action);
  if (cls === "good") return COLORS.green;
  if (cls === "bad") return COLORS.red;
  if (cls === "warn") return COLORS.amber;
  return COLORS.cyan;
}

function palette(index) {
  const values = [COLORS.cyan, COLORS.green, COLORS.amber, COLORS.blue, COLORS.pink, "#9ed36a", "#ff9f68", "#b7a0ff", "#6ee7f5", "#d6e05f"];
  return values[index % values.length];
}

function fmtMoney(value) {
  if (isMissing(value)) return "--";
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: Math.abs(n) >= 1000 ? 0 : 2 }).format(n);
}

function fmtMoneySigned(value) {
  if (isMissing(value)) return "--";
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  const sign = n > 0 ? "+" : "";
  return `${sign}${fmtMoney(n)}`;
}

function fmtMoneyCompact(value) {
  if (isMissing(value)) return "--";
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(n);
}

function fmtPct(value, digits = 1, fraction = false) {
  if (isMissing(value)) return "--";
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  const pct = fraction ? n * 100 : n;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(digits)}%`;
}

function fmtNum(value, digits = 2) {
  if (isMissing(value)) return "--";
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  return n.toLocaleString("en-US", { maximumFractionDigits: digits });
}

function fmtInt(value) {
  if (isMissing(value)) return "--";
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  return Math.round(n).toLocaleString("en-US");
}

function fmtBytes(value) {
  if (isMissing(value)) return "--";
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function formatExitPnl(pnl) {
  if (!pnl) return "--";
  if (!pnl.complete) {
    return pnl.missing && pnl.missing.length ? `Missing ${pnl.missing.join(", ")}` : "--";
  }
  return `${fmtMoneySigned(pnl.pnl_value)} (${fmtPct(pnl.pnl_pct, 2, true)})`;
}

function formatDateTime(value) {
  if (!value) return "--";
  const text = String(value);
  if (text.length === 10 && text[4] === "-" && text[7] === "-") return text;
  const date = new Date(text);
  if (Number.isNaN(date.getTime())) return text.slice(0, 19);
  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short"
  });
}

function shortTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 19);
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function shortDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16);
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function classFor(value) {
  if (isMissing(value)) return "";
  const n = Number(value);
  if (!Number.isFinite(n) || n === 0) return "";
  return n > 0 ? "pos" : "neg";
}

function numberOr(value, fallback) {
  if (isMissing(value)) return fallback;
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function isMissing(value) {
  return value === null || value === undefined || value === "";
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

function debounce(fn, wait) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), wait);
  };
}

function setToast(message, sticky = false) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  if (!sticky) {
    clearTimeout(setToast.timer);
    setToast.timer = setTimeout(() => toast.classList.add("hidden"), 2400);
  }
}
