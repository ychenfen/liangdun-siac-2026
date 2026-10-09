const state = { data: null, policy: "OURS", hour: 72, timer: null };
const names = {
  B0_RULE_UNCAPPED: "独立阈值 不限电",
  B1_FCFS: "先到先得",
  B2_TEMP_GREEDY: "粮温优先",
  OURS: "粮盾协同策略"
};
const colors = { OURS: "#13795b", B2_TEMP_GREEDY: "#3178a6", B1_FCFS: "#7e9b48", B0_RULE_UNCAPPED: "#d88a16" };

const $ = (id) => document.getElementById(id);
const rowsFor = () => state.data.timeseries.filter((r) => r.policy === state.policy);
const current = () => rowsFor()[state.hour];

function formatTime(value) {
  const d = new Date(value);
  return `${String(d.getMonth() + 1).padStart(2, "0")}月${String(d.getDate()).padStart(2, "0")}日 ${String(d.getHours()).padStart(2, "0")}:00`;
}

function drawGauge(value) {
  const canvas = $("powerGauge");
  const ctx = canvas.getContext("2d");
  const cap = state.data.meta.power_cap_kw;
  const ratio = Math.min(value / cap, 1.2);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.lineCap = "round";
  ctx.strokeStyle = "#e2ebe7";
  ctx.lineWidth = 28;
  ctx.beginPath(); ctx.arc(340, 190, 142, Math.PI, 2 * Math.PI); ctx.stroke();
  ctx.strokeStyle = ratio > 1 ? "#c84d4d" : "#20a678";
  ctx.beginPath(); ctx.arc(340, 190, 142, Math.PI, Math.PI + Math.PI * Math.min(ratio, 1)); ctx.stroke();
  ctx.fillStyle = "#102a43"; ctx.textAlign = "center"; ctx.font = "700 36px PingFang SC";
  ctx.fillText(`${value.toFixed(0)} kW`, 340, 155);
  ctx.fillStyle = "#6b7f91"; ctx.font = "20px PingFang SC";
  ctx.fillText(`站级上限 ${cap} kW`, 340, 190);
}

function drawTrend() {
  const canvas = $("trendChart");
  const ctx = canvas.getContext("2d");
  const rows = rowsFor();
  const W = canvas.width, H = canvas.height;
  const plot = { x: 58, y: 18, w: W - 90, h: H - 64 };
  ctx.clearRect(0, 0, W, H);
  ctx.font = "15px PingFang SC"; ctx.fillStyle = "#718493"; ctx.textAlign = "right";
  for (let i = 0; i <= 4; i++) {
    const y = plot.y + plot.h * i / 4;
    ctx.strokeStyle = "#e5ecef"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(plot.x, y); ctx.lineTo(plot.x + plot.w, y); ctx.stroke();
    ctx.fillText((0.8 - i * 0.2).toFixed(1), plot.x - 10, y + 5);
  }
  const drawLine = (values, max, color, width) => {
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.beginPath();
    values.forEach((v, i) => {
      const x = plot.x + plot.w * i / (values.length - 1);
      const y = plot.y + plot.h * (1 - v / max);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  };
  drawLine(rows.map((r) => r.weighted_risk), 0.8, colors[state.policy], 4);
  drawLine(rows.map((r) => Math.min(r.power_kw, 720)), 720, "rgba(216,138,22,.58)", 2);
  const markerX = plot.x + plot.w * state.hour / 167;
  ctx.strokeStyle = "#102a43"; ctx.setLineDash([5, 5]); ctx.beginPath(); ctx.moveTo(markerX, plot.y); ctx.lineTo(markerX, plot.y + plot.h); ctx.stroke(); ctx.setLineDash([]);
  ctx.textAlign = "left"; ctx.fillStyle = colors[state.policy]; ctx.fillRect(plot.x + 12, plot.y + 9, 28, 4);
  ctx.fillStyle = "#536b78"; ctx.fillText("容量加权风险", plot.x + 48, plot.y + 17);
  ctx.fillStyle = "rgba(216,138,22,.75)"; ctx.fillRect(plot.x + 178, plot.y + 9, 28, 4);
  ctx.fillStyle = "#536b78"; ctx.fillText("站级功率 归一化", plot.x + 214, plot.y + 17);
}

function riskClass(risk) { return risk >= 0.65 ? "alert" : risk >= 0.35 ? "watch" : "safe"; }

function renderBins(row) {
  const bins = state.data.bin_timeseries.filter((b) => b.policy === state.policy && b.hour === state.hour);
  $("binGrid").innerHTML = bins.map((b) => {
    return `<div class="bin ${riskClass(b.risk)}"><b>${b.bin_id}</b><span class="risk">${b.risk.toFixed(2)}</span>` +
      `<span class="reading">${b.temp_c.toFixed(1)}°C · ${b.moisture_pct.toFixed(2)}%</span>` +
      `<span class="fan ${b.fan_active ? "on" : ""}">${b.fan_active ? "风机运行" : "风机待机"}</span></div>`;
  }).join("");
}

function render() {
  const row = current();
  const agg = state.data.aggregate.find((r) => r.policy === state.policy);
  $("riskNow").textContent = row.weighted_risk.toFixed(3);
  $("powerNow").textContent = row.power_kw.toFixed(0);
  $("highRiskNow").textContent = row.high_risk_bins;
  $("fansNow").textContent = row.active_fans;
  $("energyMean").textContent = `十种子均值 ${agg.energy_kwh_mean.toFixed(0)} kWh`;
  $("capState").textContent = row.power_kw > 240 ? "超过 240 kW 上限" : "240 kW 上限内";
  $("outsideTemp").textContent = `${row.outside_temp_c.toFixed(1)} °C`;
  $("outsideRh").textContent = `${row.outside_rh_pct.toFixed(0)} %`;
  $("waitNow").textContent = `${row.max_wait_hours.toFixed(0)} 小时`;
  $("timeLabel").textContent = formatTime(row.timestamp);
  $("hourValue").textContent = state.hour;
  $("hourSlider").value = state.hour;
  const open = row.active_fans > 0;
  $("windowState").textContent = open ? "存在可用窗口" : "当前窗口关闭";
  $("windowState").classList.toggle("closed", !open);
  renderBins(row); drawGauge(row.power_kw); drawTrend();
}

async function boot() {
  state.data = await fetch("data.json").then((r) => r.json());
  $("scenarioText").textContent = state.data.meta.scenario;
  $("disclosure").textContent = state.data.meta.disclosure;
  $("policySelect").addEventListener("change", (e) => { state.policy = e.target.value; render(); });
  $("hourSlider").addEventListener("input", (e) => { state.hour = Number(e.target.value); render(); });
  $("playButton").addEventListener("click", () => {
    if (state.timer) { clearInterval(state.timer); state.timer = null; $("playButton").textContent = "播放"; return; }
    $("playButton").textContent = "暂停";
    state.timer = setInterval(() => { state.hour = (state.hour + 1) % 168; render(); }, 220);
  });
  render();
}

boot().catch((error) => {
  console.error(error);
  document.body.innerHTML = `<pre>看板数据加载失败：${error.message}</pre>`;
});
