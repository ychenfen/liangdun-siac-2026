from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = Path(os.environ.get("LIANGDUN_FIGURES_DIR", ROOT / "figures"))
PROCESSED = ROOT / "data/processed"
FONT_SCALE = float(os.environ.get("LIANGDUN_FIG_FONT_SCALE", "1"))

W, H = 1600, 900
BG = "#F4F7FA"
INK = "#102A43"
MUTED = "#627D98"
GRID = "#D9E2EC"
BLUE = "#1677B8"
TEAL = "#168C78"
ORANGE = "#E57A2D"
RED = "#C94C4C"
NAVY = "#0B1F33"
COLORS = [ORANGE, "#7A9E3A", BLUE, TEAL]
# (常规体路径, 常规体字库序号, 粗体路径, 粗体字库序号)。按顺序取第一个存在的字体，
# 便于在 macOS（PingFang）与 Linux（Noto Sans CJK）上复现；也可用环境变量指定。
FONT_CANDIDATES = [
    (
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/3419f2a427639ad8c8e139149a287865a90fa17e.asset/AssetData/PingFang.ttc",
        0,
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/3419f2a427639ad8c8e139149a287865a90fa17e.asset/AssetData/PingFang.ttc",
        2,
    ),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 2, "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 2),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0, "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),
]


def resolve_font_files() -> tuple[str, int, str, int]:
    env_regular = os.environ.get("LIANGDUN_FONT_REGULAR")
    env_bold = os.environ.get("LIANGDUN_FONT_BOLD")
    if env_regular:
        return env_regular, 0, env_bold or env_regular, 0
    for regular, r_index, bold, b_index in FONT_CANDIDATES:
        if Path(regular).exists() and Path(bold).exists():
            return regular, r_index, bold, b_index
    raise FileNotFoundError("未找到中文字体，请设置 LIANGDUN_FONT_REGULAR / LIANGDUN_FONT_BOLD")


FONT_FILES = resolve_font_files()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    scaled_size = max(1, round(size * FONT_SCALE))
    path, index = (FONT_FILES[2], FONT_FILES[3]) if bold else (FONT_FILES[0], FONT_FILES[1])
    return ImageFont.truetype(path, size=scaled_size, index=index)


def canvas(title: str, subtitle: str = "") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    draw.text((70, 42), title, font=font(44, True), fill=INK)
    if subtitle:
        draw.text((72, 103), subtitle, font=font(20), fill=MUTED)
    draw.line((70, 140, W - 70, 140), fill="#BCCCDC", width=2)
    return image, draw


def save(image: Image.Image, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    image.save(FIGURES / name, optimize=True)


def draw_axes(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], y_min: float, y_max: float, y_label: str, steps: int = 5) -> None:
    x0, y0, x1, y1 = box
    draw.line((x0, y0, x0, y1), fill=INK, width=2)
    draw.line((x0, y1, x1, y1), fill=INK, width=2)
    for step in range(steps + 1):
        y = y1 - (y1 - y0) * step / steps
        value = y_min + (y_max - y_min) * step / steps
        draw.line((x0, y, x1, y), fill=GRID, width=1)
        draw.text((x0 - 72, y - 12), f"{value:.1f}", font=font(17), fill=MUTED)
    draw.text((x0 - 70, y0 - 36), y_label, font=font(18, True), fill=INK)


def line_points(values: np.ndarray, box: tuple[int, int, int, int], y_min: float, y_max: float) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = box
    denom = max(len(values) - 1, 1)
    return [
        (
            x0 + (x1 - x0) * idx / denom,
            y1 - (float(value) - y_min) / max(y_max - y_min, 1e-9) * (y1 - y0),
        )
        for idx, value in enumerate(values)
    ]


def weather_figure() -> None:
    data = pd.read_csv(PROCESSED / "weather_hourly.csv")
    image, draw = canvas(
        "哈尔滨一周外部环境输入",
        "NASA POWER Hourly API · 2025-10-01 至 2025-10-07 · LST · 168 小时",
    )
    box1 = (145, 205, 1510, 480)
    box2 = (145, 565, 1510, 820)
    temp = data.temp_c.to_numpy()
    rh = data.rh_pct.to_numpy()
    draw_axes(draw, box1, math.floor(temp.min() / 5) * 5, math.ceil(temp.max() / 5) * 5, "气温 °C")
    draw_axes(draw, box2, 0, 100, "相对湿度 %")
    draw.line(line_points(temp, box1, math.floor(temp.min() / 5) * 5, math.ceil(temp.max() / 5) * 5), fill=ORANGE, width=5)
    draw.line(line_points(rh, box2, 0, 100), fill=BLUE, width=5)
    for day in range(8):
        x = box1[0] + (box1[2] - box1[0]) * day / 7
        draw.line((x, box1[1], x, box1[3]), fill="#CBD5E1", width=1)
        draw.line((x, box2[1], x, box2[3]), fill="#CBD5E1", width=1)
        if day < 7:
            draw.text((x + 8, 835), f"10月{day + 1}日", font=font(18), fill=MUTED)
    draw.text((1280, 218), f"最高 {temp.max():.1f}°C", font=font(21, True), fill=ORANGE)
    draw.text((1280, 578), f"最高 {rh.max():.0f}%", font=font(21, True), fill=BLUE)
    save(image, "fig_weather.png")


def bar_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, values: list[float], labels: list[str], fmt: str) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=18, fill="white", outline="#D9E2EC", width=2)
    draw.text((x0 + 22, y0 + 18), title, font=font(23, True), fill=INK)
    base = y1 - 75
    chart_top = y0 + 95
    vmax = max(values) * 1.12
    n = len(values)
    slot = (x1 - x0 - 70) / n
    for idx, (label, value) in enumerate(zip(labels, values)):
        bx0 = x0 + 42 + idx * slot + slot * 0.18
        bx1 = x0 + 42 + idx * slot + slot * 0.78
        by0 = base - (value / vmax) * (base - chart_top)
        draw.rounded_rectangle((bx0, by0, bx1, base), radius=6, fill=COLORS[idx])
        draw.text((bx0, by0 - 30), format(value, fmt), font=font(17, True), fill=INK)
        draw.text((bx0 - 6, base + 14), label, font=font(16), fill=MUTED)


def main_metrics_figure() -> None:
    agg = pd.read_csv(RESULTS / "main_aggregate.csv").set_index("policy")
    order = ["B0_RULE_UNCAPPED", "B1_FCFS", "B2_TEMP_GREEDY", "OURS"]
    labels = ["独立阈值", "先到先得", "粮温优先", "粮盾"]
    image, draw = canvas(
        "十个随机种子的主实验结果",
        "24 仓 · 168 小时 · 站级功率上限 240 kW · 数字为十个种子的均值",
    )
    bar_panel(draw, (70, 175, 790, 505), "风险暴露 累计指数小时 越低越好", [agg.loc[p, "risk_exposure_mean"] for p in order], labels, ".1f")
    bar_panel(draw, (820, 175, 1530, 505), "高风险仓时 越低越好", [agg.loc[p, "high_risk_bin_hours_mean"] for p in order], labels, ".0f")
    bar_panel(draw, (70, 535, 790, 865), "通风能耗 kWh", [agg.loc[p, "energy_kwh_mean"] for p in order], labels, ".0f")
    bar_panel(draw, (820, 535, 1530, 865), "峰值功率 kW", [agg.loc[p, "peak_power_kw_mean"] for p in order], labels, ".0f")
    save(image, "fig_main_metrics.png")


def timeseries_figure() -> None:
    data = pd.read_csv(RESULTS / "timeseries_seed0.csv")
    image, draw = canvas("种子 0 的风险与功率时序", "粮盾在站级功率上限内分配风机，并保留高湿窗口中的停机状态")
    risk_box = (145, 205, 1510, 495)
    power_box = (145, 585, 1510, 835)
    draw_axes(draw, risk_box, 0.0, 0.8, "容量加权风险")
    draw_axes(draw, power_box, 0.0, 720.0, "功率 kW")
    styles = {
        "B0_RULE_UNCAPPED": (ORANGE, "独立阈值"),
        "B1_FCFS": ("#7A9E3A", "先到先得"),
        "B2_TEMP_GREEDY": (BLUE, "粮温优先"),
        "OURS": (TEAL, "粮盾"),
    }
    for idx, (policy, (color, label)) in enumerate(styles.items()):
        subset = data[data.policy == policy]
        draw.line(line_points(subset.weighted_risk.to_numpy(), risk_box, 0.0, 0.8), fill=color, width=4)
        draw.line(line_points(subset.power_kw.to_numpy(), power_box, 0.0, 720.0), fill=color, width=3)
        lx = 930 + idx * 145
        draw.line((lx, 165, lx + 42, 165), fill=color, width=6)
        draw.text((lx + 50, 151), label, font=font(17), fill=INK)
    cap_y = power_box[3] - 240 / 720 * (power_box[3] - power_box[1])
    draw.line((power_box[0], cap_y, power_box[2], cap_y), fill=RED, width=3)
    draw.text((power_box[2] - 200, cap_y - 30), "站级上限 240 kW", font=font(17, True), fill=RED)
    save(image, "fig_timeseries.png")


def ablation_figure() -> None:
    data = pd.read_csv(RESULTS / "ablation_seed0.csv").set_index("policy")
    order = ["OURS", "OURS_NO_FORECAST", "OURS_NO_MOISTURE", "OURS_NO_FAIRNESS"]
    labels = ["完整方案", "无12小时预见", "无水分收益", "无等待公平"]
    image, draw = canvas("关键模块消融", "固定种子 0；纵轴均为越低越好")
    bar_panel(draw, (70, 190, 790, 770), "风险暴露", [data.loc[p, "risk_exposure"] for p in order], labels, ".2f")
    bar_panel(draw, (820, 190, 1530, 770), "高风险仓时", [data.loc[p, "high_risk_bin_hours"] for p in order], labels, ".0f")
    draw.text((92, 810), "说明：消融只定位模块作用，不外推为真实粮库效果。", font=font(20), fill=MUTED)
    save(image, "fig_ablation.png")


SCALE_Y_MIN, SCALE_Y_MAX = 50.0, 75.0


def scale_figure() -> None:
    data = pd.read_csv(RESULTS / "scale.csv")
    grouped = data.groupby(["n_bins", "policy"], as_index=False).agg(risk=("risk_exposure", "mean"), wait=("max_wait_hours", "mean"))
    image, draw = canvas("仓群规模扩展", "每个规模 5 个随机种子；功率上限保持 240 kW，因此 36–48 仓属于拥塞压力测试")
    risk_box = (145, 220, 1510, 760)
    draw_axes(draw, risk_box, SCALE_Y_MIN, SCALE_Y_MAX, "风险暴露（纵轴已放大，非零起点）")
    colors = {"B1_FCFS": "#7A9E3A", "B2_TEMP_GREEDY": BLUE, "OURS": TEAL}
    names = {"B1_FCFS": "先到先得", "B2_TEMP_GREEDY": "粮温优先", "OURS": "粮盾"}
    for idx, policy in enumerate(colors):
        subset = grouped[grouped.policy == policy].sort_values("n_bins")
        xvals = subset.n_bins.to_numpy()
        vals = subset.risk.to_numpy()
        points = []
        for xval, val in zip(xvals, vals):
            x = risk_box[0] + (xval - 12) / 36 * (risk_box[2] - risk_box[0])
            y = risk_box[3] - (val - SCALE_Y_MIN) / (SCALE_Y_MAX - SCALE_Y_MIN) * (risk_box[3] - risk_box[1])
            points.append((x, y))
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=colors[policy])
            draw.text((x - 18, risk_box[3] + 18), str(int(xval)), font=font(18), fill=MUTED)
        draw.line(points, fill=colors[policy], width=6)
        lx = 935 + idx * 170
        draw.line((lx, 170, lx + 45, 170), fill=colors[policy], width=6)
        draw.text((lx + 55, 156), names[policy], font=font(18), fill=INK)
    draw.text((650, 820), "仓数", font=font(20, True), fill=INK)
    save(image, "fig_scale.png")


def bins_figure() -> None:
    data = pd.read_csv(RESULTS / "raw/final_bins_OURS.csv")
    image, draw = canvas("粮盾方案最终仓群状态", "固定种子 0；颜色表示相对风险指数，仓号下方为粮温与水分")
    cols, rows = 6, 4
    x0, y0 = 85, 185
    cell_w, cell_h = 235, 155
    for idx, row in data.iterrows():
        col, r = idx % cols, idx // cols
        cx0, cy0 = x0 + col * cell_w, y0 + r * cell_h
        risk = float(row.final_risk)
        if risk < 0.2:
            color = "#CDEFE6"
        elif risk < 0.4:
            color = "#F7E5A8"
        elif risk < 0.65:
            color = "#F3B27A"
        else:
            color = "#E98787"
        draw.rounded_rectangle((cx0, cy0, cx0 + 205, cy0 + 125), radius=15, fill=color, outline="#9FB3C8", width=2)
        draw.text((cx0 + 15, cy0 + 12), row.bin_id, font=font(23, True), fill=INK)
        draw.text((cx0 + 15, cy0 + 50), f"风险 {risk:.3f}", font=font(18), fill=INK)
        draw.text((cx0 + 15, cy0 + 82), f"{row.final_temp_c:.1f}°C  {row.final_moisture_pct:.2f}%", font=font(17), fill=MUTED)
    save(image, "fig_bins.png")


def architecture_figure() -> None:
    image, draw = canvas("粮盾系统闭环", "公开天气输入、合成粮情、滚动决策与执行反馈在同一结果链中")
    boxes = [
        (90, 240, 360, 430, "数据底座", "NASA POWER 天气\n合成仓群与粮情\n参数与随机种子"),
        (430, 240, 700, 430, "温湿状态模型", "粮温与水分更新\n热点修正\n相对风险指数"),
        (770, 240, 1040, 430, "通风窗口", "温差约束\n高湿禁入\n水分收益判断"),
        (1110, 240, 1380, 430, "协同调度", "12 小时天气预见\n240 kW 功率上限\n等待公平与优先级"),
        (430, 570, 700, 760, "执行记录", "风机功率与能耗\n风险暴露与仓时\n约束违例日志"),
        (770, 570, 1040, 760, "数字孪生看板", "仓群状态回放\n策略切换\n结果与证据边界"),
    ]
    for x0, y0, x1, y1, title, body in boxes:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=20, fill="white", outline=BLUE, width=3)
        draw.text((x0 + 22, y0 + 18), title, font=font(25, True), fill=BLUE)
        draw.multiline_text((x0 + 22, y0 + 68), body, font=font(18), fill=INK, spacing=10)
    arrows = [((360, 335), (430, 335)), ((700, 335), (770, 335)), ((1040, 335), (1110, 335)), ((1245, 430), (905, 570)), ((770, 665), (700, 665)), ((565, 570), (225, 430))]
    for start, end in arrows:
        draw.line((start, end), fill=TEAL, width=6)
        ex, ey = end
        draw.polygon([(ex, ey), (ex - 16 if ex >= start[0] else ex + 16, ey - 10), (ex - 16 if ex >= start[0] else ex + 16, ey + 10)], fill=TEAL)
    draw.text((620, 810), "每小时滚动更新", font=font(22, True), fill=TEAL)
    save(image, "fig_architecture.png")


def write_summary() -> None:
    agg = pd.read_csv(RESULTS / "main_aggregate.csv").set_index("policy")
    ours = agg.loc["OURS"]
    temp = agg.loc["B2_TEMP_GREEDY"]
    fcfs = agg.loc["B1_FCFS"]
    b0 = agg.loc["B0_RULE_UNCAPPED"]
    summary = {
        "ours": ours.to_dict(),
        "relative_to_temp_greedy_pct": {
            "risk_exposure": float((ours.risk_exposure_mean / temp.risk_exposure_mean - 1) * 100),
            "high_risk_bin_hours": float((ours.high_risk_bin_hours_mean / temp.high_risk_bin_hours_mean - 1) * 100),
            "energy_kwh": float((ours.energy_kwh_mean / temp.energy_kwh_mean - 1) * 100),
            "final_weighted_risk": float((ours.final_weighted_risk_mean / temp.final_weighted_risk_mean - 1) * 100),
        },
        "relative_to_fcfs_pct": {
            "risk_exposure": float((ours.risk_exposure_mean / fcfs.risk_exposure_mean - 1) * 100),
            "high_risk_bin_hours": float((ours.high_risk_bin_hours_mean / fcfs.high_risk_bin_hours_mean - 1) * 100),
            "energy_kwh": float((ours.energy_kwh_mean / fcfs.energy_kwh_mean - 1) * 100),
        },
        "uncapped_baseline": {
            "peak_power_kw": float(b0.peak_power_kw_mean),
            "cap_violation_hours_mean": float(b0.cap_violation_hours_mean),
        },
        "boundary": "多种子合成仓群与简化温湿模型；不得解读为真实粮库控制效果。",
    }
    (RESULTS / "result_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    weather_figure()
    main_metrics_figure()
    timeseries_figure()
    ablation_figure()
    scale_figure()
    bins_figure()
    architecture_figure()
    write_summary()
    print("generated", len(list(FIGURES.glob("*.png"))), "figures")


if __name__ == "__main__":
    main()
