# EV-TMS-PLOT
毕业设计，输入环境工况参数，输出特斯拉model y的热管理系统各部分温度变化的图
# 主程序文件夹说明
## heat_modules
文件夹内程序用于计算座舱和动力系统热负荷

# 项目辅助程序说明
## png_tree
txt转为html,png,png输出，用于查看程序的结构

## plot
生成动力系统吧和座舱产热的图

# 配置环境
pip install -r requirements.txt

# 程序逻辑
├── main.py                     # 主程序

├── simulation_engine.py        # 仿真核心逻辑

├── results_analyzer.py         # 结果数据后处理与分析

├── simulation_parameters.py    # 仿真参数加载

├── heat_vehicle_class.py       # 车辆部件计算

├── heat_cabin_class.py          # 座舱热负荷计算

├── refrigeration_cycle.py      # 制冷循环COP计算

├── plotting.py                 # 绘图模块

└── config.ini                  # 配置文件

# 编译选项
python -m nuitka --onefile --lto=yes --python-flag=-OO --mingw64 main.py

python -m nuitka --lto=yes --python-flag=-OO --mingw64 main.py
