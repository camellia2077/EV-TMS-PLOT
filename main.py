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
# Uses parameters from simulation_parameters.py
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
Q_cabin_cool_actual_hist = np.zeros(n_steps + 1) # Log for cabin cooling power

# Set initial values from simulation_parameters.py
T_motor_hist[0] = sp.T_motor_init
T_inv_hist[0] = sp.T_inv_init
T_batt_hist[0] = sp.T_batt_init
T_cabin_hist[0] = sp.T_cabin_init # This should be used from config.ini if specified
T_coolant_hist[0] = sp.T_coolant_init
v_vehicle_profile_hist[0] = sp.v_start

# --- 3. Simulation Loop ---
powertrain_chiller_on = False # Initialize Chiller state

# Initialize cabin cooling state based on initial temperature
# If T_cabin_init is already below T_cabin_cool_off_threshold, start with low power.
# Otherwise, assume high power is needed if T_cabin_init > T_cabin_target.
if T_cabin_hist[0] <= sp.T_cabin_cool_off_threshold:
    cabin_cooling_high_power_active = False
elif T_cabin_hist[0] > sp.T_cabin_target: # If above target, definitely start with high
    cabin_cooling_high_power_active = True
else: # Between cool_off_threshold and target, could be either, let's default to True or based on need
    cabin_cooling_high_power_active = False # Start low if already cool enough

# Set initial Q_cabin_cool_actual_hist[0]
if cabin_cooling_high_power_active:
    Q_cabin_cool_actual_hist[0] = sp.cabin_cooling_power_high if T_cabin_hist[0] > sp.T_cabin_target else 0
else:
    Q_cabin_cool_actual_hist[0] = sp.cabin_cooling_power_low if T_cabin_hist[0] > sp.T_cabin_target else 0


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
    v_vehicle_current = max(sp.v_start, min(sp.v_end, v_vehicle_current))
    v_vehicle_profile_hist[i] = v_vehicle_current

    # 3.2. Calculate instantaneous PROPULSION power and heat generation
    P_wheel = hv.P_wheel_func(v_vehicle_current, sp.m_vehicle, sp.T_ambient)
    P_motor_in = hv.P_motor_func(P_wheel, sp.eta_motor)
    P_inv_in = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0 # Used for battery load
    
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

    # 3.4. Cabin Cooling Control (REVISED LOGIC)
    
    # Step 1: Determine if the cooling power state (high/low) needs to change based on thresholds
    if cabin_cooling_high_power_active:
        # Currently in HIGH power mode
        if current_cabin_temp <= sp.T_cabin_cool_off_threshold:
            cabin_cooling_high_power_active = False # Switch to LOW power
            # print(f"Time: {current_time_sec:.1f}s, T_cabin: {current_cabin_temp:.2f}°C -> Switching to LOW power.")
    else:
        # Currently in LOW power mode
        if current_cabin_temp >= sp.T_cabin_cool_on_threshold:
            cabin_cooling_high_power_active = True # Switch to HIGH power
            # print(f"Time: {current_time_sec:.1f}s, T_cabin: {current_cabin_temp:.2f}°C -> Switching to HIGH power.")

    # Step 2: Set actual cooling power based on the current state (cabin_cooling_high_power_active)
    #         and whether cooling is actually needed (i.e., if current_cabin_temp is above a certain point).
    Q_cabin_cool_actual = 0 # Default to no cooling

    if cabin_cooling_high_power_active:
        # In HIGH power mode.
        # We want to cool if the temperature is above the point where we'd switch to low power.
        # This ensures that high power continues to drive the temperature down towards T_cabin_cool_off_threshold.
        if current_cabin_temp > sp.T_cabin_cool_off_threshold: # Use T_cabin_cool_off_threshold as the lower bound for high power operation
            Q_cabin_cool_actual = sp.cabin_cooling_power_high
        # If current_cabin_temp is AT or BELOW T_cabin_cool_off_threshold, 
        # cabin_cooling_high_power_active should have just been set to False in the block above.
        # If for some reason it's still True here and temp is low, set power to 0 or low.
        # However, the state transition should handle this. If it just switched, next iteration will use low power.
        # For this iteration, if it just crossed T_cabin_cool_off_threshold, it will switch to low,
        # and then the 'else' block below will apply for Q_cabin_cool_actual.
        # So, if it's high power and temp > off_thresh, use high. Otherwise, it implies it's at/below off_thresh,
        # and the state will flip, leading to low power or zero in the next step or correctly in the 'else' if state flipped this step.

    else: # cabin_cooling_high_power_active is False (LOW power mode)
        # In LOW power mode.
        # We want to provide low cooling if the temperature is still above the overall target T_cabin_target.
        # Or, more conservatively, if it's above T_cabin_cool_off_threshold to prevent it from dropping further.
        # Using T_cabin_target allows it to gently bring temp down if it slightly overshot T_cabin_cool_off_threshold
        # or if low power is meant to maintain around T_cabin_target.
        if current_cabin_temp > sp.T_cabin_target: # Cool with low power if above the general target
            Q_cabin_cool_actual = sp.cabin_cooling_power_low
        # If current_cabin_temp is at or below T_cabin_target, no cooling in low power mode.
        # This prevents low power from further cooling if it's already at or below the main target.

    # Ensure cooling power does not exceed max capability (already handled by cabin_cooling_power_high/low if they are <= max)
    # Q_cabin_cool_actual = min(Q_cabin_cool_actual, sp.max_cabin_cool_power) # This line is good
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
    Q_coolant_radiator = max(0, Q_radiator_potential) # Radiator can only reject heat

    start_cooling_powertrain = (T_motor_hist[i] > sp.T_motor_target) or \
                               (T_inv_hist[i] > sp.T_inv_target) or \
                               (T_batt_hist[i] > sp.T_batt_target_high)
    stop_cooling_powertrain = (T_motor_hist[i] < sp.T_motor_stop_cool) and \
                              (T_inv_hist[i] < sp.T_inv_stop_cool) and \
                              (T_batt_hist[i] < sp.T_batt_stop_cool)
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
        else:
            P_comp_elec = 3000 
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

    # 3.10. Update Temperatures using Euler forward method
    T_motor_hist[i+1] = T_motor_hist[i] + dT_motor_dt * sp.dt
    T_inv_hist[i+1] = T_inv_hist[i] + dT_inv_dt * sp.dt
    T_batt_hist[i+1] = T_batt_hist[i] + dT_batt_dt * sp.dt
    T_cabin_hist[i+1] = T_cabin_hist[i] + dT_cabin_dt * sp.dt
    T_coolant_hist[i+1] = T_coolant_hist[i] + dT_coolant_dt * sp.dt

print("Simulation loop finished.")

# --- 4. Post-processing for Plots (Ensure last data point is consistent) ---
current_time_sec_last = time_sim[n_steps]
if current_time_sec_last <= sp.ramp_up_time_sec:
    speed_increase_last = (sp.v_end - sp.v_start) * (current_time_sec_last / sp.ramp_up_time_sec)
    v_vehicle_profile_hist[n_steps] = max(sp.v_start, min(sp.v_end, sp.v_start + speed_increase_last))
else:
    v_vehicle_profile_hist[n_steps] = sp.v_end

if n_steps > 0: 
    powertrain_chiller_active_log[n_steps] = powertrain_chiller_active_log[n_steps-1]
    Q_gen_motor_profile_hist[n_steps] = Q_gen_motor_profile_hist[n_steps-1]
    Q_gen_inv_profile_hist[n_steps] = Q_gen_inv_profile_hist[n_steps-1]
    Q_gen_batt_profile_hist[n_steps] = Q_gen_batt_profile_hist[n_steps-1]
    P_comp_elec_profile_hist[n_steps] = P_comp_elec_profile_hist[n_steps-1]
    Q_cabin_cool_actual_hist[n_steps] = Q_cabin_cool_actual_hist[n_steps-1] 
elif n_steps == 0: 
    pass 

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
sim_params_dict = {
    'T_ambient': sp.T_ambient,
    'T_motor_target': sp.T_motor_target,
    'T_inv_target': sp.T_inv_target,
    'T_batt_target_high': sp.T_batt_target_high,
    'T_batt_stop_cool': sp.T_batt_stop_cool,
    'T_cabin_target': sp.T_cabin_target,
    'T_cabin_cool_off_threshold': sp.T_cabin_cool_off_threshold, 
    'T_cabin_cool_on_threshold': sp.T_cabin_cool_on_threshold,   
    'v_start': sp.v_start,
    'v_end': sp.v_end,
    'sim_duration': sp.sim_duration,
    'dt': sp.dt,
    'eta_comp_drive': sp.eta_comp_drive,
    'ramp_up_time_sec': sp.ramp_up_time_sec,
}

plotting.plot_results(
    time_sim, temperatures_data, powertrain_chiller_active_log, 
    P_comp_elec_profile_hist, Q_cabin_cool_actual_hist, 
    v_vehicle_profile_hist, heat_gen_data, battery_power_data,
    sim_params_dict, COP
)

print("Main script finished.")