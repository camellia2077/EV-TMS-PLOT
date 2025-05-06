# -*- coding: utf-8 -*-
#修改速度变化
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import CoolProp.CoolProp as CP
import os  # Import os module to handle file paths

# 设置 matplotlib 支持中文显示
mpl.rcParams['font.sans-serif'] = ['SimHei'] # 指定默认字体为黑体
mpl.rcParams['axes.unicode_minus'] = False # 解决保存图像是负号'-'显示为方块的问题

def rho_air_func(t):
    """计算空气密度"""
    t_k = t + 273.15
    p = 101325
    R_air = 287.05
    return p / (R_air * t_k)

def F_roll_func(m):
    """计算滚动阻力"""
    mu = 0.008
    g = 9.8
    return mu * m * g

def F_aero_func(v_kmh, T_amb):
    """计算空气阻力"""
    rho = rho_air_func(T_amb)
    Cd = 0.22
    a = 3.00
    vmps = v_kmh / 3.6
    if vmps < 0: vmps = 0 # Avoid issues with potential negative speed if logic slips
    return 0.5 * rho * Cd * a * (vmps**2)

def P_wheel_func(v_kmh, m, T_amb):
    """计算车轮处的驱动功率需求"""
    force_roll = F_roll_func(m)
    force_aero = F_aero_func(v_kmh, T_amb)
    force_total = force_aero + force_roll
    v_mps = v_kmh / 3.6
    if v_mps < 0: v_mps = 0
    return force_total * v_mps

def P_motor_func(p_wheel, eta_m):
    """计算电机输入功率 (来自逆变器)"""
    if p_wheel <= 0: return 0 # No power needed if not moving or braking (simplified)
    # Ensure efficiency is positive before dividing
    return p_wheel / eta_m if eta_m > 0 else float('inf')


def Q_mot_func(p_motor_in, eta_m):
    """计算电机产热功率"""
    if p_motor_in <= 0: return 0
    return p_motor_in * (1 - eta_m)

def Q_inv_func(p_motor_in, eta_inv):
    """计算逆变器产热功率"""
    if p_motor_in <= 0: return 0
    # Calculate power input to inverter, avoid division by zero
    p_inv_in = p_motor_in / eta_inv if eta_inv > 0 else float('inf')
    # Heat generated is the loss
    return p_inv_in * (1 - eta_inv) if eta_inv > 0 else 0

def Q_batt_func(p_elec_total, u_batt, r_int):
    """计算电池产热功率 (基于总电流和内阻)"""
    if p_elec_total <= 0: return 0
    # Calculate total current from the battery
    I_batt = p_elec_total / u_batt if u_batt > 0 else 0 # Avoid division by zero
    # Calculate heat based on internal resistance
    return (I_batt**2) * r_int

# --- (Other heat transfer functions remain the same) ---
def heat_universal_func(N_passengers):
    """计算座舱内部通用热源"""
    q_person = 100
    Q_passengers = N_passengers * q_person
    Q_electronics = 100
    Q_powertrain = 50
    return Q_passengers + Q_electronics + Q_powertrain

def calculate_h_out_func(v_vehicle_kmh):
    """计算车身外表面对流换热系数"""
    if v_vehicle_kmh < 0: v_vehicle_kmh = 0
    v_mps = v_vehicle_kmh / 3.6
    return 5.7 + 3.8 * v_mps

def calculate_h_in_func(v_air_internal_mps):
    """计算座舱内表面对流换热系数"""
    h_natural = 2.5
    h_forced_factor = 5.5
    return max(h_natural, h_natural + h_forced_factor * v_air_internal_mps)

def calculate_u_value_func(h_internal, R_material, h_external):
    """计算总传热系数 U 值"""
    if h_internal <= 0 or h_external <= 0: return 0
    R_in = 1.0 / h_internal
    R_out = 1.0 / h_external
    R_total = R_in + R_material + R_out
    if R_total <= 0: return float('inf') # Avoid division by zero or negative resistance
    return 1.0 / R_total

def heat_body_func(T_outside, T_inside, v_vehicle_kmh, v_air_internal_mps, A_body, R_body):
    """计算通过车身(非玻璃)的传导热量"""
    h_outside = calculate_h_out_func(v_vehicle_kmh)
    h_inside = calculate_h_in_func(v_air_internal_mps)
    U_body = calculate_u_value_func(h_inside, R_body, h_outside)
    return U_body * A_body * (T_outside - T_inside)

def heat_glass_func(T_outside, T_inside, I_solar, v_vehicle_kmh, v_air_internal_mps, A_glass, R_glass, SHGC, A_glass_sun):
    """计算通过玻璃的传导和太阳辐射热量"""
    h_outside = calculate_h_out_func(v_vehicle_kmh)
    h_inside = calculate_h_in_func(v_air_internal_mps)
    U_glass = calculate_u_value_func(h_inside, R_glass, h_outside)
    Q_glass_conduction = U_glass * A_glass * (T_outside - T_inside)
    Q_glass_solar_gain = SHGC * A_glass_sun * I_solar
    return Q_glass_conduction + Q_glass_solar_gain

def heat_vent_summer_func(N_passengers, T_outside, T_inside, W_outside, W_inside, fraction_fresh_air):
    """计算夏季通风带来的热负荷 (显热+潜热)"""
    air_density = rho_air_func(T_outside) # Use outside air density for fresh air mass calc
    air_vol_flow_per_person = 0.007 # m^3/s per person (typical value)
    air_vol_flow_total_demand = air_vol_flow_per_person * N_passengers
    air_vol_flow_fresh = air_vol_flow_total_demand * fraction_fresh_air
    m_air_flow_fresh = air_density * air_vol_flow_fresh # kg/s
    c_p_air = 1005 # J/kg/K
    Q_vent_sensible = m_air_flow_fresh * c_p_air * (T_outside - T_inside)
    h_fg = 2.45e6 # J/kg (latent heat of vaporization for water approx)
    # Calculate latent load based on humidity difference (ensure W_outside > W_inside)
    Q_vent_latent = m_air_flow_fresh * h_fg * max(0, W_outside - W_inside)
    return Q_vent_sensible + Q_vent_latent
# --- End 函数定义 ---

# --- Refrigeration Cycle Inputs ---
T_suc_C = 15      # 压缩机吸气温度 (°C)
T_cond_sat_C = 45 # LCC中制冷剂饱和冷凝温度 (°C)
T_be_C = 42       # 膨胀阀前制冷剂温度 (°C) (Before Expansion)
T_evap_sat_C = 5  # 代表性蒸发饱和温度 (°C)
T_dis_C = 70      # 压缩机排气温度 (°C) (User Provided)
REFRIGERANT = 'R1234yf' # 指定制冷剂类型

# --- Calculate Refrigerant State Points & COP using CoolProp ---
COP = 0.0 # Initialize COP
try:
    # Convert temps to Kelvin
    T_suc_K = T_suc_C + 273.15
    T_cond_sat_K = T_cond_sat_C + 273.15
    T_be_K = T_be_C + 273.15
    T_evap_sat_K = T_evap_sat_C + 273.15
    T_dis_K = T_dis_C + 273.15

    # Determine pressures from saturation temperatures
    P_evap = CP.PropsSI('P', 'T', T_evap_sat_K, 'Q', 1, REFRIGERANT) # Pa (use Q=1 for sat vapor pressure)
    P_cond = CP.PropsSI('P', 'T', T_cond_sat_K, 'Q', 0, REFRIGERANT) # Pa (use Q=0 for sat liquid pressure)

    # State 1: Compressor Suction (Superheated Vapor)
    h1 = CP.PropsSI('H', 'T', T_suc_K, 'P', P_evap, REFRIGERANT) # J/kg
    s1 = CP.PropsSI('S', 'T', T_suc_K, 'P', P_evap, REFRIGERANT) # J/kg/K

    # State 2: Compressor Discharge (Superheated Vapor - using given T_dis)
    if T_dis_K <= T_cond_sat_K:
        print(f"Warning: Provided T_dis ({T_dis_C}°C) is not above T_cond_sat ({T_cond_sat_C}°C). Check inputs.")
    h2 = CP.PropsSI('H', 'T', T_dis_K, 'P', P_cond, REFRIGERANT) # J/kg

    # State 3: Condenser Outlet / Before Expansion Valve (Subcooled Liquid)
    if T_be_K >= T_cond_sat_K:
        print(f"Warning: Provided T_be ({T_be_C}°C) is not below T_cond_sat ({T_cond_sat_C}°C). Check inputs.")
    h3 = CP.PropsSI('H', 'T', T_be_K, 'P', P_cond, REFRIGERANT) # J/kg

    # State 4: Evaporator Inlet / After Expansion Valve (Two-Phase Mixture)
    h4 = h3 # Isenthalpic expansion (constant enthalpy)

    # Calculate performance metrics
    w_comp_spec = h2 - h1 # Specific compressor work (J/kg)
    q_evap_spec = h1 - h4 # Specific evaporator cooling effect (J/kg)
    q_cond_spec = h2 - h3 # Specific condenser heat rejection (J/kg)

    # Calculate COP (Coefficient of Performance for cooling)
    if w_comp_spec > 0:
        COP = q_evap_spec / w_comp_spec
    else:
        print("Warning: Specific compressor work is zero or negative. COP cannot be calculated.")
        COP = float('inf') # Or handle as an error

    print("--- Refrigeration Cycle Analysis (using CoolProp) ---")
    print(f"Refrigerant: {REFRIGERANT}")
    print(f"Evaporation Pressure: {P_evap / 1e5:.3f} bar (at {T_evap_sat_C}°C sat)")
    print(f"Condensation Pressure: {P_cond / 1e5:.3f} bar (at {T_cond_sat_C}°C sat)")
    print(f"State 1 (Comp. Suction): T={T_suc_C}°C, P={P_evap/1e5:.3f} bar, h1={h1/1000:.2f} kJ/kg")
    print(f"State 2 (Comp. Discharge): T={T_dis_C}°C, P={P_cond/1e5:.3f} bar, h2={h2/1000:.2f} kJ/kg")
    print(f"State 3 (Expansion Valve In): T={T_be_C}°C, P={P_cond/1e5:.3f} bar, h3={h3/1000:.2f} kJ/kg")
    print(f"State 4 (Evaporator In): P={P_evap/1e5:.3f} bar, h4={h4/1000:.2f} kJ/kg (T={T_evap_sat_C}°C)")
    print(f"\nSpecific Compressor Work: {w_comp_spec/1000:.2f} kJ/kg")
    print(f"Specific Evaporator Cooling: {q_evap_spec/1000:.2f} kJ/kg")
    print(f"Specific Condenser Heat Rejection: {q_cond_spec/1000:.2f} kJ/kg")
    print(f"COP (Cooling): {COP:.3f}")
    print("----------------------------------------------------\n")

except ImportError:
    print("\n*** Error: CoolProp library not found. Please install it (`pip install coolprop`) ***\n")
    COP = 2.5 # Example default value if CoolProp fails
    print(f"Warning: Using default COP = {COP}\n")
except ValueError as e:
     print(f"\n*** An error occurred during CoolProp calculations: {e} ***")
     print("Please check if the refrigerant state points are valid (e.g., T_dis > T_cond_sat, T_be < T_cond_sat).")
     COP = 2.5 # Example default value
     print(f"Warning: Using default COP = {COP}\n")
except Exception as e:
    print(f"\n*** An unexpected error occurred with CoolProp: {e} ***\n")
    COP = 2.5 # Example default value
    print(f"Warning: Using default COP = {COP}\n")

# --- Simulation Parameters ---
T_ambient = 35.0      # 环境温度 (°C)
sim_duration = 2100     # 模拟时长 (秒)
dt = 1                # 模拟时间步长 (秒)

# --- Speed Profile Parameters (MODIFIED) ---
v_start = 60.0            # 起始速度 km/h
v_end = 120.0             # 结束速度 km/h
ramp_up_time_sec = 5 * 60 # 加速时间 (秒), 5 分钟

# --- Vehicle & Component Parameters ---
m_vehicle = 2503      # 整车质量 (kg)
mass_motor = 60; cp_motor = 500; mc_motor = mass_motor * cp_motor
mass_inverter = 15; cp_inverter = 800; mc_inverter = mass_inverter * cp_inverter
mass_battery = 500; cp_battery = 1000; mc_battery = mass_battery * cp_battery
cabin_volume = 3.5; cp_air = 1005; rho_air_cabin_avg = rho_air_func(28); mc_cabin = cabin_volume * rho_air_cabin_avg * cp_air
cp_coolant = 3400; rho_coolant = 1050; coolant_volume = 10; mass_coolant = coolant_volume * rho_coolant / 1000; mc_coolant = mass_coolant * cp_coolant
UA_motor_coolant = 500; UA_inv_coolant = 300; UA_batt_coolant = 1000
UA_coolant_chiller = 1500; UA_coolant_radiator = 1200; UA_cabin_evap = 2000 # Note: UA_cabin_evap not used in current loop
N_passengers = 2; v_air_in_mps = 0.5; W_out_summer = 0.0133; W_in_target = 0.0100
I_solar_summer = 800; R_body = 0.60; R_glass = 0.009; A_body = 12; A_glass = 4
A_glass_sun = A_glass * 0.4; SHGC = 0.50; fresh_air_fraction = 0.10
T_motor_target = 45.0; T_inv_target = 45.0; T_batt_target_low = 30.0; T_batt_target_high = 35.0
T_cabin_target = 26.0
hysteresis_band = 2.5
T_motor_stop_cool = T_motor_target - hysteresis_band
T_inv_stop_cool = T_inv_target - hysteresis_band
T_batt_stop_cool = T_batt_target_high - hysteresis_band
T_evap_sat = T_evap_sat_C # Use the input saturation temp for the UA calculation
max_cabin_cool_power = 5000; max_chiller_cool_power = 4000
eta_motor = 0.95; eta_inv = 0.985; u_batt = 340; R_int_batt = 0.05
eta_comp_drive = 0.85 # Compressor overall efficiency (electrical to mechanical)

# --- Initial Conditions ---
T_motor_init = T_ambient + 5
T_inv_init = T_ambient + 5
T_batt_init = T_ambient + 2
T_cabin_init = T_ambient + 5 # Start cabin warmer than target
T_coolant_init = T_ambient + 2

# --- Simulation Setup ---
n_steps = int(sim_duration / dt)
time = np.linspace(0, sim_duration, n_steps + 1)
T_motor = np.zeros(n_steps + 1); T_inv = np.zeros(n_steps + 1); T_batt = np.zeros(n_steps + 1)
T_cabin = np.zeros(n_steps + 1); T_coolant = np.zeros(n_steps + 1)
powertrain_chiller_active_log = np.zeros(n_steps + 1)
v_vehicle_profile = np.zeros(n_steps + 1)
Q_gen_motor_profile = np.zeros(n_steps + 1)
Q_gen_inv_profile = np.zeros(n_steps + 1)
Q_gen_batt_profile = np.zeros(n_steps + 1)
P_comp_elec_profile = np.zeros(n_steps + 1) # Log AC Power

# Set initial values
T_motor[0] = T_motor_init; T_inv[0] = T_inv_init; T_batt[0] = T_batt_init
T_cabin[0] = T_cabin_init; T_coolant[0] = T_coolant_init
v_vehicle_profile[0] = v_start # Start at initial speed (MODIFIED)

# --- Simulation Loop ---
powertrain_chiller_on = False # Initialize Chiller state
print("Starting simulation loop...")
for i in range(n_steps):
    current_time_sec = time[i]

    # 1. Calculate current vehicle speed (MODIFIED LOGIC)
    if current_time_sec <= ramp_up_time_sec:
        # Linearly increase speed during the ramp-up period
        # Fraction of ramp completed = current_time_sec / ramp_up_time_sec
        speed_increase = (v_end - v_start) * (current_time_sec / ramp_up_time_sec)
        v_vehicle_current = v_start + speed_increase
    else:
        # Maintain max speed after ramp-up
        v_vehicle_current = v_end

    # Clamp the value just in case (optional, but good practice)
    v_vehicle_current = max(v_start, min(v_end, v_vehicle_current))
    v_vehicle_profile[i] = v_vehicle_current # Log the speed for this step

    # 2. Calculate instantaneous PROPULSION power and heat generation
    P_wheel = P_wheel_func(v_vehicle_current, m_vehicle, T_ambient)
    P_motor_in = P_motor_func(P_wheel, eta_motor)
    P_inv_in = P_motor_in / eta_inv if eta_inv > 0 else 0
    Q_gen_motor = Q_mot_func(P_motor_in, eta_motor)
    Q_gen_inv = Q_inv_func(P_motor_in, eta_inv)
    Q_gen_motor_profile[i] = Q_gen_motor
    Q_gen_inv_profile[i] = Q_gen_inv

    # 3. Calculate Cabin Heat Loads
    Q_cabin_internal = heat_universal_func(N_passengers)
    Q_cabin_conduction_body = heat_body_func(T_ambient, T_cabin[i], v_vehicle_current, v_air_in_mps, A_body, R_body)
    Q_cabin_conduction_glass = heat_glass_func(T_ambient, T_cabin[i], I_solar_summer, v_vehicle_current, v_air_in_mps, A_glass, R_glass, SHGC, A_glass_sun)
    Q_cabin_ventilation = heat_vent_summer_func(N_passengers, T_ambient, T_cabin[i], W_out_summer, W_in_target, fresh_air_fraction)
    Q_cabin_load_total = Q_cabin_internal + Q_cabin_conduction_body + Q_cabin_conduction_glass + Q_cabin_ventilation

    # 4. Cabin Cooling Control
    cabin_temp_error = T_cabin[i] - T_cabin_target
    gain_cabin_cool = 1000
    Q_cabin_cool_demand = gain_cabin_cool * cabin_temp_error if cabin_temp_error > 0 else 0
    Q_cabin_cool_actual = min(Q_cabin_cool_demand, max_cabin_cool_power) if T_cabin[i] > T_cabin_target else 0
    Q_out_cabin = Q_cabin_cool_actual

    # 5. Heat Transfer between Components and Coolant
    Q_motor_to_coolant = UA_motor_coolant * (T_motor[i] - T_coolant[i])
    Q_inv_to_coolant = UA_inv_coolant * (T_inv[i] - T_coolant[i])
    Q_batt_to_coolant = UA_batt_coolant * (T_batt[i] - T_coolant[i])
    Q_coolant_absorb = Q_motor_to_coolant + Q_inv_to_coolant + Q_batt_to_coolant

    # 6. Coolant Cooling Control (Radiator and Chiller)
    Q_radiator_potential = UA_coolant_radiator * (T_coolant[i] - T_ambient)
    Q_coolant_radiator = max(0, Q_radiator_potential)
    start_cooling_powertrain = (T_motor[i] > T_motor_target) or \
                               (T_inv[i] > T_inv_target) or \
                               (T_batt[i] > T_batt_target_high)
    stop_cooling_powertrain = (T_motor[i] < T_motor_stop_cool) and \
                              (T_inv[i] < T_inv_stop_cool) and \
                              (T_batt[i] < T_batt_stop_cool)
    if start_cooling_powertrain:
        powertrain_chiller_on = True
    elif stop_cooling_powertrain:
        powertrain_chiller_on = False
    Q_chiller_potential = UA_coolant_chiller * (T_coolant[i] - T_evap_sat) if T_coolant[i] > T_evap_sat else 0
    Q_coolant_chiller = min(Q_chiller_potential, max_chiller_cool_power) if powertrain_chiller_on else 0
    powertrain_chiller_active_log[i] = 1 if powertrain_chiller_on else 0
    Q_coolant_reject = Q_coolant_chiller + Q_coolant_radiator

    # 7. Calculate AC Compressor Power
    P_comp_elec = 0.0
    # Combine cabin and powertrain cooling demands for AC compressor
    total_cooling_demand_for_AC = Q_out_cabin + Q_coolant_chiller # Note: Simplified - assumes both use the same AC system directly
    # Check if AC is needed for either cabin or powertrain chiller
    if total_cooling_demand_for_AC > 0: # AC needed if cabin cooling is active or powertrain chiller is active
        if COP > 0 and COP != float('inf') and eta_comp_drive > 0:
            # Calculate required *evaporator* cooling power.
            # For cabin: Q_out_cabin IS the evaporator cooling power
            # For chiller: Q_coolant_chiller IS the evaporator cooling power
            # Total evaporator cooling needed:
            Q_evap_total_needed = Q_out_cabin + Q_coolant_chiller # This assumes one AC loop handles both loads

            P_comp_mech = Q_evap_total_needed / COP
            P_comp_elec = P_comp_mech / eta_comp_drive
        else:
            P_comp_elec = 3000 # Fallback power if COP calculation failed or is zero
            # print(f"Warning: Using fallback compressor power {P_comp_elec} W at time {time[i]:.1f}s due to COP/eta issue")
    P_comp_elec_profile[i] = P_comp_elec

    # 8. Update Battery Load & Heat Generation
    P_elec_total = P_inv_in + P_comp_elec # Total electrical load from battery
    Q_gen_batt = Q_batt_func(P_elec_total, u_batt, R_int_batt)
    Q_gen_batt_profile[i] = Q_gen_batt

    # 9. Calculate Temperature Derivatives
    dT_motor_dt = (Q_gen_motor - Q_motor_to_coolant) / mc_motor if mc_motor > 0 else 0
    dT_inv_dt = (Q_gen_inv - Q_inv_to_coolant) / mc_inverter if mc_inverter > 0 else 0
    dT_batt_dt = (Q_gen_batt - Q_batt_to_coolant) / mc_battery if mc_battery > 0 else 0
    dT_cabin_dt = (Q_cabin_load_total - Q_out_cabin) / mc_cabin if mc_cabin > 0 else 0
    dT_coolant_dt = (Q_coolant_absorb - Q_coolant_reject) / mc_coolant if mc_coolant > 0 else 0

    # 10. Update Temperatures using Euler forward method
    T_motor[i+1] = T_motor[i] + dT_motor_dt * dt
    T_inv[i+1] = T_inv[i] + dT_inv_dt * dt
    T_batt[i+1] = T_batt[i] + dT_batt_dt * dt
    T_cabin[i+1] = T_cabin[i] + dT_cabin_dt * dt
    T_coolant[i+1] = T_coolant[i] + dT_coolant_dt * dt

print("Simulation loop finished.")

# Handle last time step data logging for plotting consistency
# Calculate speed for the very last time point
current_time_sec = time[n_steps]
if current_time_sec <= ramp_up_time_sec:
    speed_increase = (v_end - v_start) * (current_time_sec / ramp_up_time_sec)
    v_vehicle_profile[n_steps] = max(v_start, min(v_end, v_start + speed_increase))
else:
    v_vehicle_profile[n_steps] = v_end

powertrain_chiller_active_log[n_steps] = powertrain_chiller_active_log[n_steps-1] # Repeat last state
Q_gen_motor_profile[n_steps] = Q_gen_motor_profile[n_steps-1] # Repeat last value
Q_gen_inv_profile[n_steps] = Q_gen_inv_profile[n_steps-1] # Repeat last value
Q_gen_batt_profile[n_steps] = Q_gen_batt_profile[n_steps-1] # Repeat last value
P_comp_elec_profile[n_steps] = P_comp_elec_profile[n_steps-1] # Repeat last value

# Calculate P_inv_in profile for plotting
P_inv_in_profile = np.zeros(n_steps + 1)
for i in range(n_steps + 1): # Include the last step
    P_wheel_i = P_wheel_func(v_vehicle_profile[i], m_vehicle, T_ambient)
    P_motor_in_i = P_motor_func(P_wheel_i, eta_motor)
    P_inv_in_profile[i] = P_motor_in_i / eta_inv if eta_inv > 0 else 0
P_elec_total_profile = P_inv_in_profile + P_comp_elec_profile


# --- Plotting Results to PNG Files ---
print("Generating plots...")
output_dir = "simulation_plots"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created directory: {output_dir}")

plt_figure_size = (12, 6) # Define a standard figure size
plt_dpi = 300 # Define resolution for saved images

# --- Plot 1: Temperatures ---
plt.figure(figsize=plt_figure_size)
plt.plot(time / 60, T_motor, label='电机温度 (°C)', color='blue')
plt.plot(time / 60, T_inv, label='逆变器温度 (°C)', color='orange')
plt.plot(time / 60, T_batt, label='电池温度 (°C)', color='green')
plt.plot(time / 60, T_cabin, label='座舱温度 (°C)', color='red')
plt.plot(time / 60, T_coolant, label='冷却液温度 (°C)', color='purple', alpha=0.6)
plt.axhline(T_motor_target, color='blue', linestyle='--', alpha=0.7, label=f'电机目标 ({T_motor_target}°C)')
plt.axhline(T_inv_target, color='orange', linestyle='--', alpha=0.7, label=f'逆变器目标 ({T_inv_target}°C)')
plt.axhline(T_batt_target_high, color='green', linestyle='--', alpha=0.7, label=f'电池制冷启动 ({T_batt_target_high}°C)')
plt.axhline(T_batt_stop_cool, color='green', linestyle=':', alpha=0.7, label=f'电池制冷停止 ({T_batt_stop_cool:.1f}°C)')
plt.axhline(T_cabin_target, color='red', linestyle='--', alpha=0.7, label=f'座舱目标 ({T_cabin_target}°C)')
plt.axhline(T_ambient, color='grey', linestyle=':', alpha=0.7, label=f'环境温度 ({T_ambient}°C)')
plt.ylabel('温度 (°C)')
plt.xlabel('时间 (分钟)')
plt.xlim(left=0, right=35)
plt.title(f'车辆估算温度 (线性加速 {v_start}-{v_end}km/h, 含空调, COP={COP:.2f}, 环境={T_ambient}°C)') # Updated Title
plt.legend(loc='best')
plt.grid(True)
plt.tight_layout()
filename1 = os.path.join(output_dir, "plot_temperatures.png")
plt.savefig(filename1, dpi=plt_dpi)
plt.close() # Close the figure to free memory
print(f"Saved: {filename1}")

# --- Plot 2: Chiller State & AC Power ---
fig, ax1 = plt.subplots(figsize=plt_figure_size) # Create figure and primary axis
ax2 = ax1.twinx() # Create twin axis for AC power
ax1.plot(time / 60, powertrain_chiller_active_log, label='动力总成Chiller状态 (1=ON)', color='black', drawstyle='steps-post')
ax2.plot(time / 60, P_comp_elec_profile, label=f'空调压缩机总电耗 (W, $\\eta_{{comp}}={eta_comp_drive}$)', color='cyan', alpha=0.8) # Updated label
ax1.set_xlabel('时间 (分钟)')
ax1.set_ylabel('Chiller 状态 (0/1)')
ax2.set_ylabel('压缩机功率 (W)', color='cyan')
plt.xlim(left=0, right=35)
ax1.set_ylim(-0.1, 1.1)
ax2.set_ylim(bottom=0)
ax2.tick_params(axis='y', labelcolor='cyan')
ax1.grid(True)
# Combine legends from both axes
lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax2.legend(lines + lines2, labels + labels2, loc='best')
plt.title('制冷系统状态和总功耗') # Updated Title
plt.tight_layout()
filename2 = os.path.join(output_dir, "plot_chiller_ac_power.png")
plt.savefig(filename2, dpi=plt_dpi)
plt.close() # Close the figure
print(f"Saved: {filename2}")

# --- Plot 3: Vehicle Speed ---
plt.figure(figsize=plt_figure_size)
plt.plot(time / 60, v_vehicle_profile, label='车速 (km/h)', color='magenta')
plt.ylabel('车速 (km/h)')
plt.xlabel('时间 (分钟)')
plt.xlim(left=0, right=35) # <--- 新增行：设置X轴的起始点为0
plt.ylim(v_start - 5, v_end + 5) # Adjusted Y limits
plt.title(f'车辆速度变化曲线 ({v_start}到{v_end}km/h匀速加速)') # Updated Title
plt.grid(True)
plt.legend(loc='best')
plt.tight_layout()
filename3 = os.path.join(output_dir, "plot_vehicle_speed.png")
plt.savefig(filename3, dpi=plt_dpi)
plt.close() # Close the figure
print(f"Saved: {filename3}")

# --- Plot 4: Powertrain Heat Generation ---
plt.figure(figsize=plt_figure_size)
plt.plot(time / 60, Q_gen_motor_profile, label='电机产热 (W)', color='blue', alpha=0.8)
plt.plot(time / 60, Q_gen_inv_profile, label='逆变器产热 (W)', color='orange', alpha=0.8)
plt.plot(time / 60, Q_gen_batt_profile, label='电池产热 (W, 含空调负载)', color='green', alpha=0.8)
plt.ylabel('产热功率 (W)')
plt.xlabel('时间 (分钟)')
plt.xlim(left=0, right=35)
plt.ylim(bottom=0) # Heat generation should not be negative
plt.title('主要部件产热功率')
plt.grid(True)
plt.legend(loc='best')
plt.tight_layout()
filename4 = os.path.join(output_dir, "plot_heat_generation.png")
plt.savefig(filename4, dpi=plt_dpi)
plt.close() # Close the figure
print(f"Saved: {filename4}")

# --- Plot 5: Battery Power Output Breakdown ---
plt.figure(figsize=plt_figure_size)
plt.plot(time / 60, P_inv_in_profile, label='驱动功率 (逆变器输入 W)', color='brown', alpha=0.7)
plt.plot(time / 60, P_comp_elec_profile, label='空调功率 (W)', color='cyan', alpha=0.7)
plt.plot(time / 60, P_elec_total_profile, label='总电池输出功率 (W)', color='black', linestyle='--')
plt.xlabel('时间 (分钟)')
plt.ylabel('功率 (W)')
plt.xlim(left=0, right=35)
plt.ylim(bottom=0)
plt.title('电池输出功率分解')
plt.grid(True)
plt.legend(loc='best')
plt.tight_layout()
filename5 = os.path.join(output_dir, "plot_battery_power.png")
plt.savefig(filename5, dpi=plt_dpi)
plt.close() # Close the figure
print(f"Saved: {filename5}")


# --- Plot 6: Temperatures vs. Vehicle Speed (ACCELERATION PHASE ONLY) ---
plt.figure(figsize=plt_figure_size)

# 找到加速阶段结束对应的索引
# ramp_up_time_sec 是加速用的总秒数, dt 是时间步长
ramp_up_index = int(ramp_up_time_sec / dt)
# 确保索引不超过数组范围 (虽然理论上不应超过)
ramp_up_index = min(ramp_up_index, n_steps)

# 只绘制加速阶段的数据 (索引 0 到 ramp_up_index)
# 注意：Python切片 [a:b] 包含 a 但不包含 b，所以我们需要 ramp_up_index + 1
v_accel = v_vehicle_profile[0:ramp_up_index + 1]
T_motor_accel = T_motor[0:ramp_up_index + 1]
T_inv_accel = T_inv[0:ramp_up_index + 1]
T_batt_accel = T_batt[0:ramp_up_index + 1]
T_cabin_accel = T_cabin[0:ramp_up_index + 1]
T_coolant_accel = T_coolant[0:ramp_up_index + 1]

# 绘制温度随速度变化的轨迹点 (仅加速段)
plt.plot(v_accel, T_motor_accel, label='电机温度 (°C)', color='blue', marker='.', markersize=1, linestyle='-')
plt.plot(v_accel, T_inv_accel, label='逆变器温度 (°C)', color='orange', marker='.', markersize=1, linestyle='-')
plt.plot(v_accel, T_batt_accel, label='电池温度 (°C)', color='green', marker='.', markersize=1, linestyle='-')
plt.plot(v_accel, T_cabin_accel, label='座舱温度 (°C)', color='red', marker='.', markersize=1, linestyle='-')
plt.plot(v_accel, T_coolant_accel, label='冷却液温度 (°C)', color='purple', marker='.', markersize=1, linestyle='-', alpha=0.6)
plt.xlabel('车速 (km/h)')
plt.ylabel('温度 (°C)')
plt.title(f'部件温度随车速变化轨迹 (仅加速阶段 {v_start} 到 {v_end} km/h)') # 更新标题
plt.legend(loc='best')
plt.grid(True)
# X轴范围从起始速度到结束速度
plt.xlim(left=v_start, right=v_end) # X轴从 v_start 开始, 稍微超过 v_end
# Y轴自动调整

plt.tight_layout()
filename6 = os.path.join(output_dir, "plot_temp_vs_speed_accel.png") # 修改文件名以反映内容
plt.savefig(filename6, dpi=plt_dpi)
plt.close() # Close the figure
print(f"Saved: {filename6}")
# --- Plot 7: Temperatures vs. Time (CONSTANT SPEED PHASE ONLY) ---
plt.figure(figsize=plt_figure_size)

# 匀速阶段开始的索引
const_speed_start_index = ramp_up_index + 1

# 检查是否存在匀速阶段的数据
if const_speed_start_index <= n_steps:
    # 获取匀速阶段的时间和温度数据
    time_const_speed = time[const_speed_start_index:]
    T_motor_const_speed = T_motor[const_speed_start_index:]
    T_inv_const_speed = T_inv[const_speed_start_index:]
    T_batt_const_speed = T_batt[const_speed_start_index:]
    T_cabin_const_speed = T_cabin[const_speed_start_index:]
    T_coolant_const_speed = T_coolant[const_speed_start_index:]

    # 绘制匀速阶段的温度随时间变化
    plt.plot(time_const_speed / 60, T_motor_const_speed, label='电机温度 (°C)', color='blue')
    plt.plot(time_const_speed / 60, T_inv_const_speed, label='逆变器温度 (°C)', color='orange')
    plt.plot(time_const_speed / 60, T_batt_const_speed, label='电池温度 (°C)', color='green')
    plt.plot(time_const_speed / 60, T_cabin_const_speed, label='座舱温度 (°C)', color='red')
    plt.plot(time_const_speed / 60, T_coolant_const_speed, label='冷却液温度 (°C)', color='purple', alpha=0.6)

    # 添加目标温度等参考线 (可选，与 Plot 1 类似)
    plt.axhline(T_motor_target, color='blue', linestyle='--', alpha=0.7, label=f'电机目标 ({T_motor_target}°C)')
    plt.axhline(T_inv_target, color='orange', linestyle='--', alpha=0.7, label=f'逆变器目标 ({T_inv_target}°C)')
    plt.axhline(T_batt_target_high, color='green', linestyle='--', alpha=0.7, label=f'电池制冷启动 ({T_batt_target_high}°C)')
    plt.axhline(T_cabin_target, color='red', linestyle='--', alpha=0.7, label=f'座舱目标 ({T_cabin_target}°C)')
    plt.axhline(T_ambient, color='grey', linestyle=':', alpha=0.7, label=f'环境温度 ({T_ambient}°C)')

    plt.xlabel('时间 (分钟)') # 使用总模拟时间轴
    plt.ylabel('温度 (°C)')
    plt.title(f'部件温度变化 (匀速 {v_end} km/h 阶段)')
    plt.legend(loc='best')
    plt.grid(True)
    # X轴可以限制只显示匀速阶段，或者显示整个模拟时间但数据只在后半段
    plt.xlim(left=ramp_up_time_sec / 60) # X轴从匀速开始的时间点开始

    plt.tight_layout()
    filename7 = os.path.join(output_dir, "plot_temp_at_const_speed.png")
    plt.savefig(filename7, dpi=plt_dpi)
    plt.close() # Close the figure
    print(f"Saved: {filename7}")
else:
    print("Warning: No constant speed phase data found to generate Plot 7.")


# 更新最后的打印语句，表明所有图表已保存
print("All plots saved successfully.")

# 确保 plt.show() 被注释掉或移除
# plt.show() # Remove or comment out plt.show() as we are saving files instead
