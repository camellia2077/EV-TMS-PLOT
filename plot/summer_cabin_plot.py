import matplotlib.pyplot as plt


# --- 输入参数 ---
N_p = 2 # 人数
v_kmh = 120 # 车速 (km/h)

v_air_in_mps = 0.5 # 舱内空气平均流速 (m/s) - 假设值 (降低)


# --- 计算不同温度下的热负荷 ---
temperatures = list(range(26, 40, 1)) # 温度范围 15°C 到 39°C
q_univ_list = []
q_body_list = []
q_glass_cond_list = [] # 玻璃传导热
q_vent_list = []
q_solar_glass_list = [] # 透过玻璃的太阳辐射
q_total_list = []
# --- 夏季参数 ---
T_in = 26 # 夏季期望的车内温度 (°C)

# 注意：室外湿度 W_out 会随温度变化，这里为了简化，
# 我们仍然使用一个固定值，或者你可以根据需要实现更复杂的湿度模型。
# 如果假设相对湿度恒定（例如 50% RH），则 W_out 会随 T_out 升高而显著增加。
# 这里我们保持原脚本的逻辑，使用一个固定的 W_out 值，但这在物理上不完全准确。
W_out_summer = 0.0133 # 夏季@30摄氏度50% RH, 室外空气湿度 (kg水蒸气 / kg干空气)
W_in = 0.0100 # 期望的舱内空气湿度@25摄氏度约50% RH (kg水蒸气 / kg干空气)

I_solar_summer = 800 # 夏季晴天太阳辐射强度 (W/m²)

# --- 基础参数和假设 ---

R_body = 0.45         # 车身材料热阻 (m²·K/W) - 调整值, 假设有少量隔热 (U ~ 2.2 W/m²K)
R_glass = 0.004       # 玻璃材料热阻 (m²·K/W) - 基于约4mm玻璃的物理热阻 (导热系数~1 W/mK)

A_body = 12           # 除去玻璃的车体不透明总表面积 (m²) - 调整为更合理的值 (中型车)
A_glass = 4           # 包括天窗的玻璃总面积 (m²) - 调整为更典型的值 (轿车/小SUV)

A_glass_sun = A_glass * 0.6 # 假设60%玻璃受太阳直射
A_body_sun = A_body * 0.4   # 假设40%不透明面积受太阳直射

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
    # 如果外部温度低于内部温度，传导热为负（散热），但空调负荷通常关心的是热增益，
    # 所以这里可以取 max(0, ...) 如果只关心制冷负荷
    # Q_body_conduction = U_body * A_body * max(0, T_delta)
    Q_body_conduction = U_body * A_body * T_delta # 保留原始计算，允许负值表示散热
    return Q_body_conduction

# --- 玻璃传导热计算 ---
def heat_conduction_glass(T_outside, T_inside, v_vehicle_kmh, v_air_internal_mps):
    """通过玻璃传入的传导热负荷功率 (W)"""
    h_outside = calculate_h_out(v_vehicle_kmh)
    h_inside = calculate_h_in(v_air_internal_mps)
    U_glass = calculate_u_value(h_inside, R_glass, h_outside)
    T_delta = T_outside - T_inside
    # Q_glass_conduction = U_glass * A_glass * max(0, T_delta) # 只考虑热量传入
    Q_glass_conduction = U_glass * A_glass * T_delta # 允许负值
    return Q_glass_conduction

# --- 透过玻璃进入车内的太阳辐射热量 ---
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
    # Q_vent_sensible = m_air_flow_fresh * c_p_air * max(0, T_delta) # 只考虑加热负荷
    Q_vent_sensible = m_air_flow_fresh * c_p_air * T_delta # 允许制冷

    # 潜热负荷 (Latent Heat) - 由新风引起
    h_fg = 2.45e6 # 水的汽化潜热 @ 25°C (J/kg), e6 = 10^6
    W_delta = W_outside - W_inside
    # 仅当外部湿度大于内部湿度时才计算潜热负荷（制冷除湿）
    # 如果外部湿度低，W_delta < 0, max(0, W_delta) = 0
    Q_vent_latent = m_air_flow_fresh * h_fg * max(0, W_delta)

    Q_vent_total = Q_vent_sensible + Q_vent_latent
    return Q_vent_total



# 计算固定热源 (不随外部温度变化)
Q_universal_sources = heat_universal(N_p)
# 计算透过玻璃的太阳辐射热 (不随外部温度变化，只与太阳强度有关)
# 注意：这里用户标签 Q_solar (亮蓝色) 对应的是透过玻璃的辐射热
Q_glass_solar = heat_solar_gain_glass(SHGC, A_glass_sun, I_solar_summer)

for T_out in temperatures:
    # 固定热源 (每次循环值相同，但为了列表长度一致，仍添加)
    q_univ_list.append(Q_universal_sources)

    # 车身传导热 (Q_body, 品红色)
    Q_body_conduction = heat_conduction_body(T_out, T_in, v_kmh, v_air_in_mps)
    q_body_list.append(Q_body_conduction)

    # 玻璃传导热 (Q_glass, 黄色)
    Q_glass_conduction = heat_conduction_glass(T_out, T_in, v_kmh, v_air_in_mps)
    q_glass_cond_list.append(Q_glass_conduction)

    # 新风热负荷 (Q_vent, 亮绿色)
    # 使用当前循环的 T_out, 但 W_out 仍是固定值 W_out_summer (简化处理)
    Q_ventilation_load = heat_vent_summer(N_p, T_out, T_in, W_out_summer, W_in, fresh_air_fraction)
    q_vent_list.append(Q_ventilation_load)

    # 透过玻璃的太阳辐射热 (Q_solar, 亮蓝色 - 值固定)
    q_solar_glass_list.append(Q_glass_solar)

    # 总负荷计算 (Q_total, 黑色)
    # 注意：这里的总负荷是所有热量 *进入* 车内的总和。
    # 当 T_out < T_in 时，传导项可能为负（表示热量流失）。
    # 如果是计算制冷负荷，通常只考虑正值或热量增益。
    # 但为了完整展示各部分贡献，这里直接求和。
    Q_total_load = (Q_universal_sources +
                    Q_body_conduction +
                    Q_glass_conduction +
                    Q_glass_solar + # 这个始终是正值或零
                    Q_ventilation_load) # 通风负荷已包含显热和潜热（潜热只在W_out > W_in时为正）
    q_total_list.append(Q_total_load)


# --- 绘图 ---
plt.figure(figsize=(12, 7)) # 设置图形大小
size = 20


plt.plot(temperatures, q_univ_list, label='固定热源', color='#17becf', marker='.')
plt.plot(temperatures, q_body_list, label='车身传入热量', color='#e377c2', marker='.')
plt.plot(temperatures, q_glass_cond_list, label='玻璃传入热量', color='#ffdb58', marker='.')
plt.plot(temperatures, q_vent_list, label='新风热负荷', color='#90EE90', marker='.') # 亮绿色
plt.plot(temperatures, q_solar_glass_list, label='吸收太阳辐射热负荷 (透过玻璃)', color='#6495ED', marker='.') # 亮蓝色
plt.plot(temperatures, q_total_list, label='总负荷', color='black', linewidth=2, marker='.') # 黑色，加粗线宽

# 添加图表元素
plt.xlabel('室外温度 $T_{out}$ (°C)', fontsize=size) # <--- 修改X轴标签字体大小 (示例)
plt.ylabel('热负荷 (W)', fontsize=size) # <--- 修改Y轴标签字体大小 (示例)
plt.title(f'不同室外温度下的车辆热负荷分析\n($T_{{in}}$={T_in}°C, $v$={v_kmh}km/h, $I_{{solar}}$={I_solar_summer}W/m²)',fontsize = size)
plt.legend(fontsize = size) # 显示图例
plt.grid(True) # 显示网格
plt.xticks(range(26, 40, 1), fontsize=20) # 设置x轴刻度，每隔2度显示一个
plt.yticks(fontsize=20)



plt.rcParams['font.sans-serif'] = ['SimSun'] # 或者其他你系统上有的中文字体，如 'Microsoft YaHei'
plt.rcParams['axes.unicode_minus'] = False # 解决负号显示问题

plt.tight_layout() # 调整布局防止标签重叠
plt.show() # 显示图形

# 可以在绘图后打印一些特定温度点的数据作为参考
print("\n--- 部分温度点计算结果示例 ---")

idx_30c = temperatures.index(30)
idx_39c = temperatures.index(39)



print(f"\n当 T_out = 30°C:")
print(f"  Q_univ = {q_univ_list[idx_30c]:.2f} W")
print(f"  Q_body = {q_body_list[idx_30c]:.2f} W")
print(f"  Q_glass = {q_glass_cond_list[idx_30c]:.2f} W")
print(f"  Q_vent = {q_vent_list[idx_30c]:.2f} W")
print(f"  Q_solar = {q_solar_glass_list[idx_30c]:.2f} W")
print(f"  Q_total = {q_total_list[idx_30c]:.2f} W")

print(f"\n当 T_out = 39°C:")
print(f"  Q_univ = {q_univ_list[idx_39c]:.2f} W")
print(f"  Q_body = {q_body_list[idx_39c]:.2f} W")
print(f"  Q_glass = {q_glass_cond_list[idx_39c]:.2f} W")
print(f"  Q_vent = {q_vent_list[idx_39c]:.2f} W")
print(f"  Q_solar = {q_solar_glass_list[idx_39c]:.2f} W")
print(f"  Q_total = {q_total_list[idx_39c]:.2f} W")