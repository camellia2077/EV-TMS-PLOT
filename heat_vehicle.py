# heat_vehicle.py
# 该模块包含用于计算车辆基本物理特性相关的函数，
# 此程序默认输入数值合法。
def rho_air_func(t):
    """计算给定温度下的空气密度。
    参数:
    t: 环境温度 (°C)。
    返回:
    空气密度 (kg/m^3)。
    """
    t_k = t + 273.15# 开尔文 = 摄氏度 + 273.15
    p = 101325# 标准大气压 (单位: 帕斯卡 Pa)
    R_air = 287.05# 空气的比气体常数 (单位: 焦耳/(千克·开尔文) J/(kg·K))
    return p / (R_air * t_k)# 根据理想气体状态方程 rho = p / (R * T) 计算空气密度
def F_roll_func(m):
    """计算车辆的滚动阻力。
    参数:
    m =: 车辆总质量 (kg)。
    返回:
    float: 滚动阻力 (N)。
    """
    mu = 0.008# 滚动阻力系数 (无量纲)
    g = 9.8# 重力加速度 (单位: 米/平方秒 m/s^2)
    return mu * m * g# 滚动阻力 F_roll = mu * m * g
def F_aero_func(v_kmh, T_amb):
    """计算车辆的空气阻力。
    参数:
    v_kmh: 车速 (km/h)。
    T_amb : 环境空气温度 (°C)，用于计算空气密度。
    返回:
    float: 空气阻力 (N)。
    """
    rho = rho_air_func(T_amb) # 计算当前环境温度下的空气密度( kg/m^3)
    Cd = 0.22# 空气阻力系数 (无量纲)，取决于车辆外形设计
    a = 3.00# 车辆的迎风面积 (m^2)
    vmps = v_kmh / 3.6# 将车速从 (km/h) 转换为(m/s)
    return 0.5 * rho * Cd * a * (vmps**2)# 空气阻力 F_aero = 0.5 * rho * Cd * A * v^2、
def P_wheel_func(v_kmh, m, T_amb):
    """
    计算车辆在车轮处克服行驶阻力所需的驱动功率。
    参数:
    v_kmh : 车速 (km/h)。
    m : 车辆总质量 (kg)。
    T_amb : 环境空气温度 ( °C)。
    返回:
    float: 车轮处的驱动功率需求 (W)。
    """
    force_roll = F_roll_func(m) #计算滚动阻力( N)
    force_aero = F_aero_func(v_kmh, T_amb)#计算空气阻力 (N)
    force_total = force_aero + force_roll#总行驶阻力 (不考虑坡度阻力及加速阻力)(单位: N)
    v_mps = v_kmh / 3.6# 将车速从 千米/小时 (km/h) 转换为 米/秒 (m/s)
    return force_total * v_mps# 功率(W) P = F * v (力乘以速度)
def P_motor_func(p_wheel, motor_eta):
    """
    计算电机输入功率。
    参数:
    p_wheel (float): 车轮处的驱动功率需求(W)。
    motor_eta (float): 电机的效率。
    返回:
    float: 电机的输入功率(W)。
    """
    return p_wheel / motor_eta
def Q_mot_func(p_motor_in, motor_eta):
    """
    计算电机的产热功率。
    参数:
    p_motor_in (float): 电机的输入功率(W)。
    motor_eta (float): 电机的效率。
    返回:
    float: 电机的产热功率 (W)。
    """
    return p_motor_in * (1 - motor_eta)# 电机产热功率 Q_motor = P_motor_in * (1 - motor_eta)

def Q_inv_func(p_motor_in, eta_inv):
    """
    计算逆变器的产热功率。
    参数:
    p_motor_in: 电机的输入功率 (也是逆变器的输出功率) (单 W)。
    eta_inv   逆变器的效率。
    返回:
    逆变器的产热功率 ( W)。
    """
    return p_motor_in * (1 - eta_inv) / eta_inv
def Q_batt_func(p_motor, u_batt, r_int):
    """
    计算电池的产热功率。
    参数:
    p_elec_total : 车辆总的电功率需求 (近似等于电池输出功率) ( W)。
    u_batt: 电池的端电压 (V)。
    r_int: 电池的等效内阻 (Ω)。
    返回:
    float: 电池的产热功率 (W)。
    """
    I_batt = p_motor / u_batt # 计算电池电流 I_batt = P_elec_total / U_batt(A)
    Q_heat_batt = (I_batt**2) * r_int# 
    return Q_heat_batt

