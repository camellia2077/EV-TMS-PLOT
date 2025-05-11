# results_analyzer.py
# 后处理仿真结果、计算派生数据和分析特定事件
import numpy as np
import heat_vehicle as hv # For P_inv_in calculation

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