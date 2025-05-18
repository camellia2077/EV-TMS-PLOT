import math # Import math for potential future use, although not strictly needed now

# --- 输入参数 ---
N_p = 2 # 人数
v_kmh = 120 # 车速 (km/h)

v_air_in_mps = 0.5 # 舱内空气平均流速 (m/s) - 假设值 (降低)

# --- 夏季参数 ---
T_out_summer = 26 # 夏车外温度 (°C)
T_in = 26 # 夏季期望的车内温度 (°C)

W_out_summer = 0.0133 # 夏季@30摄氏度50% RH, 室外空气湿度 (kg水蒸气 / kg干空气)
W_in = 0.0100 # 期望的舱内空气湿度@25摄氏度约50% RH (kg水蒸气 / kg干空气)

I_solar_summer = 800 # 夏季晴天太阳辐射强度 (W/m²)

# --- 基础参数和假设 ---

R_body = 0.45         # 车身材料热阻 (m²·K/W) - 调整值, 假设有少量隔热 (U ~ 2.2 W/m²K)
R_glass = 0.004       # 玻璃材料热阻 (m²·K/W) - 基于约4mm玻璃的物理热阻 (导热系数~1 W/mK)

A_body = 12           # 除去玻璃的车体不透明总表面积 (m²) - 调整为更合理的值 (中型车)
A_glass = 4           # 包括天窗的玻璃总面积 (m²) - 调整为更典型的值 (轿车/小SUV)

A_glass_sun = A_glass * 0.6 # 假设60%玻璃受太阳直射#2.4
A_body_sun = A_body * 0.4   # 假设40%不透明面积受太阳直射#4.8

SHGC = 0.65           # 玻璃的太阳辐射热增益系数 - 调整为普通汽车玻璃的典型值
alpha_solar_body = 0.85 # 车身不透明部分太阳辐射吸收率 (-) - 黑色车身假设值 (典型值 0.85-0.95)
                        # 如果是浅色车，可以改为 0.3 - 0.4

fresh_air_fraction = 0.25 # 假设 25% 新风, 75% 再循环 (可调)


def heat_universal(N_passengers):
    """舱内固定热源计算 (W)"""
    q_person = 100      # 每人散热量 (W) - 调整值 (显热+潜热)
    Q_passengers = N_passengers * q_person
    Q_electronics = 100 # 电子设备发热 (W) - 假设值
    Q_powertrain = 100  # 动力总成传入热量 (W) - 假设值 (电动车可能较低, 燃油车可能更高)
    Q_uni = Q_passengers + Q_electronics + Q_powertrain
    return Q_uni


def calculate_h_out(v_vehicle_kmh):
    """根据车速计算车辆外部对流换热系数 h_out (W/m²·K)"""
    v_mps = v_vehicle_kmh / 3.6
    # 常见的经验公式之一
    h_forced = 5.7 + 3.8 * v_mps
    # 也可以考虑其他公式, e.g., h = 8.3 + 2.3 * v_mps
    return h_forced

def calculate_h_in(v_air_internal_mps):
    """根据内部空气流速计算内部对流换热系数 h_in (W/m²·K) - 示例公式"""
    h_natural = 2.5 # 假设的自然对流基值 (W/m²·K)
    h_forced_factor = 5.5 # 强制对流影响因子 (W/m²·K) / (m/s)
    h_in_calc = max(h_natural, h_natural + h_forced_factor * v_air_internal_mps) # 确保不低于自然对流
    # 或者直接使用固定值: h_in_calc = 7.0
    return h_in_calc

def calculate_u_value(h_internal, R_material, h_external):
    """根据内外对流系数和材料热阻计算总传热系数 U (W/m²·K)"""
    if h_internal <= 0 or h_external <= 0:
        return 0 # 避免除零错误
    R_in = 1.0 / h_internal # 计算内表面热阻 (R_in)
    R_out = 1.0 / h_external # 计算外表面热阻 (R_out)
    R_total = R_in + R_material + R_out # 计算总热阻 (R_total)
    if R_total <= 0:
        return float('inf') # 避免除零
    U_value = 1.0 / R_total # 计算总传热系数 (U)
    return U_value

# --- 车身传导热计算 ---
def heat_conduction_body(T_outside, T_inside, v_vehicle_kmh, v_air_internal_mps):
    """通过车身覆盖件传入的传导热负荷功率(W)，仅基于温差"""
    h_outside = calculate_h_out(v_vehicle_kmh)
    h_inside = calculate_h_in(v_air_internal_mps)
    U_body = calculate_u_value(h_inside, R_body, h_outside)
    T_delta = T_outside - T_inside
    Q_body_conduction = U_body * A_body * T_delta
    # 注意：此函数仅计算基于空气温差的传导热。太阳辐射对车身外表面的加热效应需单独考虑
    # (例如通过 Sol-Air 温度，或如下面独立计算的吸收量)。
    return Q_body_conduction



# --- 玻璃传导热计算 (原 heat_glass 的传导部分) ---
def heat_conduction_glass(T_outside, T_inside, v_vehicle_kmh, v_air_internal_mps):
    """通过玻璃传入的传导热负荷功率 (W)"""
    h_outside = calculate_h_out(v_vehicle_kmh)
    h_inside = calculate_h_in(v_air_internal_mps)
    U_glass = calculate_u_value(h_inside, R_glass, h_outside)
    T_delta = T_outside - T_inside
    Q_glass_conduction = U_glass * A_glass * T_delta
    return Q_glass_conduction

# --- 新增: 透过玻璃进入车内的太阳辐射热量 ---
def heat_solar_gain_glass(shgc_glass, area_glass_exposed_to_sun, solar_intensity):
    """计算透过玻璃进入车内的太阳辐射热增益 (W)"""
    Q_glass_solar_gain = shgc_glass * area_glass_exposed_to_sun * solar_intensity
    # SHGC (Solar Heat Gain Coefficient) 直接表示了透过玻璃的太阳能比例
    return Q_glass_solar_gain

def rho_air(t):
    """计算不同温度下标准大气压的空气密度 (kg/m³)"""
    t_k = t + 273.15 # 摄氏度转开尔文
    p = 101325 # 标准大气压 (Pa)
    R_air = 287.05 # 干空气气体常数 (J/(kg·K))
    density = p / (R_air * t_k)
    return density

def heat_vent_summer(N_passengers, T_outside, T_inside, W_outside, W_inside, fraction_fresh_air):
    """夏季通风带来的热负荷 (W)，考虑新风比例"""
    air_density = rho_air(T_outside) # 使用外部空气温度计算密度

    # 新风量标准 (ASHRAE等)，这里用一个简化值
    air_vol_flow_per_person = 0.007 # m³/s per person (约 25 m³/h/person) - 假设值
    # 总 *需求* 通风量 (如果100%新风)
    air_vol_flow_total_demand = air_vol_flow_per_person * N_passengers
    # 实际引入的新风量
    air_vol_flow_fresh = air_vol_flow_total_demand * fraction_fresh_air

    # 质量流量 (仅计算新风部分，因为再循环空气不带来额外的温湿度差负荷)
    m_air_flow_fresh = air_density * air_vol_flow_fresh # kg/s

    # 显热负荷 (Sensible Heat) - 由新风引起
    c_p_air = 1005 # 干空气定压比热容 (J/(kg·K))
    T_delta = T_outside - T_inside
    Q_vent_sensible = m_air_flow_fresh * c_p_air * T_delta

    # 潜热负荷 (Latent Heat) - 由新风引起
    h_fg = 2.45e6 # 水的汽化潜热 @ 25°C (J/kg)
    W_delta = W_outside - W_inside
    # 仅当外部湿度大于内部湿度时才计算潜热负荷（制冷除湿）
    Q_vent_latent = m_air_flow_fresh * h_fg * max(0, W_delta)

    Q_vent_total = Q_vent_sensible + Q_vent_latent
    return Q_vent_total

# --- 主计算过程 (夏季制冷工况) ---
Q_universal_sources = heat_universal(N_p) # 内部固定热源

# 车身热量计算
Q_body_conduction = heat_conduction_body(T_out_summer, T_in, v_kmh, v_air_in_mps) # 车身温差传导热

# 玻璃热量计算
Q_glass_conduction = heat_conduction_glass(T_out_summer, T_in, v_kmh, v_air_in_mps) # 玻璃温差传导热
Q_glass_solar = heat_solar_gain_glass(SHGC, A_glass_sun, I_solar_summer) # 透过玻璃的太阳辐射热增益

# 通风热负荷
Q_ventilation_load = heat_vent_summer(N_p, T_out_summer, T_in, W_out_summer, W_in, fresh_air_fraction) # 新风热负荷

# 总制冷负荷
# 注意： Q_solar_body_absorbed 不直接计入总负荷，因为它代表的是被车身外表面吸收的能量，
# 这部分能量会提高车身外表面温度，从而间接增加 Q_body_conduction，
# 但也会增加车身向外部环境的散热。精确计算需要 Sol-Air 温度。
# 这里我们只加总直接进入车舱的热量和需要通过空调处理的新风负荷。
Q_total_cooling_load = (Q_universal_sources +
                        Q_body_conduction +    # 热量通过车身传导进来
                        Q_glass_conduction +   # 热量通过玻璃传导进来
                        Q_glass_solar +        # 太阳辐射直接透过玻璃进来
                        Q_ventilation_load)    # 处理新风所需的能量

# --- 输出结果 ---
print("--- 夏季制冷热负荷计算结果 (太阳辐射已分离计算) ---")
print(f"车辆速度 (Vehicle Speed): {v_kmh} km/h")
print(f"外部温度 (Outside Temp): {T_out_summer} °C")
print(f"内部目标温度 (Inside Target Temp): {T_in} °C")
print(f"内部空气平均流速假设 (Internal Air Speed Assumption): {v_air_in_mps} m/s")
print(f"太阳辐射强度 (Solar Radiation): {I_solar_summer} W/m²")
print(f"乘客人数 (Occupants): {N_p}")
print(f"车身不透明面积 (Opaque Body Area): {A_body} m² (受光照面积: {A_body_sun} m²)")
print(f"玻璃总面积 (Glass Area): {A_glass} m² (受光照面积: {A_glass_sun} m²)")
print(f"玻璃SHGC (Glass SHGC): {SHGC}")
print(f"车身太阳辐射吸收率 (Body Absorptivity): {alpha_solar_body}")
print(f"新风比例 (Fresh Air Fraction): {fresh_air_fraction*100:.0f}%")

print("-------------------------------------")
print(f"各部分热负荷明细:")
print(f"  内部固定热源 (Q_univ): {Q_universal_sources:.2f} W")
print(f"  车身传导热 (Q_Body_Cond): {Q_body_conduction:.2f} W")
print(f"  玻璃传导热 (Q_Glass_Cond): {Q_glass_conduction:.2f} W")

print(f"  新风热负荷 (Q_Vent): {Q_ventilation_load:.2f} W")
print(f"  透过玻璃的太阳辐射热 (Q_Glass_Solar): {Q_glass_solar:.2f} W")
print("-------------------------------------")

print(f"总制冷负荷 (Q_Total): {Q_total_cooling_load:.2f} W")
