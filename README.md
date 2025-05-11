# EV-TMS-PLOT
毕业设计，用于输出随速度时间变化，特斯拉model y的热管理系统各部分温度变化的图

# 配置环境
pip install -r requirements.txt

# 程序逻辑
├── main.py                     # 主程序入口和流程编排
├── simulation_engine.py        # 仿真核心逻辑 (SimulationEngine 类)
├── results_analyzer.py         # 结果数据后处理与分析
├── simulation_parameters.py    # 仿真参数加载
├── heat_vehicle.py             # 车辆部件产热计算
├── heat_cabin.py               # 座舱热负荷计算
├── refrigeration_cycle.py      # 制冷循环COP计算
├── plotting.py                 # 绘图模块
└── config.ini                  # 配置文件
