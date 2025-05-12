# refrigeration_cycle.py
import CoolProp.CoolProp as CP

def calculate_refrigeration_cop(T_suc_C, T_cond_sat_C, T_be_C, T_evap_sat_C, T_dis_C, REFRIGERANT):
    """
    Calculates the Coefficient of Performance (COP) for a refrigeration cycle.
    Returns the COP and a dictionary of state points and performance metrics,
    including calculated superheat and subcooling.
    """
    cop_value = 0.0
    cycle_details = {}
    # 定义一个字典来存储各项参数的单位
    units = {
        "P_evap_bar": "bar",
        "T_evap_sat_C": "°C",
        "P_cond_bar": "bar",
        "T_cond_sat_C": "°C",
        "T_C": "°C", # 用于 state 字典中的温度
        "P_bar": "bar", # 用于 state 字典中的压力
        "h_kJ_kg": "kJ/kg", # 用于 state 字典中的焓值
        "w_comp_spec_kJ_kg": "kJ/kg",
        "q_evap_spec_kJ_kg": "kJ/kg",
        "q_cond_spec_kJ_kg": "kJ/kg",
        "COP": "", # COP 是无量纲的
        "superheat_C": "°C", # 新增：过热度单位
        "subcooling_C": "°C"  # 新增：过冷度单位
    }

    try:
        # --- 计算过热度和过冷度 ---
        superheat_C = T_suc_C - T_evap_sat_C
        subcooling_C = T_cond_sat_C - T_be_C

        # --- 现有计算逻辑 ---
        T_suc_K = T_suc_C + 273.15
        T_cond_sat_K = T_cond_sat_C + 273.15
        T_be_K = T_be_C + 273.15
        T_evap_sat_K = T_evap_sat_C + 273.15
        T_dis_K = T_dis_C + 273.15

        P_evap = CP.PropsSI('P', 'T', T_evap_sat_K, 'Q', 1, REFRIGERANT)
        P_cond = CP.PropsSI('P', 'T', T_cond_sat_K, 'Q', 0, REFRIGERANT)

        h1 = CP.PropsSI('H', 'T', T_suc_K, 'P', P_evap, REFRIGERANT)
        s1 = CP.PropsSI('S', 'T', T_suc_K, 'P', P_evap, REFRIGERANT)

        if T_dis_K <= T_cond_sat_K:
            print(f"Warning (CoolProp): Provided T_dis ({T_dis_C}°C) is not above T_cond_sat ({T_cond_sat_C}°C). Check inputs.")
        h2 = CP.PropsSI('H', 'T', T_dis_K, 'P', P_cond, REFRIGERANT)

        if T_be_K >= T_cond_sat_K: # 应该是 T_be_K < T_cond_sat_K 才是过冷
            # 如果膨胀阀前温度高于或等于冷凝饱和温度，则没有过冷或者状态点定义可能有问题
             print(f"Warning (CoolProp): Provided T_be ({T_be_C}°C) is not strictly below T_cond_sat ({T_cond_sat_C}°C). Subcooling will be zero or negative.")
        h3 = CP.PropsSI('H', 'T', T_be_K, 'P', P_cond, REFRIGERANT)
        h4 = h3

        w_comp_spec = h2 - h1
        q_evap_spec = h1 - h4
        q_cond_spec = h2 - h3

        if w_comp_spec > 0:
            cop_value = q_evap_spec / w_comp_spec
        else:
            print("Warning (CoolProp): Specific compressor work is zero or negative. COP cannot be calculated.")
            cop_value = float('inf')

        cycle_details = {
            "refrigerant": REFRIGERANT,
            "P_evap_bar": P_evap / 1e5, "T_evap_sat_C": T_evap_sat_C,
            "P_cond_bar": P_cond / 1e5, "T_cond_sat_C": T_cond_sat_C,
            "state1": {"T_C": T_suc_C, "P_bar": P_evap/1e5, "h_kJ_kg": h1/1000},
            "state2": {"T_C": T_dis_C, "P_bar": P_cond/1e5, "h_kJ_kg": h2/1000},
            "state3": {"T_C": T_be_C, "P_bar": P_cond/1e5, "h_kJ_kg": h3/1000},
            "state4": {"P_bar": P_evap/1e5, "h_kJ_kg": h4/1000, "T_sat_C": T_evap_sat_C},
            "w_comp_spec_kJ_kg": w_comp_spec/1000,
            "q_evap_spec_kJ_kg": q_evap_spec/1000,
            "q_cond_spec_kJ_kg": q_cond_spec/1000,
            "COP": cop_value,
            "superheat_C": superheat_C,    # 新增：将计算得到的过热度添加到字典
            "subcooling_C": subcooling_C   # 新增：将计算得到的过冷度添加到字典
        }
        units["T_sat_C"] = "°C"

        print("--- Refrigeration Cycle Analysis (using CoolProp) ---")
        # 更新打印逻辑以包含新的单位
        for key, value in cycle_details.items():
            unit_str = units.get(key, "")
            if isinstance(value, dict):
                 print(f"{key.replace('_', ' ').title()}:")
                 for sub_key, sub_val in value.items():
                     sub_unit_str = units.get(sub_key, "")
                     if isinstance(sub_val, float):
                         print(f"  {sub_key}: {sub_val:.3f} {sub_unit_str}")
                     else:
                         print(f"  {sub_key}: {sub_val} {sub_unit_str}")
            else:
                 # 特别处理过热度和过冷度的打印，使其更易读
                 if key == "superheat_C" or key == "subcooling_C":
                    if key == "superheat_C":
                         title = "Superheat (Calculated) 过热度"
                    elif key == "subcooling_C":
                         title = "Subcooling (Calculated) 过冷度"
                    else:
                         title = key.replace('_', ' ').title()
                    print(f"{title}: {value:.2f} {unit_str}")
                 elif isinstance(value, float):
                     print(f"{key.replace('_', ' ').title()}: {value:.3f} {unit_str}")
                 else:
                     print(f"{key.replace('_', ' ').title()}: {value} {unit_str}")
        print("----------------------------------------------------\n")

    except ImportError:
        print("\n*** Error: CoolProp library not found. Please install it (`pip install coolprop`) ***\n")
        cop_value = 2.5 # Fallback COP
        # 即使CoolProp导入失败，仍然计算并记录过冷过热度
        superheat_C = T_suc_C - T_evap_sat_C
        subcooling_C = T_cond_sat_C - T_be_C
        cycle_details.update({
            "superheat_C": superheat_C,
            "subcooling_C": subcooling_C,
            "COP_status": "Using default due to CoolProp import error"
        })
        print(f"Warning: Using default COP = {cop_value}")
        print(f"Calculated Superheat: {superheat_C:.2f} °C")
        print(f"Calculated Subcooling: {subcooling_C:.2f} °C\n")
    except ValueError as e:
        print(f"\n*** An error occurred during CoolProp calculations: {e} ***")
        print("Please check if the refrigerant state points are valid (e.g., T_dis > T_cond_sat, T_be < T_cond_sat).")
        cop_value = 2.5 # Fallback COP
        superheat_C = T_suc_C - T_evap_sat_C
        subcooling_C = T_cond_sat_C - T_be_C
        cycle_details.update({
            "superheat_C": superheat_C,
            "subcooling_C": subcooling_C,
            "COP_status": "Using default due to CoolProp calculation error"
        })
        print(f"Warning: Using default COP = {cop_value}")
        print(f"Calculated Superheat: {superheat_C:.2f} °C")
        print(f"Calculated Subcooling: {subcooling_C:.2f} °C\n")
    except Exception as e:
        print(f"\n*** An unexpected error occurred with CoolProp: {e} ***\n")
        cop_value = 2.5 # Fallback COP
        superheat_C = T_suc_C - T_evap_sat_C
        subcooling_C = T_cond_sat_C - T_be_C
        cycle_details.update({
            "superheat_C": superheat_C,
            "subcooling_C": subcooling_C,
            "COP_status": "Using default due to unexpected CoolProp error"
        })
        print(f"Warning: Using default COP = {cop_value}")
        print(f"Calculated Superheat: {superheat_C:.2f} °C")
        print(f"Calculated Subcooling: {subcooling_C:.2f} °C\n")

    return cop_value, cycle_details
