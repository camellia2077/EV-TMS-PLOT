# results_analyzer.py
# 后处理仿真结果、计算派生数据和分析特定事件
import numpy as np
import heat_vehicle as hv # For P_inv_in calculation
import plotting # <--- 新增导入，为了使用 ensure_profile_length

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
        self.processed_data['cabin_cool_power_log'] = self.raw_results['cooling_system_logs']['Q_cabin_evap']
        self.processed_data['speed_profile'] = self.raw_results['speed_profile']
        self.processed_data['heat_gen_profiles'] = self.raw_results['heat_gen_data']
        self.processed_data['battery_power_profiles'] = {
            'inv_in': P_inv_in_profile_hist,
            'comp_elec': P_comp_elec_profile, # Already exists in raw_results['ac_power_log']
            'total_elec': P_elec_total_profile_hist
        }
        self.processed_data['cooling_system_logs'] = self.raw_results['cooling_system_logs']
        
        # sim_params_dict for plotting
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
            'UA_coolant_radiator_max': self.sp.UA_coolant_radiator_max,
            'radiator_effectiveness_at_target': self.sp.radiator_effectiveness_at_target,
            'radiator_effectiveness_below_stop_cool': self.sp.radiator_effectiveness_below_stop_cool
        }
        return self.processed_data

    def analyze_chiller_transitions(self):
        """
        Identifies and prints points where the powertrain chiller state transitions.
        """
        print("\n--- Chiller 状态 Transition Points (Analyzed) ---")
        powertrain_chiller_active_log = self.raw_results['cooling_system_logs']['chiller_active']
        time_sim = self.raw_results['time_sim']
        n_points = len(powertrain_chiller_active_log)

        if n_points <= 1:
            print("  Simulation has less than 2 steps, cannot detect transitions.")
            return

        found_transitions = False
        for k in range(1, n_points): # Iterate from the second element
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
        """
        Prints the local temperature extrema found by the plotting module.
        """
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
        """
        Calculates and prints the average value for each relevant data series.
        """
        print("\n--- 各项数据平均值 ---")
        processed_data = self.processed_data # 使用已处理的数据

        # 温度图 (plot_temperatures.png)
        if 'temperatures' in processed_data:
            print("\n  平均温度 (°C):")
            for component, temp_data in processed_data['temperatures'].items():
                if temp_data is not None and len(temp_data) > 0:
                    avg_temp = np.mean(temp_data)
                    print(f"    {component.capitalize()}温度: {avg_temp:.2f} °C")

        # 制冷系统运行状态图 (plot_cooling_system_operation.png)
        print("\n  制冷系统运行相关平均值:")
        if 'ac_power_log' in processed_data and processed_data['ac_power_log'] is not None and len(processed_data['ac_power_log']) > 0:
            avg_ac_power = np.mean(processed_data['ac_power_log'])
            print(f"    空调压缩机总电耗: {avg_ac_power:.2f} W")
        
        cooling_logs = processed_data.get('cooling_system_logs', {})
        q_radiator = cooling_logs.get('Q_radiator')
        if q_radiator is not None and len(q_radiator) > 0:
            avg_q_radiator = np.mean(q_radiator)
            print(f"    散热器实际散热功率: {avg_q_radiator:.2f} W")
        
        # 动力总成Chiller状态 和 散热器效能因子 是状态值或比例，直接平均意义不大，除非特定需求

        # 车辆速度图 (plot_vehicle_speed.png)
        if 'speed_profile' in processed_data and processed_data['speed_profile'] is not None and len(processed_data['speed_profile']) > 0:
            avg_speed = np.mean(processed_data['speed_profile'])
            print(f"\n  平均车速: {avg_speed:.2f} km/h")

        # 动力总成部件产热功率图 (plot_powertrain_heat_generation.png)
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

        # 电池输出功率分解图 (plot_battery_power.png)
        if 'battery_power_profiles' in processed_data:
            print("\n  平均电池相关功率 (W):")
            for profile_name, power_data in processed_data['battery_power_profiles'].items():
                if power_data is not None and len(power_data) > 0:
                    avg_power = np.mean(power_data)
                    name_map_battery = {
                        'inv_in': '驱动用电功率 (逆变器输入)',
                        'comp_elec': '空调压缩机电功率', # 这个数据也存在于 ac_power_log
                        'total_elec': '总电池输出功率'
                    }
                    display_name = name_map_battery.get(profile_name, profile_name.capitalize())
                    # 避免重复打印压缩机功率
                    if profile_name != 'comp_elec' or 'ac_power_log' not in processed_data:
                         print(f"    {display_name}: {avg_power:.2f} W")


        # 座舱实际制冷功率变化图 (plot_cabin_cooling_power.png)
        # cabin_cool_power_log 存储了 Q_cabin_evap
        if 'cabin_cool_power_log' in processed_data and processed_data['cabin_cool_power_log'] is not None and len(processed_data['cabin_cool_power_log']) > 0:
            avg_cabin_cool_power = np.mean(processed_data['cabin_cool_power_log'])
            print(f"\n  平均座舱蒸发器制冷功率: {avg_cabin_cool_power:.2f} W")
        
        # 总热负荷 vs 总散热功率图 (plot_total_heat_balance.png)
        # 这些值是在 plotting.py 中计算的，我们需要在这里重新计算它们以获取平均值
        try:
            q_motor = processed_data['heat_gen_profiles']['motor']
            q_inv = processed_data['heat_gen_profiles']['inv']
            q_batt = processed_data['heat_gen_profiles']['batt']
            q_cabin_load = processed_data['heat_gen_profiles']['cabin_load']
            
            q_radiator_cb = cooling_logs.get('Q_radiator') # _cb for current block
            q_pt_chiller = cooling_logs.get('Q_chiller_powertrain')
            q_cabin_evap = cooling_logs.get('Q_cabin_evap') # Same as cabin_cool_power_log

            all_components_present = all(
                d is not None and len(d) > 0 for d in 
                [q_motor, q_inv, q_batt, q_cabin_load, q_radiator_cb, q_pt_chiller, q_cabin_evap]
            )

            if all_components_present:
                target_len = len(self.time_sim) # 确保所有数组长度一致
                
                q_motor_arr = plotting.ensure_profile_length(np.array(q_motor), target_len)
                q_inv_arr = plotting.ensure_profile_length(np.array(q_inv), target_len)
                q_batt_arr = plotting.ensure_profile_length(np.array(q_batt), target_len)
                q_cabin_load_arr = plotting.ensure_profile_length(np.array(q_cabin_load), target_len)
                q_radiator_arr = plotting.ensure_profile_length(np.array(q_radiator_cb), target_len)
                q_pt_chiller_arr = plotting.ensure_profile_length(np.array(q_pt_chiller), target_len)
                q_cabin_evap_arr = plotting.ensure_profile_length(np.array(q_cabin_evap), target_len)

                total_heat_load = q_motor_arr + q_inv_arr + q_batt_arr + q_cabin_load_arr
                total_heat_rejection = q_radiator_arr + q_pt_chiller_arr + q_cabin_evap_arr
                
                avg_total_load = np.mean(total_heat_load)
                avg_total_rejection = np.mean(total_heat_rejection)
                print("\n  平均总热平衡功率 (W):")
                print(f"    总热负荷功率: {avg_total_load:.2f} W")
                print(f"    总散热系统散热功率: {avg_total_rejection:.2f} W")
        except KeyError as e:
            print(f"\n  注意: 无法计算平均总热平衡，缺少数据: {e}")
        except Exception as e: #捕获其他潜在错误
            print(f"\n  计算平均总热平衡时发生错误: {e}")

        print("\n--- 平均值打印结束 ---")