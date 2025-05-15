import matplotlib.pyplot as plt
# Import all necessary functions from power_sys.py
from power_sys import (
    rho_air_func,
    F_roll_func,
    F_aero_func,
    P_wheel_func,
    P_motor_func,
    Q_mot_func,
    Q_inv_func,  # Import Q_inv_func from power_sys
    Q_batt_func  # Import Q_batt_func from power_sys
)

# --- 参数定义 ---
m = 2503  # 质量 kg

# 选择当前计算使用的环境温度
T_temp = 38.0

# 效率和电阻
η_motor = 0.95  # 电机效率 (假设在常用速度范围内近似恒定)
η_inv = 0.985  # 逆变器效率
u_batt = 340  # 电池电压 (假设恒定) V
R_int = 0.05  # 电池内阻 Ω

# --- 函数定义 (Local helper function, if needed, otherwise remove) ---
# We will use Q_total from here, or you can move it to power_sys.py as well.
def Q_total(mot, inv, batt):
    """计算总产热功率"""
    output = mot + inv + batt
    return output

# --- 计算特定速度下的产热 (可选，用于验证或对比) ---
v_speed_example = 120 # km/h
print(f"--- 单点计算示例 (速度: {v_speed_example} km/h, 温度: {T_temp}℃) ---")
power_wheel_ex = P_wheel_func(v_speed_example, m, T_temp)
power_motor_ex = P_motor_func(power_wheel_ex, η_motor) # This is P_motor_in for Q_mot_func, and P_motor_out for Q_inv_func logic in power_sys.py
                                                      # Let's clarify: P_motor_func returns P_motor_in (input to motor)

# Q_mot_func expects p_motor_in
heat_motor_ex = Q_mot_func(power_motor_ex, η_motor)

# Q_inv_func from power_sys.py expects p_motor_in (which is inverter's output power)
heat_invent_ex = Q_inv_func(power_motor_ex, η_inv)

# Q_batt_func from power_sys.py expects p_elec_total (total electrical power drawn from battery)
# This p_elec_total would be the input to the inverter (P_inv_in)
# P_inv_in = power_motor_ex / η_inv (if power_motor_ex is motor *output* power)
# OR P_inv_in = power_motor_ex (if power_motor_ex is motor *input* power, and also inverter *output* power)

# Based on power_sys.py:
# P_motor_func returns P_motor_in (motor input power)
# Q_inv_func(p_motor_in, eta_inv) -> p_motor_in is inverter output power
# Q_batt_func(p_elec_total, u_batt, r_int)

# Let's assume P_motor_func calculates motor INPUT power.
# So, power_motor_ex is motor INPUT power.
# The input to the inverter (P_inv_in) is also power_motor_ex / η_motor (if motor_eta is drive train before motor)
# Or, if P_motor_func is power *after* motor losses but *before* inverter.
# Let's stick to the definitions in power_sys.py for clarity for Q_inv_func and Q_batt_func

# P_motor_in (as calculated by P_motor_func) is the input power to the motor.
# This is also the output power from the inverter.
P_inverter_output = power_motor_ex

heat_invent_ex = Q_inv_func(P_inverter_output, η_inv) # Correctly uses inverter output power

# To calculate battery heat, we need the total power drawn from the battery.
# Power drawn from battery (P_batt_out) = Inverter Input Power
P_inverter_input = P_inverter_output / η_inv #This is P_elec_total for Q_batt_func
heat_battery_ex = Q_batt_func(P_inverter_input, u_batt, R_int)


heat_total_ex = Q_total(heat_motor_ex, heat_invent_ex, heat_battery_ex)

print(f"Wheel Power: {power_wheel_ex:.2f}W")
print(f"Motor Input Power (Inverter Output Power): {power_motor_ex:.2f}W")
print(f"Inverter Input Power (Battery Output Power): {P_inverter_input:.2f}W")
print(f"Heat Motor: {heat_motor_ex:.2f}W")
print(f"Heat Inverter: {heat_invent_ex:.2f}W")
print(f"Heat Battery: {heat_battery_ex:.2f}W")
print(f"Heat Total: {heat_total_ex:.2f}W")
print("-" * 30)


# --- 计算速度范围内的产热 ---
speeds = list(range(20, 210, 1)) # 速度范围 20 到 210 km/h，步长为 1
total_heat_values = []
motor_heat_values = []
inverter_heat_values = []
battery_heat_values = []

for v in speeds:
    # 1. 计算车轮功率
    p_wheel_current = P_wheel_func(v, m, T_temp)
    # 2. 计算电机输入功率 (this is also inverter output power)
    p_motor_input_current = P_motor_func(p_wheel_current, η_motor)

    # 3. 计算各部分产热
    # Motor heat using Q_mot_func from power_sys.py
    q_mot_current = Q_mot_func(p_motor_input_current, η_motor)

    # Inverter heat using Q_inv_func from power_sys.py
    # p_motor_input_current is the output power of the inverter
    q_inv_current = Q_inv_func(p_motor_input_current, η_inv)

    # Battery heat using Q_batt_func from power_sys.py
    # We need total power drawn from battery = inverter input power
    p_inverter_input_current = p_motor_input_current / η_inv # Power at the input of the inverter
    q_batt_current = Q_batt_func(p_inverter_input_current, u_batt, R_int)

    # 4. 计算总产热
    q_total_current = Q_total(q_mot_current, q_inv_current, q_batt_current)

    # 5. 存储结果
    total_heat_values.append(q_total_current)
    motor_heat_values.append(q_mot_current)
    inverter_heat_values.append(q_inv_current)
    battery_heat_values.append(q_batt_current)

# --- 绘图 ---
plt.figure(figsize=(12, 8)) # 设置图形大小

# 绘制总产热和各部分产热
plt.plot(speeds, total_heat_values, label='总产热功率 (Total Heat)', linewidth=2)
plt.plot(speeds, motor_heat_values, label='电机产热 (Motor Heat)', linestyle='--')
plt.plot(speeds, inverter_heat_values, label='逆变器产热 (Inverter Heat)', linestyle=':')
plt.plot(speeds, battery_heat_values, label='电池产热 (Battery Heat)', linestyle='-.')


# 添加标题和标签
plt.title(f'不同速度下的产热功率 (环境温度: {T_temp}℃)')
plt.xlabel('速度 (km/h)')
plt.ylabel('产热功率 (W)')

# 添加图例
plt.legend()

# 添加网格
plt.grid(True)
# 设置纵坐标(Y轴)的下限为0，让其从0开始
plt.ylim(bottom=0)
plt.xlim(left=25) # Corrected from plt.xlim(left=20) if you want to start axis from 25
# 显示图形
# 在某些环境中（如Jupyter Notebook），需要设置matplotlib以正确显示中文
plt.rcParams['font.sans-serif'] = ['SimSun'] 
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示为方块的问题
plt.show()