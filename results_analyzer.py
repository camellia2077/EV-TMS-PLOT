# results_analyzer.py
import numpy as np
import heat_vehicle as hv
from plotting import SimulationPlotter

class ResultsAnalyzer:
    def __init__(self, simulation_results, sp):
        self.raw_results = simulation_results
        self.sp = sp
        self.n_steps = int(sp.sim_duration / sp.dt)
        self.time_sim = simulation_results["time_sim"]
        self.processed_data = {}

    def post_process_data(self):
        """
        Calculates derived data like inverter input power and total battery power.
        Prepares data structures for plotting and further analysis.
        """
        # Calculate P_inv_in_profile and P_elec_total_profile
        v_vehicle_profile = self.raw_results['speed_profile']
        P_comp_elec_profile = self.raw_results['ac_power_log']
        n_points = len(v_vehicle_profile)

        P_inv_in_profile_hist = np.zeros(n_points)
        for idx in range(n_points):
            P_wheel_i = hv.P_wheel_func(v_vehicle_profile[idx], self.sp.m_vehicle, self.sp.T_ambient)
            P_motor_in_i = hv.P_motor_func(P_wheel_i, self.sp.eta_motor)
            P_inv_in_profile_hist[idx] = P_motor_in_i / self.sp.eta_inv if self.sp.eta_inv > 0 else 0
        
        P_elec_total_profile_hist = P_inv_in_profile_hist + P_comp_elec_profile

        self.processed_data['time_data'] = self.raw_results['time_sim']
        self.processed_data['temperatures'] = self.raw_results['temperatures_data']
        self.processed_data['ac_power_log'] = self.raw_results['ac_power_log']
        self.processed_data['cabin_cool_power_log'] = self.raw_results['cooling_system_logs']['Q_cabin_evap_cooling']
        self.processed_data['speed_profile'] = self.raw_results['speed_profile']
        self.processed_data['heat_gen_profiles'] = self.raw_results['heat_gen_data']
        self.processed_data['battery_power_profiles'] = {
            'inv_in': P_inv_in_profile_hist,
            'comp_elec': P_comp_elec_profile, 
            'total_elec': P_elec_total_profile_hist
        }
        self.processed_data['cooling_system_logs'] = self.raw_results['cooling_system_logs']
        
        self.processed_data['sim_params_dict'] = {
            'T_ambient': self.sp.T_ambient,
            'T_motor_target': self.sp.T_motor_target,
            'T_inv_target': self.sp.T_inv_target,
            'T_batt_target_high': self.sp.T_batt_target_high,
            'T_batt_stop_cool': self.sp.T_batt_stop_cool,
            'T_cabin_target': self.sp.T_cabin_target,
            'v_start': self.sp.v_start,
            'v_end': self.sp.v_end,
            'sim_duration': self.sp.sim_duration,
            'dt': self.sp.dt,
            'eta_comp_drive': self.sp.eta_comp_drive,
            'ramp_up_time_sec': self.sp.ramp_up_time_sec,
            'cabin_cooling_temp_thresholds': self.sp.cabin_cooling_temp_thresholds,
            'cabin_cooling_power_levels': self.sp.cabin_cooling_power_levels,
            'figure_width_inches': self.sp.figure_width_inches,
            'figure_height_inches': self.sp.figure_height_inches,
            'figure_dpi': self.sp.figure_dpi,
            'legend_font_size': self.sp.legend_font_size,
            'axis_label_font_size': self.sp.axis_label_font_size,
            'tick_label_font_size': self.sp.tick_label_font_size,
            'title_font_size': self.sp.title_font_size,

            'UA_LTR_max': getattr(self.sp, 'UA_LTR_max', None), # 使用 getattr 添加 LTR 参数
            'LTR_effectiveness_levels': getattr(self.sp, 'LTR_effectiveness_levels', None),
            'LTR_effectiveness_factors': getattr(self.sp, 'LTR_effectiveness_factors', None),
            'LTR_coolant_temp_thresholds': getattr(self.sp, 'LTR_coolant_temp_thresholds', None),
            'UA_coolant_LCC': getattr(self.sp, 'UA_coolant_LCC', None),
            
            
        }
        return self.processed_data

    def analyze_chiller_transitions(self):
        print("\n--- Chiller 状态 Transition Points (Analyzed) ---")
        powertrain_chiller_active_log = self.raw_results['cooling_system_logs']['chiller_active']
        time_sim = self.raw_results['time_sim']
        n_points = len(powertrain_chiller_active_log)

        if n_points <= 1:
            print("  Simulation has less than 2 steps, cannot detect transitions.")
            return

        found_transitions = False
        for k in range(1, n_points): 
            current_chiller_state = powertrain_chiller_active_log[k]
            previous_chiller_state = powertrain_chiller_active_log[k-1]

            if current_chiller_state != previous_chiller_state:
                transition_time_sec = time_sim[k]
                transition_time_min = transition_time_sec / 60
                if current_chiller_state == 1 and previous_chiller_state == 0:
                    print(f"  Transition: OFF (0) -> ON (1) at Time: {transition_time_sec:.2f} s ({transition_time_min:.2f} min)")
                    found_transitions = True
                elif current_chiller_state == 0 and previous_chiller_state == 1:
                    print(f"  Transition: ON (1) -> OFF (0) at Time: {transition_time_sec:.2f} s ({transition_time_min:.2f} min)")
                    found_transitions = True
        
        if not found_transitions:
            print("  No powertrain chiller state transitions recorded during the simulation.")

    def print_temperature_extrema(self, all_temperature_extrema):
        print("\n--- Local Temperature Extrema (Analyzed) ---")
        for component_name, extrema in all_temperature_extrema.items():
            if extrema['minima']:
                print(f"\n{component_name} - 局部最低点:")
                for time_min, temp_c in extrema['minima']:
                    print(f"  时间: {time_min:.2f} 分钟, 温度: {temp_c:.2f} °C")
            if extrema['maxima']:
                print(f"\n{component_name} - 局部最高点:")
                for time_min, temp_c in extrema['maxima']:
                    print(f"  时间: {time_min:.2f} 分钟, 温度: {temp_c:.2f} °C")

    def print_average_values(self):
        print("\n--- 各项数据平均值 ---")
        processed_data = self.processed_data 

        if 'temperatures' in processed_data:
            print("\n  平均温度 (°C):")
            for component, temp_data in processed_data['temperatures'].items():
                if temp_data is not None and len(temp_data) > 0:
                    avg_temp = np.mean(temp_data)
                    print(f"    {component.capitalize()}温度: {avg_temp:.2f} °C")

        print("\n  制冷系统运行相关平均值:")
        if 'ac_power_log' in processed_data and processed_data['ac_power_log'] is not None and len(processed_data['ac_power_log']) > 0:
            avg_ac_power = np.mean(processed_data['ac_power_log'])
            print(f"    空调压缩机总电耗: {avg_ac_power:.2f} W")
        
        cooling_logs = processed_data.get('cooling_system_logs', {})
        q_ltr_to_ambient = cooling_logs.get('Q_LTR_to_ambient')
        if q_ltr_to_ambient is not None and len(q_ltr_to_ambient) > 0:
            avg_q_ltr = np.mean(q_ltr_to_ambient)
            print(f"    外置散热器(LTR)实际散热功率: {avg_q_ltr:.2f} W") # 修改标签
        
        # --- 添加 LCC 热量 ---
        q_coolant_from_lcc = cooling_logs.get('Q_coolant_from_LCC')
        if q_coolant_from_lcc is not None and len(q_coolant_from_lcc) > 0:
            avg_q_lcc = np.mean(q_coolant_from_lcc)
            print(f"    LCC从制冷剂吸收热量: {avg_q_lcc:.2f} W")

        # --- Chiller 热量 (键名已更新) ---
        q_coolant_to_chiller = cooling_logs.get('Q_coolant_to_chiller')
        if q_coolant_to_chiller is not None and len(q_coolant_to_chiller) > 0:
            avg_q_chiller = np.mean(q_coolant_to_chiller)
            print(f"    冷却液到Chiller的热量: {avg_q_chiller:.2f} W")

        if 'speed_profile' in processed_data and processed_data['speed_profile'] is not None and len(processed_data['speed_profile']) > 0:
            avg_speed = np.mean(processed_data['speed_profile'])
            print(f"\n  平均车速: {avg_speed:.2f} km/h")

        if 'heat_gen_profiles' in processed_data:
            print("\n  平均产热功率 (W):")
            for component, heat_data in processed_data['heat_gen_profiles'].items():
                if heat_data is not None and len(heat_data) > 0:
                    avg_heat = np.mean(heat_data)
                    name_map_heat = {
                        'motor': '电机产热',
                        'inv': '逆变器产热',
                        'batt': '电池产热',
                        'cabin_load': '座舱热负荷'
                    }
                    display_name = name_map_heat.get(component, component.capitalize())
                    print(f"    {display_name}: {avg_heat:.2f} W")

        if 'battery_power_profiles' in processed_data:
            print("\n  平均电池相关功率 (W):")
            for profile_name, power_data in processed_data['battery_power_profiles'].items():
                if power_data is not None and len(power_data) > 0:
                    avg_power = np.mean(power_data)
                    name_map_battery = {
                        'inv_in': '驱动用电功率 (逆变器输入)',
                        'comp_elec': '空调压缩机电功率',
                        'total_elec': '总电池输出功率'
                    }
                    display_name = name_map_battery.get(profile_name, profile_name.capitalize())
                    if profile_name != 'comp_elec' or 'ac_power_log' not in processed_data:
                         print(f"    {display_name}: {avg_power:.2f} W")

        if 'cabin_cool_power_log' in processed_data and processed_data['cabin_cool_power_log'] is not None and len(processed_data['cabin_cool_power_log']) > 0:
            avg_cabin_cool_power = np.mean(processed_data['cabin_cool_power_log'])
            print(f"\n  平均座舱蒸发器制冷功率: {avg_cabin_cool_power:.2f} W")
        
        try:
            q_motor = processed_data['heat_gen_profiles']['motor']
            q_inv = processed_data['heat_gen_profiles']['inv']
            q_batt = processed_data['heat_gen_profiles']['batt']
            q_cabin_load = processed_data['heat_gen_profiles']['cabin_load']
            
            # 获取散热量 (使用更新后的键名)
            q_ltr_cb = cooling_logs.get('Q_LTR_to_ambient')      # LTR 散热
            q_pt_chiller_cb = cooling_logs.get('Q_coolant_to_chiller') # Chiller 从冷却液吸收热量
            q_cabin_evap_cb = cooling_logs.get('Q_cabin_evap_cooling') # 座舱蒸发器吸收热量

            # LCC 热量 (从制冷剂到冷却液)
            q_lcc_cb = cooling_logs.get('Q_coolant_from_LCC')

            all_components_present = all(
                d is not None and len(d) > 0 for d in
                [q_motor, q_inv, q_batt, q_cabin_load, q_ltr_cb, q_pt_chiller_cb, q_cabin_evap_cb]
            )

            if all_components_present:
                target_len = len(self.time_sim)

                q_motor_arr = SimulationPlotter._ensure_profile_length(np.array(q_motor), target_len)
                q_inv_arr = SimulationPlotter._ensure_profile_length(np.array(q_inv), target_len)
                q_batt_arr = SimulationPlotter._ensure_profile_length(np.array(q_batt), target_len)
                q_cabin_load_arr = SimulationPlotter._ensure_profile_length(np.array(q_cabin_load), target_len)
                q_ltr_arr = SimulationPlotter._ensure_profile_length(np.array(q_ltr_cb), target_len)
                q_pt_chiller_arr = SimulationPlotter._ensure_profile_length(np.array(q_pt_chiller_cb), target_len)
                q_cabin_evap_arr = SimulationPlotter._ensure_profile_length(np.array(q_cabin_evap_cb), target_len)

                # 总产热/负荷 = 电机产热 + 逆变器产热 + 电池产热 + 座舱热负荷
                total_heat_load = q_motor_arr + q_inv_arr + q_batt_arr + q_cabin_load_arr
                # 总散热/制冷 = LTR散热 + Chiller从冷却液吸热 + 座舱蒸发器吸热
                total_heat_rejection_cooling = q_ltr_arr + q_pt_chiller_arr + q_cabin_evap_arr

                avg_total_load = np.mean(total_heat_load)
                avg_total_rejection_cooling = np.mean(total_heat_rejection_cooling)
                print("\n  平均总热负荷 vs 总散热/制冷功率 (W):")
                print(f"    总产热/负荷功率: {avg_total_load:.2f} W")
                print(f"    总散热系统移除功率 (LTR+Chiller+CabinEvap): {avg_total_rejection_cooling:.2f} W")
        except KeyError as e:
            print(f"\n  注意: 无法计算平均总热平衡，缺少数据: {e}")
        except Exception as e:
            print(f"\n  计算平均总热平衡时发生错误: {e}")

        print("\n--- 平均值打印结束 ---")