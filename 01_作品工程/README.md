# 粮盾

面向寒地粮库的多仓温湿耦合预测与通风协同决策仿真原型。

## 数据边界

- 外部环境：NASA POWER Hourly API 的 2025-10-01 至 2025-10-07 小时级气温、相对湿度和风速，坐标 126.535°E、45.804°N，时间标准为 LST。
- 仓房、容量、初始粮温、含水率、热点系数和风机配置均为合成数据。
- 风险指数和平衡水分公式是用于方案比较的简化代理，不替代粮情检测、国家标准判定或真实仓储控制。

## 运行

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m unittest discover -s src/tests -v
PYTHONPATH=src python3 src/run_experiments.py
PYTHONPATH=src python3 src/verify_results.py
PYTHONPATH=src python3 src/generate_figures.py
python3 src/build_dashboard_data.py
python3 -m http.server 8765 --directory web
```

运行后生成多随机种子主实验、消融、仓数扩展和天气扰动结果。所有文稿、图表和看板必须从 `results/` 读取，不得手工改写关键数字。

浏览器打开 `http://127.0.0.1:8765` 可查看离线数字孪生看板。看板默认回放随机种子 0，全部数据由脚本从实验 CSV 固化到 `web/data.json`。

## 结果核对

主实验为 24 仓、168 小时、10 个随机种子，站级功率上限为 240 kW。`verify_results.py` 会检查：

- 四种策略和 40 行主实验结果是否齐全；
- 策略时序是否为 168×4 行，仓级时序是否为 168×24×4 行；
- 仓级活动风机数是否与站级时序一致；
- 天气原始文件哈希是否为 `381d0b056d623b965c80645c6a165495f13ecb7f556f2aec156bcef4f00fac80`；
- 三种受约束策略是否保持零功率越限与零不合规通风。

十种子均值中，粮盾的风险暴露为 58.7023，高风险仓时为 487.3，能耗为 11681.5 kWh，峰值功率为 238.7 kW。相对粮温优先策略，高风险仓时下降 12.15%，能耗下降 4.37%；末时点加权风险高 0.90%，这是方案的明确权衡。

## 文件说明

- `data/raw/`：NASA POWER 原始响应，只读输入；
- `data/processed/`：天气表和固定随机种子生成的仓群；
- `src/`：状态模型、策略、仿真、实验、验证和看板数据构建脚本；
- `results/`：主实验、消融、规模扩展、天气扰动与仓级时序；
- `figures/`：从结果文件生成的论文图；
- `web/`：无需联网的离线看板。

NASA POWER Hourly API 文档：<https://power.larc.nasa.gov/docs/services/api/temporal/hourly/>。
