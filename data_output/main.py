# -*- coding: utf-8 -*-
# main.py (只输出数据，无绘图)
print("Starting---------------------")
import numpy as np

# Import functions from modules
import vehicle_physics as vp
import heat_transfer as ht
import refrigeration_cycle as rc
import simulation_parameters as sp

# --- Function to print data at a specific time point ---
def print_data_at_time_for_plots(target_time_seconds, time_sim_arr,
                                 temperatures_data_dict, chiller_log_arr, ac_power_log_arr,
                                 speed_profile_arr, heat_gen_profiles_dict,
                                 battery_power_profiles_dict, sim_params_dict_local, cop_value_local):
    """
    Prints the x, y data values related to the 7 specified data groups
    at the closest available simulation time to the target_time_seconds.
    """
    idx = (np.abs(time_sim_arr - target_time_seconds)).argmin()
    actual_time_s = time_sim_arr[idx]
    actual_time_min = actual_time_s / 60.0

    print(f"\n--- 数据输出：目标时间点 {target_time_seconds:.2f} 秒 (实际仿真时间: {actual_time_s:.2f} 秒 / {actual_time_min:.2f} 分钟) ---")

    # 提取 sim_params 用于信息输出和条件判断
    v_start = sim_params_dict_local['v_start']
    v_end = sim_params_dict_local['v_end']
    T_ambient_val = sim_params_dict_local['T_ambient']
    eta_comp_drive_val = sim_params_dict_local['eta_comp_drive']
    ramp_up_time_sec_val = sim_params_dict_local['ramp_up_time_sec']
    # 目标温度等参数，用于模拟标题或作为参考值打印
    T_motor_target_val = sim_params_dict_local['T_motor_target']
    T_inv_target_val = sim_params_dict_local['T_inv_target']
    T_batt_target_high_val = sim_params_dict_local['T_batt_target_high']
    T_batt_stop_cool_val = sim_params_dict_local['T_batt_stop_cool']
    T_cabin_target_val = sim_params_dict_local['T_cabin_target']


    # 1. 车辆估算温度
    print(f"\n1. 车辆估算温度:")
    print(f"   参考图表标题: 车辆估算温度 (线性加速 {v_start}-{v_end}km/h, 含空调, COP={cop_value_local:.2f}, 环境={T_ambient_val}°C)")
    print(f"   X轴 (时间): {actual_time_min:.2f} 分钟")
    print(f"   Y轴 (温度 °C):")
    print(f"     - 电机温度: {temperatures_data_dict['motor'][idx]:.2f} °C (目标: {T_motor_target_val}°C)")
    print(f"     - 逆变器温度: {temperatures_data_dict['inv'][idx]:.2f} °C (目标: {T_inv_target_val}°C)")
    print(f"     - 电池温度: {temperatures_data_dict['batt'][idx]:.2f} °C (制冷启动目标: {T_batt_target_high_val}°C, 制冷停止目标: {T_batt_stop_cool_val}°C)")
    print(f"     - 座舱温度: {temperatures_data_dict['cabin'][idx]:.2f} °C (目标: {T_cabin_target_val}°C)")
    print(f"     - 冷却液温度: {temperatures_data_dict['coolant'][idx]:.2f} °C")
    print(f"     - 环境温度参考: {T_ambient_val}°C")


    # 2. 制冷系统状态和总功耗
    print(f"\n2. 制冷系统状态和总功耗:")
    print(f"   参考图表标题: 制冷系统状态和总功耗")
    print(f"   X轴 (时间): {actual_time_min:.2f} 分钟")
    print(f"   左Y轴 (Chiller 状态 0/1): {chiller_log_arr[idx]:.0f} (0=关闭, 1=开启)")
    print(f"   右Y轴 (压缩机功率 W): {ac_power_log_arr[idx]:.2f} W (空调压缩机总电耗, η_comp={eta_comp_drive_val})")

    # 3. 车辆速度变化曲线
    print(f"\n3. 车辆速度变化曲线:")
    print(f"   参考图表标题: 车辆速度变化曲线 ({v_start}到{v_end}km/h匀速加速)")
    print(f"   X轴 (时间): {actual_time_min:.2f} 分钟")
    print(f"   Y轴 (车速 km/h): {speed_profile_arr[idx]:.2f} km/h")

    # 4. 主要部件产热功率
    print(f"\n4. 主要部件产热功率:")
    print(f"   参考图表标题: 主要部件产热功率")
    print(f"   X轴 (时间): {actual_time_min:.2f} 分钟")
    print(f"   Y轴 (产热功率 W):")
    print(f"     - 电机产热功率: {heat_gen_profiles_dict['motor'][idx]:.2f} W")
    print(f"     - 逆变器产热功率: {heat_gen_profiles_dict['inv'][idx]:.2f} W")
    print(f"     - 电池产热功率 (含空调负载): {heat_gen_profiles_dict['batt'][idx]:.2f} W")

    # 5. 电池输出功率分解
    print(f"\n5. 电池输出功率分解:")
    print(f"   参考图表标题: 电池输出功率分解")
    print(f"   X轴 (时间): {actual_time_min:.2f} 分钟")
    print(f"   Y轴 (功率 W):")
    print(f"     - 驱动功率 (逆变器输入功率): {battery_power_profiles_dict['inv_in'][idx]:.2f} W")
    print(f"     - 空调功率: {battery_power_profiles_dict['comp_elec'][idx]:.2f} W")
    print(f"     - 总电池输出功率: {battery_power_profiles_dict['total_elec'][idx]:.2f} W")

    # 6. 部件温度随车速变化轨迹 (仅加速阶段)
    print(f"\n6. 部件温度随车速变化轨迹 (仅加速阶段):")
    print(f"   参考图表标题: 部件温度随车速变化轨迹 (仅加速阶段 {v_start} 到 {v_end} km/h)")
    if actual_time_s <= ramp_up_time_sec_val and sim_params_dict_local['dt'] > 0: # 仅当在加速阶段内且dt有效
        current_speed_at_idx = speed_profile_arr[idx]
        print(f"   X轴 (车速 km/h): {current_speed_at_idx:.2f} km/h (时间点在加速阶段内)")
        print(f"   Y轴 (温度 °C):")
        print(f"     - 电机温度: {temperatures_data_dict['motor'][idx]:.2f} °C")
        print(f"     - 逆变器温度: {temperatures_data_dict['inv'][idx]:.2f} °C")
        print(f"     - 电池温度: {temperatures_data_dict['batt'][idx]:.2f} °C")
        print(f"     - 座舱温度: {temperatures_data_dict['cabin'][idx]:.2f} °C")
        print(f"     - 冷却液温度: {temperatures_data_dict['coolant'][idx]:.2f} °C")
    else:
        if sim_params_dict_local['dt'] == 0:
             print(f"   无法确定加速阶段，因为仿真时间步长 dt 为 0。")
        else:
             print(f"   指定时间点 ({actual_time_min:.2f} 分钟) 不在加速阶段 (0 - {ramp_up_time_sec_val/60:.2f} 分钟)，此部分无对应数据点。")

    # 7. 部件温度变化 (匀速阶段)
    print(f"\n7. 部件温度变化 (匀速阶段):")
    print(f"   参考图表标题: 部件温度变化 (匀速 {v_end} km/h 阶段)")
    # 匀速阶段开始于加速结束之后，并持续到仿真结束
    if actual_time_s > ramp_up_time_sec_val and actual_time_s <= sim_params_dict_local['sim_duration'] and sim_params_dict_local['dt'] > 0:
        print(f"   X轴 (时间): {actual_time_min:.2f} 分钟 (时间点在匀速阶段内)")
        print(f"   Y轴 (温度 °C):")
        print(f"     - 电机温度: {temperatures_data_dict['motor'][idx]:.2f} °C (目标: {T_motor_target_val}°C)")
        print(f"     - 逆变器温度: {temperatures_data_dict['inv'][idx]:.2f} °C (目标: {T_inv_target_val}°C)")
        print(f"     - 电池温度: {temperatures_data_dict['batt'][idx]:.2f} °C (制冷启动目标: {T_batt_target_high_val}°C)")
        print(f"     - 座舱温度: {temperatures_data_dict['cabin'][idx]:.2f} °C (目标: {T_cabin_target_val}°C)")
        print(f"     - 冷却液温度: {temperatures_data_dict['coolant'][idx]:.2f} °C")
        print(f"     - 环境温度参考: {T_ambient_val}°C")

    else:
        if sim_params_dict_local['dt'] == 0:
             print(f"   无法确定匀速阶段，因为仿真时间步长 dt 为 0。")
        elif actual_time_s <= ramp_up_time_sec_val :
            print(f"   指定时间点 ({actual_time_min:.2f} 分钟) 仍在加速阶段 (0 - {ramp_up_time_sec_val/60:.2f} 分钟)，匀速阶段数据尚未开始。")
        elif actual_time_s > sim_params_dict_local['sim_duration']:
             print(f"   指定时间点 ({actual_time_min:.2f} 分钟) 超出仿真总时长 ({sim_params_dict_local['sim_duration']/60:.2f} 分钟)。")
        else:
            print(f"   指定时间点 ({actual_time_min:.2f} 分钟) 不在有效的匀速阶段内。")
    print("\n--- 数据输出结束 ---")


# --- 1. Calculate Refrigeration COP ---
COP, cycle_data = rc.calculate_refrigeration_cop(
    sp.T_suc_C_in, sp.T_cond_sat_C_in, sp.T_be_C_in,
    sp.T_evap_sat_C_in, sp.T_dis_C_in, sp.REFRIGERANT_TYPE
)

# --- 2. Simulation Setup ---
# 确保dt不为0，以避免ZeroDivisionError
if sp.dt == 0:
    if sp.sim_duration > 0:
        print("错误: 仿真时间步长 dt 不能为0，如果仿真时长 sim_duration 大于0。")
        exit() # 或者抛出异常
    else: # sim_duration is also 0
        n_steps = 0 # 只有单个时间点 (t=0)
else:
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

# Set initial values from simulation_parameters.py
T_motor_hist[0] = sp.T_motor_init
T_inv_hist[0] = sp.T_inv_init
T_batt_hist[0] = sp.T_batt_init
T_cabin_hist[0] = sp.T_cabin_init
T_coolant_hist[0] = sp.T_coolant_init
v_vehicle_profile_hist[0] = sp.v_start

# --- 3. Simulation Loop ---
powertrain_chiller_on = False # Initialize Chiller state
print("Starting simulation loop...")
for i in range(n_steps): # Loop will not run if n_steps is 0
    current_time_sec = time_sim[i]

    # 3.1. Calculate current vehicle speed
    if current_time_sec <= sp.ramp_up_time_sec:
        # Ensure ramp_up_time_sec is not zero to avoid division by zero
        if sp.ramp_up_time_sec > 0:
            speed_increase = (sp.v_end - sp.v_start) * (current_time_sec / sp.ramp_up_time_sec)
        else: # If ramp_up_time is zero, speed is instantly v_end (or v_start if v_end < v_start)
            speed_increase = (sp.v_end - sp.v_start) if current_time_sec > 0 else 0 # jump at t>0
        v_vehicle_current = sp.v_start + speed_increase
    else:
        v_vehicle_current = sp.v_end
    # Clamp speed to be between v_start and v_end, correctly handling both ramp up and ramp down scenarios
    v_vehicle_current = max(min(sp.v_start, sp.v_end), min(max(sp.v_start, sp.v_end), v_vehicle_current))
    v_vehicle_profile_hist[i] = v_vehicle_current

    # 3.2. Calculate instantaneous PROPULSION power and heat generation
    P_wheel = vp.P_wheel_func(v_vehicle_current, sp.m_vehicle, sp.T_ambient)
    P_motor_in = vp.P_motor_func(P_wheel, sp.eta_motor)
    P_inv_in = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0 # Used for battery load
    
    Q_gen_motor = vp.Q_mot_func(P_motor_in, sp.eta_motor)
    Q_gen_inv = vp.Q_inv_func(P_motor_in, sp.eta_inv)
    Q_gen_motor_profile_hist[i] = Q_gen_motor
    Q_gen_inv_profile_hist[i] = Q_gen_inv

    # 3.3. Calculate Cabin Heat Loads
    Q_cabin_internal = ht.heat_universal_func(sp.N_passengers)
    Q_cabin_conduction_body = ht.heat_body_func(sp.T_ambient, T_cabin_hist[i], v_vehicle_current, sp.v_air_in_mps, sp.A_body, sp.R_body)
    Q_cabin_conduction_glass = ht.heat_glass_func(sp.T_ambient, T_cabin_hist[i], sp.I_solar_summer, v_vehicle_current, sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
    Q_cabin_ventilation = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, T_cabin_hist[i], sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
    Q_cabin_load_total = Q_cabin_internal + Q_cabin_conduction_body + Q_cabin_conduction_glass + Q_cabin_ventilation

    # 3.4. Cabin Cooling Control
    cabin_temp_error = T_cabin_hist[i] - sp.T_cabin_target
    gain_cabin_cool = 1000 # Proportional gain for cabin cooling
    Q_cabin_cool_demand = gain_cabin_cool * cabin_temp_error if cabin_temp_error > 0 else 0
    Q_cabin_cool_actual = min(Q_cabin_cool_demand, sp.max_cabin_cool_power) if T_cabin_hist[i] > sp.T_cabin_target else 0
    Q_out_cabin = Q_cabin_cool_actual # Heat removed from cabin by AC evaporator

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
            P_comp_elec = 3000 # Fallback
    P_comp_elec_profile_hist[i] = P_comp_elec

    # 3.8. Update Battery Load & Heat Generation
    P_elec_total_batt_out = P_inv_in + P_comp_elec
    Q_gen_batt = vp.Q_batt_func(P_elec_total_batt_out, sp.u_batt, sp.R_int_batt)
    Q_gen_batt_profile_hist[i] = Q_gen_batt

    # 3.9. Calculate Temperature Derivatives (dt already checked not to be 0 if n_steps > 0)
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

if n_steps == 0 and sp.sim_duration >= 0 : # Handle calculations for t=0 if sim_duration is 0 (single point in time)
    print("Simulation for a single time point (t=0). Calculating initial state values...")
    i = 0 # Index for the single time point
    current_time_sec = time_sim[i] # Should be 0
    
    # Speed at t=0
    if sp.ramp_up_time_sec > 0:
        if current_time_sec <= sp.ramp_up_time_sec :
            speed_increase = (sp.v_end - sp.v_start) * (current_time_sec / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 0
        else: # Should not happen for t=0 if ramp_up_time > 0
            speed_increase = (sp.v_end - sp.v_start)
    else: # ramp_up_time is 0
         speed_increase = (sp.v_end - sp.v_start) if current_time_sec > 0 else 0 # Instantly v_end if t>0, else v_start
    
    v_vehicle_current = sp.v_start + speed_increase
    v_vehicle_current = max(min(sp.v_start, sp.v_end), min(max(sp.v_start, sp.v_end), v_vehicle_current))
    v_vehicle_profile_hist[i] = v_vehicle_current

    # Propulsion power and heat at t=0
    P_wheel = vp.P_wheel_func(v_vehicle_current, sp.m_vehicle, sp.T_ambient)
    P_motor_in = vp.P_motor_func(P_wheel, sp.eta_motor)
    P_inv_in_val = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0
    
    Q_gen_motor_profile_hist[i] = vp.Q_mot_func(P_motor_in, sp.eta_motor)
    Q_gen_inv_profile_hist[i] = vp.Q_inv_func(P_motor_in, sp.eta_inv)

    # Cabin loads at t=0
    Q_cabin_internal = ht.heat_universal_func(sp.N_passengers)
    Q_cabin_conduction_body = ht.heat_body_func(sp.T_ambient, T_cabin_hist[i], v_vehicle_current, sp.v_air_in_mps, sp.A_body, sp.R_body)
    Q_cabin_conduction_glass = ht.heat_glass_func(sp.T_ambient, T_cabin_hist[i], sp.I_solar_summer, v_vehicle_current, sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
    Q_cabin_ventilation = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, T_cabin_hist[i], sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
    Q_cabin_load_total = Q_cabin_internal + Q_cabin_conduction_body + Q_cabin_conduction_glass + Q_cabin_ventilation
    
    # Cabin cooling at t=0
    cabin_temp_error = T_cabin_hist[i] - sp.T_cabin_target
    Q_cabin_cool_demand = (1000 * cabin_temp_error) if cabin_temp_error > 0 else 0
    Q_cabin_cool_actual = min(Q_cabin_cool_demand, sp.max_cabin_cool_power) if T_cabin_hist[i] > sp.T_cabin_target else 0
    Q_out_cabin_val = Q_cabin_cool_actual

    # Chiller status at t=0
    powertrain_chiller_on_val = False # Initial state
    start_cooling_powertrain = (T_motor_hist[i] > sp.T_motor_target) or \
                               (T_inv_hist[i] > sp.T_inv_target) or \
                               (T_batt_hist[i] > sp.T_batt_target_high)
    if start_cooling_powertrain: powertrain_chiller_on_val = True
    
    Q_chiller_potential_val = sp.UA_coolant_chiller * (T_coolant_hist[i] - sp.T_evap_sat_for_UA_calc) if T_coolant_hist[i] > sp.T_evap_sat_for_UA_calc else 0
    Q_coolant_chiller_actual_val = min(Q_chiller_potential_val, sp.max_chiller_cool_power) if powertrain_chiller_on_val else 0
    powertrain_chiller_active_log[i] = 1 if powertrain_chiller_on_val and Q_coolant_chiller_actual_val > 0 else 0
        
    # AC Compressor Power at t=0
    P_comp_elec_val = 0.0
    Q_evap_total_needed_val = Q_out_cabin_val + Q_coolant_chiller_actual_val
    if Q_evap_total_needed_val > 0:
        if COP > 0 and COP != float('inf') and sp.eta_comp_drive > 0:
            P_comp_mech_val = Q_evap_total_needed_val / COP
            P_comp_elec_val = P_comp_mech_val / sp.eta_comp_drive
        else:
            P_comp_elec_val = 3000 
    P_comp_elec_profile_hist[i] = P_comp_elec_val
    
    # Battery heat generation at t=0
    Q_gen_batt_profile_hist[i] = vp.Q_batt_func(P_inv_in_val + P_comp_elec_val, sp.u_batt, sp.R_int_batt)
    # Temperatures at t=0 are initial values, no update needed for T_xxx_hist[i+1] as i=0 is the only step.

print("Simulation loop finished.")

# --- 4. Post-processing (Ensure last data point is consistent if simulation ran for multiple steps) ---
if n_steps > 0 : # Only if simulation loop actually ran
    current_time_sec_last = time_sim[n_steps]
    # Recalculate speed for the very last time point
    if current_time_sec_last <= sp.ramp_up_time_sec:
        if sp.ramp_up_time_sec > 0: # Avoid division by zero if ramp_up_time_sec is 0
            speed_increase_last = (sp.v_end - sp.v_start) * (current_time_sec_last / sp.ramp_up_time_sec)
        else: # ramp_up_time_sec is 0, speed is v_end if t_last > 0 else v_start
            speed_increase_last = (sp.v_end - sp.v_start) if current_time_sec_last > 0 else 0
        v_vehicle_profile_hist[n_steps] = max(min(sp.v_start,sp.v_end), min(max(sp.v_start,sp.v_end), sp.v_start + speed_increase_last))
    else:
        v_vehicle_profile_hist[n_steps] = sp.v_end

    # Repeat last calculated state for logs (that were indexed with 'i' in the loop) for the (i+1)-th or n_steps-th entry
    powertrain_chiller_active_log[n_steps] = powertrain_chiller_active_log[n_steps-1]
    Q_gen_motor_profile_hist[n_steps] = Q_gen_motor_profile_hist[n_steps-1]
    Q_gen_inv_profile_hist[n_steps] = Q_gen_inv_profile_hist[n_steps-1]
    Q_gen_batt_profile_hist[n_steps] = Q_gen_batt_profile_hist[n_steps-1]
    P_comp_elec_profile_hist[n_steps] = P_comp_elec_profile_hist[n_steps-1]


# Calculate P_inv_in profile for all time steps (including the last if applicable)
P_inv_in_profile_hist = np.zeros(n_steps + 1)
for idx_calc in range(n_steps + 1): 
    P_wheel_idx = vp.P_wheel_func(v_vehicle_profile_hist[idx_calc], sp.m_vehicle, sp.T_ambient)
    P_motor_in_idx = vp.P_motor_func(P_wheel_idx, sp.eta_motor)
    P_inv_in_profile_hist[idx_calc] = P_motor_in_idx / sp.eta_inv if sp.eta_inv > 0 else 0
P_elec_total_profile_hist = P_inv_in_profile_hist + P_comp_elec_profile_hist


# --- 5. Prepare Data for Output ---
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
    'v_start': sp.v_start,
    'v_end': sp.v_end,
    'sim_duration': sp.sim_duration,
    'dt': sp.dt, # dt is crucial for ramp_up_index in plotting
    'eta_comp_drive': sp.eta_comp_drive,
    'ramp_up_time_sec': sp.ramp_up_time_sec,
}

# --- Call the function to print data for a specific time ---
# 你可以在这里修改 target_time_to_print_seconds 来指定你想要查看数据的时间点 (单位：秒)
target_time_to_print_seconds = 300 # 例如，查看仿真开始后300秒的数据

# 如果仿真时长小于此时间，则会选择最接近的有效时间点
if n_steps == 0 : # Only one time point at t=0
    target_time_to_print_seconds = 0
    print(f"\n警告: 仿真时长为0 (或dt=0)。将打印 t=0s 的数据。")
elif target_time_to_print_seconds > sp.sim_duration:
     print(f"\n警告: 请求打印的时间 {target_time_to_print_seconds}s 超出总仿真时长 {sp.sim_duration}s。将打印最后一个时间点 ({sp.sim_duration}s) 的数据。")
     target_time_to_print_seconds = sp.sim_duration


print_data_at_time_for_plots(
    target_time_seconds=target_time_to_print_seconds,
    time_sim_arr=time_sim,
    temperatures_data_dict=temperatures_data,
    chiller_log_arr=powertrain_chiller_active_log,
    ac_power_log_arr=P_comp_elec_profile_hist,
    speed_profile_arr=v_vehicle_profile_hist,
    heat_gen_profiles_dict=heat_gen_data,
    battery_power_profiles_dict=battery_power_data,
    sim_params_dict_local=sim_params_dict,
    cop_value_local=COP
)

# 绘图相关的调用已被移除
# plotting.plot_results(...)

print("Main script finished. Data for the specified time point has been printed above.")