# simulation_engine.py
import numpy as np
import heat_vehicle as hv # 假设此模块存在并包含所用函数
from heat_cabin_class import CabinHeatCalculator # 假设此类存在

class DataManager:
    """
    管理所有仿真数据、历史记录数组和时间步。
    """
    def __init__(self, sp):
        self.sp = sp
        self.n_steps = int(sp.sim_duration / sp.dt)
        self.time_sim = np.linspace(0, sp.sim_duration, self.n_steps + 1)

        # --- 温度历史记录 ---
        self.T_motor_hist = np.zeros(self.n_steps + 1)
        self.T_inv_hist = np.zeros(self.n_steps + 1)
        self.T_batt_hist = np.zeros(self.n_steps + 1)
        self.T_cabin_hist = np.zeros(self.n_steps + 1)
        self.T_coolant_hist = np.zeros(self.n_steps + 1)

        # --- 控制状态日志 ---
        self.powertrain_chiller_active_log = np.zeros(self.n_steps + 1, dtype=int)
        self.LTR_level_log = np.zeros(self.n_steps + 1, dtype=int)
        self.P_LTR_fan_actual_hist = np.zeros(self.n_steps + 1)
        self.LTR_effectiveness_log = np.zeros(self.n_steps + 1)

        # --- 热流日志 ---
        self.Q_LTR_hist = np.zeros(self.n_steps + 1)
        self.Q_coolant_from_LCC_hist = np.zeros(self.n_steps + 1)
        self.Q_coolant_chiller_actual_hist = np.zeros(self.n_steps + 1)
        self.Q_cabin_load_total_hist = np.zeros(self.n_steps + 1)
        self.Q_cabin_cool_actual_hist = np.zeros(self.n_steps + 1)

        # --- 产热和功率日志 ---
        self.v_vehicle_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_motor_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_inv_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_batt_profile_hist = np.zeros(self.n_steps + 1)
        self.P_comp_elec_profile_hist = np.zeros(self.n_steps + 1)

    def set_initial_values_from_sp(self):
        """设置来自 sp 参数的初始温度和速度。"""
        sp = self.sp
        self.T_motor_hist[0] = sp.T_motor_init
        self.T_inv_hist[0] = sp.T_inv_init
        self.T_batt_hist[0] = sp.T_batt_init
        self.T_cabin_hist[0] = sp.T_cabin_init
        self.T_coolant_hist[0] = sp.T_coolant_init
        self.v_vehicle_profile_hist[0] = sp.v_start
        
        # 初始 LTR 状态
        initial_coolant_temp_for_ltr = self.T_coolant_hist[0]
        current_ltr_level_idx = 0
        initial_UA_LTR_effective = 0
        initial_P_LTR_fan = 0
        if hasattr(sp, 'LTR_coolant_temp_thresholds') and hasattr(sp, 'LTR_UA_values_at_levels') and hasattr(sp, 'LTR_fan_power_levels'):
            for lvl_idx_init in range(len(sp.LTR_coolant_temp_thresholds)):
                if initial_coolant_temp_for_ltr > sp.LTR_coolant_temp_thresholds[lvl_idx_init]:
                    current_ltr_level_idx = lvl_idx_init + 1
                else:
                    break
            if current_ltr_level_idx < len(sp.LTR_UA_values_at_levels):
                 initial_UA_LTR_effective = sp.LTR_UA_values_at_levels[current_ltr_level_idx]
                 initial_P_LTR_fan = sp.LTR_fan_power_levels[current_ltr_level_idx]
            else: 
                current_ltr_level_idx = 0 
                initial_UA_LTR_effective = sp.LTR_UA_values_at_levels[0] if hasattr(sp, 'LTR_UA_values_at_levels') and len(sp.LTR_UA_values_at_levels) > 0 else 0
                initial_P_LTR_fan = sp.LTR_fan_power_levels[0] if hasattr(sp, 'LTR_fan_power_levels') and len(sp.LTR_fan_power_levels) > 0 else 0
        self.LTR_level_log[0] = current_ltr_level_idx
        self.P_LTR_fan_actual_hist[0] = initial_P_LTR_fan
        self.LTR_effectiveness_log[0] = (initial_UA_LTR_effective / sp.UA_LTR_max) if hasattr(sp, 'UA_LTR_max') and sp.UA_LTR_max > 0 else (1.0 if initial_UA_LTR_effective > 0 else 0.0)
        self.Q_LTR_hist[0] = max(0, initial_UA_LTR_effective * (initial_coolant_temp_for_ltr - sp.T_ambient))

        # 初始座舱冷却功率
        Q_cabin_cool_initial = 0
        if hasattr(sp, 'cabin_cooling_power_levels') and hasattr(sp, 'cabin_cooling_temp_thresholds') and sp.cabin_cooling_power_levels:
            Q_cabin_cool_initial = sp.cabin_cooling_power_levels[-1] 
            for j in range(len(sp.cabin_cooling_temp_thresholds)):
                if self.T_cabin_hist[0] <= sp.cabin_cooling_temp_thresholds[j]:
                    Q_cabin_cool_initial = sp.cabin_cooling_power_levels[j]
                    break
        self.Q_cabin_cool_actual_hist[0] = max(0, Q_cabin_cool_initial)
        
        # 初始冷却器状态
        self.powertrain_chiller_active_log[0] = 0 
        self.Q_coolant_chiller_actual_hist[0] = 0.0

    def get_current_states(self, i):
        """获取第 i 步的当前状态。"""
        return {
            "time_sec": self.time_sim[i],
            "T_cabin": self.T_cabin_hist[i],
            "T_motor": self.T_motor_hist[i],
            "T_inv": self.T_inv_hist[i],
            "T_batt": self.T_batt_hist[i],
            "T_coolant": self.T_coolant_hist[i],
            "v_vehicle_kmh": self.v_vehicle_profile_hist[i], # 这是区间开始时的速度
            "powertrain_chiller_on_prev_state": bool(self.powertrain_chiller_active_log[i]) # 用于滞环控制
        }

    def record_step_data(self, i, data_for_step_i, next_step_temperatures):
        """记录第 i 步的计算数据和第 i+1 步的温度。"""
        # 更新下一时间步的温度
        self.T_motor_hist[i+1] = next_step_temperatures["T_motor_next"]
        self.T_inv_hist[i+1] = next_step_temperatures["T_inv_next"]
        self.T_batt_hist[i+1] = next_step_temperatures["T_batt_next"]
        self.T_cabin_hist[i+1] = next_step_temperatures["T_cabin_next"]
        self.T_coolant_hist[i+1] = next_step_temperatures["T_coolant_next"]

        # 记录当前时间步 i 的日志/剖面数据
        self.v_vehicle_profile_hist[i] = data_for_step_i["v_vehicle_current_kmh"]
        self.Q_gen_motor_profile_hist[i] = data_for_step_i["Q_gen_motor"]
        self.Q_gen_inv_profile_hist[i] = data_for_step_i["Q_gen_inv"]
        self.Q_cabin_load_total_hist[i] = data_for_step_i["Q_cabin_load_total"]
        self.Q_cabin_cool_actual_hist[i] = data_for_step_i["Q_cabin_cool_actual"]
        self.powertrain_chiller_active_log[i] = 1 if data_for_step_i["powertrain_chiller_on_current_step"] else 0
        self.Q_coolant_chiller_actual_hist[i] = data_for_step_i["Q_coolant_chiller_actual"]
        self.P_comp_elec_profile_hist[i] = data_for_step_i["P_comp_elec"]
        self.Q_coolant_from_LCC_hist[i] = data_for_step_i["Q_coolant_from_LCC"]
        self.LTR_level_log[i] = data_for_step_i["LTR_level"]
        self.P_LTR_fan_actual_hist[i] = data_for_step_i["P_LTR_fan_actual"]
        self.Q_LTR_hist[i] = data_for_step_i["Q_LTR_to_ambient"]
        self.LTR_effectiveness_log[i] = data_for_step_i["LTR_effectiveness"]
        self.Q_gen_batt_profile_hist[i] = data_for_step_i["Q_gen_batt"]

    def package_results(self):
        """将所有历史数据打包成字典以供返回。"""
        return {
            "time_sim": self.time_sim,
            "temperatures_data": {
                'motor': self.T_motor_hist, 'inv': self.T_inv_hist, 'batt': self.T_batt_hist,
                'cabin': self.T_cabin_hist, 'coolant': self.T_coolant_hist
            },
            "heat_gen_data": {
                'motor': self.Q_gen_motor_profile_hist, 'inv': self.Q_gen_inv_profile_hist,
                'batt': self.Q_gen_batt_profile_hist, 'cabin_load': self.Q_cabin_load_total_hist
            },
            "cooling_system_logs": {
                'chiller_active': self.powertrain_chiller_active_log,
                'LTR_level': self.LTR_level_log, 'P_LTR_fan': self.P_LTR_fan_actual_hist,
                'LTR_effectiveness_factor_equiv': self.LTR_effectiveness_log,
                'Q_LTR_to_ambient': self.Q_LTR_hist,
                'Q_coolant_from_LCC': self.Q_coolant_from_LCC_hist,
                'Q_coolant_to_chiller': self.Q_coolant_chiller_actual_hist,
                'Q_cabin_evap_cooling': self.Q_cabin_cool_actual_hist
            },
            "ac_power_log": self.P_comp_elec_profile_hist,
            "speed_profile": self.v_vehicle_profile_hist
        }

class VehicleMotionModel:
    """处理车辆运动和相关动力总成热量产生。"""
    def __init__(self, sp):
        self.sp = sp

    def get_current_speed_kmh(self, current_time_sec):
        sp = self.sp
        if current_time_sec <= sp.ramp_up_time_sec:
            speed_increase_ratio = (current_time_sec / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 1.0
            v_vehicle_current = sp.v_start + (sp.v_end - sp.v_start) * speed_increase_ratio
        else:
            v_vehicle_current = sp.v_end
        return max(min(sp.v_start, sp.v_end), min(max(sp.v_start, sp.v_end), v_vehicle_current))

    def get_powertrain_heat_generation(self, v_vehicle_current_kmh):
        sp = self.sp
        P_inv_in = 0; Q_gen_motor = 0; Q_gen_inv = 0
        try:
            P_wheel = hv.P_wheel_func(v_vehicle_current_kmh, sp.m_vehicle, sp.T_ambient)
            P_motor_in = hv.P_motor_func(P_wheel, sp.eta_motor)
            P_inv_in = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0
            Q_gen_motor = hv.Q_mot_func(P_motor_in, sp.eta_motor)
            Q_gen_inv = hv.Q_inv_func(P_motor_in, sp.eta_inv)
        except AttributeError as e:
            print(f"警告: 动力总成产热函数缺失/错误 (heat_vehicle.py)。{e}")
        except Exception as e:
            print(f"警告: 动力总成产热时发生意外错误。{e}")
        return Q_gen_motor, Q_gen_inv, P_inv_in

class CabinModel:
    """管理座舱热负荷和座舱冷却。"""
    def __init__(self, sp):
        self.sp = sp
        try:
            self.cabin_heat_calculator = CabinHeatCalculator(
                N_passengers=sp.N_passengers, v_air_internal_mps=sp.v_air_in_mps,
                A_body=sp.A_body, R_body=sp.R_body, A_glass=sp.A_glass, R_glass=sp.R_glass,
                SHGC=sp.SHGC, A_glass_sun=sp.A_glass_sun, W_out_summer=sp.W_out_summer,
                W_in_target=sp.W_in_target, fraction_fresh_air=sp.fresh_air_fraction,
                cp_air=sp.cp_air, h_fg=getattr(sp, 'h_fg_water', 2.45e6),
                Q_powertrain=getattr(sp, 'Q_cabin_powertrain_invasion', 50),
                Q_electronics=getattr(sp, 'Q_cabin_electronics', 100),
                q_person=getattr(sp, 'q_person_heat', 100)
            )
            print("CabinHeatCalculator 在 CabinModel 中初始化成功。")
        except AttributeError as e:
            print(f"CabinModel 初始化 CabinHeatCalculator 错误: {e}")
            self.cabin_heat_calculator = None
        except Exception as e:
            print(f"CabinModel 初始化 CabinHeatCalculator 时发生意外错误: {e}")
            self.cabin_heat_calculator = None

    def get_cabin_total_heat_load(self, current_cabin_temp_C, v_vehicle_current_kmh):
        sp = self.sp
        Q_cabin_load_total = 0
        if self.cabin_heat_calculator:
            try:
                Q_cabin_load_total = self.cabin_heat_calculator.calculate_total_cabin_heat_load(
                    T_outside=sp.T_ambient, T_inside=current_cabin_temp_C,
                    v_vehicle_kmh=v_vehicle_current_kmh, I_solar=getattr(sp, 'I_solar_summer', 0)
                )
            except Exception as e:
                print(f"警告: 计算座舱热负荷时出错。{e}")
        else:
            print("警告: CabinHeatCalculator 不可用，无法计算座舱热负荷。")
        return Q_cabin_load_total

    def get_cabin_cooling_power(self, current_cabin_temp_C):
        sp = self.sp
        Q_cabin_cool_actual = 0
        if hasattr(sp, 'cabin_cooling_power_levels') and hasattr(sp, 'cabin_cooling_temp_thresholds') and sp.cabin_cooling_power_levels:
            Q_cabin_cool_actual = sp.cabin_cooling_power_levels[-1] # 默认最大功率
            for j in range(len(sp.cabin_cooling_temp_thresholds)):
                if current_cabin_temp_C <= sp.cabin_cooling_temp_thresholds[j]:
                    Q_cabin_cool_actual = sp.cabin_cooling_power_levels[j]
                    break
        return max(0, Q_cabin_cool_actual)

class ThermalManagementSystem:
    """
    管理冷却回路（冷却器、压缩机、LCC、LTR）和动力总成部件的热模型。
    """
    def __init__(self, sp, cop_value):
        self.sp = sp
        self.cop = cop_value
        self.powertrain_chiller_on_state = False # 用于滞环的内部状态

    def run_cooling_loop_logic(self, current_system_states, Q_cabin_cool_actual_W):
        sp = self.sp
        # 从 current_system_states 解包所需变量
        current_T_coolant = current_system_states["T_coolant"]
        current_T_motor = current_system_states["T_motor"]
        current_T_inv = current_system_states["T_inv"]
        current_T_batt = current_system_states["T_batt"]
        # prev_chiller_state = current_system_states["powertrain_chiller_on_prev_state"] # 使用内部状态

        # 1. 动力总成冷却器控制（滞环）
        T_motor_target = getattr(sp, 'T_motor_target', float('inf'))
        T_inv_target = getattr(sp, 'T_inv_target', float('inf'))
        T_batt_target_high = getattr(sp, 'T_batt_target_high', float('inf'))
        T_motor_stop_cool = getattr(sp, 'T_motor_stop_cool', float('-inf'))
        T_inv_stop_cool = getattr(sp, 'T_inv_stop_cool', float('-inf'))
        T_batt_stop_cool = getattr(sp, 'T_batt_stop_cool', float('-inf'))

        start_cooling = (current_T_motor > T_motor_target) or \
                        (current_T_inv > T_inv_target) or \
                        (current_T_batt > T_batt_target_high)
        stop_cooling = (current_T_motor < T_motor_stop_cool) and \
                       (current_T_inv < T_inv_stop_cool) and \
                       (current_T_batt < T_batt_stop_cool)

        if start_cooling:
            self.powertrain_chiller_on_state = True
        elif stop_cooling:
            self.powertrain_chiller_on_state = False
        
        powertrain_chiller_on_current_step = self.powertrain_chiller_on_state

        # 2. 冷却器传热
        Q_chiller_potential = 0
        if current_T_coolant > sp.T_evap_sat_for_UA_calc: # T_evap_sat_for_UA_calc 是制冷剂温度
            Q_chiller_potential = sp.UA_coolant_chiller * (current_T_coolant - sp.T_evap_sat_for_UA_calc)
        Q_chiller_potential = max(0, Q_chiller_potential)
        Q_coolant_chiller_actual = min(Q_chiller_potential, sp.max_chiller_cool_power) if powertrain_chiller_on_current_step else 0

        # 3. 总蒸发负荷和压缩机功率
        Q_evap_total_needed = Q_cabin_cool_actual_W + Q_coolant_chiller_actual
        P_comp_elec = 0.0; P_comp_mech = 0.0
        if Q_evap_total_needed > 0 and self.cop > 0 and hasattr(sp, 'eta_comp_drive') and sp.eta_comp_drive > 0:
            P_comp_mech = Q_evap_total_needed / self.cop
            P_comp_elec = P_comp_mech / sp.eta_comp_drive
        
        # 4. LCC 传热 (Q_condenser_total)
        Q_coolant_from_LCC = Q_evap_total_needed + P_comp_mech

        # 5. LTR 风扇控制和散热
        current_ltr_level_idx = 0; UA_LTR_effective = 0; P_LTR_fan_actual = 0
        if hasattr(sp, 'LTR_coolant_temp_thresholds') and hasattr(sp, 'LTR_UA_values_at_levels') and hasattr(sp, 'LTR_fan_power_levels'):
            for lvl_idx in range(len(sp.LTR_coolant_temp_thresholds)):
                if current_T_coolant > sp.LTR_coolant_temp_thresholds[lvl_idx]:
                    current_ltr_level_idx = lvl_idx + 1
                else:
                    break
            if current_ltr_level_idx < len(sp.LTR_UA_values_at_levels):
                UA_LTR_effective = sp.LTR_UA_values_at_levels[current_ltr_level_idx]
                P_LTR_fan_actual = sp.LTR_fan_power_levels[current_ltr_level_idx]
            else: 
                current_ltr_level_idx = 0
                UA_LTR_effective = sp.LTR_UA_values_at_levels[0] if hasattr(sp, 'LTR_UA_values_at_levels') and len(sp.LTR_UA_values_at_levels) > 0 else 0
                P_LTR_fan_actual = sp.LTR_fan_power_levels[0] if hasattr(sp, 'LTR_fan_power_levels') and len(sp.LTR_fan_power_levels) > 0 else 0

        Q_LTR_to_ambient = max(0, UA_LTR_effective * (current_T_coolant - sp.T_ambient))
        LTR_effectiveness = (UA_LTR_effective / sp.UA_LTR_max) if hasattr(sp, 'UA_LTR_max') and sp.UA_LTR_max > 0 else (1.0 if UA_LTR_effective > 0 else 0.0)
        
        return {
            "powertrain_chiller_on_current_step": powertrain_chiller_on_current_step,
            "Q_coolant_chiller_actual": Q_coolant_chiller_actual,
            "P_comp_elec": P_comp_elec, "P_comp_mech": P_comp_mech,
            "Q_coolant_from_LCC": Q_coolant_from_LCC,
            "LTR_level": current_ltr_level_idx, "P_LTR_fan_actual": P_LTR_fan_actual,
            "Q_LTR_to_ambient": Q_LTR_to_ambient, "LTR_effectiveness": LTR_effectiveness,
        }

    def get_powertrain_thermal_derivatives_and_heats(self, current_system_states, P_inv_in_W, cooling_loop_outputs, Q_gen_motor_W, Q_gen_inv_W):
        sp = self.sp
        current_T_motor = current_system_states["T_motor"]
        current_T_inv = current_system_states["T_inv"]
        current_T_batt = current_system_states["T_batt"]
        current_T_coolant = current_system_states["T_coolant"]
        P_comp_elec = cooling_loop_outputs["P_comp_elec"]
        P_LTR_fan_actual = cooling_loop_outputs["P_LTR_fan_actual"]

        # 电池产热
        P_elec_total_batt_out = P_inv_in_W + P_comp_elec + P_LTR_fan_actual
        Q_gen_batt = 0
        try:
            Q_gen_batt = hv.Q_batt_func(P_elec_total_batt_out, sp.u_batt, sp.R_int_batt)
        except AttributeError as e: print(f"警告: Q_batt_func 缺失。{e}")
        except Exception as e: print(f"警告: Q_batt_func 发生意外错误。{e}")

        # 动力总成部件到冷却液的传热
        Q_motor_to_coolant = sp.UA_motor_coolant * (current_T_motor - current_T_coolant)
        Q_inv_to_coolant = sp.UA_inv_coolant * (current_T_inv - current_T_coolant)
        Q_batt_to_coolant = sp.UA_batt_coolant * (current_T_batt - current_T_coolant)

        # 动力总成部件温度变化率
        dT_motor_dt = (Q_gen_motor_W - Q_motor_to_coolant) / sp.mc_motor if sp.mc_motor > 0 else 0
        dT_inv_dt = (Q_gen_inv_W - Q_inv_to_coolant) / sp.mc_inverter if sp.mc_inverter > 0 else 0
        dT_batt_dt = (Q_gen_batt - Q_batt_to_coolant) / sp.mc_battery if sp.mc_battery > 0 else 0
        
        return {
            "Q_gen_batt": Q_gen_batt,
            "Q_motor_to_coolant": Q_motor_to_coolant,
            "Q_inv_to_coolant": Q_inv_to_coolant,
            "Q_batt_to_coolant": Q_batt_to_coolant,
            "dT_motor_dt": dT_motor_dt, "dT_inv_dt": dT_inv_dt, "dT_batt_dt": dT_batt_dt,
        }

    def get_coolant_temp_derivative(self, powertrain_heats, cooling_loop_heats):
        sp = self.sp
        Q_coolant_net = (cooling_loop_heats["Q_coolant_from_LCC"] +
                         powertrain_heats["Q_motor_to_coolant"] +
                         powertrain_heats["Q_inv_to_coolant"] +
                         powertrain_heats["Q_batt_to_coolant"]) - \
                        (cooling_loop_heats["Q_LTR_to_ambient"] +
                         cooling_loop_heats["Q_coolant_chiller_actual"])
        return Q_coolant_net / sp.mc_coolant if sp.mc_coolant > 0 else 0

class SimulationEngine:
    def __init__(self, sp, cop_value):
        self.sp = sp
        self.cop = cop_value
        self.n_steps = int(sp.sim_duration / sp.dt)

        self.data_manager = DataManager(sp)
        self.vehicle_model = VehicleMotionModel(sp)
        self.cabin_model = CabinModel(sp)
        self.thermal_system = ThermalManagementSystem(sp, cop_value)

        self._initialize_simulation_state_t0()

    def _initialize_simulation_state_t0(self):
        """为 t=0 设置所有相关的初始日志和状态。"""
        sp = self.sp
        # 1. DataManager 设置基本初始温度、速度和一些基于温度的冷却状态
        self.data_manager.set_initial_values_from_sp()

        # 2. 获取 t=0 时的初始状态 (主要温度和速度)
        states_t0 = self.data_manager.get_current_states(0)

        # 3. 计算 t=0 时的座舱热负荷 (Q_cabin_cool_actual_hist[0] 已由 DataManager 设置)
        Q_cabin_load_t0 = self.cabin_model.get_cabin_total_heat_load(states_t0["T_cabin"], states_t0["v_vehicle_kmh"])
        self.data_manager.Q_cabin_load_total_hist[0] = Q_cabin_load_t0
        
        # 4. 计算 t=0 时的动力总成产热 (基于 v_start)
        Q_gen_motor_t0, Q_gen_inv_t0, P_inv_in_t0 = self.vehicle_model.get_powertrain_heat_generation(states_t0["v_vehicle_kmh"])
        self.data_manager.Q_gen_motor_profile_hist[0] = Q_gen_motor_t0
        self.data_manager.Q_gen_inv_profile_hist[0] = Q_gen_inv_t0

        # 5. 计算 t=0 时的压缩机功率和 LCC 热量
        # (Q_cabin_cool_actual_hist[0], Q_coolant_chiller_actual_hist[0] 已由 DataManager 设置)
        Q_evap_total_needed_t0 = self.data_manager.Q_cabin_cool_actual_hist[0] + self.data_manager.Q_coolant_chiller_actual_hist[0]
        P_comp_elec_t0 = 0.0; P_comp_mech_t0 = 0.0
        if Q_evap_total_needed_t0 > 0 and self.cop > 0 and hasattr(sp, 'eta_comp_drive') and sp.eta_comp_drive > 0:
             P_comp_mech_t0 = Q_evap_total_needed_t0 / self.cop
             P_comp_elec_t0 = P_comp_mech_t0 / sp.eta_comp_drive
        self.data_manager.P_comp_elec_profile_hist[0] = P_comp_elec_t0
        self.data_manager.Q_coolant_from_LCC_hist[0] = Q_evap_total_needed_t0 + P_comp_mech_t0
        # LTR 相关日志 (Q_LTR_hist[0] 等) 已由 DataManager 设置

        # 6. 计算 t=0 时的电池产热
        P_LTR_fan_t0 = self.data_manager.P_LTR_fan_actual_hist[0] # 从 DataManager 获取
        P_elec_total_batt_out_t0 = P_inv_in_t0 + P_comp_elec_t0 + P_LTR_fan_t0
        Q_gen_batt_t0 = 0
        try:
            Q_gen_batt_t0 = hv.Q_batt_func(P_elec_total_batt_out_t0, sp.u_batt, sp.R_int_batt)
        except AttributeError: pass 
        except Exception: pass
        self.data_manager.Q_gen_batt_profile_hist[0] = Q_gen_batt_t0
        
    def run_simulation(self):
        sp = self.sp
        print(f"开始重构后的仿真循环，共 {self.n_steps} 步...")

        for i in range(self.n_steps):
            current_states_at_i = self.data_manager.get_current_states(i)

            # 1. 车辆运动和动力总成产热 (电机、逆变器)
            v_vehicle_current_kmh = self.vehicle_model.get_current_speed_kmh(current_states_at_i["time_sec"])
            Q_gen_motor, Q_gen_inv, P_inv_in = self.vehicle_model.get_powertrain_heat_generation(v_vehicle_current_kmh)

            # 2. 座舱环境模型
            Q_cabin_load_total = self.cabin_model.get_cabin_total_heat_load(current_states_at_i["T_cabin"], v_vehicle_current_kmh)
            Q_cabin_cool_actual = self.cabin_model.get_cabin_cooling_power(current_states_at_i["T_cabin"])

            # 3. 冷却系统运行逻辑 (冷却器、压缩机、LCC、LTR)
            cooling_loop_outputs = self.thermal_system.run_cooling_loop_logic(current_states_at_i, Q_cabin_cool_actual)

            # 4. 动力总成热模型 (电池产热、部件到冷却液的传热、部件温度变化率)
            powertrain_thermal_outputs = self.thermal_system.get_powertrain_thermal_derivatives_and_heats(
                current_states_at_i, P_inv_in, cooling_loop_outputs, Q_gen_motor, Q_gen_inv
            )
            
            # 5. 计算座舱和冷却液温度变化率
            dT_cabin_dt = (Q_cabin_load_total - Q_cabin_cool_actual) / sp.mc_cabin if sp.mc_cabin > 0 else 0
            dT_coolant_dt = self.thermal_system.get_coolant_temp_derivative(powertrain_thermal_outputs, cooling_loop_outputs)

            # 6. 更新下一时间步 (i+1) 的温度
            next_step_temperatures = {
                "T_motor_next": current_states_at_i["T_motor"] + powertrain_thermal_outputs["dT_motor_dt"] * sp.dt,
                "T_inv_next": current_states_at_i["T_inv"] + powertrain_thermal_outputs["dT_inv_dt"] * sp.dt,
                "T_batt_next": current_states_at_i["T_batt"] + powertrain_thermal_outputs["dT_batt_dt"] * sp.dt,
                "T_cabin_next": current_states_at_i["T_cabin"] + dT_cabin_dt * sp.dt,
                "T_coolant_next": current_states_at_i["T_coolant"] + dT_coolant_dt * sp.dt
            }

            # 7. 存储当前步 i 的所有计算值和下一时间步 i+1 的温度
            data_for_step_i = {
                "v_vehicle_current_kmh": v_vehicle_current_kmh, "Q_gen_motor": Q_gen_motor, "Q_gen_inv": Q_gen_inv,
                "Q_cabin_load_total": Q_cabin_load_total, "Q_cabin_cool_actual": Q_cabin_cool_actual,
                "powertrain_chiller_on_current_step": cooling_loop_outputs["powertrain_chiller_on_current_step"],
                "Q_coolant_chiller_actual": cooling_loop_outputs["Q_coolant_chiller_actual"],
                "P_comp_elec": cooling_loop_outputs["P_comp_elec"],
                "Q_coolant_from_LCC": cooling_loop_outputs["Q_coolant_from_LCC"],
                "LTR_level": cooling_loop_outputs["LTR_level"],
                "P_LTR_fan_actual": cooling_loop_outputs["P_LTR_fan_actual"],
                "Q_LTR_to_ambient": cooling_loop_outputs["Q_LTR_to_ambient"],
                "LTR_effectiveness": cooling_loop_outputs["LTR_effectiveness"],
                "Q_gen_batt": powertrain_thermal_outputs["Q_gen_batt"]
                # P_comp_mech is not directly logged but used internally.
            }
            self.data_manager.record_step_data(i, data_for_step_i, next_step_temperatures)

        print(f"重构后的仿真循环在 {self.n_steps} 步后完成。")
        self._fill_final_step_profiles()
        return self.data_manager.package_results()

    def _fill_final_step_profiles(self):
        """填充最后一个时间点 (n_steps) 的剖面/日志值。"""
        sp = self.sp
        n = self.n_steps # 最后一个时间点的索引

        # 获取仿真结束时的状态 (温度已由循环计算并存储在 T_xxx_hist[n])
        final_states_at_n = self.data_manager.get_current_states(n) # 使用索引 n 获取 T_hist[n]
                                                                  # v_vehicle_profile_hist[n] 此时是上一步的，需要重新计算
                                                                  # powertrain_chiller_active_log[n] 此时是上一步的，需要重新计算

        # 1. 最后一个时间点的车速
        v_vehicle_final_kmh = self.vehicle_model.get_current_speed_kmh(self.data_manager.time_sim[n])
        self.data_manager.v_vehicle_profile_hist[n] = v_vehicle_final_kmh

        # 2. 最后一个时间点的动力总成产热
        Q_gen_motor_final, Q_gen_inv_final, P_inv_in_final = \
            self.vehicle_model.get_powertrain_heat_generation(v_vehicle_final_kmh)
        self.data_manager.Q_gen_motor_profile_hist[n] = Q_gen_motor_final
        self.data_manager.Q_gen_inv_profile_hist[n] = Q_gen_inv_final
        
        # 3. 最后一个时间点的座舱负荷和冷却
        Q_cabin_load_final = self.cabin_model.get_cabin_total_heat_load(final_states_at_n["T_cabin"], v_vehicle_final_kmh)
        Q_cabin_cool_final = self.cabin_model.get_cabin_cooling_power(final_states_at_n["T_cabin"])
        self.data_manager.Q_cabin_load_total_hist[n] = Q_cabin_load_final
        self.data_manager.Q_cabin_cool_actual_hist[n] = Q_cabin_cool_final

        # 4. 最后一个时间点的冷却系统状态
        # 对于最后一个点，冷却器状态通常从上一步骤延续或根据最终温度重新评估。
        # 为了与原始逻辑保持一致（倾向于延续），我们将使用 thermal_system 中已更新的滞环状态。
        # 但是，由于其他参数（如LTR）是基于 T_coolant[n] 计算的，我们将重新计算 cooling_loop_outputs。
        # run_cooling_loop_logic 会使用 self.thermal_system.powertrain_chiller_on_state，这个状态在循环的最后一次迭代中已更新。
        cooling_loop_outputs_final = self.thermal_system.run_cooling_loop_logic(final_states_at_n, Q_cabin_cool_final)
        
        self.data_manager.powertrain_chiller_active_log[n] = 1 if cooling_loop_outputs_final["powertrain_chiller_on_current_step"] else 0
        self.data_manager.Q_coolant_chiller_actual_hist[n] = cooling_loop_outputs_final["Q_coolant_chiller_actual"]
        self.data_manager.P_comp_elec_profile_hist[n] = cooling_loop_outputs_final["P_comp_elec"]
        self.data_manager.Q_coolant_from_LCC_hist[n] = cooling_loop_outputs_final["Q_coolant_from_LCC"]
        self.data_manager.LTR_level_log[n] = cooling_loop_outputs_final["LTR_level"]
        self.data_manager.P_LTR_fan_actual_hist[n] = cooling_loop_outputs_final["P_LTR_fan_actual"]
        self.data_manager.Q_LTR_hist[n] = cooling_loop_outputs_final["Q_LTR_to_ambient"]
        self.data_manager.LTR_effectiveness_log[n] = cooling_loop_outputs_final["LTR_effectiveness"]

        # 5. 最后一个时间点的电池产热
        # powertrain_thermal_outputs_final = self.thermal_system.get_powertrain_thermal_derivatives_and_heats(...)
        # 这里我们只需要 Q_gen_batt，其他 dT/dt 在这一点上不再用于更新温度。
        P_elec_total_batt_out_final = P_inv_in_final + cooling_loop_outputs_final["P_comp_elec"] + cooling_loop_outputs_final["P_LTR_fan_actual"]
        Q_gen_batt_final = 0
        try:
            Q_gen_batt_final = hv.Q_batt_func(P_elec_total_batt_out_final, sp.u_batt, sp.R_int_batt)
        except AttributeError: pass
        except Exception: pass
        self.data_manager.Q_gen_batt_profile_hist[n] = Q_gen_batt_final

        # 如果 n=0 (即仿真只有一个时间点 t=0)，这些值应与 _initialize_simulation_state_t0 中设置的一致。
        # 当前结构通过在 _initialize_simulation_state_t0 中为索引 0 设置所有剖面来确保这一点。
        if n == 0:
            pass # t=0 的剖面值已在初始化时设置。
