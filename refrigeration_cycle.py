# refrigeration_cycle.py
import CoolProp.CoolProp as CP

def calculate_refrigeration_cop(T_suc_C, T_cond_sat_C, T_be_C, T_evap_sat_C, T_dis_C, REFRIGERANT):
    """
    Calculates the Coefficient of Performance (COP) for a refrigeration cycle.
    Returns the COP and a dictionary of state points and performance metrics.
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
        "COP": "" # COP 是无量纲的，所以单位为空字符串
    }

    try:
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

        if T_be_K >= T_cond_sat_K:
            print(f"Warning (CoolProp): Provided T_be ({T_be_C}°C) is not below T_cond_sat ({T_cond_sat_C}°C). Check inputs.")
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
            "state4": {"P_bar": P_evap/1e5, "h_kJ_kg": h4/1000, "T_sat_C": T_evap_sat_C}, # 注意这里 T_sat_C 的单位也需要添加
            "w_comp_spec_kJ_kg": w_comp_spec/1000,
            "q_evap_spec_kJ_kg": q_evap_spec/1000,
            "q_cond_spec_kJ_kg": q_cond_spec/1000,
            "COP": cop_value
        }
        # 为了更清晰地添加单位，我们更新一下 units 字典
        units["T_sat_C"] = "°C" # 为 state4 中的 T_sat_C 添加单位

        print("--- Refrigeration Cycle Analysis (using CoolProp) ---")
        for key, value in cycle_details.items():
            unit_str = units.get(key, "") # 获取单位，如果未定义则为空字符串
            if isinstance(value, dict): # Nicer print for states
                 print(f"{key.replace('_', ' ').title()}:")
                 for sub_key, sub_val in value.items():
                     sub_unit_str = units.get(sub_key, "") # 获取子条目的单位
                     if isinstance(sub_val, float):
                         print(f"  {sub_key}: {sub_val:.3f} {sub_unit_str}")
                     else:
                         print(f"  {sub_key}: {sub_val} {sub_unit_str}")
            else:
                 if isinstance(value, float):
                     print(f"{key.replace('_', ' ').title()}: {value:.3f} {unit_str}")
                 else:
                     print(f"{key.replace('_', ' ').title()}: {value} {unit_str}")
        print("----------------------------------------------------\n")


    except ImportError:
        print("\n*** Error: CoolProp library not found. Please install it (`pip install coolprop`) ***\n")
        cop_value = 2.5
        print(f"Warning: Using default COP = {cop_value}\n")
    except ValueError as e:
        print(f"\n*** An error occurred during CoolProp calculations: {e} ***")
        print("Please check if the refrigerant state points are valid (e.g., T_dis > T_cond_sat, T_be < T_cond_sat).")
        cop_value = 2.5
        print(f"Warning: Using default COP = {cop_value}\n")
    except Exception as e:
        print(f"\n*** An unexpected error occurred with CoolProp: {e} ***\n")
        cop_value = 2.5
        print(f"Warning: Using default COP = {cop_value}\n")

    return cop_value, cycle_details
