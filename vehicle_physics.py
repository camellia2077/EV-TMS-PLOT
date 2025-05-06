# vehicle_physics.py
#动力系统产热
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
    if vmps < 0: vmps = 0
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
    if p_wheel <= 0: return 0
    return p_wheel / eta_m if eta_m > 0 else float('inf')

def Q_mot_func(p_motor_in, eta_m):
    """计算电机产热功率"""
    if p_motor_in <= 0: return 0
    return p_motor_in * (1 - eta_m)

def Q_inv_func(p_motor_in, eta_inv):
    """计算逆变器产热功率"""
    if p_motor_in <= 0: return 0
    p_inv_in = p_motor_in / eta_inv if eta_inv > 0 else float('inf')
    return p_inv_in * (1 - eta_inv) if eta_inv > 0 else 0

def Q_batt_func(p_elec_total, u_batt, r_int):
    """计算电池产热功率 (基于总电流和内阻)"""
    if p_elec_total <= 0: return 0
    I_batt = p_elec_total / u_batt if u_batt > 0 else 0
    return (I_batt**2) * r_int