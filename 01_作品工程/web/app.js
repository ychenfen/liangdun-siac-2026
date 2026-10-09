const N_HOURS = 168;
const CHART_FONT = '"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif';
const state = { data: null, policy: "OURS", hour: 72, hover: null, timer: null };

// 与静态图表保持一致的策略配色（同一策略在看板与报告图中颜色相同）
const names = {
  B0_RULE_UNCAPPED: "独立阈值 不限电",
  B1_FCFS: "先到先得",
  B2_TEMP_GREEDY: "粮温优先",
  OURS: "粮盾协同策略"
};
const colors = {
  B0_RULE_UNCAPPED: "#E57A2D",
  B1_FCFS: "#7A9E3A",
  B2_TEMP_GREEDY: "#1677B8",
  OURS: "#168C78"
};
const INK = "#102A43";
const MUTED = "#627D98";
const GRID = "#E2E8F0";
const CAP_RED = "#C94C4C";
const POWER_FILL = "rgba(242, 196, 109, 0.35)";
const POWER_LINE = "#B7791F";
const PLOT_LEFT = 56;
const PLOT_RIGHT = 18;

const $ = (id) => document.getElementById(id);
const rowsOf = (policy) => state.data.timeseries.filter((r) => r.policy === policy);
const current = () => rowsOf(state.policy)[state.hour];

function formatTime(value) {
  const d = new Date(value);
  return `${String(d.getMonth() + 1).padStart(2, "0")}月${String(d.getDate()).padStart(2, "0")}日 ${String(d.getHours()).padStart(2, "0")}:00`;
}

function dayLabel(value) {
  return `${value.slice(5, 7)}月${value.slice(8, 10)}日`;
}

// 按设备像素比重新设置画布尺寸，使文字和线条在高分屏上清晰，且不被 CSS 拉伸变形
function fitCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return { ctx, w, h };
}

function xAt(index, w) {
  return PLOT_LEFT + ((w - PLOT_LEFT - PLOT_RIGHT) * index) / (N_HOURS - 1);
}

function indexAt(px, w) {
  const raw = Math.round(((px - PLOT_LEFT) / (w - PLOT_LEFT - PLOT_RIGHT)) * (N_HOURS - 1));
  return Math.max(0, Math.min(N_HOURS - 1, raw));
}

function drawSeries(ctx, values, toY, w, color, width, alpha = 1) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineJoin = "round";
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = xAt(i, w);
    const y = toY(v);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.restore();
}

function drawCursor(ctx, w, top, bottom) {
  const x = xAt(state.hour, w);
  ctx.save();
  ctx.strokeStyle = INK;
  ctx.setLineDash([4, 4]);
  ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, bottom); ctx.stroke();
  ctx.restore();
  if (state.hover !== null) {
    const hx = xAt(state.hover, w);
    ctx.save();
    ctx.strokeStyle = "rgba(16,42,67,0.35)";
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(hx, top); ctx.lineTo(hx, bottom); ctx.stroke();
    ctx.restore();
  }
}

// 上图：容量加权风险。当前策略加粗实线，其余策略淡色作参照，便于对比。
function drawRisk() {
  const { ctx, w, h } = fitCanvas($("riskChart"));
  const top = 30;
  const bottom = h - 8;
  const toY = (v) => bottom - (Math.min(v, 0.8) / 0.8) * (bottom - top);

  ctx.font = `12px ${CHART_FONT}`;
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let k = 0; k <= 4; k++) {
    const v = 0.2 * k;
    const y = toY(v);
    ctx.strokeStyle = GRID;
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(PLOT_LEFT, y); ctx.lineTo(w - PLOT_RIGHT, y); ctx.stroke();
    ctx.fillStyle = MUTED;
    ctx.fillText(v.toFixed(1), PLOT_LEFT - 8, y);
  }

  ctx.textAlign = "left";
  ctx.fillStyle = MUTED;
  ctx.fillText("容量加权风险（淡色线为其他策略）", PLOT_LEFT, 12);

  Object.keys(names).forEach((p) => {
    if (p === state.policy) return;
    drawSeries(ctx, rowsOf(p).map((r) => r.weighted_risk), toY, w, colors[p], 1.5, 0.4);
  });
  drawSeries(ctx, rowsOf(state.policy).map((r) => r.weighted_risk), toY, w, colors[state.policy], 2.8);

  drawCursor(ctx, w, top, bottom);
  const row = current();
  const cx = xAt(state.hour, w);
  const cy = toY(row.weighted_risk);
  ctx.fillStyle = colors[state.policy];
  ctx.beginPath(); ctx.arc(cx, cy, 4.5, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = "#FFFFFF"; ctx.lineWidth = 2; ctx.stroke();
}

// 下图：站级功率，独立的 kW 纵轴，并标出 240 kW 上限
function drawPower() {
  const { ctx, w, h } = fitCanvas($("powerChart"));
  const cap = state.data.meta.power_cap_kw;
  const MAX = 720;
  const top = 22;
  const bottom = h - 24;
  const toY = (v) => bottom - (Math.min(v, MAX) / MAX) * (bottom - top);

  ctx.font = `12px ${CHART_FONT}`;
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  [0, 240, 480, 720].forEach((v) => {
    const y = toY(v);
    ctx.strokeStyle = GRID;
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(PLOT_LEFT, y); ctx.lineTo(w - PLOT_RIGHT, y); ctx.stroke();
    ctx.fillStyle = MUTED;
    ctx.fillText(String(v), PLOT_LEFT - 8, y);
  });
  ctx.textAlign = "left";
  ctx.fillText("站级功率 kW", PLOT_LEFT, 9);

  const rows = rowsOf(state.policy);
  const power = rows.map((r) => Math.min(r.power_kw, MAX));
  ctx.beginPath();
  power.forEach((v, i) => {
    const x = xAt(i, w);
    const y = toY(v);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.lineTo(xAt(N_HOURS - 1, w), toY(0));
  ctx.lineTo(xAt(0, w), toY(0));
  ctx.closePath();
  ctx.fillStyle = POWER_FILL;
  ctx.fill();
  drawSeries(ctx, power, toY, w, POWER_LINE, 1.6);

  // 240 kW 上限线
  ctx.save();
  ctx.strokeStyle = CAP_RED;
  ctx.lineWidth = 1.6;
  ctx.setLineDash([6, 4]);
  ctx.beginPath(); ctx.moveTo(PLOT_LEFT, toY(cap)); ctx.lineTo(w - PLOT_RIGHT, toY(cap)); ctx.stroke();
  ctx.restore();
  ctx.textAlign = "right";
  ctx.textBaseline = "bottom";
  ctx.fillStyle = CAP_RED;
  ctx.fillText(`站级上限 ${cap} kW`, w - PLOT_RIGHT, toY(cap) - 4);

  // 日期刻度：每 24 小时一个
  ctx.textBaseline = "top";
  ctx.fillStyle = MUTED;
  for (let i = 0; i < N_HOURS; i += 24) {
    const x = xAt(i, w);
    ctx.textAlign = i === 0 ? "left" : "center";
    ctx.fillText(dayLabel(rows[i].timestamp), x, bottom + 7);
  }

  drawCursor(ctx, w, top, bottom);
  const row = current();
  const cx = xAt(state.hour, w);
  const cy = toY(Math.min(row.power_kw, MAX));
  ctx.fillStyle = POWER_LINE;
  ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI * 2); ctx.fill();
}

// 仪表：刻度 0 — 300 kW，240 kW 处标出上限，超过上限时变红
function drawGauge(value) {
  const { ctx, w, h } = fitCanvas($("powerGauge"));
  const cap = state.data.meta.power_cap_kw;
  const MAX = Math.round(cap * 1.25);
  const cx = w / 2;
  const cy = h * 0.82;
  const r = Math.min(w / 2 - 34, h * 0.72);
  const angle = (v) => Math.PI + Math.PI * Math.min(Math.max(v, 0) / MAX, 1);

  ctx.lineCap = "round";
  ctx.lineWidth = 16;
  ctx.strokeStyle = "#E2EBE7";
  ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, 2 * Math.PI); ctx.stroke();
  ctx.strokeStyle = value > cap ? CAP_RED : "#20A678";
  ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, angle(value)); ctx.stroke();

  // 上限刻度
  const capAngle = angle(cap);
  ctx.strokeStyle = CAP_RED;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(cx + (r - 14) * Math.cos(capAngle), cy + (r - 14) * Math.sin(capAngle));
  ctx.lineTo(cx + (r + 12) * Math.cos(capAngle), cy + (r + 12) * Math.sin(capAngle));
  ctx.stroke();

  ctx.font = `12px ${CHART_FONT}`;
  ctx.fillStyle = MUTED;
  ctx.textBaseline = "top";
  ctx.textAlign = "left";
  ctx.fillText("0", cx - r - 6, cy + 10);
  ctx.textAlign = "right";
  ctx.fillText(`${MAX}`, cx + r + 6, cy + 10);
  ctx.textAlign = "center";
  ctx.fillStyle = CAP_RED;
  ctx.fillText(`上限 ${cap}`, cx + (r + 22) * Math.cos(capAngle), cy + (r + 22) * Math.sin(capAngle) - 14);

  ctx.fillStyle = INK;
  ctx.font = `700 28px ${CHART_FONT}`;
  ctx.textBaseline = "alphabetic";
  ctx.fillText(`${value.toFixed(0)} kW`, cx, cy - r * 0.32);
}

function riskClass(risk) { return risk >= 0.65 ? "alert" : risk >= 0.35 ? "watch" : "safe"; }

function renderBins() {
  const bins = state.data.bin_timeseries.filter((b) => b.policy === state.policy && b.hour === state.hour);
  $("binGrid").innerHTML = bins.map((b) => {
    return `<div class="bin ${riskClass(b.risk)}" title="${b.bin_id}：风险 ${b.risk.toFixed(2)}，${b.fan_active ? "风机运行" : "风机待机"}">` +
      `<b>${b.bin_id}</b><span class="risk">${b.risk.toFixed(2)}</span>` +
      `<span class="reading">${b.temp_c.toFixed(1)}°C · ${b.moisture_pct.toFixed(2)}%</span>` +
      `<span class="fan ${b.fan_active ? "on" : ""}">${b.fan_active ? "风机运行" : "风机待机"}</span></div>`;
  }).join("");
}

function drawAll() {
  drawRisk();
  drawPower();
  drawGauge(current().power_kw);
}

function showTooltip(index, clientX) {
  const wrap = $("trendWrap");
  const tip = $("tooltip");
  const row = rowsOf(state.policy)[index];
  tip.innerHTML =
    `<b>${formatTime(row.timestamp)}</b><br>` +
    `${names[state.policy]}<br>` +
    `容量加权风险 ${row.weighted_risk.toFixed(3)}<br>` +
    `站级功率 ${row.power_kw.toFixed(0)} kW<br>` +
    `高风险仓 ${row.high_risk_bins} / 24　活动风机 ${row.active_fans} 台`;
  tip.hidden = false;
  const rect = wrap.getBoundingClientRect();
  const tipWidth = tip.offsetWidth;
  let left = clientX - rect.left + 14;
  if (left + tipWidth > rect.width) left = clientX - rect.left - tipWidth - 14;
  tip.style.left = `${Math.max(0, left)}px`;
  tip.style.top = "8px";
}

function setupTrendInteraction() {
  const wrap = $("trendWrap");
  wrap.addEventListener("mousemove", (e) => {
    const rect = $("riskChart").getBoundingClientRect();
    const index = indexAt(e.clientX - rect.left, rect.width);
    state.hover = index;
    showTooltip(index, e.clientX);
    drawAll();
  });
  wrap.addEventListener("mouseleave", () => {
    state.hover = null;
    $("tooltip").hidden = true;
    drawAll();
  });
  wrap.addEventListener("click", (e) => {
    const rect = $("riskChart").getBoundingClientRect();
    state.hour = indexAt(e.clientX - rect.left, rect.width);
    render();
  });
}

function render() {
  const row = current();
  const agg = state.data.aggregate.find((r) => r.policy === state.policy);
  $("riskNow").textContent = row.weighted_risk.toFixed(3);
  $("powerNow").textContent = row.power_kw.toFixed(0);
  $("highRiskNow").textContent = row.high_risk_bins;
  $("fansNow").textContent = row.active_fans;
  $("energyMean").textContent = `十种子均值 ${agg.energy_kwh_mean.toFixed(0)} kWh`;
  $("capState").textContent = row.power_kw > state.data.meta.power_cap_kw ? "超过上限" : "上限内";
  $("outsideTemp").textContent = `${row.outside_temp_c.toFixed(1)} °C`;
  $("outsideRh").textContent = `${row.outside_rh_pct.toFixed(0)} %`;
  $("waitNow").textContent = `${row.max_wait_hours.toFixed(0)} 小时`;
  $("timeLabel").textContent = formatTime(row.timestamp);
  $("hourValue").textContent = state.hour;
  $("hourSlider").value = state.hour;
  const open = row.active_fans > 0;
  $("windowState").textContent = open ? "存在可用窗口" : "当前窗口关闭";
  $("windowState").classList.toggle("closed", !open);
  renderBins();
  drawAll();
}

async function boot() {
  state.data = await fetch("data.json").then((r) => r.json());
  $("scenarioText").textContent = state.data.meta.scenario;
  $("disclosure").textContent = state.data.meta.disclosure;
  $("policySelect").addEventListener("change", (e) => { state.policy = e.target.value; render(); });
  $("hourSlider").addEventListener("input", (e) => { state.hour = Number(e.target.value); render(); });
  $("playButton").addEventListener("click", () => {
    if (state.timer) {
      clearInterval(state.timer);
      state.timer = null;
      $("playButton").textContent = "播放";
      return;
    }
    $("playButton").textContent = "暂停";
    state.timer = setInterval(() => { state.hour = (state.hour + 1) % N_HOURS; render(); }, 220);
  });
  setupTrendInteraction();
  // 画布尺寸随容器变化时重绘，避免拉伸变形
  if ("ResizeObserver" in window) new ResizeObserver(() => drawAll()).observe($("trendWrap"));
  window.addEventListener("resize", () => drawAll());
  render();
}

boot().catch((error) => {
  console.error(error);
  document.body.innerHTML = `<pre>看板数据加载失败：${error.message}</pre>`;
});
