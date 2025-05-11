# simulation_engine.py
# 负责运行整个仿真循环
import numpy as np
import heat_vehicle as hv
import heat_cabin as ht
# simulation_parameters (sp) 将作为参数传递给 SimulationEngine

class SimulationEngine:
    def __init__(self, sp, cop_value):
        self.sp = sp
        self.cop = cop_value
        self.n_steps = int(sp.sim_duration / sp.dt)
        self.time_sim = np.linspace(0, sp.sim_duration, self.n_steps + 1)

        # Initialize history arrays
        self.T_motor_hist = np.zeros(self.n_steps + 1)
        self.T_inv_hist = np.zeros(self.n_steps + 1)
        self.T_batt_hist = np.zeros(self.n_steps + 1)
        self.T_cabin_hist = np.zeros(self.n_steps + 1)
        self.T_coolant_hist = np.zeros(self.n_steps + 1)
        self.powertrain_chiller_active_log = np.zeros(self.n_steps + 1)
        self.radiator_effectiveness_log = np.zeros(self.n_steps + 1)
        self.Q_coolant_radiator_log = np.zeros(self.n_steps + 1)
        self.Q_coolant_chiller_actual_hist = np.zeros(self.n_steps + 1)
        self.Q_cabin_load_total_hist = np.zeros(self.n_steps + 1)
        self.v_vehicle_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_motor_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_inv_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_batt_profile_hist = np.zeros(self.n_steps + 1)
        self.P_comp_elec_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_cabin_cool_actual_hist = np.zeros(self.n_steps + 1)

        # Set initial values
        self.T_motor_hist[0] = sp.T_motor_init
        self.T_inv_hist[0] = sp.T_inv_init
        self.T_batt_hist[0] = sp.T_batt_init
        self.T_cabin_hist[0] = sp.T_cabin_init
        self.T_coolant_hist[0] = sp.T_coolant_init
        self.v_vehicle_profile_hist[0] = sp.v_start
        self.radiator_effectiveness_log[0] = 1.0

        initial_cabin_temp = self.T_cabin_hist[0]
        Q_cabin_cool_initial = sp.cabin_cooling_power_levels[-1]
        for j in range(len(sp.cabin_cooling_temp_thresholds)):
            if initial_cabin_temp <= sp.cabin_cooling_temp_thresholds[j]:
                Q_cabin_cool_initial = sp.cabin_cooling_power_levels[j]
                break
        self.Q_cabin_cool_actual_hist[0] = max(0, Q_cabin_cool_initial)

        Q_cabin_internal_init = ht.heat_universal_func(sp.N_passengers)
        Q_cabin_conduction_body_init = ht.heat_body_func(sp.T_ambient, initial_cabin_temp, self.v_vehicle_profile_hist[0], sp.v_air_in_mps, sp.A_body, sp.R_body)
        Q_cabin_conduction_glass_init = ht.heat_glass_func(sp.T_ambient, initial_cabin_temp, sp.I_solar_summer, self.v_vehicle_profile_hist[0], sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
        Q_cabin_ventilation_init = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, initial_cabin_temp, sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
        self.Q_cabin_load_total_hist[0] = Q_cabin_internal_init + Q_cabin_conduction_body_init + Q_cabin_conduction_glass_init + Q_cabin_ventilation_init

        self.powertrain_chiller_on = False

    def run_simulation(self):
        sp = self.sp # shortcut
        print("Starting simulation loop in SimulationEngine...")
        for i in range(self.n_steps):
            current_time_sec = self.time_sim[i]
            current_cabin_temp = self.T_cabin_hist[i]
            current_T_motor = self.T_motor_hist[i]
            current_T_inv = self.T_inv_hist[i]
            current_T_batt = self.T_batt_hist[i]
            current_T_coolant = self.T_coolant_hist[i]

            # Vehicle speed profile
            if current_time_sec <= sp.ramp_up_time_sec:
                speed_increase = (sp.v_end - sp.v_start) * (current_time_sec / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 0
                v_vehicle_current = sp.v_start + speed_increase
            else:
                v_vehicle_current = sp.v_end
            v_vehicle_current = max(min(sp.v_start, sp.v_end), min(max(sp.v_start, sp.v_end), v_vehicle_current))
            if current_time_sec > sp.ramp_up_time_sec : v_vehicle_current = sp.v_end # Ensure it stays at v_end
            self.v_vehicle_profile_hist[i] = v_vehicle_current

            # Powertrain heat generation
            P_wheel = hv.P_wheel_func(v_vehicle_current, sp.m_vehicle, sp.T_ambient)
            P_motor_in = hv.P_motor_func(P_wheel, sp.eta_motor)
            P_inv_in = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0 # Used later for battery heat

            Q_gen_motor = hv.Q_mot_func(P_motor_in, sp.eta_motor)
            Q_gen_inv = hv.Q_inv_func(P_motor_in, sp.eta_inv) # Note: P_motor_in is output of inverter
            self.Q_gen_motor_profile_hist[i] = Q_gen_motor
            self.Q_gen_inv_profile_hist[i] = Q_gen_inv

            # Cabin heat load
            Q_cabin_internal = ht.heat_universal_func(sp.N_passengers)
            Q_cabin_conduction_body = ht.heat_body_func(sp.T_ambient, current_cabin_temp, v_vehicle_current, sp.v_air_in_mps, sp.A_body, sp.R_body)
            Q_cabin_conduction_glass = ht.heat_glass_func(sp.T_ambient, current_cabin_temp, sp.I_solar_summer, v_vehicle_current, sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
            Q_cabin_ventilation = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, current_cabin_temp, sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
            Q_cabin_load_total = Q_cabin_internal + Q_cabin_conduction_body + Q_cabin_conduction_glass + Q_cabin_ventilation
            self.Q_cabin_load_total_hist[i] = Q_cabin_load_total

            # Cabin cooling control
            Q_cabin_cool_actual = sp.cabin_cooling_power_levels[-1] # Default to max if no threshold met
            for j in range(len(sp.cabin_cooling_temp_thresholds)):
                if current_cabin_temp <= sp.cabin_cooling_temp_thresholds[j]:
                    Q_cabin_cool_actual = sp.cabin_cooling_power_levels[j]
                    break
            Q_cabin_cool_actual = max(0, Q_cabin_cool_actual) # Ensure non-negative cooling
            Q_out_cabin = Q_cabin_cool_actual # Heat extracted from cabin
            self.Q_cabin_cool_actual_hist[i] = Q_out_cabin

            # Heat transfer to coolant
            Q_motor_to_coolant = sp.UA_motor_coolant * (current_T_motor - current_T_coolant)
            Q_inv_to_coolant = sp.UA_inv_coolant * (current_T_inv - current_T_coolant)
            Q_batt_to_coolant = sp.UA_batt_coolant * (current_T_batt - current_T_coolant) # Battery temp updated later
            Q_coolant_absorb = Q_motor_to_coolant + Q_inv_to_coolant + Q_batt_to_coolant

            # Radiator heat rejection
            current_radiator_effectiveness = 1.0
            all_comps_below_stop_cool = (current_T_motor < sp.T_motor_stop_cool) and \
                                        (current_T_inv < sp.T_inv_stop_cool) and \
                                        (current_T_batt < sp.T_batt_stop_cool)
            all_comps_at_or_below_target = (current_T_motor <= sp.T_motor_target) and \
                                           (current_T_inv <= sp.T_inv_target) and \
                                           (current_T_batt <= sp.T_batt_target_low) # Using low target for battery effectiveness logic

            if all_comps_below_stop_cool:
                current_radiator_effectiveness = sp.radiator_effectiveness_below_stop_cool
            elif all_comps_at_or_below_target:
                current_radiator_effectiveness = sp.radiator_effectiveness_at_target

            self.radiator_effectiveness_log[i] = current_radiator_effectiveness
            UA_coolant_radiator_effective = sp.UA_coolant_radiator_max * current_radiator_effectiveness
            Q_radiator_potential = UA_coolant_radiator_effective * (current_T_coolant - sp.T_ambient)
            Q_coolant_radiator = max(0, Q_radiator_potential) # Radiator can only reject heat
            self.Q_coolant_radiator_log[i] = Q_coolant_radiator

            # Powertrain chiller control
            start_cooling_powertrain = (current_T_motor > sp.T_motor_target) or \
                                       (current_T_inv > sp.T_inv_target) or \
                                       (current_T_batt > sp.T_batt_target_high)
            stop_cooling_powertrain = (current_T_motor < sp.T_motor_stop_cool) and \
                                      (current_T_inv < sp.T_inv_stop_cool) and \
                                      (current_T_batt < sp.T_batt_stop_cool)

            if start_cooling_powertrain:
                self.powertrain_chiller_on = True
            elif stop_cooling_powertrain:
                self.powertrain_chiller_on = False

            Q_chiller_potential = sp.UA_coolant_chiller * (current_T_coolant - sp.T_evap_sat_for_UA_calc) if current_T_coolant > sp.T_evap_sat_for_UA_calc else 0
            Q_coolant_chiller_actual = min(Q_chiller_potential, sp.max_chiller_cool_power) if self.powertrain_chiller_on else 0
            self.Q_coolant_chiller_actual_hist[i] = Q_coolant_chiller_actual
            self.powertrain_chiller_active_log[i] = 1 if self.powertrain_chiller_on and Q_coolant_chiller_actual > 0 else 0

            # Total heat rejected by coolant
            Q_coolant_reject = Q_coolant_chiller_actual + Q_coolant_radiator

            # Compressor power
            P_comp_elec = 0.0
            Q_evap_total_needed = Q_out_cabin + Q_coolant_chiller_actual # Total cooling demand on evaporator
            if Q_evap_total_needed > 0:
                if self.cop > 0 and self.cop != float('inf') and sp.eta_comp_drive > 0:
                    P_comp_mech = Q_evap_total_needed / self.cop
                    P_comp_elec = P_comp_mech / sp.eta_comp_drive
                else: # Fallback if COP or efficiency is invalid
                    P_comp_elec = Q_evap_total_needed / 2.0  # Simplified fallback
                    if sp.eta_comp_drive > 0: P_comp_elec /= sp.eta_comp_drive

            self.P_comp_elec_profile_hist[i] = P_comp_elec

            # Battery heat generation (depends on total electrical load)
            P_elec_total_batt_out = P_inv_in + P_comp_elec # P_inv_in already calculated
            Q_gen_batt = hv.Q_batt_func(P_elec_total_batt_out, sp.u_batt, sp.R_int_batt)
            self.Q_gen_batt_profile_hist[i] = Q_gen_batt

            # Temperature updates
            dT_motor_dt = (Q_gen_motor - Q_motor_to_coolant) / sp.mc_motor if sp.mc_motor > 0 else 0
            dT_inv_dt = (Q_gen_inv - Q_inv_to_coolant) / sp.mc_inverter if sp.mc_inverter > 0 else 0
            dT_batt_dt = (Q_gen_batt - Q_batt_to_coolant) / sp.mc_battery if sp.mc_battery > 0 else 0 # Q_batt_to_coolant uses T_batt[i]
            dT_cabin_dt = (Q_cabin_load_total - Q_out_cabin) / sp.mc_cabin if sp.mc_cabin > 0 else 0
            dT_coolant_dt = (Q_coolant_absorb - Q_coolant_reject) / sp.mc_coolant if sp.mc_coolant > 0 else 0

            self.T_motor_hist[i+1] = current_T_motor + dT_motor_dt * sp.dt
            self.T_inv_hist[i+1] = current_T_inv + dT_inv_dt * sp.dt
            self.T_batt_hist[i+1] = current_T_batt + dT_batt_dt * sp.dt
            self.T_cabin_hist[i+1] = current_cabin_temp + dT_cabin_dt * sp.dt
            self.T_coolant_hist[i+1] = current_T_coolant + dT_coolant_dt * sp.dt

        print("Simulation loop finished in SimulationEngine.")
        self._fill_last_step_values() # Fill values for the very last data point

        # --- Prepare results dictionary ---
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
                'radiator_effectiveness': self.radiator_effectiveness_log,
                'Q_radiator': self.Q_coolant_radiator_log,
                'Q_chiller_powertrain': self.Q_coolant_chiller_actual_hist,
                'Q_cabin_evap': self.Q_cabin_cool_actual_hist
            },
            "ac_power_log": self.P_comp_elec_profile_hist,
            "speed_profile": self.v_vehicle_profile_hist
            # P_inv_in_profile and P_elec_total_profile will be calculated in results_analyzer
        }
        return simulation_results

    def _fill_last_step_values(self):
        """Ensure the last data point of profiles is consistent or calculated."""
        sp = self.sp
        n = self.n_steps # index for the last point

        # Speed for the last point
        current_time_sec_last = self.time_sim[n]
        if current_time_sec_last <= sp.ramp_up_time_sec:
            speed_increase_last = (sp.v_end - sp.v_start) * (current_time_sec_last / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 0
            self.v_vehicle_profile_hist[n] = max(min(sp.v_start,sp.v_end), min(max(sp.v_start,sp.v_end), sp.v_start + speed_increase_last))
        else:
            self.v_vehicle_profile_hist[n] = sp.v_end
        
        if n > 0: # If simulation had steps, copy from previous for logs
            self.powertrain_chiller_active_log[n] = self.powertrain_chiller_active_log[n-1]
            self.radiator_effectiveness_log[n] = self.radiator_effectiveness_log[n-1]
            self.Q_coolant_radiator_log[n] = self.Q_coolant_radiator_log[n-1]
            self.Q_coolant_chiller_actual_hist[n] = self.Q_coolant_chiller_actual_hist[n-1]
            self.Q_cabin_load_total_hist[n] = self.Q_cabin_load_total_hist[n-1]
            self.Q_gen_motor_profile_hist[n] = self.Q_gen_motor_profile_hist[n-1]
            self.Q_gen_inv_profile_hist[n] = self.Q_gen_inv_profile_hist[n-1]
            self.Q_gen_batt_profile_hist[n] = self.Q_gen_batt_profile_hist[n-1]
            self.P_comp_elec_profile_hist[n] = self.P_comp_elec_profile_hist[n-1]
            self.Q_cabin_cool_actual_hist[n] = self.Q_cabin_cool_actual_hist[n-1]

        elif n == 0: # Simulation has only one point (t=0)
            # Recalculate relevant values for t=0 if they were meant to be dynamic
            v_init = self.v_vehicle_profile_hist[0]
            P_wheel_init_calc = hv.P_wheel_func(v_init, sp.m_vehicle, sp.T_ambient)
            P_motor_in_init_calc = hv.P_motor_func(P_wheel_init_calc, sp.eta_motor)
            self.Q_gen_motor_profile_hist[0] = hv.Q_mot_func(P_motor_in_init_calc, sp.eta_motor)
            self.Q_gen_inv_profile_hist[0] = hv.Q_inv_func(P_motor_in_init_calc, sp.eta_inv) # P_motor_in is inv output
            P_inv_in_init_calc = P_motor_in_init_calc / sp.eta_inv if sp.eta_inv > 0 else 0


            Q_evap_total_needed_init = self.Q_cabin_cool_actual_hist[0] + self.Q_coolant_chiller_actual_hist[0] # chiller is 0 at init
            P_comp_elec_init = 0.0
            if Q_evap_total_needed_init > 0:
                if self.cop > 0 and self.cop != float('inf') and sp.eta_comp_drive > 0:
                    P_comp_mech_init = Q_evap_total_needed_init / self.cop
                    P_comp_elec_init = P_comp_mech_init / sp.eta_comp_drive
                else:
                    P_comp_elec_init = Q_evap_total_needed_init / 2.0 
                    if sp.eta_comp_drive > 0: P_comp_elec_init /= sp.eta_comp_drive
            self.P_comp_elec_profile_hist[0] = P_comp_elec_init

            P_elec_total_batt_out_init = P_inv_in_init_calc + self.P_comp_elec_profile_hist[0]
            self.Q_gen_batt_profile_hist[0] = hv.Q_batt_func(P_elec_total_batt_out_init, sp.u_batt, sp.R_int_batt)

            self.radiator_effectiveness_log[0] = 1.0 # Already set, but for clarity
            UA_eff_init = sp.UA_coolant_radiator_max * self.radiator_effectiveness_log[0]
            Q_rad_pot_init = UA_eff_init * (self.T_coolant_hist[0] - sp.T_ambient)
            self.Q_coolant_radiator_log[0] = max(0, Q_rad_pot_init)
            # Q_cabin_load_total_hist[0] already calculated in __init__