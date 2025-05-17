# refrigeration_cycle.py
# 导入 CoolProp 库，并将其重命名为 CP，CoolProp 是一个用于计算流体热力学和传递性质的库。
import CoolProp.CoolProp as CP

# 定义一个函数 calculate_refrigeration_cop，用于计算制冷循环的性能系数 (COP)。
# 参数包括：
# T_suc_C: 压缩机吸气口实际温度 (°C)
# T_cond_sat_C: 冷凝器中制冷剂的饱和冷凝温度 (°C)
# T_be_C: 进入膨胀阀之前的温度 (冷凝器出口温度) (°C)
# T_evap_sat_C: 蒸发器中制冷剂的饱和蒸发温度 (°C)
# T_dis_C: 压缩机排气口的实际制冷剂温度 (°C)
# REFRIGERANT: 制冷剂的类型 (例如 'R134a', 'R1234yf')
def calculate_refrigeration_cop(T_suc_C, T_cond_sat_C, T_be_C, T_evap_sat_C, T_dis_C, REFRIGERANT):
    """
    Calculates the Coefficient of Performance (COP) for a refrigeration cycle.
    Returns the COP and a dictionary of state points and performance metrics,
    including calculated superheat and subcooling.
    计算制冷循环的性能系数 (COP)。
    返回 COP 值以及一个包含各状态点和性能指标（包括计算得到的过热度和过冷度）的字典。
    """
    # 初始化 COP 值为 0.0
    cop_value = 0.0
    # 初始化一个空字典，用于存储制冷循环的详细信息
    cycle_details = {}
    # 定义一个字典来存储各项参数的单位
    units = {
        "P_evap_bar": "bar",       # 蒸发压力单位
        "T_evap_sat_C": "°C",      # 蒸发饱和温度单位
        "P_cond_bar": "bar",       # 冷凝压力单位
        "T_cond_sat_C": "°C",      # 冷凝饱和温度单位
        "T_C": "°C",               # 状态点温度单位
        "P_bar": "bar",            # 状态点压力单位
        "h_kJ_kg": "kJ/kg",        # 状态点焓值单位
        "w_comp_spec_kJ_kg": "kJ/kg", # 压缩机比功单位
        "q_evap_spec_kJ_kg": "kJ/kg", # 蒸发器比吸热量单位
        "q_cond_spec_kJ_kg": "kJ/kg", # 冷凝器比放热量单位
        "COP": "",                 # COP 是无量纲的
        "superheat_C": "°C",       # 过热度单位
        "subcooling_C": "°C"       # 过冷度单位
    }

    try:
        # --- 计算过热度和过冷度 ---
        # 过热度 = 压缩机吸气口实际温度 - 蒸发器饱和蒸发温度
        superheat_C = T_suc_C - T_evap_sat_C
        # 过冷度 = 冷凝器饱和冷凝温度 - 冷凝器出口实际温度 (膨胀阀入口温度)
        subcooling_C = T_cond_sat_C - T_be_C

        # --- 现有计算逻辑 ---
        # 将输入的摄氏温度转换为开尔文温度 (K = °C + 273.15)
        T_suc_K = T_suc_C + 273.15       # 压缩机吸气口开尔文温度
        T_cond_sat_K = T_cond_sat_C + 273.15 # 冷凝饱和开尔文温度
        T_be_K = T_be_C + 273.15         # 膨胀阀入口开尔文温度
        T_evap_sat_K = T_evap_sat_C + 273.15 # 蒸发饱和开尔文温度
        T_dis_K = T_dis_C + 273.15       # 压缩机排气口开尔文温度

        # 使用 CoolProp 计算蒸发压力 (P_evap)
        # 'P': 表示要获取的性质是压力
        # 'T': 表示第一个输入性质是温度 (T_evap_sat_K)
        # 'Q': 表示第二个输入性质是干度 (这里 Q=1 表示饱和蒸汽状态)
        # REFRIGERANT: 制冷剂类型
        P_evap = CP.PropsSI('P', 'T', T_evap_sat_K, 'Q', 1, REFRIGERANT)
        # 使用 CoolProp 计算冷凝压力 (P_cond)
        # 这里 Q=0 表示饱和液体状态
        P_cond = CP.PropsSI('P', 'T', T_cond_sat_K, 'Q', 0, REFRIGERANT)

        # 状态点1：压缩机吸入口
        # 计算焓值 h1 和熵值 s1
        h1 = CP.PropsSI('H', 'T', T_suc_K, 'P', P_evap, REFRIGERANT) # 焓值
        s1 = CP.PropsSI('S', 'T', T_suc_K, 'P', P_evap, REFRIGERANT) # 熵值 (虽然计算了但未使用)

        # 检查压缩机排气温度是否高于冷凝饱和温度，这是一个物理约束
        if T_dis_K <= T_cond_sat_K:
            print(f"Warning (CoolProp): Provided T_dis ({T_dis_C}°C) is not above T_cond_sat ({T_cond_sat_C}°C). Check inputs.")
        # 状态点2：压缩机排出口
        # 计算焓值 h2
        h2 = CP.PropsSI('H', 'T', T_dis_K, 'P', P_cond, REFRIGERANT)

        # 检查膨胀阀入口温度是否低于冷凝饱和温度，以确保存在过冷
        if T_be_K >= T_cond_sat_K: # 应该是 T_be_K < T_cond_sat_K 才是过冷
            # 如果膨胀阀前温度高于或等于冷凝饱和温度，则没有过冷或者状态点定义可能有问题
             print(f"Warning (CoolProp): Provided T_be ({T_be_C}°C) is not strictly below T_cond_sat ({T_cond_sat_C}°C). Subcooling will be zero or negative.")
        # 状态点3：膨胀阀入口 (冷凝器出口)
        # 计算焓值 h3
        h3 = CP.PropsSI('H', 'T', T_be_K, 'P', P_cond, REFRIGERANT)
        # 状态点4：膨胀阀出口 (蒸发器入口)
        # 假设膨胀过程为等焓过程
        h4 = h3

        # 计算压缩机比功 (单位质量制冷剂所消耗的功)
        w_comp_spec = h2 - h1
        # 计算蒸发器比吸热量 (单位质量制冷剂在蒸发器吸收的热量)
        q_evap_spec = h1 - h4
        # 计算冷凝器比放热量 (单位质量制冷剂在冷凝器放出的热量)
        q_cond_spec = h2 - h3 # 注意：这里计算的是放热量，所以是 h2-h3 (h2 > h3)

        # 计算性能系数 COP
        if w_comp_spec > 0: # 确保压缩机功大于0，避免除零错误
            cop_value = q_evap_spec / w_comp_spec
        else:
            # 如果压缩机功为零或负值，COP 无法计算或无意义
            print("Warning (CoolProp): Specific compressor work is zero or negative. COP cannot be calculated.")
            cop_value = float('inf') # 理论上COP可以为无穷大，如果压缩机不耗功但仍有制冷效果

        # 将计算结果存储到 cycle_details 字典中
        cycle_details = {
            "refrigerant": REFRIGERANT,                     # 制冷剂类型
            "P_evap_bar": P_evap / 1e5,                     # 蒸发压力 (bar)
            "T_evap_sat_C": T_evap_sat_C,                   # 蒸发饱和温度 (°C)
            "P_cond_bar": P_cond / 1e5,                     # 冷凝压力 (bar)
            "T_cond_sat_C": T_cond_sat_C,                   # 冷凝饱和温度 (°C)
            "state1": {"T_C": T_suc_C, "P_bar": P_evap/1e5, "h_kJ_kg": h1/1000}, # 状态点1参数
            "state2": {"T_C": T_dis_C, "P_bar": P_cond/1e5, "h_kJ_kg": h2/1000}, # 状态点2参数
            "state3": {"T_C": T_be_C, "P_bar": P_cond/1e5, "h_kJ_kg": h3/1000},  # 状态点3参数
            # 状态点4 的温度是饱和温度 T_evap_sat_C
            "state4": {"P_bar": P_evap/1e5, "h_kJ_kg": h4/1000, "T_sat_C": T_evap_sat_C}, # 状态点4参数
            "w_comp_spec_kJ_kg": w_comp_spec/1000,          # 压缩机比功 (kJ/kg)
            "q_evap_spec_kJ_kg": q_evap_spec/1000,          # 蒸发器比吸热量 (kJ/kg)
            "q_cond_spec_kJ_kg": q_cond_spec/1000,          # 冷凝器比放热量 (kJ/kg)
            "COP": cop_value,                               # 性能系数
            "superheat_C": superheat_C,                     # 过热度 (°C)
            "subcooling_C": subcooling_C                    # 过冷度 (°C)
        }
        # 为状态点4的饱和温度添加单位 (如果之前没有)
        units["T_sat_C"] = "°C"

        # 打印制冷循环分析结果的标题
        print("--- Refrigeration Cycle Analysis (using CoolProp) ---")
        # 更新打印逻辑以包含新的单位
        # 遍历 cycle_details 字典中的每个键值对
        for key, value in cycle_details.items():
            unit_str = units.get(key, "") # 获取对应键的单位，如果找不到则为空字符串
            if isinstance(value, dict): # 如果值本身是一个字典 (例如 state1, state2 等)
                 print(f"{key.replace('_', ' ').title()}:") # 打印状态点名称
                 for sub_key, sub_val in value.items(): # 遍历状态点字典中的参数
                     sub_unit_str = units.get(sub_key, "") # 获取参数的单位
                     if isinstance(sub_val, float): # 如果参数值是浮点数，格式化输出
                         print(f"  {sub_key}: {sub_val:.3f} {sub_unit_str}")
                     else: # 否则直接打印
                         print(f"  {sub_key}: {sub_val} {sub_unit_str}")
            else: # 如果值不是字典 (例如 COP, P_evap_bar 等)
                 # 特别处理过热度和过冷度的打印，使其更易读
                 if key == "superheat_C" or key == "subcooling_C":
                    if key == "superheat_C":
                         title = "Superheat (Calculated) 过热度"
                    elif key == "subcooling_C":
                         title = "Subcooling (Calculated) 过冷度"
                    else:
                         # 将下划线替换为空格，并将首字母大写，作为打印的标题
                         title = key.replace('_', ' ').title()
                    print(f"{title}: {value:.2f} {unit_str}") # 格式化打印过热度/过冷度
                 elif isinstance(value, float): # 如果值是浮点数，格式化输出
                     print(f"{key.replace('_', ' ').title()}: {value:.3f} {unit_str}")
                 else: # 否则直接打印
                     print(f"{key.replace('_', ' ').title()}: {value} {unit_str}")
        # 打印分隔线
        print("----------------------------------------------------\n")

    # 捕获 CoolProp 库未安装的错误
    except ImportError:
        print("\n*** Error: CoolProp library not found. Please install it (`pip install coolprop`) ***\n")
        cop_value = 2.5 # 如果 CoolProp 导入失败，使用一个备用的 COP 值
        # 即使CoolProp导入失败，仍然计算并记录过冷过热度
        superheat_C = T_suc_C - T_evap_sat_C
        subcooling_C = T_cond_sat_C - T_be_C
        cycle_details.update({
            "superheat_C": superheat_C,
            "subcooling_C": subcooling_C,
            "COP_status": "Using default due to CoolProp import error" # 记录COP状态
        })
        print(f"Warning: Using default COP = {cop_value}")
        print(f"Calculated Superheat: {superheat_C:.2f} °C")
        print(f"Calculated Subcooling: {subcooling_C:.2f} °C\n")
    # 捕获 CoolProp 计算过程中可能发生的 ValueError (例如无效的状态点)
    except ValueError as e:
        print(f"\n*** An error occurred during CoolProp calculations: {e} ***")
        print("Please check if the refrigerant state points are valid (e.g., T_dis > T_cond_sat, T_be < T_cond_sat).")
        cop_value = 2.5 # 使用备用 COP 值
        superheat_C = T_suc_C - T_evap_sat_C
        subcooling_C = T_cond_sat_C - T_be_C
        cycle_details.update({
            "superheat_C": superheat_C,
            "subcooling_C": subcooling_C,
            "COP_status": "Using default due to CoolProp calculation error" # 记录COP状态
        })
        print(f"Warning: Using default COP = {cop_value}")
        print(f"Calculated Superheat: {superheat_C:.2f} °C")
        print(f"Calculated Subcooling: {subcooling_C:.2f} °C\n")
    # 捕获其他所有与 CoolProp 相关的意外错误
    except Exception as e:
        print(f"\n*** An unexpected error occurred with CoolProp: {e} ***\n")
        cop_value = 2.5 # 使用备用 COP 值
        superheat_C = T_suc_C - T_evap_sat_C
        subcooling_C = T_cond_sat_C - T_be_C
        cycle_details.update({
            "superheat_C": superheat_C,
            "subcooling_C": subcooling_C,
            "COP_status": "Using default due to unexpected CoolProp error" # 记录COP状态
        })
        print(f"Warning: Using default COP = {cop_value}")
        print(f"Calculated Superheat: {superheat_C:.2f} °C")
        print(f"Calculated Subcooling: {subcooling_C:.2f} °C\n")

    # 返回计算得到的 COP 值和包含循环详细信息的字典
    return cop_value, cycle_details
