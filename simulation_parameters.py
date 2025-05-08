# simulation_parameters.py
from vehicle_physics import rho_air_func # For cabin air density calculation
#输入变量
# --- Refrigeration Cycle Inputs ---
T_suc_C_in = 15
T_cond_sat_C_in = 45
T_be_C_in = 42
T_evap_sat_C_in = 5 # This is a key parameter for chiller performance
T_dis_C_in = 70
REFRIGERANT_TYPE = 'R1234yf'

# --- Simulation Parameters ---
T_ambient = 35.0
sim_duration = 2100
dt = 1

# --- Speed Profile Parameters ---
v_start = 60.0
v_end = 120.0
ramp_up_time_sec = 5 * 60

# --- Vehicle & Component Parameters ---
m_vehicle = 2503
mass_motor = 60; cp_motor = 500; mc_motor = mass_motor * cp_motor
mass_inverter = 15; cp_inverter = 800; mc_inverter = mass_inverter * cp_inverter
mass_battery = 500; cp_battery = 1000; mc_battery = mass_battery * cp_battery

# For mc_cabin, ensure T_cabin_init is defined or use a representative temp for rho_air_func
# If T_cabin_init is used later, you might want to pass it or calculate rho_air_cabin_avg then.
# For now, using a fixed representative temperature for average cabin air density.
_T_cabin_avg_for_rho = 28 # Representative average cabin temp for initial mass calculation
cabin_volume = 3.5; cp_air = 1005; rho_air_cabin_avg = rho_air_func(_T_cabin_avg_for_rho); mc_cabin = cabin_volume * rho_air_cabin_avg * cp_air

cp_coolant = 3400; rho_coolant = 1050; coolant_volume = 10; mass_coolant = coolant_volume * rho_coolant / 1000; mc_coolant = mass_coolant * cp_coolant
UA_motor_coolant = 500; UA_inv_coolant = 300; UA_batt_coolant = 1000
UA_coolant_chiller = 1500; UA_coolant_radiator = 1200; UA_cabin_evap = 2000
N_passengers = 2; v_air_in_mps = 0.5; W_out_summer = 0.0133; W_in_target = 0.0100
I_solar_summer = 800; R_body = 0.60; R_glass = 0.009; A_body = 12; A_glass = 4
A_glass_sun = A_glass * 0.4; SHGC = 0.50; fresh_air_fraction = 0.10

T_motor_target = 45.0; T_inv_target = 45.0; T_batt_target_low = 30.0; T_batt_target_high = 35.0
T_cabin_target = 26.0
hysteresis_band = 2.5

# Derived stop cooling temperatures
T_motor_stop_cool = T_motor_target - hysteresis_band
T_inv_stop_cool = T_inv_target - hysteresis_band
T_batt_stop_cool = T_batt_target_high - hysteresis_band # Stop cooling when below the HIGH target minus hysteresis

T_evap_sat_for_UA_calc = T_evap_sat_C_in # Use the input saturation temp for the UA calculation in main loop

max_cabin_cool_power = 5000
max_chiller_cool_power = 4000

eta_motor = 0.95; eta_inv = 0.985; u_batt = 340; R_int_batt = 0.05
eta_comp_drive = 0.85

# --- Initial Conditions ---
T_motor_init = T_ambient + 5
T_inv_init = T_ambient + 5
T_batt_init = T_ambient + 2
T_cabin_init = T_ambient + 5
T_coolant_init = T_ambient + 2