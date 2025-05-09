# heat_transfer.py
from heat_vehicle import rho_air_func # Import necessary function
#计算座舱热负荷
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
    if R_total <= 0: return float('inf')
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
    air_density = rho_air_func(T_outside)
    air_vol_flow_per_person = 0.007
    air_vol_flow_total_demand = air_vol_flow_per_person * N_passengers
    air_vol_flow_fresh = air_vol_flow_total_demand * fraction_fresh_air
    m_air_flow_fresh = air_density * air_vol_flow_fresh
    c_p_air = 1005
    Q_vent_sensible = m_air_flow_fresh * c_p_air * (T_outside - T_inside)
    h_fg = 2.45e6
    Q_vent_latent = m_air_flow_fresh * h_fg * max(0, W_outside - W_inside)
    return Q_vent_sensible + Q_vent_latent