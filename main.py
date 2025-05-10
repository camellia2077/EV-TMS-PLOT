# -*- coding: utf-8 -*-
# main.py
import numpy as np

# Import functions from modules
import heat_vehicle as hv
import heat_cabin as ht
import refrigeration_cycle as rc
import simulation_parameters as sp # sp now loads all plotting font sizes
import plotting
# --- 0. 打印输入的制冷循环参数 ---
print("\n--- 初始制冷循环输入参数 ---")
print(f"压缩机入口过热度 (T_suc_C_in): {sp.T_suc_C_in}°C")
print(f"冷凝饱和温度 (T_cond_sat_C_in): {sp.T_cond_sat_C_in}°C")
print(f"冷凝器出口过冷度 (T_be_C_in): {sp.T_be_C_in}°C") # 通常 T_be_C_in 指的是冷凝器出口温度，其与饱和冷凝温度的差值为过冷度
print(f"蒸发饱和温度 (T_evap_sat_C_in): {sp.T_evap_sat_C_in}°C")
print(f"压缩机排气温度 (T_dis_C_in): {sp.T_dis_C_in}°C")
print(f"制冷剂类型 (REFRIGERANT_TYPE): {sp.REFRIGERANT_TYPE}")
print("----------------------------------------------------")
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
radiator_effectiveness_log = np.zeros(n_steps + 1)
Q_coolant_radiator_log = np.zeros(n_steps + 1)

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
radiator_effectiveness_log[0] = 1.0

initial_cabin_temp = T_cabin_hist[0]
Q_cabin_cool_initial = sp.cabin_cooling_power_levels[-1]

for j in range(len(sp.cabin_cooling_temp_thresholds)):
    if initial_cabin_temp <= sp.cabin_cooling_temp_thresholds[j]:
        Q_cabin_cool_initial = sp.cabin_cooling_power_levels[j]
        break
Q_cabin_cool_actual_hist[0] = max(0, Q_cabin_cool_initial)

powertrain_chiller_on = False

print("Starting simulation loop...")
for i in range(n_steps):
    current_time_sec = time_sim[i]
    current_cabin_temp = T_cabin_hist[i]
    current_T_motor = T_motor_hist[i]
    current_T_inv = T_inv_hist[i]
    current_T_batt = T_batt_hist[i]
    current_T_coolant = T_coolant_hist[i]

    if current_time_sec <= sp.ramp_up_time_sec:
        speed_increase = (sp.v_end - sp.v_start) * (current_time_sec / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 0
        v_vehicle_current = sp.v_start + speed_increase
    else:
        v_vehicle_current = sp.v_end
    v_vehicle_current = max(min(sp.v_start, sp.v_end), min(max(sp.v_start, sp.v_end), v_vehicle_current))
    if current_time_sec > sp.ramp_up_time_sec : v_vehicle_current = sp.v_end
    v_vehicle_profile_hist[i] = v_vehicle_current

    P_wheel = hv.P_wheel_func(v_vehicle_current, sp.m_vehicle, sp.T_ambient)
    P_motor_in = hv.P_motor_func(P_wheel, sp.eta_motor)
    P_inv_in = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0

    Q_gen_motor = hv.Q_mot_func(P_motor_in, sp.eta_motor)
    Q_gen_inv = hv.Q_inv_func(P_motor_in, sp.eta_inv)
    Q_gen_motor_profile_hist[i] = Q_gen_motor
    Q_gen_inv_profile_hist[i] = Q_gen_inv

    Q_cabin_internal = ht.heat_universal_func(sp.N_passengers)
    Q_cabin_conduction_body = ht.heat_body_func(sp.T_ambient, current_cabin_temp, v_vehicle_current, sp.v_air_in_mps, sp.A_body, sp.R_body)
    Q_cabin_conduction_glass = ht.heat_glass_func(sp.T_ambient, current_cabin_temp, sp.I_solar_summer, v_vehicle_current, sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
    Q_cabin_ventilation = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, current_cabin_temp, sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
    Q_cabin_load_total = Q_cabin_internal + Q_cabin_conduction_body + Q_cabin_conduction_glass + Q_cabin_ventilation

    Q_cabin_cool_actual = sp.cabin_cooling_power_levels[-1]
    for j in range(len(sp.cabin_cooling_temp_thresholds)):
        if current_cabin_temp <= sp.cabin_cooling_temp_thresholds[j]:
            Q_cabin_cool_actual = sp.cabin_cooling_power_levels[j]
            break
    Q_cabin_cool_actual = max(0, Q_cabin_cool_actual)
    Q_out_cabin = Q_cabin_cool_actual
    Q_cabin_cool_actual_hist[i] = Q_out_cabin

    Q_motor_to_coolant = sp.UA_motor_coolant * (current_T_motor - current_T_coolant)
    Q_inv_to_coolant = sp.UA_inv_coolant * (current_T_inv - current_T_coolant)
    Q_batt_to_coolant = sp.UA_batt_coolant * (current_T_batt - current_T_coolant)
    Q_coolant_absorb = Q_motor_to_coolant + Q_inv_to_coolant + Q_batt_to_coolant

    current_radiator_effectiveness = 1.0
    all_comps_below_stop_cool = (current_T_motor < sp.T_motor_stop_cool) and \
                                (current_T_inv < sp.T_inv_stop_cool) and \
                                (current_T_batt < sp.T_batt_stop_cool)
    all_comps_at_or_below_target = (current_T_motor <= sp.T_motor_target) and \
                                   (current_T_inv <= sp.T_inv_target) and \
                                   (current_T_batt <= sp.T_batt_target_low)
    if all_comps_below_stop_cool:
        current_radiator_effectiveness = sp.radiator_effectiveness_below_stop_cool
    elif all_comps_at_or_below_target:
        current_radiator_effectiveness = sp.radiator_effectiveness_at_target
    radiator_effectiveness_log[i] = current_radiator_effectiveness
    UA_coolant_radiator_effective = sp.UA_coolant_radiator_max * current_radiator_effectiveness
    Q_radiator_potential = UA_coolant_radiator_effective * (current_T_coolant - sp.T_ambient)
    Q_coolant_radiator = max(0, Q_radiator_potential)
    Q_coolant_radiator_log[i] = Q_coolant_radiator

    start_cooling_powertrain = (current_T_motor > sp.T_motor_target) or \
                               (current_T_inv > sp.T_inv_target) or \
                               (current_T_batt > sp.T_batt_target_high)
    stop_cooling_powertrain = (current_T_motor < sp.T_motor_stop_cool) and \
                              (current_T_inv < sp.T_inv_stop_cool) and \
                              (current_T_batt < sp.T_batt_stop_cool)
    if start_cooling_powertrain:
        powertrain_chiller_on = True
    elif stop_cooling_powertrain:
        powertrain_chiller_on = False

    Q_chiller_potential = sp.UA_coolant_chiller * (current_T_coolant - sp.T_evap_sat_for_UA_calc) if current_T_coolant > sp.T_evap_sat_for_UA_calc else 0
    Q_coolant_chiller_actual = min(Q_chiller_potential, sp.max_chiller_cool_power) if powertrain_chiller_on else 0
    powertrain_chiller_active_log[i] = 1 if powertrain_chiller_on and Q_coolant_chiller_actual > 0 else 0

    Q_coolant_reject = Q_coolant_chiller_actual + Q_coolant_radiator

    P_comp_elec = 0.0
    Q_evap_total_needed = Q_out_cabin + Q_coolant_chiller_actual
    if Q_evap_total_needed > 0:
        if COP > 0 and COP != float('inf') and sp.eta_comp_drive > 0:
            P_comp_mech = Q_evap_total_needed / COP
            P_comp_elec = P_comp_mech / sp.eta_comp_drive
        else:
            P_comp_elec = Q_evap_total_needed / 2.0 if sp.eta_comp_drive <=0 else Q_evap_total_needed / (2.0 * sp.eta_comp_drive)
    P_comp_elec_profile_hist[i] = P_comp_elec

    P_elec_total_batt_out = P_inv_in + P_comp_elec
    Q_gen_batt = hv.Q_batt_func(P_elec_total_batt_out, sp.u_batt, sp.R_int_batt)
    Q_gen_batt_profile_hist[i] = Q_gen_batt

    dT_motor_dt = (Q_gen_motor - Q_motor_to_coolant) / sp.mc_motor if sp.mc_motor > 0 else 0
    dT_inv_dt = (Q_gen_inv - Q_inv_to_coolant) / sp.mc_inverter if sp.mc_inverter > 0 else 0
    dT_batt_dt = (Q_gen_batt - Q_batt_to_coolant) / sp.mc_battery if sp.mc_battery > 0 else 0
    dT_cabin_dt = (Q_cabin_load_total - Q_out_cabin) / sp.mc_cabin if sp.mc_cabin > 0 else 0
    dT_coolant_dt = (Q_coolant_absorb - Q_coolant_reject) / sp.mc_coolant if sp.mc_coolant > 0 else 0

    T_motor_hist[i+1] = current_T_motor + dT_motor_dt * sp.dt
    T_inv_hist[i+1] = current_T_inv + dT_inv_dt * sp.dt
    T_batt_hist[i+1] = current_T_batt + dT_batt_dt * sp.dt
    T_cabin_hist[i+1] = current_cabin_temp + dT_cabin_dt * sp.dt
    T_coolant_hist[i+1] = current_T_coolant + dT_coolant_dt * sp.dt

print("Simulation loop finished.")

current_time_sec_last = time_sim[n_steps]
if current_time_sec_last <= sp.ramp_up_time_sec:
    speed_increase_last = (sp.v_end - sp.v_start) * (current_time_sec_last / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 0
    v_vehicle_profile_hist[n_steps] = max(min(sp.v_start,sp.v_end), min(max(sp.v_start,sp.v_end), sp.v_start + speed_increase_last))
else:
    v_vehicle_profile_hist[n_steps] = sp.v_end

if n_steps > 0:
    powertrain_chiller_active_log[n_steps] = powertrain_chiller_active_log[n_steps-1]
    radiator_effectiveness_log[n_steps] = radiator_effectiveness_log[n_steps-1]
    Q_coolant_radiator_log[n_steps] = Q_coolant_radiator_log[n_steps-1]
    Q_gen_motor_profile_hist[n_steps] = Q_gen_motor_profile_hist[n_steps-1]
    Q_gen_inv_profile_hist[n_steps] = Q_gen_inv_profile_hist[n_steps-1]
    Q_gen_batt_profile_hist[n_steps] = Q_gen_batt_profile_hist[n_steps-1]
    P_comp_elec_profile_hist[n_steps] = P_comp_elec_profile_hist[n_steps-1]
    Q_cabin_cool_actual_hist[n_steps] = Q_cabin_cool_actual_hist[n_steps-1]
elif n_steps == 0:
    radiator_effectiveness_log[n_steps] = 1.0
    pass

P_inv_in_profile_hist = np.zeros(n_steps + 1)
for idx in range(n_steps + 1):
    P_wheel_i = hv.P_wheel_func(v_vehicle_profile_hist[idx], sp.m_vehicle, sp.T_ambient)
    P_motor_in_i = hv.P_motor_func(P_wheel_i, sp.eta_motor)
    P_inv_in_profile_hist[idx] = P_motor_in_i / sp.eta_inv if sp.eta_inv > 0 else 0
P_elec_total_profile_hist = P_inv_in_profile_hist + P_comp_elec_profile_hist

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
cooling_system_logs = {
    'chiller_active': powertrain_chiller_active_log,
    'radiator_effectiveness': radiator_effectiveness_log,
    'Q_radiator': Q_coolant_radiator_log
}
sim_params_dict = {
    'T_ambient': sp.T_ambient,
    'T_motor_target': sp.T_motor_target,
    'T_inv_target': sp.T_inv_target,
    'T_batt_target_high': sp.T_batt_target_high,
    'T_batt_stop_cool': sp.T_batt_stop_cool,
    'T_cabin_target': sp.T_cabin_target,
    'v_start': sp.v_start,
    'v_end': sp.v_end,
    'sim_duration': sp.sim_duration,
    'dt': sp.dt,
    'eta_comp_drive': sp.eta_comp_drive,
    'ramp_up_time_sec': sp.ramp_up_time_sec,
    'cabin_cooling_temp_thresholds': sp.cabin_cooling_temp_thresholds,
    'cabin_cooling_power_levels': sp.cabin_cooling_power_levels,
    'figure_width_inches': sp.figure_width_inches,
    'figure_height_inches': sp.figure_height_inches,
    'figure_dpi': sp.figure_dpi,
    'legend_font_size': sp.legend_font_size,
    'axis_label_font_size': sp.axis_label_font_size,
    'tick_label_font_size': sp.tick_label_font_size,
    'title_font_size': sp.title_font_size,
    'UA_coolant_radiator_max': sp.UA_coolant_radiator_max,
    'radiator_effectiveness_at_target': sp.radiator_effectiveness_at_target,
    'radiator_effectiveness_below_stop_cool': sp.radiator_effectiveness_below_stop_cool
}

# --- 5. Plotting Results and Retrieving Extrema ---
all_temperature_extrema = plotting.plot_results( # 修改：接收返回值
    time_data=time_sim,
    temperatures=temperatures_data,
    ac_power_log=P_comp_elec_profile_hist,
    cabin_cool_power_log=Q_cabin_cool_actual_hist,
    speed_profile=v_vehicle_profile_hist,
    heat_gen_profiles=heat_gen_data,
    battery_power_profiles=battery_power_data,
    sim_params=sim_params_dict,
    cop_value=COP,
    cooling_system_logs=cooling_system_logs
)

# --- 6. 部件温度极值点 ---
print("\n--- Local Temperature Extrema ---")
for component_name, extrema in all_temperature_extrema.items():
    if extrema['minima']:
        print(f"\n{component_name} - 局部最低点:")
        for time_min, temp_c in extrema['minima']:
            print(f"  时间: {time_min:.2f} 分钟, 温度: {temp_c:.2f} °C")
    if extrema['maxima']:
        print(f"\n{component_name} - 局部最高点:")
        for time_min, temp_c in extrema['maxima']:
            print(f"  时间: {time_min:.2f} 分钟, 温度: {temp_c:.2f} °C")
# --- 7. Print Powertrain Chiller State Transition Points ---
print("\n--- Chiller 状态 Transition Points ---")
if n_steps > 0: # Ensure there's more than one state to compare

    found_transitions = False

    for k in range(1, n_steps + 1): # Iterate from the second element up to the last
        # State at current time step k (time_sim[k])
        current_chiller_state = powertrain_chiller_active_log[k]
        # State at previous time step k-1 (time_sim[k-1])
        previous_chiller_state = powertrain_chiller_active_log[k-1]

        if current_chiller_state != previous_chiller_state:
            transition_time_sec = time_sim[k] # The change is observed at this time step
            transition_time_min = transition_time_sec / 60
            if current_chiller_state == 1 and previous_chiller_state == 0:
                print(f"  Transition: OFF (0) -> ON (1) at Time: {transition_time_sec:.2f} s ({transition_time_min:.2f} min)")
                found_transitions = True
            elif current_chiller_state == 0 and previous_chiller_state == 1:
                print(f"  Transition: ON (1) -> OFF (0) at Time: {transition_time_sec:.2f} s ({transition_time_min:.2f} min)")
                found_transitions = True
            # else: This case should not happen for boolean 0/1 states if they are distinct.

    if not found_transitions:
        print("  No powertrain chiller state transitions recorded during the simulation.")
else:
    print("  Simulation has less than 2 steps, cannot detect transitions.")

print("Main script finished.")
