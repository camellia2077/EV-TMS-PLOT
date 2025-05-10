# simulation_parameters.py
import configparser
from heat_vehicle import rho_air_func # For cabin air density calculation

# --- 0. Initialize ConfigParser and read the INI file ---
config = configparser.ConfigParser()
config_file_path = 'config.ini' # 确保 config.ini 与此脚本在同一目录或提供正确路径

# 尝试读取配置文件，如果文件不存在或格式错误，则打印错误信息并使用默认值（或引发异常）
try:
    if not config.read(config_file_path, encoding='utf-8'): # 添加 encoding='utf-8' 以支持中文注释
        raise FileNotFoundError(f"Configuration file '{config_file_path}' not found or is empty.")
    print(f"Successfully loaded configuration from '{config_file_path}'")
except FileNotFoundError as e:
    print(f"Error: {e}. Please ensure '{config_file_path}' exists and is readable.")
    # 为了简单起见，如果文件找不到，我们将依赖下面定义的默认值（如果有的话）或导致后续错误
    # exit() # 或者 raise
except configparser.Error as e:
    print(f"Error parsing configuration file '{config_file_path}': {e}")
    # exit() # 或者 raise

# --- Helper function to get config values with type conversion and fallback ---
def get_config_value(section, key, type_func=str, default=None):
    try:
        return type_func(config.get(section, key))
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
        if default is not None:
            print(f"Warning: Config value '{key}' in section '[{section}]' not found or invalid. Using default: {default}. Error: {e}")
            return default
        else:
            print(f"Error: Config value '{key}' in section '[{section}]' not found or invalid, and no default provided. Error: {e}")
            raise # Or handle more gracefully, e.g., by exiting

# --- 1. Read Refrigeration Cycle Inputs ---
T_suc_C_in = get_config_value('RefrigerationCycle', 'T_suc_C_in', float, 15)
T_cond_sat_C_in = get_config_value('RefrigerationCycle', 'T_cond_sat_C_in', float, 45)
T_be_C_in = get_config_value('RefrigerationCycle', 'T_be_C_in', float, 42)
T_evap_sat_C_in = get_config_value('RefrigerationCycle', 'T_evap_sat_C_in', float, 5)
T_dis_C_in = get_config_value('RefrigerationCycle', 'T_dis_C_in', float, 70)
REFRIGERANT_TYPE = get_config_value('RefrigerationCycle', 'REFRIGERANT_TYPE', str, 'R1234yf')

# --- 2. Read Simulation Parameters ---
T_ambient = get_config_value('Simulation', 'T_ambient', float, 35.0)
sim_duration = get_config_value('Simulation', 'sim_duration', int, 2100)
dt = get_config_value('Simulation', 'dt', int, 1)

# --- Read Plotting Parameters --- 
figure_width_inches = get_config_value('Plotting', 'figure_width_inches', float, 18)
figure_height_inches = get_config_value('Plotting', 'figure_height_inches', float, 8)
figure_dpi = get_config_value('Plotting', 'figure_dpi', int, 300)
legend_font_size = get_config_value('Plotting', 'legend_font_size', int, 15)#图示字体大小

# --- 3. Read Speed Profile Parameters ---
v_start = get_config_value('SpeedProfile', 'v_start', float, 60.0)
v_end = get_config_value('SpeedProfile', 'v_end', float, 120.0)
ramp_up_time_sec = get_config_value('SpeedProfile', 'ramp_up_time_sec', int, 300)

# --- 4. Read Vehicle & Component Parameters ---
m_vehicle = get_config_value('Vehicle', 'm_vehicle', float, 2503)
mass_motor = get_config_value('Vehicle', 'mass_motor', float, 60)
cp_motor = get_config_value('Vehicle', 'cp_motor', float, 500)
mc_motor = mass_motor * cp_motor

mass_inverter = get_config_value('Vehicle', 'mass_inverter', float, 15)
cp_inverter = get_config_value('Vehicle', 'cp_inverter', float, 800)
mc_inverter = mass_inverter * cp_inverter

mass_battery = get_config_value('Vehicle', 'mass_battery', float, 500)
cp_battery = get_config_value('Vehicle', 'cp_battery', float, 1000)
mc_battery = mass_battery * cp_battery

cabin_volume = get_config_value('Vehicle', 'cabin_volume', float, 3.5)
cp_air = get_config_value('Vehicle', 'cp_air', float, 1005)
_T_cabin_avg_for_rho = get_config_value('Vehicle', '_T_cabin_avg_for_rho', float, 28)
rho_air_cabin_avg = rho_air_func(_T_cabin_avg_for_rho)
mc_cabin = cabin_volume * rho_air_cabin_avg * cp_air

cp_coolant = get_config_value('Vehicle', 'cp_coolant', float, 3400)
rho_coolant = get_config_value('Vehicle', 'rho_coolant', float, 1050)
coolant_volume_liters = get_config_value('Vehicle', 'coolant_volume_liters', float, 10)
mass_coolant = coolant_volume_liters * rho_coolant / 1000
mc_coolant = mass_coolant * cp_coolant

UA_motor_coolant = get_config_value('Vehicle', 'UA_motor_coolant', float, 500)
UA_inv_coolant = get_config_value('Vehicle', 'UA_inv_coolant', float, 300)
UA_batt_coolant = get_config_value('Vehicle', 'UA_batt_coolant', float, 1000)
UA_coolant_chiller = get_config_value('Vehicle', 'UA_coolant_chiller', float, 1500)
UA_coolant_radiator = get_config_value('Vehicle', 'UA_coolant_radiator', float, 1200)
UA_cabin_evap = get_config_value('Vehicle', 'UA_cabin_evap', float, 2000) # This might relate to max heat exchange at evaporator

N_passengers = get_config_value('Vehicle', 'N_passengers', int, 2)
v_air_in_mps = get_config_value('Vehicle', 'v_air_in_mps', float, 0.5)
W_out_summer = get_config_value('Vehicle', 'W_out_summer', float, 0.0133)
W_in_target = get_config_value('Vehicle', 'W_in_target', float, 0.0100)
I_solar_summer = get_config_value('Vehicle', 'I_solar_summer', float, 800)
R_body = get_config_value('Vehicle', 'R_body', float, 0.60)
R_glass = get_config_value('Vehicle', 'R_glass', float, 0.009)
A_body = get_config_value('Vehicle', 'A_body', float, 12)
A_glass = get_config_value('Vehicle', 'A_glass', float, 4)
A_glass_sun_factor = get_config_value('Vehicle', 'A_glass_sun_factor', float, 0.4)
A_glass_sun = A_glass * A_glass_sun_factor
SHGC = get_config_value('Vehicle', 'SHGC', float, 0.50)
fresh_air_fraction = get_config_value('Vehicle', 'fresh_air_fraction', float, 0.10)

# --- 5. Read Targets and Control Parameters ---
T_motor_target = get_config_value('TargetsAndControl', 'T_motor_target', float, 45.0)
T_inv_target = get_config_value('TargetsAndControl', 'T_inv_target', float, 45.0)
T_batt_target_low = get_config_value('TargetsAndControl', 'T_batt_target_low', float, 30.0)
T_batt_target_high = get_config_value('TargetsAndControl', 'T_batt_target_high', float, 35.0)
T_cabin_target = get_config_value('TargetsAndControl', 'T_cabin_target', float, 26.0) # General target
hysteresis_band = get_config_value('TargetsAndControl', 'hysteresis_band', float, 2.5)
max_chiller_cool_power = get_config_value('TargetsAndControl', 'max_chiller_cool_power', float, 4000)

# --- New Multi-level Cabin Cooling Control Parameters ---
cabin_cooling_power_levels_str = get_config_value('TargetsAndControl', 'cabin_cooling_power_levels', str, '0,4000')
cabin_cooling_power_levels = [float(x.strip()) for x in cabin_cooling_power_levels_str.split(',')]

cabin_cooling_temp_thresholds_str = get_config_value('TargetsAndControl', 'cabin_cooling_temp_thresholds', str, '25.0,100.0')
cabin_cooling_temp_thresholds = [float(x.strip()) for x in cabin_cooling_temp_thresholds_str.split(',')]

# Validation for new cabin cooling parameters
if not cabin_cooling_power_levels:
    raise ValueError("Config error: 'cabin_cooling_power_levels' cannot be empty.")
if len(cabin_cooling_power_levels) != len(cabin_cooling_temp_thresholds):
    raise ValueError("Config error: 'cabin_cooling_power_levels' and 'cabin_cooling_temp_thresholds' must have the same number of entries.")
# Ensure thresholds are sorted (important for the logic in main.py)
for i in range(len(cabin_cooling_temp_thresholds) - 1):
    if cabin_cooling_temp_thresholds[i] >= cabin_cooling_temp_thresholds[i+1]:
        raise ValueError("Config error: 'cabin_cooling_temp_thresholds' must be in strictly increasing order.")
# Ensure power levels are sorted by power (optional, but good practice)
# for i in range(len(cabin_cooling_power_levels) - 1):
#     if cabin_cooling_power_levels[i] > cabin_cooling_power_levels[i+1]:
#         print(f"Warning: 'cabin_cooling_power_levels' are not in strictly increasing order: {cabin_cooling_power_levels}")
#         # Depending on the logic, this might not be an error, but it's unusual for this setup.


# --- 6. Read Efficiency Parameters ---
eta_motor = get_config_value('Efficiency', 'eta_motor', float, 0.95)
eta_inv = get_config_value('Efficiency', 'eta_inv', float, 0.985)
u_batt = get_config_value('Efficiency', 'u_batt', float, 340)
R_int_batt = get_config_value('Efficiency', 'R_int_batt', float, 0.05)
eta_comp_drive = get_config_value('Efficiency', 'eta_comp_drive', float, 0.85)

# --- 7. Read Initial Conditions ---
T_motor_init_offset = get_config_value('InitialConditions', 'T_motor_init_offset', float, 5)
T_inv_init_offset = get_config_value('InitialConditions', 'T_inv_init_offset', float, 5)
T_batt_init_offset = get_config_value('InitialConditions', 'T_batt_init_offset', float, 2)
T_cabin_init_offset = get_config_value('InitialConditions', 'T_cabin_init_offset', float, 0)
T_coolant_init_offset = get_config_value('InitialConditions', 'T_coolant_init_offset', float, 2)

T_motor_init = T_ambient + T_motor_init_offset
T_inv_init = T_ambient + T_inv_init_offset
T_batt_init = T_ambient + T_batt_init_offset
T_cabin_init = T_ambient + T_cabin_init_offset
T_coolant_init = T_ambient + T_coolant_init_offset

if config.has_option('InitialConditions', 'T_cabin_init'):
    T_cabin_init = get_config_value('InitialConditions', 'T_cabin_init', float, T_cabin_init)
    print(f"Info: Using absolute initial cabin temperature from config.ini: {T_cabin_init}°C")


# --- 8. Derived Parameters ---
T_motor_stop_cool = T_motor_target - hysteresis_band
T_inv_stop_cool = T_inv_target - hysteresis_band
T_batt_stop_cool = T_batt_target_high - hysteresis_band # This is likely T_batt_target_low or similar.
                                                      # The original used T_batt_target_high - hysteresis.
                                                      # Let's assume T_batt_target_low for stopping.
T_batt_stop_cool = T_batt_target_low # More logical to stop cooling when reaching the lower target.

T_evap_sat_for_UA_calc = T_evap_sat_C_in

# --- End of Configuration Loading ---
print("All parameters loaded/derived.")
print(f"Plot settings: Size=({figure_width_inches}, {figure_height_inches}), DPI={figure_dpi}") # <--- (可选) 打印确认
print(f"Cabin cooling levels (W): {cabin_cooling_power_levels}")
print(f"Cabin cooling upper temp thresholds (°C): {cabin_cooling_temp_thresholds}")
