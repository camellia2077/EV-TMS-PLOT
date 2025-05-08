# simulation_parameters.py
import configparser
from vehicle_physics import rho_air_func # For cabin air density calculation

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the INI file
try:
    # 明确指定编码为 utf-8
    with open('config.ini', 'r', encoding='utf-8') as f:
        config.read_file(f)
    if not config.sections():
        raise FileNotFoundError("config.ini not found or is empty.")
except FileNotFoundError as e:
    print(f"Error: {e}. Please ensure 'config.ini' exists in the same directory and is correctly formatted.")
    # You might want to exit or use default values here if the config file is critical
    # For now, we'll let it raise an error if sections are missing later.
except configparser.Error as e:
    print(f"Error parsing 'config.ini': {e}")
    # Handle parsing errors as needed

# Helper function to get values, converting types as needed
def get_config_value(section, key, type_func=float, default=None):
    try:
        if type_func == bool:
            return config.getboolean(section, key)
        elif type_func == int:
            return config.getint(section, key)
        else: # float or str
            return type_func(config.get(section, key))
    except (configparser.NoSectionError, configparser.NoOptionError):
        if default is not None:
            print(f"Warning: '{key}' not found in section '{section}' of config.ini. Using default value: {default}")
            return default
        else:
            raise KeyError(f"Required key '{key}' not found in section '{section}' of config.ini and no default was provided.")
    except ValueError as e:
        raise ValueError(f"Error converting value for '{key}' in section '{section}': {e}")


# --- Read Refrigeration Cycle Inputs ---
T_suc_C_in = get_config_value('RefrigerationCycle', 'T_suc_C_in')
T_cond_sat_C_in = get_config_value('RefrigerationCycle', 'T_cond_sat_C_in')
T_be_C_in = get_config_value('RefrigerationCycle', 'T_be_C_in')
T_evap_sat_C_in = get_config_value('RefrigerationCycle', 'T_evap_sat_C_in')
T_dis_C_in = get_config_value('RefrigerationCycle', 'T_dis_C_in')
REFRIGERANT_TYPE = get_config_value('RefrigerationCycle', 'REFRIGERANT_TYPE', type_func=str)

# --- Read Simulation Parameters ---
T_ambient = get_config_value('Simulation', 'T_ambient')
sim_duration = get_config_value('Simulation', 'sim_duration', type_func=int)
dt = get_config_value('Simulation', 'dt', type_func=int)

# --- Read Speed Profile Parameters ---
v_start = get_config_value('SpeedProfile', 'v_start')
v_end = get_config_value('SpeedProfile', 'v_end')
ramp_up_time_sec = get_config_value('SpeedProfile', 'ramp_up_time_sec', type_func=int)

# --- Read Vehicle & Component Parameters ---
m_vehicle = get_config_value('Vehicle', 'm_vehicle')
mass_motor = get_config_value('Vehicle', 'mass_motor')
cp_motor = get_config_value('Vehicle', 'cp_motor')
mass_inverter = get_config_value('Vehicle', 'mass_inverter')
cp_inverter = get_config_value('Vehicle', 'cp_inverter')
mass_battery = get_config_value('Vehicle', 'mass_battery')
cp_battery = get_config_value('Vehicle', 'cp_battery')

_T_cabin_avg_for_rho = get_config_value('Vehicle', '_T_cabin_avg_for_rho')
cabin_volume = get_config_value('Vehicle', 'cabin_volume')
cp_air = get_config_value('Vehicle', 'cp_air')

cp_coolant = get_config_value('Vehicle', 'cp_coolant')
rho_coolant = get_config_value('Vehicle', 'rho_coolant')
coolant_volume_liters = get_config_value('Vehicle', 'coolant_volume_liters') # liters

UA_motor_coolant = get_config_value('Vehicle', 'UA_motor_coolant')
UA_inv_coolant = get_config_value('Vehicle', 'UA_inv_coolant')
UA_batt_coolant = get_config_value('Vehicle', 'UA_batt_coolant')
UA_coolant_chiller = get_config_value('Vehicle', 'UA_coolant_chiller')
UA_coolant_radiator = get_config_value('Vehicle', 'UA_coolant_radiator')
UA_cabin_evap = get_config_value('Vehicle', 'UA_cabin_evap')

N_passengers = get_config_value('Vehicle', 'N_passengers', type_func=int)
v_air_in_mps = get_config_value('Vehicle', 'v_air_in_mps')
W_out_summer = get_config_value('Vehicle', 'W_out_summer')
W_in_target = get_config_value('Vehicle', 'W_in_target')
I_solar_summer = get_config_value('Vehicle', 'I_solar_summer')
R_body = get_config_value('Vehicle', 'R_body')
R_glass = get_config_value('Vehicle', 'R_glass')
A_body = get_config_value('Vehicle', 'A_body')
A_glass = get_config_value('Vehicle', 'A_glass')
A_glass_sun_factor = get_config_value('Vehicle', 'A_glass_sun_factor')
SHGC = get_config_value('Vehicle', 'SHGC')
fresh_air_fraction = get_config_value('Vehicle', 'fresh_air_fraction')

# --- Read TargetsAndControl ---
T_motor_target = get_config_value('TargetsAndControl', 'T_motor_target')
T_inv_target = get_config_value('TargetsAndControl', 'T_inv_target')
T_batt_target_low = get_config_value('TargetsAndControl', 'T_batt_target_low')
T_batt_target_high = get_config_value('TargetsAndControl', 'T_batt_target_high')
T_cabin_target = get_config_value('TargetsAndControl', 'T_cabin_target')
hysteresis_band = get_config_value('TargetsAndControl', 'hysteresis_band')
max_cabin_cool_power = get_config_value('TargetsAndControl', 'max_cabin_cool_power')
max_chiller_cool_power = get_config_value('TargetsAndControl', 'max_chiller_cool_power')

# --- Read Efficiency ---
eta_motor = get_config_value('Efficiency', 'eta_motor')
eta_inv = get_config_value('Efficiency', 'eta_inv')
u_batt = get_config_value('Efficiency', 'u_batt')
R_int_batt = get_config_value('Efficiency', 'R_int_batt')
eta_comp_drive = get_config_value('Efficiency', 'eta_comp_drive')

# --- Calculated Parameters (Derived from INI values) ---
mc_motor = mass_motor * cp_motor
mc_inverter = mass_inverter * cp_inverter
mc_battery = mass_battery * cp_battery

rho_air_cabin_avg = rho_air_func(_T_cabin_avg_for_rho)
mc_cabin = cabin_volume * rho_air_cabin_avg * cp_air

mass_coolant_kg = coolant_volume_liters * rho_coolant / 1000 # Convert liters to m^3 then to kg
mc_coolant = mass_coolant_kg * cp_coolant

A_glass_sun = A_glass * A_glass_sun_factor

T_evap_sat_for_UA_calc = T_evap_sat_C_in # Use the input saturation temp for the UA calculation in main loop

# Derived stop cooling temperatures
T_motor_stop_cool = T_motor_target - hysteresis_band
T_inv_stop_cool = T_inv_target - hysteresis_band
T_batt_stop_cool = T_batt_target_high - hysteresis_band # Stop cooling when below the HIGH target minus hysteresis

# --- Read Initial Conditions (Using offsets from T_ambient by default) ---
# Check if absolute initial temperatures are provided, otherwise use offsets
try:
    T_motor_init = get_config_value('InitialConditions', 'T_motor_init')
    T_inv_init = get_config_value('InitialConditions', 'T_inv_init')
    T_batt_init = get_config_value('InitialConditions', 'T_batt_init')
    T_cabin_init = get_config_value('InitialConditions', 'T_cabin_init')
    T_coolant_init = get_config_value('InitialConditions', 'T_coolant_init')
    print("Using absolute initial temperatures from config.ini")
except KeyError: # If absolute values are not found, use offsets
    print("Absolute initial temperatures not found, using offsets from T_ambient.")
    T_motor_init_offset = get_config_value('InitialConditions', 'T_motor_init_offset')
    T_inv_init_offset = get_config_value('InitialConditions', 'T_inv_init_offset')
    T_batt_init_offset = get_config_value('InitialConditions', 'T_batt_init_offset')
    T_cabin_init_offset = get_config_value('InitialConditions', 'T_cabin_init_offset')
    T_coolant_init_offset = get_config_value('InitialConditions', 'T_coolant_init_offset')

    T_motor_init = T_ambient + T_motor_init_offset
    T_inv_init = T_ambient + T_inv_init_offset
    T_batt_init = T_ambient + T_batt_init_offset
    T_cabin_init = T_ambient + T_cabin_init_offset
    T_coolant_init = T_ambient + T_coolant_init_offset

# --- End of parameter definitions ---

# You can add a check here to ensure all necessary parameters are loaded
print("Configuration parameters loaded from config.ini")
# Example: print one value to confirm
# print(f"Ambient Temperature from INI: {T_ambient}°C")