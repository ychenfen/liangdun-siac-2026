# 粮盾

“粮盾”是面向寒地粮库的多仓温湿耦合预测与通风协同决策仿真原型，用于中国仿真创新应用大赛——数字建模与智能决策赛道。

项目使用 NASA POWER 小时级天气数据和固定随机种子生成的合成仓群，逐小时更新粮温、含水率与相对风险，并在 240 kW 站级功率上限下安排风机。项目同时提供可复现实验、离线数字孪生看板、研究报告、答辩材料和演示视频。

## 重要边界

- 仓房、容量、初始粮温、含水率、热点系数和风机配置均为合成数据。
- 风险指数、平衡水分和通风条件是用于策略比较的简化代理，不替代粮情检测、国家标准判定或真实仓储控制。
- 当前状态为本地验证完成；参赛单位、联系人、成员信息和手写签字仍待填写，尚未代表赛事官方受理或获奖。

## 目录

- `00_官方原始材料/`：赛事通知、模板和赛道要求。
- `01_作品工程/`：数据、模型、策略、实验、图表和离线看板。
- `02_制作中/`：可编辑文档、PPT、PDF、视频和附件支撑材料。
- `03_最终提交包/`：已通过本地校验的提交候选包和 SHA-256 记录。
- `MANIFEST.md`：项目状态、要求基线、交付物与验证证据。

## 复现实验

```bash
cd 01_作品工程
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m unittest discover -s src/tests -v
PYTHONPATH=src python3 src/run_experiments.py
PYTHONPATH=src python3 src/verify_results.py
python3 src/generate_figures.py
python3 src/build_dashboard_data.py
python3 -m http.server 8765 --directory web
```

浏览器打开 `http://127.0.0.1:8765` 即可查看离线决策看板。更详细的数据边界、校验项和结果说明见 [`01_作品工程/README.md`](01_作品工程/README.md)。
