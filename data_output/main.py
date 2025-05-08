# -*- coding: utf-8 -*-
# main.py
print("Starting---------------------")

# Import standard libraries
import numpy as np

# Import functions from modules
import refrigeration_cycle as rc
import simulation_parameters as sp 
import plotting
import simulation_core

def main():
    """
    主程序入口，协调整个模拟流程。
    """
    print("Executing main function...")

    # --- 1. Calculate Refrigeration COP ---
    # Uses parameters from simulation_parameters.py
    # 注意：cycle_data 在原 main.py 中未被后续使用，如果需要，可以从 rc.calculate_refrigeration_cop 返回并传递
    cop, _ = rc.calculate_refrigeration_cop( # cycle_data 暂时忽略
        sp.T_suc_C_in, sp.T_cond_sat_C_in, sp.T_be_C_in,
        sp.T_evap_sat_C_in, sp.T_dis_C_in, sp.REFRIGERANT_TYPE
    )
    if cop is None or cop == float('inf') or cop <=0: # 添加COP有效性检查
        print(f"Warning: Invalid COP calculated ({cop}). Using a default fallback or exiting might be necessary.")
        # 可以选择在这里设置一个默认COP或退出
        # cop = 2.5 # 示例：设置默认值
        # return # 或者直接退出

    # --- 2. Run Core Simulation ---
    # simulation_core.run_simulation 将处理循环、数据记录和大部分后处理
    (time_sim, temperatures_data, powertrain_chiller_active_log,
     P_comp_elec_profile_hist, v_vehicle_profile_hist, heat_gen_data,
     battery_power_data, sim_params_dict) = simulation_core.run_simulation(cop)

    # --- 3. Plotting Results ---
    # sim_params_dict 已经由 simulation_core 准备好
    # cop 值也已从 refrigeration_cycle 计算得到
    plotting.plot_results(
        time_sim, temperatures_data, powertrain_chiller_active_log, P_comp_elec_profile_hist,
        v_vehicle_profile_hist, heat_gen_data, battery_power_data,
        sim_params_dict, cop # 传递计算得到的 COP
    )

    print("Main script finished.")

if __name__ == "__main__":
    main()
