# -*- coding: utf-8 -*-
# main.py
import numpy as np

# Import functions from modules
import heat_vehicle as hv
import heat_cabin as ht
import refrigeration_cycle as rc
import simulation_parameters as sp
import plotting

# --- 1. Calculate Refrigeration COP ---
COP, cycle_data = rc.calculate_refrigeration_cop(
    sp.T_suc_C_in, sp.T_cond_sat_C_in, sp.T_be_C_in,
    sp.T_evap_sat_C_in, sp.T_dis_C_in, sp.REFRIGERANT_TYPE
)

# --- 2. Simulation Setup ---
n_steps = int(sp.sim_duration / sp.dt)
time_sim = np.linspace(0, sp.sim_duration, n_steps + 1)

# Initialize arrays for storing results
T_motor_hist = np.zeros(n_steps + 1)
T_inv_hist = np.zeros(n_steps + 1)
T_batt_hist = np.zeros(n_steps + 1)
T_cabin_hist = np.zeros(n_steps + 1)
T_coolant_hist = np.zeros(n_steps + 1)
powertrain_chiller_active_log = np.zeros(n_steps + 1)
v_vehicle_profile_hist = np.zeros(n_steps + 1)
Q_gen_motor_profile_hist = np.zeros(n_steps + 1)
Q_gen_inv_profile_hist = np.zeros(n_steps + 1)
Q_gen_batt_profile_hist = np.zeros(n_steps + 1)
P_comp_elec_profile_hist = np.zeros(n_steps + 1)
Q_cabin_cool_actual_hist = np.zeros(n_steps + 1)

# Set initial values
T_motor_hist[0] = sp.T_motor_init
T_inv_hist[0] = sp.T_inv_init
T_batt_hist[0] = sp.T_batt_init
T_cabin_hist[0] = sp.T_cabin_init
T_coolant_hist[0] = sp.T_coolant_init
v_vehicle_profile_hist[0] = sp.v_start

# --- Initialize Cabin Cooling Power based on initial temperature ---
initial_cabin_temp = T_cabin_hist[0]
Q_cabin_cool_initial = sp.cabin_cooling_power_levels[-1] # Default to highest power if above all lower thresholds

for j in range(len(sp.cabin_cooling_temp_thresholds)):
    if initial_cabin_temp <= sp.cabin_cooling_temp_thresholds[j]:
        Q_cabin_cool_initial = sp.cabin_cooling_power_levels[j]
        break
Q_cabin_cool_actual_hist[0] = max(0, Q_cabin_cool_initial)


# --- 3. Simulation Loop ---
powertrain_chiller_on = False

print("Starting simulation loop...")
for i in range(n_steps):
    current_time_sec = time_sim[i]
    current_cabin_temp = T_cabin_hist[i]

    # 3.1. Calculate current vehicle speed
    if current_time_sec <= sp.ramp_up_time_sec:
        speed_increase = (sp.v_end - sp.v_start) * (current_time_sec / sp.ramp_up_time_sec)
        v_vehicle_current = sp.v_start + speed_increase
    else:
        v_vehicle_current = sp.v_end
    v_vehicle_current = max(min(sp.v_start, sp.v_end), min(max(sp.v_start, sp.v_end), v_vehicle_current)) # Ensure it's within start/end bounds during ramp
    if current_time_sec > sp.ramp_up_time_sec : v_vehicle_current = sp.v_end # clamp to v_end after ramp
    v_vehicle_profile_hist[i] = v_vehicle_current

    # 3.2. Calculate instantaneous PROPULSION power and heat generation
    P_wheel = hv.P_wheel_func(v_vehicle_current, sp.m_vehicle, sp.T_ambient)
    P_motor_in = hv.P_motor_func(P_wheel, sp.eta_motor)
    P_inv_in = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0
    
    Q_gen_motor = hv.Q_mot_func(P_motor_in, sp.eta_motor)
    Q_gen_inv = hv.Q_inv_func(P_motor_in, sp.eta_inv)
    Q_gen_motor_profile_hist[i] = Q_gen_motor
    Q_gen_inv_profile_hist[i] = Q_gen_inv

    # 3.3. Calculate Cabin Heat Loads
    Q_cabin_internal = ht.heat_universal_func(sp.N_passengers)
    Q_cabin_conduction_body = ht.heat_body_func(sp.T_ambient, current_cabin_temp, v_vehicle_current, sp.v_air_in_mps, sp.A_body, sp.R_body)
    Q_cabin_conduction_glass = ht.heat_glass_func(sp.T_ambient, current_cabin_temp, sp.I_solar_summer, v_vehicle_current, sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
    Q_cabin_ventilation = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, current_cabin_temp, sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
    Q_cabin_load_total = Q_cabin_internal + Q_cabin_conduction_body + Q_cabin_conduction_glass + Q_cabin_ventilation

    # 3.4. Cabin Cooling Control (Multi-level based on temperature thresholds)
    Q_cabin_cool_actual = sp.cabin_cooling_power_levels[-1] # Default to highest power

    for j in range(len(sp.cabin_cooling_temp_thresholds)):
        if current_cabin_temp <= sp.cabin_cooling_temp_thresholds[j]:
            Q_cabin_cool_actual = sp.cabin_cooling_power_levels[j]
            break
            
    # Ensure non-negative cooling power
    Q_cabin_cool_actual = max(0, Q_cabin_cool_actual)
    Q_out_cabin = Q_cabin_cool_actual
    Q_cabin_cool_actual_hist[i] = Q_out_cabin

    # 3.5. Heat Transfer between Components and Coolant
    Q_motor_to_coolant = sp.UA_motor_coolant * (T_motor_hist[i] - T_coolant_hist[i])
    Q_inv_to_coolant = sp.UA_inv_coolant * (T_inv_hist[i] - T_coolant_hist[i])
    Q_batt_to_coolant = sp.UA_batt_coolant * (T_batt_hist[i] - T_coolant_hist[i])
    Q_coolant_absorb = Q_motor_to_coolant + Q_inv_to_coolant + Q_batt_to_coolant

    # 3.6. Coolant Cooling Control (Radiator and Chiller)
    Q_radiator_potential = sp.UA_coolant_radiator * (T_coolant_hist[i] - sp.T_ambient)
    Q_coolant_radiator = max(0, Q_radiator_potential)

    start_cooling_powertrain = (T_motor_hist[i] > sp.T_motor_target) or \
                               (T_inv_hist[i] > sp.T_inv_target) or \
                               (T_batt_hist[i] > sp.T_batt_target_high)
    stop_cooling_powertrain = (T_motor_hist[i] < sp.T_motor_stop_cool) and \
                              (T_inv_hist[i] < sp.T_inv_stop_cool) and \
                              (T_batt_hist[i] < sp.T_batt_stop_cool) # Using T_batt_stop_cool from sp
    if start_cooling_powertrain:
        powertrain_chiller_on = True
    elif stop_cooling_powertrain:
        powertrain_chiller_on = False
    
    Q_chiller_potential = sp.UA_coolant_chiller * (T_coolant_hist[i] - sp.T_evap_sat_for_UA_calc) if T_coolant_hist[i] > sp.T_evap_sat_for_UA_calc else 0
    Q_coolant_chiller_actual = min(Q_chiller_potential, sp.max_chiller_cool_power) if powertrain_chiller_on else 0
    powertrain_chiller_active_log[i] = 1 if powertrain_chiller_on and Q_coolant_chiller_actual > 0 else 0
    
    Q_coolant_reject = Q_coolant_chiller_actual + Q_coolant_radiator

    # 3.7. Calculate AC Compressor Power
    P_comp_elec = 0.0
    Q_evap_total_needed = Q_out_cabin + Q_coolant_chiller_actual
    
    if Q_evap_total_needed > 0:
        if COP > 0 and COP != float('inf') and sp.eta_comp_drive > 0:
            P_comp_mech = Q_evap_total_needed / COP
            P_comp_elec = P_comp_mech / sp.eta_comp_drive
        else: # Fallback if COP is invalid
            P_comp_elec = Q_evap_total_needed / 2.0 if sp.eta_comp_drive <=0 else Q_evap_total_needed / (2.0 * sp.eta_comp_drive) # Assuming a default COP of 2.0
            print(f"Warning: Using fallback for P_comp_elec due to COP={COP} or eta_comp_drive={sp.eta_comp_drive}")
    P_comp_elec_profile_hist[i] = P_comp_elec

    # 3.8. Update Battery Load & Heat Generation
    P_elec_total_batt_out = P_inv_in + P_comp_elec
    Q_gen_batt = hv.Q_batt_func(P_elec_total_batt_out, sp.u_batt, sp.R_int_batt)
    Q_gen_batt_profile_hist[i] = Q_gen_batt

    # 3.9. Calculate Temperature Derivatives
    dT_motor_dt = (Q_gen_motor - Q_motor_to_coolant) / sp.mc_motor if sp.mc_motor > 0 else 0
    dT_inv_dt = (Q_gen_inv - Q_inv_to_coolant) / sp.mc_inverter if sp.mc_inverter > 0 else 0
    dT_batt_dt = (Q_gen_batt - Q_batt_to_coolant) / sp.mc_battery if sp.mc_battery > 0 else 0
    dT_cabin_dt = (Q_cabin_load_total - Q_out_cabin) / sp.mc_cabin if sp.mc_cabin > 0 else 0
    dT_coolant_dt = (Q_coolant_absorb - Q_coolant_reject) / sp.mc_coolant if sp.mc_coolant > 0 else 0

    # 3.10. Update Temperatures
    T_motor_hist[i+1] = T_motor_hist[i] + dT_motor_dt * sp.dt
    T_inv_hist[i+1] = T_inv_hist[i] + dT_inv_dt * sp.dt
    T_batt_hist[i+1] = T_batt_hist[i] + dT_batt_dt * sp.dt
    T_cabin_hist[i+1] = T_cabin_hist[i] + dT_cabin_dt * sp.dt
    T_coolant_hist[i+1] = T_coolant_hist[i] + dT_coolant_dt * sp.dt

print("Simulation loop finished.")

# --- 4. Post-processing for Plots ---
current_time_sec_last = time_sim[n_steps]
if current_time_sec_last <= sp.ramp_up_time_sec:
    speed_increase_last = (sp.v_end - sp.v_start) * (current_time_sec_last / sp.ramp_up_time_sec)
    v_vehicle_profile_hist[n_steps] = max(min(sp.v_start,sp.v_end), min(max(sp.v_start,sp.v_end), sp.v_start + speed_increase_last))
else:
    v_vehicle_profile_hist[n_steps] = sp.v_end

if n_steps > 0:
    powertrain_chiller_active_log[n_steps] = powertrain_chiller_active_log[n_steps-1]
    Q_gen_motor_profile_hist[n_steps] = Q_gen_motor_profile_hist[n_steps-1]
    Q_gen_inv_profile_hist[n_steps] = Q_gen_inv_profile_hist[n_steps-1]
    Q_gen_batt_profile_hist[n_steps] = Q_gen_batt_profile_hist[n_steps-1]
    P_comp_elec_profile_hist[n_steps] = P_comp_elec_profile_hist[n_steps-1]
    Q_cabin_cool_actual_hist[n_steps] = Q_cabin_cool_actual_hist[n_steps-1]

P_inv_in_profile_hist = np.zeros(n_steps + 1)
for idx in range(n_steps + 1):
    P_wheel_i = hv.P_wheel_func(v_vehicle_profile_hist[idx], sp.m_vehicle, sp.T_ambient)
    P_motor_in_i = hv.P_motor_func(P_wheel_i, sp.eta_motor)
    P_inv_in_profile_hist[idx] = P_motor_in_i / sp.eta_inv if sp.eta_inv > 0 else 0
P_elec_total_profile_hist = P_inv_in_profile_hist + P_comp_elec_profile_hist


# --- 5. Plotting Results ---
temperatures_data = {
    'motor': T_motor_hist, 'inv': T_inv_hist, 'batt': T_batt_hist,
    'cabin': T_cabin_hist, 'coolant': T_coolant_hist
}
heat_gen_data = {
    'motor': Q_gen_motor_profile_hist, 'inv': Q_gen_inv_profile_hist, 'batt': Q_gen_batt_profile_hist
}
battery_power_data = {
    'inv_in': P_inv_in_profile_hist,
    'comp_elec': P_comp_elec_profile_hist,
    'total_elec': P_elec_total_profile_hist
}
# Remove old threshold parameters from sim_params_dict for plotting
sim_params_dict = {
    'T_ambient': sp.T_ambient,
    'T_motor_target': sp.T_motor_target,
    'T_inv_target': sp.T_inv_target,
    'T_batt_target_high': sp.T_batt_target_high,
    'T_batt_stop_cool': sp.T_batt_stop_cool,
    'T_cabin_target': sp.T_cabin_target,
    # 'T_cabin_cool_off_threshold': sp.T_cabin_cool_off_threshold, # Removed
    # 'T_cabin_cool_on_threshold': sp.T_cabin_cool_on_threshold,   # Removed
    'v_start': sp.v_start,
    'v_end': sp.v_end,
    'sim_duration': sp.sim_duration,
    'dt': sp.dt,
    'eta_comp_drive': sp.eta_comp_drive,
    'ramp_up_time_sec': sp.ramp_up_time_sec,
    # Optionally pass the new thresholds if you want to plot them
    'cabin_cooling_temp_thresholds': sp.cabin_cooling_temp_thresholds,
    'cabin_cooling_power_levels': sp.cabin_cooling_power_levels
}

plotting.plot_results(
    time_sim, temperatures_data, powertrain_chiller_active_log,
    P_comp_elec_profile_hist, Q_cabin_cool_actual_hist,
    v_vehicle_profile_hist, heat_gen_data, battery_power_data,
    sim_params_dict, COP
)

print("Main script finished.")
