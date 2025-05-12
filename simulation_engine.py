# simulation_engine.py
import numpy as np
import heat_vehicle as hv # 假设这个模块包含车辆相关的热量计算函数
import heat_cabin as ht # 假设这个模块包含座舱相关的热量计算函数
# simulation_parameters (sp) 将作为参数传递给 SimulationEngine

class SimulationEngine:
    def __init__(self, sp, cop_value):
        self.sp = sp
        self.cop = cop_value
        self.n_steps = int(sp.sim_duration / sp.dt)
        self.time_sim = np.linspace(0, sp.sim_duration, self.n_steps + 1)

        # --- Initialize history arrays for temperatures ---
        self.T_motor_hist = np.zeros(self.n_steps + 1)
        self.T_inv_hist = np.zeros(self.n_steps + 1)
        self.T_batt_hist = np.zeros(self.n_steps + 1)
        self.T_cabin_hist = np.zeros(self.n_steps + 1)
        self.T_coolant_hist = np.zeros(self.n_steps + 1)

        # --- Control/State Logs ---
        self.powertrain_chiller_active_log = np.zeros(self.n_steps + 1)
        self.LTR_level_log = np.zeros(self.n_steps + 1)
        self.P_LTR_fan_actual_hist = np.zeros(self.n_steps + 1)
        # VVVVVV  在这里添加初始化 VVVVVV
        self.LTR_effectiveness_log = np.zeros(self.n_steps + 1) # Log for equivalent 0-1 effectiveness factor
        # ^^^^^^  在这里添加初始化 ^^^^^^

        # --- Heat Flow Logs ---
        self.Q_LTR_hist = np.zeros(self.n_steps + 1)
        self.Q_coolant_from_LCC_hist = np.zeros(self.n_steps + 1)
        self.Q_coolant_chiller_actual_hist = np.zeros(self.n_steps + 1)
        self.Q_cabin_load_total_hist = np.zeros(self.n_steps + 1)
        self.Q_cabin_cool_actual_hist = np.zeros(self.n_steps + 1)

        # --- Input/Generation Logs ---
        self.v_vehicle_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_motor_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_inv_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_batt_profile_hist = np.zeros(self.n_steps + 1)
        self.P_comp_elec_profile_hist = np.zeros(self.n_steps + 1)

        # --- Set initial values (t=0) ---
        self.T_motor_hist[0] = sp.T_motor_init
        self.T_inv_hist[0] = sp.T_inv_init
        self.T_batt_hist[0] = sp.T_batt_init
        self.T_cabin_hist[0] = sp.T_cabin_init
        self.T_coolant_hist[0] = sp.T_coolant_init
        self.v_vehicle_profile_hist[0] = sp.v_start

        # Initial LTR state
        initial_coolant_temp_for_ltr = self.T_coolant_hist[0]
        current_ltr_level_idx = 0
        for lvl_idx_init in range(len(sp.LTR_coolant_temp_thresholds)):
            if initial_coolant_temp_for_ltr > sp.LTR_coolant_temp_thresholds[lvl_idx_init]:
                current_ltr_level_idx = lvl_idx_init + 1
            else:
                break
        
        self.LTR_level_log[0] = current_ltr_level_idx
        initial_UA_LTR_effective = sp.LTR_UA_values_at_levels[current_ltr_level_idx]
        initial_P_LTR_fan = sp.LTR_fan_power_levels[current_ltr_level_idx]
        self.P_LTR_fan_actual_hist[0] = initial_P_LTR_fan

        if sp.UA_LTR_max > 0:
            self.LTR_effectiveness_log[0] = initial_UA_LTR_effective / sp.UA_LTR_max
        else:
            self.LTR_effectiveness_log[0] = 1.0 if initial_UA_LTR_effective > 0 else 0.0
        
        Q_LTR_init = max(0, initial_UA_LTR_effective * (initial_coolant_temp_for_ltr - sp.T_ambient))
        self.Q_LTR_hist[0] = Q_LTR_init

        # ... (其余 __init__ 代码与我上次提供的完整版本一致)
        # Initial cabin cooling power
        initial_cabin_temp_for_cooling = self.T_cabin_hist[0]
        Q_cabin_cool_initial = sp.cabin_cooling_power_levels[-1] # Default to max power
        for j in range(len(sp.cabin_cooling_temp_thresholds)):
            if initial_cabin_temp_for_cooling <= sp.cabin_cooling_temp_thresholds[j]:
                Q_cabin_cool_initial = sp.cabin_cooling_power_levels[j]
                break
        self.Q_cabin_cool_actual_hist[0] = max(0, Q_cabin_cool_initial)

        # Initial cabin heat load
        try:
            Q_cabin_internal_init = ht.heat_universal_func(sp.N_passengers)
            Q_cabin_conduction_body_init = ht.heat_body_func(sp.T_ambient, initial_cabin_temp_for_cooling, self.v_vehicle_profile_hist[0], sp.v_air_in_mps, sp.A_body, sp.R_body)
            Q_cabin_conduction_glass_init = ht.heat_glass_func(sp.T_ambient, initial_cabin_temp_for_cooling, sp.I_solar_summer, self.v_vehicle_profile_hist[0], sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
            Q_cabin_ventilation_init = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, initial_cabin_temp_for_cooling, sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
            self.Q_cabin_load_total_hist[0] = Q_cabin_internal_init + Q_cabin_conduction_body_init + Q_cabin_conduction_glass_init + Q_cabin_ventilation_init
        except AttributeError:
            print("Warning: Cabin heat load functions (ht.heat_..._func) not found in heat_cabin.py. Initial cabin load set to 0.")
            self.Q_cabin_load_total_hist[0] = 0
            Q_cabin_internal_init, Q_cabin_conduction_body_init, Q_cabin_conduction_glass_init, Q_cabin_ventilation_init = 0,0,0,0


        self.powertrain_chiller_on = False
        self.Q_coolant_chiller_actual_hist[0] = 0.0

        # Initial compressor power and LCC heat
        Q_evap_total_needed_init = self.Q_cabin_cool_actual_hist[0] + self.Q_coolant_chiller_actual_hist[0]
        P_comp_elec_init = 0.0
        P_comp_mech_init = 0.0
        if Q_evap_total_needed_init > 0 and self.cop > 0 and sp.eta_comp_drive > 0:
             P_comp_mech_init = Q_evap_total_needed_init / self.cop
             P_comp_elec_init = P_comp_mech_init / sp.eta_comp_drive
        self.P_comp_elec_profile_hist[0] = P_comp_elec_init
        self.Q_coolant_from_LCC_hist[0] = Q_evap_total_needed_init + P_comp_mech_init

        # Initial heat generation for powertrain components, now including LTR fan power in battery load
        P_inv_in_init = 0
        try:
            P_wheel_init = hv.P_wheel_func(self.v_vehicle_profile_hist[0], sp.m_vehicle, sp.T_ambient)
            P_motor_in_init = hv.P_motor_func(P_wheel_init, sp.eta_motor)
            P_inv_in_init = P_motor_in_init / sp.eta_inv if sp.eta_inv > 0 else 0

            self.Q_gen_motor_profile_hist[0] = hv.Q_mot_func(P_motor_in_init, sp.eta_motor)
            self.Q_gen_inv_profile_hist[0] = hv.Q_inv_func(P_motor_in_init, sp.eta_inv)
            
            P_elec_total_batt_out_init = P_inv_in_init + P_comp_elec_init + initial_P_LTR_fan # ADDED LTR FAN POWER
            self.Q_gen_batt_profile_hist[0] = hv.Q_batt_func(P_elec_total_batt_out_init, sp.u_batt, sp.R_int_batt)
        except AttributeError:
            print("Warning: Powertrain heat generation functions (hv.P_..._func, hv.Q_..._func) not found in heat_vehicle.py. Initial generations set to 0.")
            self.Q_gen_motor_profile_hist[0] = 0
            self.Q_gen_inv_profile_hist[0] = 0
            self.Q_gen_batt_profile_hist[0] = 0

    def run_simulation(self):
        sp = self.sp
        print(f"Starting simulation loop (New Logic: LTR Fan Power & UA per level) for {self.n_steps} steps...")

        for i in range(self.n_steps):
            # --- 0. Get current states from previous time step ---
            current_time_sec = self.time_sim[i]
            current_cabin_temp = self.T_cabin_hist[i]
            current_T_motor = self.T_motor_hist[i]
            current_T_inv = self.T_inv_hist[i]
            current_T_batt = self.T_batt_hist[i]
            current_T_coolant = self.T_coolant_hist[i]

            # --- 1. External Inputs & Heat Generation ---
            # Vehicle speed profile
            if current_time_sec <= sp.ramp_up_time_sec:
                speed_increase = (sp.v_end - sp.v_start) * (current_time_sec / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 0
                v_vehicle_current = sp.v_start + speed_increase
            else:
                v_vehicle_current = sp.v_end
            v_vehicle_current = max(min(sp.v_start, sp.v_end), min(max(sp.v_start, sp.v_end), v_vehicle_current))
            if current_time_sec >= sp.ramp_up_time_sec : v_vehicle_current = sp.v_end
            self.v_vehicle_profile_hist[i] = v_vehicle_current

            # Powertrain heat generation (Motor, Inverter)
            P_inv_in = 0; Q_gen_motor = 0; Q_gen_inv = 0
            try:
                P_wheel = hv.P_wheel_func(v_vehicle_current, sp.m_vehicle, sp.T_ambient)
                P_motor_in = hv.P_motor_func(P_wheel, sp.eta_motor)
                P_inv_in = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0
                Q_gen_motor = hv.Q_mot_func(P_motor_in, sp.eta_motor)
                Q_gen_inv = hv.Q_inv_func(P_motor_in, sp.eta_inv)
            except AttributeError:
                 print(f"Warning at t={current_time_sec}s: Heat generation functions missing/error in heat_vehicle.py.")
            self.Q_gen_motor_profile_hist[i] = Q_gen_motor
            self.Q_gen_inv_profile_hist[i] = Q_gen_inv

            # Cabin heat load calculation
            Q_cabin_load_total = 0
            try:
                Q_cabin_internal = ht.heat_universal_func(sp.N_passengers)
                Q_cabin_conduction_body = ht.heat_body_func(sp.T_ambient, current_cabin_temp, v_vehicle_current, sp.v_air_in_mps, sp.A_body, sp.R_body)
                Q_cabin_conduction_glass = ht.heat_glass_func(sp.T_ambient, current_cabin_temp, sp.I_solar_summer, v_vehicle_current, sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
                Q_cabin_ventilation = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, current_cabin_temp, sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
                Q_cabin_load_total = Q_cabin_internal + Q_cabin_conduction_body + Q_cabin_conduction_glass + Q_cabin_ventilation
            except AttributeError:
                print(f"Warning at t={current_time_sec}s: Heat load functions missing/error in heat_cabin.py.")
            self.Q_cabin_load_total_hist[i] = Q_cabin_load_total

            # --- 2. Cooling System Control & Heat Transfer ---
            # 2a. Cabin Evaporator Cooling Control
            Q_cabin_cool_actual = sp.cabin_cooling_power_levels[-1]
            for j in range(len(sp.cabin_cooling_temp_thresholds)):
                if current_cabin_temp <= sp.cabin_cooling_temp_thresholds[j]:
                    Q_cabin_cool_actual = sp.cabin_cooling_power_levels[j]
                    break
            Q_cabin_cool_actual = max(0, Q_cabin_cool_actual)
            self.Q_cabin_cool_actual_hist[i] = Q_cabin_cool_actual

            # 2b. Powertrain Chiller Control Logic
            start_cooling_powertrain = (current_T_motor > sp.T_motor_target) or \
                                       (current_T_inv > sp.T_inv_target) or \
                                       (current_T_batt > sp.T_batt_target_high)
            stop_cooling_powertrain = (current_T_motor < sp.T_motor_stop_cool) and \
                                      (current_T_inv < sp.T_inv_stop_cool) and \
                                      (current_T_batt < sp.T_batt_stop_cool)
            if start_cooling_powertrain: self.powertrain_chiller_on = True
            elif stop_cooling_powertrain: self.powertrain_chiller_on = False
            self.powertrain_chiller_active_log[i] = 1 if self.powertrain_chiller_on else 0

            # 2c. Chiller Heat Transfer
            Q_chiller_potential = 0
            if current_T_coolant > sp.T_evap_sat_for_UA_calc:
                 Q_chiller_potential = sp.UA_coolant_chiller * (current_T_coolant - sp.T_evap_sat_for_UA_calc)
            Q_chiller_potential = max(0, Q_chiller_potential)
            Q_coolant_chiller_actual = min(Q_chiller_potential, sp.max_chiller_cool_power) if self.powertrain_chiller_on else 0
            self.Q_coolant_chiller_actual_hist[i] = Q_coolant_chiller_actual

            # 2d. Total Refrigerant Evaporation Load
            Q_evap_total_needed = Q_cabin_cool_actual + Q_coolant_chiller_actual

            # 2e. Compressor Power Calculation
            P_comp_elec = 0.0; P_comp_mech = 0.0
            if Q_evap_total_needed > 0 and self.cop > 0 and sp.eta_comp_drive > 0:
                P_comp_mech = Q_evap_total_needed / self.cop
                P_comp_elec = P_comp_mech / sp.eta_comp_drive
            self.P_comp_elec_profile_hist[i] = P_comp_elec

            # 2f. LCC Heat Transfer
            Q_coolant_from_LCC = Q_evap_total_needed + P_comp_mech
            self.Q_coolant_from_LCC_hist[i] = Q_coolant_from_LCC
            
            # 2g. LTR Fan Control (based on coolant temperature)
            current_ltr_level_idx = 0 
            for lvl_idx in range(len(sp.LTR_coolant_temp_thresholds)):
                if current_T_coolant > sp.LTR_coolant_temp_thresholds[lvl_idx]:
                    current_ltr_level_idx = lvl_idx + 1
                else:
                    break
            self.LTR_level_log[i] = current_ltr_level_idx
            
            UA_LTR_effective = sp.LTR_UA_values_at_levels[current_ltr_level_idx]
            P_LTR_fan_actual = sp.LTR_fan_power_levels[current_ltr_level_idx]
            self.P_LTR_fan_actual_hist[i] = P_LTR_fan_actual

            # LTR Heat Rejection
            Q_LTR_potential = UA_LTR_effective * (current_T_coolant - sp.T_ambient)
            Q_LTR_to_ambient = max(0, Q_LTR_potential)
            self.Q_LTR_hist[i] = Q_LTR_to_ambient

            # 2h. Battery Heat Generation (now includes LTR fan power)
            P_elec_total_batt_out = P_inv_in + P_comp_elec + P_LTR_fan_actual # ADDED LTR FAN POWER
            Q_gen_batt = 0
            try:
                Q_gen_batt = hv.Q_batt_func(P_elec_total_batt_out, sp.u_batt, sp.R_int_batt)
            except AttributeError:
                pass
            self.Q_gen_batt_profile_hist[i] = Q_gen_batt
            
            # 2i. Heat Transfer from Powertrain Components to Coolant
            Q_motor_to_coolant = sp.UA_motor_coolant * (current_T_motor - current_T_coolant)
            Q_inv_to_coolant = sp.UA_inv_coolant * (current_T_inv - current_T_coolant)
            Q_batt_to_coolant = sp.UA_batt_coolant * (current_T_batt - current_T_coolant)

            # --- 3. Temperature Updates ---
            # 3a. Coolant Temperature Update
            Q_coolant_net = (Q_coolant_from_LCC + Q_motor_to_coolant + Q_inv_to_coolant + Q_batt_to_coolant) \
                          - (Q_LTR_to_ambient + Q_coolant_chiller_actual)
            dT_coolant_dt = Q_coolant_net / sp.mc_coolant if sp.mc_coolant > 0 else 0

            # 3b. Component Temperature Updates
            dT_motor_dt = (Q_gen_motor - Q_motor_to_coolant) / sp.mc_motor if sp.mc_motor > 0 else 0
            dT_inv_dt = (Q_gen_inv - Q_inv_to_coolant) / sp.mc_inverter if sp.mc_inverter > 0 else 0
            dT_batt_dt = (Q_gen_batt - Q_batt_to_coolant) / sp.mc_battery if sp.mc_battery > 0 else 0
            dT_cabin_dt = (Q_cabin_load_total - Q_cabin_cool_actual) / sp.mc_cabin if sp.mc_cabin > 0 else 0

            # --- 4. Store results for the next time step (i+1) ---
            self.T_motor_hist[i+1] = current_T_motor + dT_motor_dt * sp.dt
            self.T_inv_hist[i+1] = current_T_inv + dT_inv_dt * sp.dt
            self.T_batt_hist[i+1] = current_T_batt + dT_batt_dt * sp.dt
            self.T_cabin_hist[i+1] = current_cabin_temp + dT_cabin_dt * sp.dt
            self.T_coolant_hist[i+1] = current_T_coolant + dT_coolant_dt * sp.dt
            
            # For LTR_effectiveness_log, if you still want to log a 0-1 factor based on UA for plotting:
            if sp.UA_LTR_max > 0: # THIS LINE IS THE SOURCE OF THE ERROR
                self.LTR_effectiveness_log[i] = UA_LTR_effective / sp.UA_LTR_max # ERROR HERE
            else:
                self.LTR_effectiveness_log[i] = 1.0 if UA_LTR_effective > 0 else 0.0


        print(f"Simulation loop finished (New Logic: LTR Fan Power & UA per level) after {self.n_steps} steps.")
        self._fill_last_step_values()

        # --- 5. Prepare results dictionary ---
        simulation_results = {
            "time_sim": self.time_sim,
            "temperatures_data": {
                'motor': self.T_motor_hist, 'inv': self.T_inv_hist, 'batt': self.T_batt_hist,
                'cabin': self.T_cabin_hist, 'coolant': self.T_coolant_hist
            },
            "heat_gen_data": {
                'motor': self.Q_gen_motor_profile_hist,
                'inv': self.Q_gen_inv_profile_hist,
                'batt': self.Q_gen_batt_profile_hist,
                'cabin_load': self.Q_cabin_load_total_hist
            },
            "cooling_system_logs": {
                'chiller_active': self.powertrain_chiller_active_log,
                'LTR_level': self.LTR_level_log,
                'P_LTR_fan': self.P_LTR_fan_actual_hist,
                'LTR_effectiveness_factor_equiv': self.LTR_effectiveness_log, # Log equivalent 0-1 factor
                'Q_LTR_to_ambient': self.Q_LTR_hist,
                'Q_coolant_from_LCC': self.Q_coolant_from_LCC_hist,
                'Q_coolant_to_chiller': self.Q_coolant_chiller_actual_hist,
                'Q_cabin_evap_cooling': self.Q_cabin_cool_actual_hist
            },
            "ac_power_log": self.P_comp_elec_profile_hist,
            "speed_profile": self.v_vehicle_profile_hist
        }
        return simulation_results

    def _fill_last_step_values(self):
        sp = self.sp
        n = self.n_steps

        # Vehicle speed
        current_time_sec_last = self.time_sim[n]
        if current_time_sec_last <= sp.ramp_up_time_sec:
            speed_increase_last = (sp.v_end - sp.v_start) * (current_time_sec_last / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 0
            v_last = sp.v_start + speed_increase_last
        else:
            v_last = sp.v_end
        v_last = max(min(sp.v_start,sp.v_end), min(max(sp.v_start,sp.v_end), v_last))
        if current_time_sec_last >= sp.ramp_up_time_sec : v_last = sp.v_end
        self.v_vehicle_profile_hist[n] = v_last

        if n > 0:
            self.powertrain_chiller_active_log[n] = self.powertrain_chiller_active_log[n-1]
            self.LTR_level_log[n] = self.LTR_level_log[n-1]
            self.P_LTR_fan_actual_hist[n] = self.P_LTR_fan_actual_hist[n-1]
            self.LTR_effectiveness_log[n] = self.LTR_effectiveness_log[n-1] # For 0-1 factor
            self.Q_LTR_hist[n] = self.Q_LTR_hist[n-1]
            self.Q_coolant_from_LCC_hist[n] = self.Q_coolant_from_LCC_hist[n-1]
            self.Q_coolant_chiller_actual_hist[n] = self.Q_coolant_chiller_actual_hist[n-1]
            self.P_comp_elec_profile_hist[n] = self.P_comp_elec_profile_hist[n-1]
            self.Q_cabin_cool_actual_hist[n] = self.Q_cabin_cool_actual_hist[n-1]

            P_inv_in_last = 0; Q_gen_motor_last = 0; Q_gen_inv_last = 0
            try:
                P_wheel_last = hv.P_wheel_func(self.v_vehicle_profile_hist[n], sp.m_vehicle, sp.T_ambient)
                P_motor_in_last = hv.P_motor_func(P_wheel_last, sp.eta_motor)
                P_inv_in_last = P_motor_in_last / sp.eta_inv if sp.eta_inv > 0 else 0
                Q_gen_motor_last = hv.Q_mot_func(P_motor_in_last, sp.eta_motor)
                Q_gen_inv_last = hv.Q_inv_func(P_motor_in_last, sp.eta_inv)
            except AttributeError: pass
            self.Q_gen_motor_profile_hist[n] = Q_gen_motor_last
            self.Q_gen_inv_profile_hist[n] = Q_gen_inv_last
            
            P_elec_total_batt_out_last = P_inv_in_last + self.P_comp_elec_profile_hist[n] + self.P_LTR_fan_actual_hist[n]
            Q_gen_batt_last = 0
            try:
                Q_gen_batt_last = hv.Q_batt_func(P_elec_total_batt_out_last, sp.u_batt, sp.R_int_batt)
            except AttributeError: pass
            self.Q_gen_batt_profile_hist[n] = Q_gen_batt_last

            Q_cabin_load_total_last = 0
            try:
                T_cabin_last = self.T_cabin_hist[n]
                Q_cabin_internal_last = ht.heat_universal_func(sp.N_passengers)
                Q_cabin_conduction_body_last = ht.heat_body_func(sp.T_ambient, T_cabin_last, self.v_vehicle_profile_hist[n], sp.v_air_in_mps, sp.A_body, sp.R_body)
                Q_cabin_conduction_glass_last = ht.heat_glass_func(sp.T_ambient, T_cabin_last, sp.I_solar_summer, self.v_vehicle_profile_hist[n], sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
                Q_cabin_ventilation_last = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, T_cabin_last, sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
                self.Q_cabin_load_total_hist[n] = Q_cabin_internal_last + Q_cabin_conduction_body_last + Q_cabin_conduction_glass_last + Q_cabin_ventilation_last
            except AttributeError: pass

        elif n == 0:
            v_init = self.v_vehicle_profile_hist[0]
            P_inv_in_init_fill = 0
            try:
                P_wheel_init_fill = hv.P_wheel_func(v_init, sp.m_vehicle, sp.T_ambient)
                P_motor_in_init_fill = hv.P_motor_func(P_wheel_init_fill, sp.eta_motor)
                P_inv_in_init_fill = P_motor_in_init_fill / sp.eta_inv if sp.eta_inv > 0 else 0
                self.Q_gen_motor_profile_hist[0] = hv.Q_mot_func(P_motor_in_init_fill, sp.eta_motor)
                self.Q_gen_inv_profile_hist[0] = hv.Q_inv_func(P_motor_in_init_fill, sp.eta_inv)
            except AttributeError: pass

            P_elec_total_batt_out_init_fill = P_inv_in_init_fill + self.P_comp_elec_profile_hist[0] + self.P_LTR_fan_actual_hist[0]
            try:
                self.Q_gen_batt_profile_hist[0] = hv.Q_batt_func(P_elec_total_batt_out_init_fill, sp.u_batt, sp.R_int_batt)
            except AttributeError: pass
            
            try:
                T_cabin_init_fill = self.T_cabin_hist[0]
                Q_cabin_internal_init_fill = ht.heat_universal_func(sp.N_passengers)
                Q_cabin_conduction_body_init_fill = ht.heat_body_func(sp.T_ambient, T_cabin_init_fill, v_init, sp.v_air_in_mps, sp.A_body, sp.R_body)
                Q_cabin_conduction_glass_init_fill = ht.heat_glass_func(sp.T_ambient, T_cabin_init_fill, sp.I_solar_summer, v_init, sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
                Q_cabin_ventilation_init_fill = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, T_cabin_init_fill, sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
                self.Q_cabin_load_total_hist[0] = Q_cabin_internal_init_fill + Q_cabin_conduction_body_init_fill + Q_cabin_conduction_glass_init_fill + Q_cabin_ventilation_init_fill
            except AttributeError: pass