# simulation_parameters.py
# 该模块负责从配置文件 (config.ini) 加载所有仿真所需的参数，
# 并进行一些必要的类型转换、默认值处理以及派生参数的计算。
# 它是整个仿真程序参数配置的中心。

import configparser # 导入用于读取和解析 .ini 配置文件的库
from heat_cabin_class import rho_air_func # 从 heat_cabin_class 模块导入 rho_air_func 函数，用于计算座舱空气密度

# --- 0. 初始化 ConfigParser 并读取 INI 配置文件 ---
config = configparser.ConfigParser() # 创建一个 ConfigParser 对象
config_file_path = 'config.ini' # 定义配置文件的路径，确保 config.ini 与此脚本在同一目录或提供正确路径

# 尝试读取配置文件
try:
    # 使用 utf-8 编码读取，以支持 .ini 文件中的中文注释
    if not config.read(config_file_path, encoding='utf-8'):
        # 如果 config.read 返回空列表（表示没有文件被成功读取）
        raise FileNotFoundError(f"配置文件 '{config_file_path}' 未找到或为空。")
    print(f"已成功从 '{config_file_path}' 加载配置。")
except FileNotFoundError as e:
    print(f"错误: {e}。请确保 '{config_file_path}' 文件存在且可读。")
    # 如果文件找不到，程序可能会依赖下面定义的默认值（如果提供了），或者在后续访问缺失参数时出错。
    # 根据需要，可以选择在这里退出程序，例如使用: exit() 或 raise
except configparser.Error as e: # 捕获解析 .ini 文件时可能发生的其他错误
    print(f"错误: 解析配置文件 '{config_file_path}' 时发生错误: {e}")
    # exit() # 或者 raise

# --- 辅助函数：从配置文件获取值，带类型转换和备用默认值 ---
def get_config_value(section, key, type_func=str, default=None):
    """
    从已加载的配置对象中获取指定 section 和 key 的值。
    如果获取失败或类型转换失败，则使用提供的默认值（如果default不为None）。
    参数:
        section (str): INI 文件中的节名 (例如 '[Simulation]')。
        key (str): 该节下的键名。
        type_func (function): 用于将获取到的字符串值转换为目标类型的函数 (例如 float, int, str)。
        default (any, optional): 如果在配置文件中找不到对应的键或值无效，则返回此默认值。
                                如果为 None 且找不到值，则会引发错误。
    返回:
        转换后的配置值或默认值。
    异常:
        如果键未找到且未提供默认值，或者类型转换失败且未提供默认值，则可能重新引发异常。
    """
    try:
        # 尝试从配置对象中获取原始字符串值，并使用 type_func 进行转换
        return type_func(config.get(section, key))
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
        # 处理获取失败（节不存在、键不存在）或类型转换失败 (ValueError) 的情况
        if default is not None: # 如果提供了默认值
            print(f"警告: 在节 '[{section}]' 中的配置值 '{key}' 未找到或无效。将使用默认值: {default}。错误: {e}")
            return default # 返回默认值
        else: # 如果没有提供默认值
            print(f"错误: 在节 '[{section}]' 中的配置值 '{key}' 未找到或无效，且未提供默认值。错误: {e}")
            raise # 重新引发异常，或进行更优雅的错误处理 (如退出程序)

# --- 1. 读取制冷循环输入参数 ---
# 从 '[RefrigerationCycle]' 节读取制冷剂循环的各个状态点温度和制冷剂类型
# T_suc_C_in: 压缩机吸气口实际过热温度 (°C)，默认值 15
T_suc_C_in = get_config_value('RefrigerationCycle', 'T_suc_C_in', float, 15)
# T_cond_sat_C_in: 冷凝器中制冷剂的饱和冷凝温度 (°C)，默认值 45
T_cond_sat_C_in = get_config_value('RefrigerationCycle', 'T_cond_sat_C_in', float, 45)
# T_be_C_in: 进入膨胀阀之前的制冷剂温度 (冷凝器出口过冷温度) (°C)，默认值 42
T_be_C_in = get_config_value('RefrigerationCycle', 'T_be_C_in', float, 42)
# T_evap_sat_C_in: 蒸发器中制冷剂的饱和蒸发温度 (°C)，默认值 5
T_evap_sat_C_in = get_config_value('RefrigerationCycle', 'T_evap_sat_C_in', float, 5)
# T_dis_C_in: 压缩机排气口的实际制冷剂温度 (°C)，默认值 70
T_dis_C_in = get_config_value('RefrigerationCycle', 'T_dis_C_in', float, 70)
# REFRIGERANT_TYPE: 制冷剂类型 (字符串，例如 'R134a', 'R1234yf')，默认值 'R1234yf'
REFRIGERANT_TYPE = get_config_value('RefrigerationCycle', 'REFRIGERANT_TYPE', str, 'R1234yf')

# --- 2. 读取仿真参数 ---
# 从 '[Simulation]' 节读取仿真相关的全局参数
# T_ambient: 环境温度 (°C)，默认值 35.0
T_ambient = get_config_value('Simulation', 'T_ambient', float, 35.0)
# sim_duration: 仿真总时长 (s)，默认值 2100
sim_duration = get_config_value('Simulation', 'sim_duration', int, 2100)
# dt: 仿真时间步长 (s)，默认值 1
dt = get_config_value('Simulation', 'dt', int, 1)

# --- 读取绘图参数 ---
# 从 '[Plotting]' 节读取用于生成图表的参数
# figure_width_inches: 图表宽度 (英寸)，默认值 18
figure_width_inches = get_config_value('Plotting', 'figure_width_inches', float, 18)
# figure_height_inches: 图表高度 (英寸)，默认值 8
figure_height_inches = get_config_value('Plotting', 'figure_height_inches', float, 8)
# figure_dpi: 图表分辨率 (每英寸点数, DPI)，默认值 300
figure_dpi = get_config_value('Plotting', 'figure_dpi', int, 300)
# legend_font_size: 图例字体大小 (points)，默认值 10
legend_font_size = get_config_value('Plotting', 'legend_font_size', int, 10)
# axis_label_font_size: 坐标轴标签字体大小 (points)，默认值 12
axis_label_font_size = get_config_value('Plotting', 'axis_label_font_size', int, 12)
# tick_label_font_size: 刻度标签字体大小 (points)，默认值 10
tick_label_font_size = get_config_value('Plotting', 'tick_label_font_size', int, 10)
# title_font_size: 图表标题字体大小 (points)，默认值 14
title_font_size = get_config_value('Plotting', 'title_font_size', int, 14)

# --- 3. 读取速度剖面参数 ---
# 从 '[SpeedProfile]' 节读取车辆行驶速度相关的参数
# v_start: 车辆初始速度 (km/h)，默认值 60.0
v_start = get_config_value('SpeedProfile', 'v_start', float, 60.0)
# v_end: 车辆最终速度 (km/h)，默认值 120.0
v_end = get_config_value('SpeedProfile', 'v_end', float, 120.0)
# ramp_up_time_sec: 从初始速度加速到最终速度所需的时间 (s)，默认值 300
ramp_up_time_sec = get_config_value('SpeedProfile', 'ramp_up_time_sec', int, 300)

# --- 4. 读取车辆及部件参数 ---
# 从 '[Vehicle]' 节读取车辆本身以及各部件的物理参数

# m_vehicle: 车辆总质量 (kg)，默认值 2503
m_vehicle = get_config_value('Vehicle', 'm_vehicle', float, 2503)

# mass_motor: 电机质量 (kg)，默认值 60
mass_motor = get_config_value('Vehicle', 'mass_motor', float, 60)
# cp_motor: 电机比热容 (J/kg·K)，默认值 500
cp_motor = get_config_value('Vehicle', 'cp_motor', float, 500)
# mc_motor: 电机热容 (质量 * 比热容) (J/K)
mc_motor = mass_motor * cp_motor

# mass_inverter: 逆变器质量 (kg)，默认值 15
mass_inverter = get_config_value('Vehicle', 'mass_inverter', float, 15)
# cp_inverter: 逆变器比热容 (J/kg·K)，默认值 800
cp_inverter = get_config_value('Vehicle', 'cp_inverter', float, 800)
# mc_inverter: 逆变器热容 (J/K)
mc_inverter = mass_inverter * cp_inverter

# mass_battery: 电池质量 (kg)，默认值 500
mass_battery = get_config_value('Vehicle', 'mass_battery', float, 500)
# cp_battery: 电池比热容 (J/kg·K)，默认值 1000
cp_battery = get_config_value('Vehicle', 'cp_battery', float, 1000)
# mc_battery: 电池热容 (J/K)
mc_battery = mass_battery * cp_battery

# cabin_volume: 座舱体积 (m^3)，默认值 3.5
cabin_volume = get_config_value('Vehicle', 'cabin_volume', float, 3.5)
# cp_air: 空气比热容 (J/kg·K)，默认值 1005
cp_air = get_config_value('Vehicle', 'cp_air', float, 1005)
# _T_cabin_avg_for_rho: 用于计算座舱平均空气密度的参考温度 (°C)，默认值 28
_T_cabin_avg_for_rho = get_config_value('Vehicle', '_T_cabin_avg_for_rho', float, 28)
# rho_air_cabin_avg: 座舱平均空气密度 (kg/m^3)，根据参考温度计算
rho_air_cabin_avg = rho_air_func(_T_cabin_avg_for_rho)
# mc_cabin: 座舱空气热容 (J/K)
mc_cabin = cabin_volume * rho_air_cabin_avg * cp_air

# cp_coolant: 冷却液比热容 (J/kg·K)，默认值 3400
cp_coolant = get_config_value('Vehicle', 'cp_coolant', float, 3400)
# rho_coolant: 冷却液密度 (kg/m^3)，默认值 1050
rho_coolant = get_config_value('Vehicle', 'rho_coolant', float, 1050)
# coolant_volume_liters: 冷却液容量 (L)，默认值 10
coolant_volume_liters = get_config_value('Vehicle', 'coolant_volume_liters', float, 10)
# mass_coolant: 冷却液质量 (kg)，通过体积和密度计算 (注意单位转换 L -> m^3)
mass_coolant = coolant_volume_liters * rho_coolant / 1000 # 1 m^3 = 1000 L
# mc_coolant: 冷却液热容 (J/K)
mc_coolant = mass_coolant * cp_coolant

# UA值 (总传热系数 * 换热面积) (W/K)
# UA_motor_coolant: 电机与冷却液之间的UA值，默认值 500
UA_motor_coolant = get_config_value('Vehicle', 'UA_motor_coolant', float, 500)
# UA_inv_coolant: 逆变器与冷却液之间的UA值，默认值 300
UA_inv_coolant = get_config_value('Vehicle', 'UA_inv_coolant', float, 300)
# UA_batt_coolant: 电池与冷却液之间的UA值，默认值 1000
UA_batt_coolant = get_config_value('Vehicle', 'UA_batt_coolant', float, 1000)
# UA_coolant_chiller: 冷却液与动力总成冷却器(Chiller的蒸发器侧)之间的UA值，默认值 1500
UA_coolant_chiller = get_config_value('Vehicle', 'UA_coolant_chiller', float, 1500)
# UA_cabin_evap: 座舱空气与空调蒸发器之间的UA值，默认值 2000
UA_cabin_evap = get_config_value('Vehicle', 'UA_cabin_evap', float, 2000)
# UA_coolant_LCC: 冷却液与低温冷凝器(LCC)之间的UA值，默认值 1800
UA_coolant_LCC = get_config_value('Vehicle', 'UA_coolant_LCC', float, 1800)

# --- 读取新的外部散热器 (LTR - Low Temperature Radiator) 参数 ---
# UA_LTR_max: LTR的最大UA值 (W/K)，对应最高风扇档位或最佳工况，默认值 2000
UA_LTR_max = get_config_value('Vehicle', 'UA_LTR_max', float, 2000)
# LTR_effectiveness_levels: LTR效能/风扇档位的数量 (整数)，默认值 3
LTR_effectiveness_levels = get_config_value('Vehicle', 'LTR_effectiveness_levels', int, 3)

# LTR_fan_power_levels_str: 每个档位LTR风扇的功耗 (W)，以逗号分隔的字符串，默认 "0, 50, 100, 200"
LTR_fan_power_levels_str = get_config_value('Vehicle', 'LTR_fan_power_levels', str, '0, 50, 100, 200')
# LTR_fan_power_levels: 将字符串转换为浮点数列表
LTR_fan_power_levels = [float(x.strip()) for x in LTR_fan_power_levels_str.split(',')]

# LTR_UA_values_at_levels_str: 每个档位LTR的实际UA值 (W/K)，以逗号分隔的字符串，默认 "200, 800, 1500, 2000"
LTR_UA_values_at_levels_str = get_config_value('Vehicle', 'LTR_UA_values_at_levels', str, '200, 800, 1500, 2000')
# LTR_UA_values_at_levels: 将字符串转换为浮点数列表
LTR_UA_values_at_levels = [float(x.strip()) for x in LTR_UA_values_at_levels_str.split(',')]

# LTR_coolant_temp_thresholds_str: LTR档位切换的冷却液温度阈值 (°C)，以逗号分隔，默认 "45, 55" 或 "40, 50, 60"
# 注意：这里重复读取了 LTR_coolant_temp_thresholds，后一个会覆盖前一个。通常应只有一个。
LTR_coolant_temp_thresholds_str = get_config_value('Vehicle', 'LTR_coolant_temp_thresholds', str, '45, 55') # 旧的默认值
LTR_coolant_temp_thresholds = [float(x.strip()) for x in LTR_coolant_temp_thresholds_str.split(',')]
# 下面这行会覆盖上面读取的 LTR_coolant_temp_thresholds，使用 config.ini 中的值或 "40, 50, 60" 作为默认
LTR_coolant_temp_thresholds_str = get_config_value('Vehicle', 'LTR_coolant_temp_thresholds', str, '40, 50, 60')
LTR_coolant_temp_thresholds = [float(x.strip()) for x in LTR_coolant_temp_thresholds_str.split(',')]


# --- LTR 参数的校验 ---
# 校验风扇功率等级数量是否与定义的档位数匹配
if len(LTR_fan_power_levels) != LTR_effectiveness_levels:
    raise ValueError(f"配置错误: LTR_fan_power_levels 的数量 ({len(LTR_fan_power_levels)}) 必须与 LTR_effectiveness_levels ({LTR_effectiveness_levels}) 匹配。")
# 校验UA值等级数量是否与定义的档位数匹配
if len(LTR_UA_values_at_levels) != LTR_effectiveness_levels:
    raise ValueError(f"配置错误: LTR_UA_values_at_levels 的数量 ({len(LTR_UA_values_at_levels)}) 必须与 LTR_effectiveness_levels ({LTR_effectiveness_levels}) 匹配。")
# 校验温度阈值的数量是否比档位数少1 (N个档位有N-1个切换阈值)
if len(LTR_coolant_temp_thresholds) != LTR_effectiveness_levels - 1:
     raise ValueError(f"配置错误: LTR_coolant_temp_thresholds 的数量 ({len(LTR_coolant_temp_thresholds)}) 必须比 LTR_effectiveness_levels ({LTR_effectiveness_levels}) 少一个。")

# 确保温度阈值是按非递减顺序排列的 (允许相等，但通常应递增)
if not all(LTR_coolant_temp_thresholds[i] <= LTR_coolant_temp_thresholds[i+1] for i in range(len(LTR_coolant_temp_thresholds)-1)):
    raise ValueError("配置错误: LTR_coolant_temp_thresholds 必须按非递减顺序排列。")

# 可选校验：风扇功率和UA值是否也按非递减顺序 (通常是的，档位越高，功率/UA越大)
if not all(LTR_fan_power_levels[i] <= LTR_fan_power_levels[i+1] for i in range(len(LTR_fan_power_levels)-1)):
     print("警告: LTR_fan_power_levels 不是按非递减顺序排列。请确认这是期望的行为。")
if not all(LTR_UA_values_at_levels[i] <= LTR_UA_values_at_levels[i+1] for i in range(len(LTR_UA_values_at_levels)-1)):
     print("警告: LTR_UA_values_at_levels 不是按非递减顺序排列。请确认这是期望的行为。")
# LTR_hysteresis_offset: LTR档位控制的滞环温度 (°C)，用于防止频繁切换，默认值 1.0
LTR_hysteresis_offset = get_config_value('Vehicle', 'LTR_hysteresis_offset', float, 1.0)
print(f"LTR 滞环偏移: {LTR_hysteresis_offset}°C")


# 座舱相关参数
# N_passengers: 乘客人数 (整数)，默认值 2
N_passengers = get_config_value('Vehicle', 'N_passengers', int, 2)
# v_air_in_mps: 新风入口速度或座舱内部等效空气流速 (m/s)，默认值 0.5
v_air_in_mps = get_config_value('Vehicle', 'v_air_in_mps', float, 0.5)
# W_out_summer: 夏季车外空气湿度 (kg_water/kg_dry_air)，默认值 0.0133
W_out_summer = get_config_value('Vehicle', 'W_out_summer', float, 0.0133)
# W_in_target: 座舱目标湿度 (kg_water/kg_dry_air)，默认值 0.0100
W_in_target = get_config_value('Vehicle', 'W_in_target', float, 0.0100)
# I_solar_summer: 夏季太阳辐射强度 (W/m²)，默认值 800
I_solar_summer = get_config_value('Vehicle', 'I_solar_summer', float, 800)
# R_body: 车身综合热阻 (m²·K/W)，默认值 0.60
R_body = get_config_value('Vehicle', 'R_body', float, 0.60)
# R_glass: 玻璃综合热阻 (m²·K/W)，默认值 0.009
R_glass = get_config_value('Vehicle', 'R_glass', float, 0.009)
# A_body: 车身面积 (m²)，默认值 12
A_body = get_config_value('Vehicle', 'A_body', float, 12)
# A_glass: 玻璃总面积 (m²)，默认值 4
A_glass = get_config_value('Vehicle', 'A_glass', float, 4)
# A_glass_sun_factor: 玻璃受太阳辐射的有效面积比例因子 (无量纲)，默认值 0.4
A_glass_sun_factor = get_config_value('Vehicle', 'A_glass_sun_factor', float, 0.4)
# A_glass_sun: 玻璃受太阳辐射的有效面积 (m²)，通过总玻璃面积和比例因子计算
A_glass_sun = A_glass * A_glass_sun_factor
# SHGC: 太阳得热系数 (Solar Heat Gain Coefficient) (无量纲)，默认值 0.50
SHGC = get_config_value('Vehicle', 'SHGC', float, 0.50)
# fresh_air_fraction: 新风比例 (占总需求新风量的百分比, 0.0 到 1.0)，默认值 0.10
fresh_air_fraction = get_config_value('Vehicle', 'fresh_air_fraction', float, 0.10)


# --- 5. 读取目标温度和控制参数 ---
# 从 '[TargetsAndControl]' 节读取各部件的目标温度和控制策略参数
# T_motor_target: 电机目标温度 (°C)，默认值 45.0
T_motor_target = get_config_value('TargetsAndControl', 'T_motor_target', float, 45.0)
# T_inv_target: 逆变器目标温度 (°C)，默认值 45.0
T_inv_target = get_config_value('TargetsAndControl', 'T_inv_target', float, 45.0)
# T_batt_target_low: 电池目标温度下限 (°C)，用于停止Chiller冷却，默认值 30.0
T_batt_target_low = get_config_value('TargetsAndControl', 'T_batt_target_low', float, 30.0)
# T_batt_target_high: 电池目标温度上限 (°C)，用于启动Chiller冷却，默认值 35.0
T_batt_target_high = get_config_value('TargetsAndControl', 'T_batt_target_high', float, 35.0)
# T_cabin_target: 座舱目标温度 (°C)，默认值 26.0
T_cabin_target = get_config_value('TargetsAndControl', 'T_cabin_target', float, 26.0)
# hysteresis_band: 温度控制的滞环带宽 (°C)，用于动力总成Chiller控制，默认值 2.5
hysteresis_band = get_config_value('TargetsAndControl', 'hysteresis_band', float, 2.5)
# max_chiller_cool_power: 动力总成冷却器(Chiller)最大制冷功率 (W)，默认值 4000
max_chiller_cool_power = get_config_value('TargetsAndControl', 'max_chiller_cool_power', float, 4000)

# 当部件达到目标温度后，散热器(LTR)的效能降低因子 (0.0 到 1.0, 1.0 表示全功率)
# radiator_effectiveness_at_target: 当所有被控部件温度都低于或等于其目标时，LTR的效能因子，默认值 0.3
radiator_effectiveness_at_target = get_config_value('TargetsAndControl', 'radiator_effectiveness_at_target', float, 0.3)
# 当部件温度远低于目标温度时（例如，低于 T_stop_cool），散热器(LTR)的效能进一步降低因子
# radiator_effectiveness_below_stop_cool: 当所有被控部件温度都低于其停止冷却阈值时，LTR的效能因子，默认值 0.1
radiator_effectiveness_below_stop_cool = get_config_value('TargetsAndControl', 'radiator_effectiveness_below_stop_cool', float, 0.1)


# --- 新的多级座舱冷却控制参数 ---
# cabin_cooling_power_levels_str: 座舱冷却功率等级 (W)，以逗号分隔的字符串，默认 "0,4000"
cabin_cooling_power_levels_str = get_config_value('TargetsAndControl', 'cabin_cooling_power_levels', str, '0,4000')
# cabin_cooling_power_levels: 将字符串转换为浮点数列表
cabin_cooling_power_levels = [float(x.strip()) for x in cabin_cooling_power_levels_str.split(',')]

# cabin_cooling_temp_thresholds_str: 座舱冷却温度阈值 (°C)，以逗号分隔，用于切换功率等级，默认 "25.0,100.0"
# 当座舱温度低于某个阈值时，使用对应的功率等级。
cabin_cooling_temp_thresholds_str = get_config_value('TargetsAndControl', 'cabin_cooling_temp_thresholds', str, '25.0,100.0')
# cabin_cooling_temp_thresholds: 将字符串转换为浮点数列表
cabin_cooling_temp_thresholds = [float(x.strip()) for x in cabin_cooling_temp_thresholds_str.split(',')]

# 校验座舱冷却控制参数的有效性
if not cabin_cooling_power_levels: # 功率等级列表不能为空
    raise ValueError("配置错误: 'cabin_cooling_power_levels' 不能为空。")
if len(cabin_cooling_power_levels) != len(cabin_cooling_temp_thresholds): # 功率等级数量必须与温度阈值数量相同
    raise ValueError("配置错误: 'cabin_cooling_power_levels' 和 'cabin_cooling_temp_thresholds' 必须有相同数量的条目。")
# 温度阈值必须严格递增排列
for i in range(len(cabin_cooling_temp_thresholds) - 1):
    if cabin_cooling_temp_thresholds[i] >= cabin_cooling_temp_thresholds[i+1]:
        raise ValueError("配置错误: 'cabin_cooling_temp_thresholds' 必须按严格递增顺序排列。")

# --- 6. 读取效率参数 ---
# 从 '[Efficiency]' 节读取各部件的效率和电池特性参数
# eta_motor: 电机效率 (无量纲, 0.0 到 1.0)，默认值 0.95
eta_motor = get_config_value('Efficiency', 'eta_motor', float, 0.95)
# eta_inv: 逆变器效率 (无量纲, 0.0 到 1.0)，默认值 0.985
eta_inv = get_config_value('Efficiency', 'eta_inv', float, 0.985)
# u_batt: 电池工作电压 (V)，默认值 340
u_batt = get_config_value('Efficiency', 'u_batt', float, 340)
# R_int_batt: 电池等效内阻 (Ω)，默认值 0.05
R_int_batt = get_config_value('Efficiency', 'R_int_batt', float, 0.05)
# eta_comp_drive: 压缩机驱动效率 (包括电机和机械传动)，默认值 0.85
eta_comp_drive = get_config_value('Efficiency', 'eta_comp_drive', float, 0.85)

# --- 7. 读取初始条件参数 ---
# 从 '[InitialConditions]' 节读取各部件初始温度相对于环境温度的偏移量
# T_motor_init_offset: 电机初始温度偏移量 (°C)，默认值 5
T_motor_init_offset = get_config_value('InitialConditions', 'T_motor_init_offset', float, 5)
# T_inv_init_offset: 逆变器初始温度偏移量 (°C)，默认值 5
T_inv_init_offset = get_config_value('InitialConditions', 'T_inv_init_offset', float, 5)
# T_batt_init_offset: 电池初始温度偏移量 (°C)，默认值 2
T_batt_init_offset = get_config_value('InitialConditions', 'T_batt_init_offset', float, 2)
# T_cabin_init_offset: 座舱初始温度偏移量 (°C)，默认值 0
T_cabin_init_offset = get_config_value('InitialConditions', 'T_cabin_init_offset', float, 0)
# T_coolant_init_offset: 冷却液初始温度偏移量 (°C)，默认值 2
T_coolant_init_offset = get_config_value('InitialConditions', 'T_coolant_init_offset', float, 2)

# 计算各部件的绝对初始温度 (°C)
T_motor_init = T_ambient + T_motor_init_offset
T_inv_init = T_ambient + T_inv_init_offset
T_batt_init = T_ambient + T_batt_init_offset
T_cabin_init = T_ambient + T_cabin_init_offset # 这是基于偏移量的初始座舱温度
T_coolant_init = T_ambient + T_coolant_init_offset

# 如果配置文件中显式定义了座舱的绝对初始温度 'T_cabin_init'，则覆盖上面基于偏移量计算的值
if config.has_option('InitialConditions', 'T_cabin_init'):
    T_cabin_init = get_config_value('InitialConditions', 'T_cabin_init', float, T_cabin_init)
    print(f"信息: 使用来自 config.ini 的绝对初始座舱温度: {T_cabin_init}°C")


# --- 8. 派生参数计算 ---
# 基于已加载的参数计算一些用于控制逻辑的派生阈值

# 动力总成部件停止Chiller冷却的温度阈值 (°C)
# 通常是目标温度减去滞环带宽，以防止Chiller在目标温度附近频繁启停
T_motor_stop_cool = T_motor_target - hysteresis_band
T_inv_stop_cool = T_inv_target - hysteresis_band
# 电池停止Chiller冷却的阈值设为其目标温度下限
T_batt_stop_cool = T_batt_target_low

# T_evap_sat_for_UA_calc: 用于计算动力总成Chiller与冷却液之间UA值换热的制冷剂蒸发饱和温度 (°C)
# 这里直接使用了从配置文件读取的蒸发器饱和蒸发温度输入值
T_evap_sat_for_UA_calc = T_evap_sat_C_in

# --- 配置加载结束 ---
print("所有参数已加载。")
# 打印一些关键的配置信息以供核对
print(f"绘图设置: 尺寸=({figure_width_inches}, {figure_height_inches}), DPI={figure_dpi}, 图例字号={legend_font_size}, 轴标签字号={axis_label_font_size}, 刻度字号={tick_label_font_size}, 标题字号={title_font_size}")
print(f"座舱冷却等级 (W): {cabin_cooling_power_levels}")
print(f"座舱冷却上限温度阈值 (°C): {cabin_cooling_temp_thresholds}")
print(f"目标温度下散热器效能: {radiator_effectiveness_at_target}")
print(f"停止冷却下散热器效能: {radiator_effectiveness_below_stop_cool}")
print(f"LCC UA值: {UA_coolant_LCC} W/K")
print(f"LTR 最大UA值: {UA_LTR_max} W/K")
print(f"LTR 等级: {LTR_effectiveness_levels}, 阈值: {LTR_coolant_temp_thresholds}")