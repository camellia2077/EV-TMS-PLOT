# heat_transfer.py
# 该模块包含用于计算车辆座舱热负荷的相关函数。
# 主要用于模拟和分析车辆在不同环境和运行条件下的热交换情况。
from vehicle_physics import rho_air_func # 导入用于计算空气密度的函数
# 计算座舱热负荷
def heat_universal_func(N_passengers):
    """
    计算座舱内部的通用热源产生的热量。
    这些热源包括乘客散热、电子设备发热以及动力系统传入座舱的热量。

    参数:
    N_passengers (int): 座舱内的乘客数量。

    返回:
    float: 座舱内部通用热源的总热量 (单位: 瓦特 W)。
    """
    q_person = 100  # 单个乘客的平均散热量 (单位: 瓦特 W/人)
    Q_passengers = N_passengers * q_person  # 乘客总散热量 (单位: 瓦特 W)

    Q_electronics = 100  # 座舱内电子设备的发热量 (单位: 瓦特 W)，这是一个估算值
    Q_powertrain = 50    # 从动力系统传入座舱的热量 (单位: 瓦特 W)，例如通过地板或防火墙传入，这是一个估算值

    # 返回所有通用热源的总和
    return Q_passengers + Q_electronics + Q_powertrain

def calculate_h_out_func(v_vehicle_kmh):
    """
    计算车身外表面的对流换热系数 (h_out)。
    该系数取决于车速，车速越高，对流换热越剧烈。

    参数:
    v_vehicle_kmh (float): 车速 (单位: 千米/小时 km/h)。

    返回:
    float: 车身外表面对流换热系数 (单位: W/(m^2*K))。
    """
    if v_vehicle_kmh < 0: # 输入校验，确保车速不为负值
        v_vehicle_kmh = 0 # 如果车速为负，则按0处理

    # 将车速从 千米/小时 (km/h) 转换为 米/秒 (m/s)
    v_mps = v_vehicle_kmh / 3.6

    # 使用经验公式估算对流换热系数，该公式通常适用于车辆外表面
    # 5.7 是自然对流部分或低速时的基础值，3.8 * v_mps 是强制对流部分
    return 5.7 + 3.8 * v_mps

def calculate_h_in_func(v_air_internal_mps):
    """
    计算座舱内表面的对流换热系数 (h_in)。
    该系数取决于座舱内部空气流动速度，若无强制通风，则主要为自然对流。

    参数:
    v_air_internal_mps (float): 座舱内部空气的平均流速 (单位: 米/秒 m/s)。
                                 通常由空调送风或车内风扇引起。

    返回:
    float: 座舱内表面对流换热系数 (单位: W/(m^2*K))。
    """
    h_natural = 2.5  # 自然对流换热系数的典型值 (单位: W/(m^2*K))，当内部空气几乎静止时采用
    h_forced_factor = 5.5 # 强制对流增强因子，用于根据空气流速增加换热

    # 实际的对流换热系数取自然对流和考虑了强制对流影响的值中的较大者。
    # 即使内部空气流速为0，也至少有自然对流。
    return max(h_natural, h_natural + h_forced_factor * v_air_internal_mps)

def calculate_u_value_func(h_internal, R_material, h_external):
    """
    计算通过某个界面的总传热系数 (U值)。
    U值是衡量材料隔热性能的指标，其倒数为总热阻。

    参数:
    h_internal (float): 内表面对流换热系数 (单位: W/(m^2*K))。
    R_material (float): 材料本身的热阻 (单位: (m^2*K)/W)。
    h_external (float): 外表面对流换热系数 (单位: W/(m^2*K))。

    返回:
    float: 总传热系数 U 值 (单位: W/(m^2*K))。
           如果输入换热系数不合法或总热阻为非正，可能返回 0 或 无穷大。
    """
    # 输入校验，对流换热系数必须为正值
    if h_internal <= 0 or h_external <= 0:
        # 如果内外表面对流换热系数有一个不大于0，则认为无法正常传热或输入有误，返回0。
        # 实际应用中可能需要更复杂的错误处理。
        return 0

    # 计算内表面热阻 (对流热阻)
    R_in = 1.0 / h_internal
    # 计算外表面热阻 (对流热阻)
    R_out = 1.0 / h_external

    # 计算总热阻，包括内外表面对流热阻和材料本身热阻
    R_total = R_in + R_material + R_out

    # 总热阻必须为正值才能计算有效的U值
    if R_total <= 0:
        # 如果总热阻为0或负值（物理上通常不可能，除非输入错误），返回无穷大表示热量无限传递，或作为错误标识。
        return float('inf')

    # 总传热系数 U 值是总热阻的倒数
    return 1.0 / R_total

def heat_body_func(T_outside, T_inside, v_vehicle_kmh, v_air_internal_mps, A_body, R_body):
    """
    计算通过车身 (非玻璃部分) 的传导热量。
    这部分热量是由于车内外温差以及车身材料的导热特性造成的。

    参数:
    T_outside (float): 车外环境温度 (单位: 摄氏度 °C 或 开尔文 K，需保持一致)。
    T_inside (float): 座舱内部温度 (单位: 摄氏度 °C 或 开尔文 K，需保持一致)。
    v_vehicle_kmh (float): 车速 (单位: 千米/小时 km/h)。
    v_air_internal_mps (float): 座舱内部空气流速 (单位: 米/秒 m/s)。
    A_body (float): 车身非玻璃部分的表面积 (单位: 平方米 m^2)。
    R_body (float): 车身非玻璃部分的材料热阻 (单位: (m^2*K)/W)。

    返回:
    float: 通过车身非玻璃部分的传导热量 (单位: 瓦特 W)。
           正值表示热量从外界流入座舱，负值表示热量从座舱流向外界。
    """
    # 计算车身外表面对流换热系数
    h_outside = calculate_h_out_func(v_vehicle_kmh)
    # 计算座舱内表面对流换热系数
    h_inside = calculate_h_in_func(v_air_internal_mps)
    # 计算车身部分的总传热系数 U 值
    U_body = calculate_u_value_func(h_inside, R_body, h_outside)

    # 根据总传热系数、面积和温差计算传导热量
    # Q = U * A * ΔT
    return U_body * A_body * (T_outside - T_inside)

def heat_glass_func(T_outside, T_inside, I_solar, v_vehicle_kmh, v_air_internal_mps, A_glass, R_glass, SHGC, A_glass_sun):
    """
    计算通过玻璃的传导热量和太阳辐射得热。
    玻璃部分的热交换包括温差传导和太阳辐射直接透入两部分。

    参数:
    T_outside (float): 车外环境温度 (单位: 摄氏度 °C 或 开尔文 K)。
    T_inside (float): 座舱内部温度 (单位: 摄氏度 °C 或 开尔文 K)。
    I_solar (float): 太阳辐射强度 (单位: 瓦特/平方米 W/m^2)，指垂直于玻璃表面的辐射。
    v_vehicle_kmh (float): 车速 (单位: 千米/小时 km/h)。
    v_air_internal_mps (float): 座舱内部空气流速 (单位: 米/秒 m/s)。
    A_glass (float): 玻璃总面积 (单位: 平方米 m^2)，用于计算传导热。
    R_glass (float): 玻璃的材料热阻 (单位: (m^2*K)/W)。
    SHGC (float): 太阳辐射得热系数 (Solar Heat Gain Coefficient)，无量纲，表示透过玻璃进入座舱的太阳辐射比例。
    A_glass_sun (float): 受太阳直接照射的玻璃面积 (单位: 平方米 m^2)，用于计算太阳辐射得热。

    返回:
    float: 通过玻璃的总热量 (传导热 + 太阳辐射得热) (单位: 瓦特 W)。
    """
    # 计算玻璃外表面对流换热系数
    h_outside = calculate_h_out_func(v_vehicle_kmh)
    # 计算玻璃内表面对流换热系数
    h_inside = calculate_h_in_func(v_air_internal_mps)
    # 计算玻璃部分的总传热系数 U 值
    U_glass = calculate_u_value_func(h_inside, R_glass, h_outside)

    # 计算通过玻璃的传导热量
    # Q_conduction = U_glass * A_glass * (T_outside - T_inside)
    Q_glass_conduction = U_glass * A_glass * (T_outside - T_inside)

    # 计算通过玻璃的太阳辐射得热
    # Q_solar_gain = SHGC * A_glass_sun * I_solar
    Q_glass_solar_gain = SHGC * A_glass_sun * I_solar

    # 总的玻璃热量是传导热和太阳辐射得热之和
    return Q_glass_conduction + Q_glass_solar_gain

def heat_vent_summer_func(N_passengers, T_outside, T_inside, W_outside, W_inside, fraction_fresh_air):
    """
    计算夏季通风带来的热负荷，包括显热和潜热。
    通风引入的新风会带来温度和湿度的变化，从而产生热负荷。

    参数:
    N_passengers (int): 座舱内的乘客数量。
    T_outside (float): 车外环境温度 (单位: 摄氏度 °C 或 开尔文 K)。
    T_inside (float): 座舱内部目标温度 (单位: 摄氏度 °C 或 开尔文 K)。
    W_outside (float): 车外空气湿度比 (含湿量) (单位: 千克水蒸气/千克干空气 kg_water/kg_dry_air)。
    W_inside (float): 座舱内部目标空气湿度比 (含湿量) (单位: 千克水蒸气/千克干空气 kg_water/kg_dry_air)。
    fraction_fresh_air (float): 新风比例 (0到1之间的数值)，表示通风量中新风所占的比例。

    返回:
    float: 夏季通风带来的总热负荷 (显热 + 潜热) (单位: 瓦特 W)。
    """
    # 使用外部函数计算当前室外温度下的空气密度
    air_density = rho_air_func(T_outside)  # (单位: 千克/立方米 kg/m^3)

    # 根据 ASHRAE 或相关标准，每人所需最小新风量
    air_vol_flow_per_person = 0.007  # (单位: 立方米/秒/人 m^3/(s*person))，这是一个参考值

    # 计算总的空调需求风量 (假设这里指满足乘客需求的最小通风量)
    air_vol_flow_total_demand = air_vol_flow_per_person * N_passengers # (单位: 立方米/秒 m^3/s)

    # 计算实际引入的新风体积流量
    air_vol_flow_fresh = air_vol_flow_total_demand * fraction_fresh_air # (单位: 立方米/秒 m^3/s)

    # 计算引入新风的质量流量
    m_air_flow_fresh = air_density * air_vol_flow_fresh  # (单位: 千克/秒 kg/s)

    # 空气的定压比热容
    c_p_air = 1005  # (单位: 焦耳/(千克*开尔文) J/(kg*K))

    # 计算通风带来的显热负荷 (由于温度差异引起)
    # Q_sensible = m_dot * c_p * (T_out - T_in)
    Q_vent_sensible = m_air_flow_fresh * c_p_air * (T_outside - T_inside) # (单位: 瓦特 W)

    # 水的汽化潜热
    h_fg = 2.45e6  # (单位: 焦耳/千克 J/kg)，在典型环境温度下水的汽化潜热近似值

    # 计算通风带来的潜热负荷 (由于湿度差异引起)
    # Q_latent = m_dot * h_fg * (W_out - W_in)
    # max(0, W_outside - W_inside)确保只在外部湿度高于内部时才计算潜热负荷（夏季制冷除湿工况）
    # 如果是冬季加湿，则 W_inside 可能大于 W_outside，此时潜热为负（即需要加湿）或不在此模型考虑范围。
    Q_vent_latent = m_air_flow_fresh * h_fg * max(0, W_outside - W_inside) # (单位: 瓦特 W)

    # 总的通风热负荷是显热和潜热之和
    return Q_vent_sensible + Q_vent_latent