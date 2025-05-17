# simulation_engine.py
# 该模块负责执行车辆热管理的动态仿真。
# 它将车辆的各个子系统（动力总成、座舱、热管理系统）模型化，
# 并在定义的时间跨度内，以离散的时间步长模拟它们之间的相互作用及与环境的热交换。

import numpy as np  # 导入NumPy库，用于高效的数值计算，特别是数组操作
import heat_vehicle as hv # 导入自定义的 heat_vehicle 模块，用于计算动力系统相关的产热和功率需求
from heat_cabin_class import CabinHeatCalculator # 导入自定义的 heat_cabin_class 模块中的 CabinHeatCalculator 类，用于计算座舱热负荷

class DataManager:
    """
    DataManager 类：
    管理所有仿真过程中的数据，包括输入参数、时间序列、以及各物理量的历史记录数组。
    它负责初始化存储空间，并在仿真结束后打包结果。
    """
    def __init__(self, sp):
        """
        初始化 DataManager 对象。
        参数:
            sp: simulation_parameters 模块的实例，包含了从配置文件加载的所有仿真参数。
        """
        self.sp = sp  # 存储仿真参数对象的引用
        # 计算总的仿真步数，基于总仿真时长和时间步长 dt
        # 加1是为了存储初始状态 (t=0) 以及之后 n_steps 个时间步结束后的状态
        self.n_steps = int(sp.sim_duration / sp.dt)
        # 创建时间序列数组，从0到总仿真时长，总共 n_steps + 1 个时间点
        self.time_sim = np.linspace(0, sp.sim_duration, self.n_steps + 1)

        # --- 初始化用于存储各项物理量历史记录的NumPy数组 ---
        # 数组长度为 n_steps + 1，用于记录每个时间点的值

        # 温度历史记录 (单位: °C)
        self.T_motor_hist = np.zeros(self.n_steps + 1)  # 电机温度
        self.T_inv_hist = np.zeros(self.n_steps + 1)    # 逆变器温度
        self.T_batt_hist = np.zeros(self.n_steps + 1)   # 电池温度
        self.T_cabin_hist = np.zeros(self.n_steps + 1)  # 座舱温度
        self.T_coolant_hist = np.zeros(self.n_steps + 1)# 冷却液温度

        # 控制状态日志
        self.powertrain_chiller_active_log = np.zeros(self.n_steps + 1, dtype=int) # 动力总成冷却器(Chiller)激活状态 (0:关闭, 1:开启)
        self.LTR_level_log = np.zeros(self.n_steps + 1, dtype=int) # 低温散热器(LTR)档位日志
        self.P_LTR_fan_actual_hist = np.zeros(self.n_steps + 1) # LTR风扇实际消耗功率 (单位: W)
        self.LTR_effectiveness_log = np.zeros(self.n_steps + 1) # LTR等效效能因子 (无单位, 0到1)

        # 热流日志 (单位: W)
        self.Q_LTR_hist = np.zeros(self.n_steps + 1) # LTR实际散热功率
        self.Q_coolant_from_LCC_hist = np.zeros(self.n_steps + 1) # 冷却液从低温冷凝器(LCC)获得的热量 (即制冷剂在LCC侧的放热量)
        self.Q_coolant_chiller_actual_hist = np.zeros(self.n_steps + 1) # 冷却液传递给动力总成Chiller的实际热量
        self.Q_cabin_load_total_hist = np.zeros(self.n_steps + 1) # 座舱总热负荷
        self.Q_cabin_cool_actual_hist = np.zeros(self.n_steps + 1) # 座舱蒸发器实际提供的制冷量

        # 产热和功率日志
        self.v_vehicle_profile_hist = np.zeros(self.n_steps + 1) # 车辆速度历史 (单位: km/h)
        self.Q_gen_motor_profile_hist = np.zeros(self.n_steps + 1) # 电机产热功率历史 (单位: W)
        self.Q_gen_inv_profile_hist = np.zeros(self.n_steps + 1)   # 逆变器产热功率历史 (单位: W)
        self.Q_gen_batt_profile_hist = np.zeros(self.n_steps + 1)  # 电池产热功率历史 (单位: W)
        self.P_comp_elec_profile_hist = np.zeros(self.n_steps + 1) # 空调压缩机总电耗历史 (单位: W)

    def set_initial_values_from_sp(self):
        """
        根据仿真参数 (sp) 中定义的初始条件，设置各个物理量在时间点 t=0 的初始值。
        """
        sp = self.sp # 引用仿真参数
        # 设置初始温度
        self.T_motor_hist[0] = sp.T_motor_init
        self.T_inv_hist[0] = sp.T_inv_init
        self.T_batt_hist[0] = sp.T_batt_init
        self.T_cabin_hist[0] = sp.T_cabin_init
        self.T_coolant_hist[0] = sp.T_coolant_init
        # 设置初始车速
        self.v_vehicle_profile_hist[0] = sp.v_start

        # --- 设置 t=0 时 LTR (低温散热器) 的初始状态 ---
        initial_coolant_temp_for_ltr = self.T_coolant_hist[0] # 获取初始冷却液温度
        current_ltr_level_idx = 0 # LTR 档位索引，默认为0档 (最低档或关闭)
        initial_UA_LTR_effective = 0 # LTR 有效UA值，默认为0
        initial_P_LTR_fan = 0 # LTR 风扇功率，默认为0

        # 检查 LTR 相关参数是否存在于 sp 对象中
        if hasattr(sp, 'LTR_coolant_temp_thresholds') and \
           hasattr(sp, 'LTR_UA_values_at_levels') and \
           hasattr(sp, 'LTR_fan_power_levels'):
            # 根据初始冷却液温度确定 LTR 的初始档位
            for lvl_idx_init in range(len(sp.LTR_coolant_temp_thresholds)):
                if initial_coolant_temp_for_ltr > sp.LTR_coolant_temp_thresholds[lvl_idx_init]:
                    current_ltr_level_idx = lvl_idx_init + 1 # 如果高于阈值，则档位至少为下一档
                else:
                    break # 温度低于当前阈值，停止检查更高档位
            # 确保档位索引在有效范围内，并获取对应的 UA 值和风扇功率
            if current_ltr_level_idx < len(sp.LTR_UA_values_at_levels):
                 initial_UA_LTR_effective = sp.LTR_UA_values_at_levels[current_ltr_level_idx]
                 initial_P_LTR_fan = sp.LTR_fan_power_levels[current_ltr_level_idx]
            else: # 如果计算出的档位索引超出范围 (例如，温度非常高)，则重置为最低有效档位
                current_ltr_level_idx = 0
                initial_UA_LTR_effective = sp.LTR_UA_values_at_levels[0] if hasattr(sp, 'LTR_UA_values_at_levels') and len(sp.LTR_UA_values_at_levels) > 0 else 0
                initial_P_LTR_fan = sp.LTR_fan_power_levels[0] if hasattr(sp, 'LTR_fan_power_levels') and len(sp.LTR_fan_power_levels) > 0 else 0
        # 记录 LTR 初始状态
        self.LTR_level_log[0] = current_ltr_level_idx
        self.P_LTR_fan_actual_hist[0] = initial_P_LTR_fan
        # 计算并记录 LTR 初始效能因子 (相对于最大UA值)
        self.LTR_effectiveness_log[0] = (initial_UA_LTR_effective / sp.UA_LTR_max) if hasattr(sp, 'UA_LTR_max') and sp.UA_LTR_max > 0 else (1.0 if initial_UA_LTR_effective > 0 else 0.0)
        # 计算并记录 LTR 初始散热量
        self.Q_LTR_hist[0] = max(0, initial_UA_LTR_effective * (initial_coolant_temp_for_ltr - sp.T_ambient))

        # --- 设置 t=0 时座舱的初始冷却功率 ---
        Q_cabin_cool_initial = 0 # 默认为0
        # 检查座舱冷却相关参数是否存在
        if hasattr(sp, 'cabin_cooling_power_levels') and \
           hasattr(sp, 'cabin_cooling_temp_thresholds') and \
           sp.cabin_cooling_power_levels: # 确保功率等级列表不为空
            # 默认使用最高档制冷功率
            Q_cabin_cool_initial = sp.cabin_cooling_power_levels[-1]
            # 根据初始座舱温度和温度阈值，确定实际的初始制冷功率等级
            for j in range(len(sp.cabin_cooling_temp_thresholds)):
                if self.T_cabin_hist[0] <= sp.cabin_cooling_temp_thresholds[j]:
                    Q_cabin_cool_initial = sp.cabin_cooling_power_levels[j]
                    break # 找到合适的等级后即跳出循环
        self.Q_cabin_cool_actual_hist[0] = max(0, Q_cabin_cool_initial) # 确保制冷功率不为负

        # --- 设置 t=0 时动力总成冷却器 (Chiller) 的初始状态 ---
        self.powertrain_chiller_active_log[0] = 0 # 默认为关闭状态
        self.Q_coolant_chiller_actual_hist[0] = 0.0 # 初始无热量交换

    def get_current_states(self, i):
        """
        获取仿真时间步 i 开始时的系统状态。
        参数:
            i (int): 当前时间步的索引。
        返回:
            dict: 包含当前时刻各关键状态量的字典。
        """
        return {
            "time_sec": self.time_sim[i],                       # 当前仿真时间 (s)
            "T_cabin": self.T_cabin_hist[i],                    # 当前座舱温度 (°C)
            "T_motor": self.T_motor_hist[i],                    # 当前电机温度 (°C)
            "T_inv": self.T_inv_hist[i],                        # 当前逆变器温度 (°C)
            "T_batt": self.T_batt_hist[i],                      # 当前电池温度 (°C)
            "T_coolant": self.T_coolant_hist[i],                # 当前冷却液温度 (°C)
            "v_vehicle_kmh": self.v_vehicle_profile_hist[i],    # 当前车速 (km/h)，实际代表该时间步开始时的速度
            "powertrain_chiller_on_prev_state": bool(self.powertrain_chiller_active_log[i]) # 上一时刻(或当前记录的)动力总成Chiller状态，用于滞环控制
        }

    def record_step_data(self, i, data_for_step_i, next_step_temperatures):
        """
        记录第 i 个时间步的计算结果，并存储计算出的下一个时间步 (i+1) 的温度。
        参数:
            i (int): 当前时间步的索引。
            data_for_step_i (dict): 包含了在第 i 步计算得到的所有中间变量和输出值的字典。
            next_step_temperatures (dict): 包含了计算得到的第 i+1 步各个部件温度的字典。
        """
        # 更新下一时间步 (i+1) 的温度历史记录
        self.T_motor_hist[i+1] = next_step_temperatures["T_motor_next"]
        self.T_inv_hist[i+1] = next_step_temperatures["T_inv_next"]
        self.T_batt_hist[i+1] = next_step_temperatures["T_batt_next"]
        self.T_cabin_hist[i+1] = next_step_temperatures["T_cabin_next"]
        self.T_coolant_hist[i+1] = next_step_temperatures["T_coolant_next"]

        # 记录当前时间步 i 的其他剖面数据和日志
        self.v_vehicle_profile_hist[i] = data_for_step_i["v_vehicle_current_kmh"] # 当前步的车速
        self.Q_gen_motor_profile_hist[i] = data_for_step_i["Q_gen_motor"]     # 电机产热
        self.Q_gen_inv_profile_hist[i] = data_for_step_i["Q_gen_inv"]         # 逆变器产热
        self.Q_cabin_load_total_hist[i] = data_for_step_i["Q_cabin_load_total"] # 座舱总热负荷
        self.Q_cabin_cool_actual_hist[i] = data_for_step_i["Q_cabin_cool_actual"]# 座舱实际制冷量
        self.powertrain_chiller_active_log[i] = 1 if data_for_step_i["powertrain_chiller_on_current_step"] else 0 # 动力总成Chiller状态
        self.Q_coolant_chiller_actual_hist[i] = data_for_step_i["Q_coolant_chiller_actual"] # 冷却液到Chiller的实际热量
        self.P_comp_elec_profile_hist[i] = data_for_step_i["P_comp_elec"]     # 压缩机电耗
        self.Q_coolant_from_LCC_hist[i] = data_for_step_i["Q_coolant_from_LCC"]# 冷却液从LCC获得的热量
        self.LTR_level_log[i] = data_for_step_i["LTR_level"]                 # LTR档位
        self.P_LTR_fan_actual_hist[i] = data_for_step_i["P_LTR_fan_actual"]  # LTR风扇功率
        self.Q_LTR_hist[i] = data_for_step_i["Q_LTR_to_ambient"]            # LTR散热量
        self.LTR_effectiveness_log[i] = data_for_step_i["LTR_effectiveness"] # LTR效能因子
        self.Q_gen_batt_profile_hist[i] = data_for_step_i["Q_gen_batt"]       # 电池产热

    def package_results(self):
        """
        将仿真过程中记录的所有历史数据打包成一个字典，方便后续处理和绘图。
        返回:
            dict: 包含所有仿真结果数据的字典。
        """
        return {
            "time_sim": self.time_sim, # 时间序列
            "temperatures_data": {     # 各部件温度历史
                'motor': self.T_motor_hist, 'inv': self.T_inv_hist, 'batt': self.T_batt_hist,
                'cabin': self.T_cabin_hist, 'coolant': self.T_coolant_hist
            },
            "heat_gen_data": {         # 各部件产热/负荷历史
                'motor': self.Q_gen_motor_profile_hist, 'inv': self.Q_gen_inv_profile_hist,
                'batt': self.Q_gen_batt_profile_hist, 'cabin_load': self.Q_cabin_load_total_hist
            },
            "cooling_system_logs": {   # 冷却系统运行日志
                'chiller_active': self.powertrain_chiller_active_log,       # 动力总成Chiller激活状态
                'LTR_level': self.LTR_level_log, 'P_LTR_fan': self.P_LTR_fan_actual_hist, # LTR档位和风扇功率
                'LTR_effectiveness_factor_equiv': self.LTR_effectiveness_log, # LTR等效效能因子
                'Q_LTR_to_ambient': self.Q_LTR_hist,                       # LTR散热量
                'Q_coolant_from_LCC': self.Q_coolant_from_LCC_hist,        # 冷却液从LCC获取热量
                'Q_coolant_to_chiller': self.Q_coolant_chiller_actual_hist, # 冷却液到Chiller热量
                'Q_cabin_evap_cooling': self.Q_cabin_cool_actual_hist     # 座舱蒸发器制冷量
            },
            "ac_power_log": self.P_comp_elec_profile_hist, # 压缩机电耗历史
            "speed_profile": self.v_vehicle_profile_hist # 车速历史
        }

class VehicleMotionModel:
    """
    VehicleMotionModel 类：
    处理车辆的运动学特性，根据预设的速度剖面计算当前车速，
    并基于当前车速和环境条件计算动力总成部件（电机、逆变器）的产热功率和逆变器输入功率。
    """
    def __init__(self, sp):
        """
        初始化 VehicleMotionModel 对象。
        参数:
            sp: simulation_parameters 模块的实例。
        """
        self.sp = sp # 存储仿真参数对象的引用

    def get_current_speed_kmh(self, current_time_sec):
        """
        根据当前仿真时间计算车辆的瞬时速度。
        速度剖面定义为：从初始速度 v_start 线性加速到最终速度 v_end，
        加速过程在 ramp_up_time_sec 内完成，之后保持 v_end 匀速行驶。
        参数:
            current_time_sec (float): 当前仿真时间 (s)。
        返回:
            float: 当前车速 (km/h)。
        """
        sp = self.sp
        if current_time_sec <= sp.ramp_up_time_sec: # 判断是否处于加速阶段
            # 计算加速阶段的速度增加比例
            speed_increase_ratio = (current_time_sec / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 1.0
            # 线性插值计算当前速度
            v_vehicle_current = sp.v_start + (sp.v_end - sp.v_start) * speed_increase_ratio
        else: # 匀速阶段
            v_vehicle_current = sp.v_end
        # 确保速度在定义的 v_start 和 v_end 之间 (处理减速工况或参数异常)
        return max(min(sp.v_start, sp.v_end), min(max(sp.v_start, sp.v_end), v_vehicle_current))


    def get_powertrain_heat_generation(self, v_vehicle_current_kmh):
        """
        根据当前车速计算动力总成主要部件（电机、逆变器）的产热功率，以及逆变器的输入功率。
        参数:
            v_vehicle_current_kmh (float): 当前车速 (km/h)。
        返回:
            tuple: (Q_gen_motor, Q_gen_inv, P_inv_in)
                Q_gen_motor (float): 电机产热功率 (W)。
                Q_gen_inv (float): 逆变器产热功率 (W)。
                P_inv_in (float): 逆变器输入功率 (W)，即从电池侧获取的用于驱动的功率。
        """
        sp = self.sp
        P_inv_in = 0; Q_gen_motor = 0; Q_gen_inv = 0 # 初始化返回值
        try:
            # 1. 计算车轮处所需功率 (克服滚动阻力和空气阻力)
            P_wheel = hv.P_wheel_func(v_vehicle_current_kmh, sp.m_vehicle, sp.T_ambient)
            # 2. 计算电机输入功率 (考虑电机效率)
            P_motor_in = hv.P_motor_func(P_wheel, sp.eta_motor)
            # 3. 计算逆变器输入功率 (考虑逆变器效率)
            P_inv_in = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0
            # 4. 计算电机产热功率
            Q_gen_motor = hv.Q_mot_func(P_motor_in, sp.eta_motor)
            # 5. 计算逆变器产热功率
            Q_gen_inv = hv.Q_inv_func(P_motor_in, sp.eta_inv)
        except AttributeError as e: # 捕获导入的 hv 模块中函数缺失的错误
            print(f"警告: 动力总成产热函数缺失/错误 (heat_vehicle.py)。{e}")
        except Exception as e: # 捕获其他潜在计算错误
            print(f"警告: 动力总成产热时发生意外错误。{e}")
        return Q_gen_motor, Q_gen_inv, P_inv_in

class CabinModel:
    """
    CabinModel 类：
    管理座舱的热负荷计算和座舱空调的制冷功率控制。
    """
    def __init__(self, sp):
        """
        初始化 CabinModel 对象。
        参数:
            sp: simulation_parameters 模块的实例。
        """
        self.sp = sp # 存储仿真参数对象的引用
        try:
            # 初始化 CabinHeatCalculator 对象，用于详细计算座舱热负荷
            self.cabin_heat_calculator = CabinHeatCalculator(
                N_passengers=sp.N_passengers, v_air_internal_mps=sp.v_air_in_mps,
                A_body=sp.A_body, R_body=sp.R_body, A_glass=sp.A_glass, R_glass=sp.R_glass,
                SHGC=sp.SHGC, A_glass_sun=sp.A_glass_sun, W_out_summer=sp.W_out_summer,
                W_in_target=sp.W_in_target, fraction_fresh_air=sp.fresh_air_fraction,
                cp_air=sp.cp_air, h_fg=getattr(sp, 'h_fg_water', 2.45e6), # 水的汽化潜热，带默认值
                Q_powertrain=getattr(sp, 'Q_cabin_powertrain_invasion', 50), # 动力总成侵入热，带默认值
                Q_electronics=getattr(sp, 'Q_cabin_electronics', 100),    # 电子设备产热，带默认值
                q_person=getattr(sp, 'q_person_heat', 100)                 # 每人产热，带默认值
            )
            print("CabinHeatCalculator 在 CabinModel 中初始化成功。")
        except AttributeError as e: # 捕获 sp 对象中缺少必要参数的错误
            print(f"CabinModel 初始化 CabinHeatCalculator 错误: {e}")
            self.cabin_heat_calculator = None # 初始化失败则设为 None
        except Exception as e: # 捕获其他初始化错误
            print(f"CabinModel 初始化 CabinHeatCalculator 时发生意外错误: {e}")
            self.cabin_heat_calculator = None

    def get_cabin_total_heat_load(self, current_cabin_temp_C, v_vehicle_current_kmh):
        """
        计算当前时刻座舱的总热负荷。
        参数:
            current_cabin_temp_C (float): 当前座舱内部温度 (°C)。
            v_vehicle_current_kmh (float): 当前车速 (km/h)。
        返回:
            float: 座舱总热负荷 (W)。正值表示热量进入座舱或在座舱内产生。
        """
        sp = self.sp
        Q_cabin_load_total = 0 # 初始化热负荷
        if self.cabin_heat_calculator: # 确保 CabinHeatCalculator 已成功初始化
            try:
                # 调用 CabinHeatCalculator 计算总热负荷
                Q_cabin_load_total = self.cabin_heat_calculator.calculate_total_cabin_heat_load(
                    T_outside=sp.T_ambient, T_inside=current_cabin_temp_C,
                    v_vehicle_kmh=v_vehicle_current_kmh, I_solar=getattr(sp, 'I_solar_summer', 0) # 太阳辐射强度，带默认值
                )
            except Exception as e:
                print(f"警告: 计算座舱热负荷时出错。{e}")
        else:
            print("警告: CabinHeatCalculator 不可用，无法计算座舱热负荷。")
        return Q_cabin_load_total

    def get_cabin_cooling_power(self, current_cabin_temp_C):
        """
        根据当前座舱温度和预设的温度阈值及功率等级，确定座舱空调蒸发器应提供的实际制冷功率。
        这是一个基于阈值的多级控制策略。
        参数:
            current_cabin_temp_C (float): 当前座舱内部温度 (°C)。
        返回:
            float: 座舱空调蒸发器实际提供的制冷功率 (W)。非负值。
        """
        sp = self.sp
        Q_cabin_cool_actual = 0 # 初始化制冷功率
        # 检查座舱冷却控制相关参数是否存在
        if hasattr(sp, 'cabin_cooling_power_levels') and \
           hasattr(sp, 'cabin_cooling_temp_thresholds') and \
           sp.cabin_cooling_power_levels: # 确保功率等级列表不为空
            # 默认使用最高等级的制冷功率 (对应温度高于所有阈值的情况)
            Q_cabin_cool_actual = sp.cabin_cooling_power_levels[-1]
            # 遍历温度阈值，找到第一个高于当前座舱温度的阈值，采用对应的功率等级
            for j in range(len(sp.cabin_cooling_temp_thresholds)):
                if current_cabin_temp_C <= sp.cabin_cooling_temp_thresholds[j]:
                    Q_cabin_cool_actual = sp.cabin_cooling_power_levels[j]
                    break # 找到合适的等级后即跳出循环
        return max(0, Q_cabin_cool_actual) # 确保制冷功率不为负

class ThermalManagementSystem:
    """
    ThermalManagementSystem 类：
    核心热管理逻辑，包括：
    - 动力总成冷却器 (Chiller) 的启停控制（带滞环）。
    - 冷却器 (Chiller) 的实际传热量计算。
    - 空调压缩机功率计算。
    - 低温冷凝器 (LCC) 的传热量计算。
    - 低温散热器 (LTR) 的风扇档位控制（带滞环）和实际散热量计算。
    - 动力总成各部件（电机、逆变器、电池）的热平衡及温度变化率计算。
    - 冷却液的热平衡及温度变化率计算。
    """
    def __init__(self, sp, cop_value):
        """
        初始化 ThermalManagementSystem 对象。
        参数:
            sp: simulation_parameters 模块的实例。
            cop_value (float): 制冷循环的性能系数 (COP)。
        """
        self.sp = sp # 存储仿真参数对象的引用
        self.cop = cop_value # 存储制冷循环 COP 值
        self.powertrain_chiller_on_state = False # 动力总成Chiller的内部开关状态，用于实现滞环控制，初始为关闭
        self.current_ltr_level_idx_state = 0 # LTR档位的内部状态索引，初始为0档 (最低档)

    def run_cooling_loop_logic(self, current_system_states, Q_cabin_cool_actual_W):
        """
        执行一个时间步内的冷却回路控制逻辑和热量计算。
        参数:
            current_system_states (dict): 包含当前各部件温度等状态的字典。
            Q_cabin_cool_actual_W (float): 当前座舱蒸发器实际提供的制冷量 (W)。
        返回:
            dict: 包含该时间步冷却回路计算结果的字典，如Chiller状态、各部分热流、压缩机功率等。
        """
        sp = self.sp
        # 从输入状态字典中解包当前各部件温度
        current_T_coolant = current_system_states["T_coolant"]
        current_T_motor = current_system_states["T_motor"]
        current_T_inv = current_system_states["T_inv"]
        current_T_batt = current_system_states["T_batt"]
        # prev_chiller_state = current_system_states["powertrain_chiller_on_prev_state"] # 原计划使用输入的状态，现改为使用内部维持的 self.powertrain_chiller_on_state

        # --- 1. 动力总成冷却器 (Chiller) 控制逻辑 (带滞环) ---
        # 获取各部件的目标温度和停止冷却的温度阈值 (目标温度 - 滞环宽度)
        T_motor_target = getattr(sp, 'T_motor_target', float('inf')) # 若参数不存在则设为无穷大，即不以此为开启条件
        T_inv_target = getattr(sp, 'T_inv_target', float('inf'))
        T_batt_target_high = getattr(sp, 'T_batt_target_high', float('inf')) # 电池高温目标
        T_motor_stop_cool = getattr(sp, 'T_motor_stop_cool', float('-inf')) # 若参数不存在则设为负无穷大，即不以此为关闭条件
        T_inv_stop_cool = getattr(sp, 'T_inv_stop_cool', float('-inf'))
        T_batt_stop_cool = getattr(sp, 'T_batt_stop_cool', float('-inf'))   # 电池低温目标 (Chiller停止条件)

        # 判断是否需要启动Chiller (任一部件温度超过其目标上限)
        start_cooling = (current_T_motor > T_motor_target) or \
                        (current_T_inv > T_inv_target) or \
                        (current_T_batt > T_batt_target_high)
        # 判断是否可以停止Chiller (所有部件温度均低于其停止冷却的阈值)
        stop_cooling = (current_T_motor < T_motor_stop_cool) and \
                       (current_T_inv < T_inv_stop_cool) and \
                       (current_T_batt < T_batt_stop_cool)

        # 应用滞环逻辑更新Chiller的开关状态
        if start_cooling:
            self.powertrain_chiller_on_state = True  # 满足开启条件，则开启
        elif stop_cooling:
            self.powertrain_chiller_on_state = False # 满足停止条件，则关闭
        # 如果既不满足开启也不满足停止，Chiller状态保持不变 (由 self.powertrain_chiller_on_state 维持)

        powertrain_chiller_on_current_step = self.powertrain_chiller_on_state # 当前步Chiller的最终状态

        # --- 2. 动力总成冷却器 (Chiller) 实际传热量计算 ---
        Q_chiller_potential = 0 # 初始化潜在制冷量
        # Chiller只有在冷却液温度高于制冷剂蒸发温度时才能从冷却液吸热
        if current_T_coolant > sp.T_evap_sat_for_UA_calc: # T_evap_sat_for_UA_calc 是制冷剂在Chiller蒸发侧的饱和温度
            Q_chiller_potential = sp.UA_coolant_chiller * (current_T_coolant - sp.T_evap_sat_for_UA_calc)
        Q_chiller_potential = max(0, Q_chiller_potential) # 确保潜在制冷量不为负
        # 实际制冷量受限于Chiller最大制冷功率和其开关状态
        Q_coolant_chiller_actual = min(Q_chiller_potential, sp.max_chiller_cool_power) if powertrain_chiller_on_current_step else 0

        # --- 3. 计算总蒸发负荷和压缩机功率 ---
        # 总蒸发负荷 = 座舱蒸发器制冷量 + 动力总成Chiller从冷却液吸热量
        Q_evap_total_needed = Q_cabin_cool_actual_W + Q_coolant_chiller_actual
        P_comp_elec = 0.0; P_comp_mech = 0.0 # 初始化压缩机电功率和机械功率
        # 如果需要制冷，且COP和压缩机驱动效率有效
        if Q_evap_total_needed > 0 and self.cop > 0 and hasattr(sp, 'eta_comp_drive') and sp.eta_comp_drive > 0:
            P_comp_mech = Q_evap_total_needed / self.cop # 压缩机所需机械功率
            P_comp_elec = P_comp_mech / sp.eta_comp_drive # 压缩机所需电功率 (考虑驱动效率)

        # --- 4. 低温冷凝器 (LCC) 传热量计算 ---
        # LCC的散热量等于总蒸发负荷加上压缩机消耗的机械功 (能量守恒)
        # 这部分热量被冷却液吸收
        Q_coolant_from_LCC = Q_evap_total_needed + P_comp_mech

        # --- 5. 低温散热器 (LTR) 风扇档位控制和实际散热量计算 ---
        UA_LTR_effective = 0 # LTR 有效UA值，初始化为0
        P_LTR_fan_actual = 0 # LTR 风扇实际功率，初始化为0
        previous_ltr_level_idx = self.current_ltr_level_idx_state # 获取上一时刻LTR的档位状态
        new_ltr_level_idx = previous_ltr_level_idx # 新档位默认保持不变

        # 检查LTR相关参数是否都已配置
        if hasattr(sp, 'LTR_coolant_temp_thresholds') and \
           hasattr(sp, 'LTR_UA_values_at_levels') and \
           hasattr(sp, 'LTR_fan_power_levels'):

            thresholds = sp.LTR_coolant_temp_thresholds # LTR档位切换的冷却液温度阈值列表
            ltr_hysteresis = getattr(sp, 'LTR_hysteresis_offset', 1.0) # LTR控制的滞环温度，默认为1.0°C

            # a. 确定不考虑滞环的理想目标档位 (target_ideal_level_idx)
            target_ideal_level_idx = 0 # 默认为最低档 (0档)
            for lvl_idx in range(len(thresholds)): # 遍历温度阈值
                if current_T_coolant > thresholds[lvl_idx]: # 如果冷却液温度高于当前阈值
                    target_ideal_level_idx = lvl_idx + 1 # 理想档位至少是下一档
                else:
                    break # 温度低于当前阈值，停止查找更高档位
            # 确保理想档位索引不超过最大有效档位
            if target_ideal_level_idx >= len(sp.LTR_UA_values_at_levels):
                target_ideal_level_idx = len(sp.LTR_UA_values_at_levels) - 1

            # b. 应用滞环逻辑来确定新的实际档位 (new_ltr_level_idx)
            if target_ideal_level_idx > previous_ltr_level_idx:
                # 情况1: 理想档位高于当前档位 (系统希望升档)
                # 直接升到理想档位 (升档阈值通常不带滞环，或者说，target_ideal_level_idx的计算已隐含升档条件)
                new_ltr_level_idx = target_ideal_level_idx
            elif target_ideal_level_idx < previous_ltr_level_idx:
                # 情况2: 理想档位低于当前档位 (系统希望降档)
                # 需要检查是否满足带滞环的降档条件
                if previous_ltr_level_idx > 0: # 只有在非0档时才能降档
                    # 触发当前 previous_ltr_level_idx 的升档阈值是 thresholds[previous_ltr_level_idx - 1]
                    # 降档条件：当前冷却液温度 < (升档到上一档的阈值 - 滞环宽度)
                    if current_T_coolant < (thresholds[previous_ltr_level_idx - 1] - ltr_hysteresis):
                        new_ltr_level_idx = target_ideal_level_idx # 允许降到理想的目标档位
                    else:
                        new_ltr_level_idx = previous_ltr_level_idx # 不满足降档条件，保持当前档位
                else: # 当前是0档，不能再降
                    new_ltr_level_idx = 0
            else: # target_ideal_level_idx == previous_ltr_level_idx
                # 情况3: 理想档位等于当前档位
                new_ltr_level_idx = previous_ltr_level_idx # 保持当前档位

            # c. 再次进行边界检查，确保 new_ltr_level_idx 在有效范围内
            if new_ltr_level_idx < 0: new_ltr_level_idx = 0
            if new_ltr_level_idx >= len(sp.LTR_UA_values_at_levels):
                new_ltr_level_idx = len(sp.LTR_UA_values_at_levels) - 1

            # d. 根据确定的新档位获取实际的UA值和风扇功率
            UA_LTR_effective = sp.LTR_UA_values_at_levels[new_ltr_level_idx]
            P_LTR_fan_actual = sp.LTR_fan_power_levels[new_ltr_level_idx]

            # e. 更新内部维持的LTR档位状态
            self.current_ltr_level_idx_state = new_ltr_level_idx
        else:
            # 如果LTR参数未配置，则LTR不工作
            self.current_ltr_level_idx_state = 0
            UA_LTR_effective = 0
            P_LTR_fan_actual = 0
            new_ltr_level_idx = 0 # 确保返回值有定义

        # 计算LTR实际散热量 (冷却液到环境)
        Q_LTR_to_ambient = max(0, UA_LTR_effective * (current_T_coolant - sp.T_ambient))
        # 计算LTR等效效能因子
        LTR_effectiveness_factor = (UA_LTR_effective / sp.UA_LTR_max) if hasattr(sp, 'UA_LTR_max') and sp.UA_LTR_max > 0 else (1.0 if UA_LTR_effective > 0 else 0.0)

        # 返回该时间步冷却回路的计算结果
        return {
            "powertrain_chiller_on_current_step": powertrain_chiller_on_current_step, # Chiller开关状态
            "Q_coolant_chiller_actual": Q_coolant_chiller_actual,   # Chiller从冷却液吸热量
            "P_comp_elec": P_comp_elec, "P_comp_mech": P_comp_mech, # 压缩机电耗和机械功
            "Q_coolant_from_LCC": Q_coolant_from_LCC,             # 冷却液从LCC吸热量
            "LTR_level": new_ltr_level_idx,                       # LTR档位
            "P_LTR_fan_actual": P_LTR_fan_actual,                 # LTR风扇功率
            "Q_LTR_to_ambient": Q_LTR_to_ambient,                 # LTR散热量
            "LTR_effectiveness": LTR_effectiveness_factor,        # LTR效能因子
        }

    def get_powertrain_thermal_derivatives_and_heats(self, current_system_states, P_inv_in_W, cooling_loop_outputs, Q_gen_motor_W, Q_gen_inv_W):
        """
        计算动力总成各部件（电机、逆变器、电池）的热平衡，确定其温度变化率 (dT/dt)，
        以及各部件与冷却液之间的传热量和电池的产热量。
        参数:
            current_system_states (dict): 当前系统状态（主要是各部件温度）。
            P_inv_in_W (float): 逆变器的输入功率 (W)，来自电池。
            cooling_loop_outputs (dict): `run_cooling_loop_logic`的输出，包含压缩机和LTR风扇电耗。
            Q_gen_motor_W (float): 电机自身产生的热量 (W)。
            Q_gen_inv_W (float): 逆变器自身产生的热量 (W)。
        返回:
            dict: 包含电池产热、各部件到冷却液的传热量、各部件温度变化率的字典。
        """
        sp = self.sp
        # 从输入状态字典中解包当前各部件温度和冷却液温度
        current_T_motor = current_system_states["T_motor"]
        current_T_inv = current_system_states["T_inv"]
        current_T_batt = current_system_states["T_batt"]
        current_T_coolant = current_system_states["T_coolant"]
        # 从冷却回路输出中获取压缩机和LTR风扇的电功率消耗
        P_comp_elec = cooling_loop_outputs["P_comp_elec"]
        P_LTR_fan_actual = cooling_loop_outputs["P_LTR_fan_actual"]

        # --- 计算电池产热 ---
        # 电池总输出电功率 = 逆变器输入功率 (驱动) + 压缩机电耗 + LTR风扇电耗
        P_elec_total_batt_out = P_inv_in_W + P_comp_elec + P_LTR_fan_actual
        Q_gen_batt = 0 # 初始化电池产热
        try:
            # 调用 heat_vehicle 模块中的函数计算电池焦耳热
            Q_gen_batt = hv.Q_batt_func(P_elec_total_batt_out, sp.u_batt, sp.R_int_batt)
        except AttributeError as e: print(f"警告: Q_batt_func 缺失。{e}")
        except Exception as e: print(f"警告: Q_batt_func 发生意外错误。{e}")

        # --- 计算动力总成部件到冷却液的传热量 ---
        # 基于部件与冷却液的温差以及UA值 (总传热系数 * 面积)
        Q_motor_to_coolant = sp.UA_motor_coolant * (current_T_motor - current_T_coolant)
        Q_inv_to_coolant = sp.UA_inv_coolant * (current_T_inv - current_T_coolant)
        Q_batt_to_coolant = sp.UA_batt_coolant * (current_T_batt - current_T_coolant)

        # --- 计算动力总成各部件的温度变化率 (dT/dt) ---
        # dT/dt = (部件产热 - 部件到冷却液的传热) / 部件热容 (mc)
        dT_motor_dt = (Q_gen_motor_W - Q_motor_to_coolant) / sp.mc_motor if sp.mc_motor > 0 else 0
        dT_inv_dt = (Q_gen_inv_W - Q_inv_to_coolant) / sp.mc_inverter if sp.mc_inverter > 0 else 0
        dT_batt_dt = (Q_gen_batt - Q_batt_to_coolant) / sp.mc_battery if sp.mc_battery > 0 else 0

        return {
            "Q_gen_batt": Q_gen_batt,                   # 电池产热 (W)
            "Q_motor_to_coolant": Q_motor_to_coolant,   # 电机到冷却液的传热 (W)
            "Q_inv_to_coolant": Q_inv_to_coolant,       # 逆变器到冷却液的传热 (W)
            "Q_batt_to_coolant": Q_batt_to_coolant,     # 电池到冷却液的传热 (W)
            "dT_motor_dt": dT_motor_dt, "dT_inv_dt": dT_inv_dt, "dT_batt_dt": dT_batt_dt, # 各部件温度变化率 (°C/s)
        }

    def get_coolant_temp_derivative(self, powertrain_heats, cooling_loop_heats):
        """
        计算冷却液的温度变化率 (dT_coolant/dt)。
        基于流入冷却液的总热量和从冷却液流出的总热量。
        参数:
            powertrain_heats (dict): `get_powertrain_thermal_derivatives_and_heats` 的输出，包含各部件到冷却液的传热。
            cooling_loop_heats (dict): `run_cooling_loop_logic` 的输出，包含LCC到冷却液、冷却液到LTR、冷却液到Chiller的传热。
        返回:
            float: 冷却液温度变化率 (°C/s)。
        """
        sp = self.sp
        # 冷却液净吸热量 = (LCC放热给冷却液 + 电机放热给冷却液 + 逆变器放热给冷却液 + 电池放热给冷却液)
        #                  - (LTR从冷却液散热到环境 + Chiller从冷却液吸热)
        Q_coolant_net = (cooling_loop_heats["Q_coolant_from_LCC"] +
                         powertrain_heats["Q_motor_to_coolant"] +
                         powertrain_heats["Q_inv_to_coolant"] +
                         powertrain_heats["Q_batt_to_coolant"]) - \
                        (cooling_loop_heats["Q_LTR_to_ambient"] +
                         cooling_loop_heats["Q_coolant_chiller_actual"])
        # 冷却液温度变化率 = 冷却液净吸热量 / 冷却液热容 (mc_coolant)
        return Q_coolant_net / sp.mc_coolant if sp.mc_coolant > 0 else 0

class SimulationEngine:
    """
    SimulationEngine 类：
    主仿真引擎，协调各个子模型（DataManager, VehicleMotionModel, CabinModel, ThermalManagementSystem）
    的交互，执行时间步进仿真。
    """
    def __init__(self, sp, cop_value):
        """
        初始化 SimulationEngine 对象。
        参数:
            sp: simulation_parameters 模块的实例。
            cop_value (float): 制冷循环的性能系数 (COP)。
        """
        self.sp = sp # 存储仿真参数对象的引用
        self.cop = cop_value # 存储制冷循环COP值
        self.n_steps = int(sp.sim_duration / sp.dt) # 计算总仿真步数

        # 实例化各个子模型管理器
        self.data_manager = DataManager(sp)
        self.vehicle_model = VehicleMotionModel(sp)
        self.cabin_model = CabinModel(sp)
        self.thermal_system = ThermalManagementSystem(sp, cop_value)

        # 初始化仿真在 t=0 时刻的状态和日志
        self._initialize_simulation_state_t0()

    def _initialize_simulation_state_t0(self):
        """
        为仿真开始时刻 (t=0) 设置所有相关的初始日志值和状态。
        这个方法确保了在第一个时间步迭代开始前，t=0 时刻的所有数据都是一致和完整的。
        """
        sp = self.sp
        # 1. DataManager 设置基本初始温度、速度，并根据初始温度计算一些冷却系统的初始状态
        #    (例如，LTR的初始档位和散热，座舱的初始制冷功率，Chiller的初始关闭状态)
        self.data_manager.set_initial_values_from_sp()

        # 2. 获取 t=0 时刻的系统状态 (主要包括各部件温度和初始车速)
        #    这些值已由 set_initial_values_from_sp 在 data_manager 的历史数组索引0处设置
        states_t0 = self.data_manager.get_current_states(0)

        # 3. 计算 t=0 时刻的座舱总热负荷
        #    (座舱初始实际制冷功率 Q_cabin_cool_actual_hist[0] 已在 set_initial_values_from_sp 中基于初始座舱温度确定)
        Q_cabin_load_t0 = self.cabin_model.get_cabin_total_heat_load(states_t0["T_cabin"], states_t0["v_vehicle_kmh"])
        self.data_manager.Q_cabin_load_total_hist[0] = Q_cabin_load_t0

        # 4. 计算 t=0 时刻的动力总成产热 (电机、逆变器) 和逆变器输入功率
        #    这些都基于初始车速 v_start
        Q_gen_motor_t0, Q_gen_inv_t0, P_inv_in_t0 = self.vehicle_model.get_powertrain_heat_generation(states_t0["v_vehicle_kmh"])
        self.data_manager.Q_gen_motor_profile_hist[0] = Q_gen_motor_t0
        self.data_manager.Q_gen_inv_profile_hist[0] = Q_gen_inv_t0
        # P_inv_in_t0 将在步骤6中用于计算电池产热

        # 5. 计算 t=0 时刻的压缩机电耗和LCC传给冷却液的热量
        #    需要用到已在 set_initial_values_from_sp 中确定的 Q_cabin_cool_actual_hist[0] 和 Q_coolant_chiller_actual_hist[0]
        Q_evap_total_needed_t0 = self.data_manager.Q_cabin_cool_actual_hist[0] + self.data_manager.Q_coolant_chiller_actual_hist[0]
        P_comp_elec_t0 = 0.0; P_comp_mech_t0 = 0.0
        if Q_evap_total_needed_t0 > 0 and self.cop > 0 and hasattr(sp, 'eta_comp_drive') and sp.eta_comp_drive > 0:
             P_comp_mech_t0 = Q_evap_total_needed_t0 / self.cop
             P_comp_elec_t0 = P_comp_mech_t0 / sp.eta_comp_drive
        self.data_manager.P_comp_elec_profile_hist[0] = P_comp_elec_t0
        self.data_manager.Q_coolant_from_LCC_hist[0] = Q_evap_total_needed_t0 + P_comp_mech_t0
        # LTR相关的初始日志 (Q_LTR_hist[0], P_LTR_fan_actual_hist[0], LTR_level_log[0], LTR_effectiveness_log[0])
        # 已经在 set_initial_values_from_sp 中基于初始冷却液温度计算并记录

        # 6. 计算 t=0 时刻的电池产热
        #    需要用到步骤4的 P_inv_in_t0，步骤5的 P_comp_elec_t0，以及 set_initial_values_from_sp 中确定的 LTR风扇功率 P_LTR_fan_actual_hist[0]
        P_LTR_fan_t0 = self.data_manager.P_LTR_fan_actual_hist[0]
        P_elec_total_batt_out_t0 = P_inv_in_t0 + P_comp_elec_t0 + P_LTR_fan_t0
        Q_gen_batt_t0 = 0
        try:
            Q_gen_batt_t0 = hv.Q_batt_func(P_elec_total_batt_out_t0, sp.u_batt, sp.R_int_batt)
        except AttributeError: pass # 忽略 Q_batt_func 缺失错误 (已在其他地方警告)
        except Exception: pass    # 忽略其他计算错误 (已在其他地方警告)
        self.data_manager.Q_gen_batt_profile_hist[0] = Q_gen_batt_t0

    def run_simulation(self):
        """
        执行主仿真循环。
        在每个时间步内：
        1. 获取当前系统状态。
        2. 计算车辆运动学和动力总成（电机、逆变器）的产热。
        3. 计算座舱热负荷和所需的座舱制冷量。
        4. 运行冷却系统控制逻辑，确定各冷却部件（Chiller, LTR, LCC, 压缩机）的工作状态和热交换量。
        5. 计算动力总成各部件（包括电池）的热平衡，得到温度变化率。
        6. 计算座舱和冷却液的温度变化率。
        7. 使用欧拉法更新下一时间步的温度。
        8. 记录当前时间步的所有计算结果。
        仿真结束后，填充最后一个时间点的剖面值并返回所有结果。
        返回:
            dict: 包含所有仿真结果数据的字典。
        """
        sp = self.sp # 引用仿真参数
        print(f"开始重构后的仿真循环，共 {self.n_steps} 步...")

        # --- 主仿真循环 ---
        # 循环 n_steps 次，对应 n_steps 个时间间隔 dt
        # 索引 i 代表当前时间步的开始时刻 (t_i)
        # 计算结果将用于更新下一时间步 t_{i+1} 的状态
        for i in range(self.n_steps):
            # 获取当前时间步开始时的系统状态 (T_motor[i], T_inv[i], ..., v_vehicle[i], etc.)
            current_states_at_i = self.data_manager.get_current_states(i)

            # --- 1. 车辆运动模型 和 动力总成主要部件产热 (基于 t_i 的车速) ---
            # 根据当前时间 current_states_at_i["time_sec"] 计算当前的车速
            v_vehicle_current_kmh = self.vehicle_model.get_current_speed_kmh(current_states_at_i["time_sec"])
            # 根据当前车速计算电机和逆变器的产热，以及逆变器的输入功率
            Q_gen_motor, Q_gen_inv, P_inv_in = self.vehicle_model.get_powertrain_heat_generation(v_vehicle_current_kmh)

            # --- 2. 座舱环境模型 (基于 t_i 的座舱温度和车速) ---
            # 计算座舱总热负荷 (包括传导、对流、辐射、人员、新风等)
            Q_cabin_load_total = self.cabin_model.get_cabin_total_heat_load(current_states_at_i["T_cabin"], v_vehicle_current_kmh)
            # 根据当前座舱温度确定空调蒸发器实际提供的制冷功率
            Q_cabin_cool_actual = self.cabin_model.get_cabin_cooling_power(current_states_at_i["T_cabin"])

            # --- 3. 冷却系统运行控制逻辑 (基于 t_i 的各部件温度和座舱制冷需求) ---
            # 决定Chiller开关、LTR档位，并计算各热交换器热流、压缩机功率等
            cooling_loop_outputs = self.thermal_system.run_cooling_loop_logic(current_states_at_i, Q_cabin_cool_actual)

            # --- 4. 动力总成热模型 (计算电池产热，及各部件与冷却液的传热，确定各部件温度变化率 dT/dt) ---
            # 需要用到步骤1的电机/逆变器产热，步骤3的压缩机/LTR风扇电耗 (用于电池总功率)
            powertrain_thermal_outputs = self.thermal_system.get_powertrain_thermal_derivatives_and_heats(
                current_states_at_i, P_inv_in, cooling_loop_outputs, Q_gen_motor, Q_gen_inv
            )

            # --- 5. 计算座舱和冷却液的温度变化率 (dT/dt) ---
            # 座舱温度变化率 = (座舱总热负荷 - 座舱实际制冷量) / 座舱热容
            dT_cabin_dt = (Q_cabin_load_total - Q_cabin_cool_actual) / sp.mc_cabin if sp.mc_cabin > 0 else 0
            # 冷却液温度变化率 (已在 ThermalManagementSystem 内部计算并返回)
            dT_coolant_dt = self.thermal_system.get_coolant_temp_derivative(powertrain_thermal_outputs, cooling_loop_outputs)

            # --- 6. 更新下一时间步 (t_{i+1}) 的各部件温度 (使用前向欧拉法) ---
            # T_next = T_current + (dT/dt)_current * dt
            next_step_temperatures = {
                "T_motor_next": current_states_at_i["T_motor"] + powertrain_thermal_outputs["dT_motor_dt"] * sp.dt,
                "T_inv_next": current_states_at_i["T_inv"] + powertrain_thermal_outputs["dT_inv_dt"] * sp.dt,
                "T_batt_next": current_states_at_i["T_batt"] + powertrain_thermal_outputs["dT_batt_dt"] * sp.dt,
                "T_cabin_next": current_states_at_i["T_cabin"] + dT_cabin_dt * sp.dt,
                "T_coolant_next": current_states_at_i["T_coolant"] + dT_coolant_dt * sp.dt
            }

            # --- 7. 存储当前时间步 i 的所有计算得到的剖面数据和日志 ---
            #    并将下一时间步 i+1 的温度存入历史数组
            data_for_step_i = {
                "v_vehicle_current_kmh": v_vehicle_current_kmh, # 当前步的车速
                "Q_gen_motor": Q_gen_motor,                     # 电机产热
                "Q_gen_inv": Q_gen_inv,                         # 逆变器产热
                "Q_cabin_load_total": Q_cabin_load_total,       # 座舱总热负荷
                "Q_cabin_cool_actual": Q_cabin_cool_actual,     # 座舱实际制冷量
                "powertrain_chiller_on_current_step": cooling_loop_outputs["powertrain_chiller_on_current_step"], # Chiller状态
                "Q_coolant_chiller_actual": cooling_loop_outputs["Q_coolant_chiller_actual"], # Chiller从冷却液吸热
                "P_comp_elec": cooling_loop_outputs["P_comp_elec"],                         # 压缩机电耗
                "Q_coolant_from_LCC": cooling_loop_outputs["Q_coolant_from_LCC"],         # 冷却液从LCC吸热
                "LTR_level": cooling_loop_outputs["LTR_level"],                             # LTR档位
                "P_LTR_fan_actual": cooling_loop_outputs["P_LTR_fan_actual"],             # LTR风扇功率
                "Q_LTR_to_ambient": cooling_loop_outputs["Q_LTR_to_ambient"],             # LTR散热量
                "LTR_effectiveness": cooling_loop_outputs["LTR_effectiveness"],           # LTR效能因子
                "Q_gen_batt": powertrain_thermal_outputs["Q_gen_batt"]                  # 电池产热
                # P_comp_mech (压缩机机械功) 在 cooling_loop_outputs 中，但通常不直接记录，而是用于中间计算
            }
            self.data_manager.record_step_data(i, data_for_step_i, next_step_temperatures)

        print(f"重构后的仿真循环在 {self.n_steps} 步后完成。")
        # 仿真主循环结束后，填充最后一个时间点 (索引为 n_steps) 的相关剖面数据
        # (温度值 T_xxx_hist[n_steps] 已经在循环的最后一次迭代中计算并存储)
        self._fill_final_step_profiles()
        # 打包所有记录的数据并返回
        return self.data_manager.package_results()

    def _fill_final_step_profiles(self):
        """
        在主仿真循环结束后，填充最后一个时间点 (索引 n_steps) 的各个剖面/日志值。
        这是因为主循环计算的是从 t_i 到 t_{i+1} 的变化，所以对于 t_{n_steps} (即 time_sim[-1])
        时刻的瞬时产热、功率、控制状态等需要基于该时刻的温度和车速重新计算一次。
        温度值 T_xxx_hist[n_steps] 本身已在循环的最后一步正确计算并存储。
        """
        sp = self.sp
        n = self.n_steps # 最后一个时间点的索引，对应 self.time_sim[n]

        # 获取仿真结束时 (t=n) 的系统状态 (此时 T_xxx_hist[n] 已经是最终温度)
        # 但 v_vehicle_profile_hist[n] 和 powertrain_chiller_active_log[n] 还是上一步 (n-1) 计算时的值
        # 我们需要基于 time_sim[n] 重新计算这些量
        final_states_at_n = self.data_manager.get_current_states(n) # 获取已更新的温度 T_hist[n]

        # --- 1. 重新计算最后一个时间点 (t_n) 的车速 ---
        v_vehicle_final_kmh = self.vehicle_model.get_current_speed_kmh(self.data_manager.time_sim[n])
        self.data_manager.v_vehicle_profile_hist[n] = v_vehicle_final_kmh # 更新车速历史数组的最后一点

        # --- 2. 重新计算最后一个时间点 (t_n) 的动力总成产热和逆变器输入功率 ---
        Q_gen_motor_final, Q_gen_inv_final, P_inv_in_final = \
            self.vehicle_model.get_powertrain_heat_generation(v_vehicle_final_kmh)
        self.data_manager.Q_gen_motor_profile_hist[n] = Q_gen_motor_final
        self.data_manager.Q_gen_inv_profile_hist[n] = Q_gen_inv_final

        # --- 3. 重新计算最后一个时间点 (t_n) 的座舱热负荷和实际制冷功率 ---
        Q_cabin_load_final = self.cabin_model.get_cabin_total_heat_load(final_states_at_n["T_cabin"], v_vehicle_final_kmh)
        Q_cabin_cool_final = self.cabin_model.get_cabin_cooling_power(final_states_at_n["T_cabin"])
        self.data_manager.Q_cabin_load_total_hist[n] = Q_cabin_load_final
        self.data_manager.Q_cabin_cool_actual_hist[n] = Q_cabin_cool_final

        # --- 4. 重新计算最后一个时间点 (t_n) 的冷却系统状态和相关热流/功率 ---
        # 注意：run_cooling_loop_logic 内部的滞环状态 (如 self.thermal_system.powertrain_chiller_on_state, self.thermal_system.current_ltr_level_idx_state)
        # 已经是仿真循环最后一步迭代后更新的状态，这里再次调用会基于 T_hist[n] 和这些最新的内部状态来决定 t_n 时刻的输出。
        cooling_loop_outputs_final = self.thermal_system.run_cooling_loop_logic(final_states_at_n, Q_cabin_cool_final)

        self.data_manager.powertrain_chiller_active_log[n] = 1 if cooling_loop_outputs_final["powertrain_chiller_on_current_step"] else 0
        self.data_manager.Q_coolant_chiller_actual_hist[n] = cooling_loop_outputs_final["Q_coolant_chiller_actual"]
        self.data_manager.P_comp_elec_profile_hist[n] = cooling_loop_outputs_final["P_comp_elec"]
        self.data_manager.Q_coolant_from_LCC_hist[n] = cooling_loop_outputs_final["Q_coolant_from_LCC"]
        self.data_manager.LTR_level_log[n] = cooling_loop_outputs_final["LTR_level"]
        self.data_manager.P_LTR_fan_actual_hist[n] = cooling_loop_outputs_final["P_LTR_fan_actual"]
        self.data_manager.Q_LTR_hist[n] = cooling_loop_outputs_final["Q_LTR_to_ambient"]
        self.data_manager.LTR_effectiveness_log[n] = cooling_loop_outputs_final["LTR_effectiveness"]

        # --- 5. 重新计算最后一个时间点 (t_n) 的电池产热 ---
        # 此时不需要再计算 dT/dt，因为温度已经是最终值了，只需要 Q_gen_batt 本身。
        P_elec_total_batt_out_final = P_inv_in_final + cooling_loop_outputs_final["P_comp_elec"] + cooling_loop_outputs_final["P_LTR_fan_actual"]
        Q_gen_batt_final = 0
        try:
            Q_gen_batt_final = hv.Q_batt_func(P_elec_total_batt_out_final, sp.u_batt, sp.R_int_batt)
        except AttributeError: pass # 忽略函数缺失错误
        except Exception: pass    # 忽略其他计算错误
        self.data_manager.Q_gen_batt_profile_hist[n] = Q_gen_batt_final

        # 如果 n=0 (即仿真只有一个时间点 t=0，总步数为0)，
        # 这些值应与 _initialize_simulation_state_t0 中为索引0设置的值一致或被其覆盖。
        # 当前结构确保了 _initialize_simulation_state_t0 首先为索引0设置了所有剖面值。
        # 如果 n_steps=0, 主循环不执行，此函数会基于 t=0 的状态重新计算 t=0 的剖面，这应该是冗余但无害的。
        if n == 0:
            pass # t=0 的剖面值已在初始化时设置。
