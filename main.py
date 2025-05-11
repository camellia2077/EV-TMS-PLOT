# -*- coding: utf-8 -*-
# main.py
import time
import simulation_parameters as sp # Parameters are loaded when this module is imported
import refrigeration_cycle as rc
from simulation_engine import SimulationEngine
from results_analyzer import ResultsAnalyzer
import plotting

def main():
    start_time = time.time()
    print("\nPProgram started.")
    # --- 0. 打印输入的制冷循环参数 ---
    print("\n--- 初始制冷循环输入参数 ---")
    print(f"压缩机入口过热度 (T_suc_C_in): {sp.T_suc_C_in}°C")
    print(f"冷凝饱和温度 (T_cond_sat_C_in): {sp.T_cond_sat_C_in}°C")
    print(f"冷凝器出口温度 (T_be_C_in): {sp.T_be_C_in}°C") # T_be_C_in is condenser outlet temp
    print(f"蒸发饱和温度 (T_evap_sat_C_in): {sp.T_evap_sat_C_in}°C")
    print(f"压缩机排气温度 (T_dis_C_in): {sp.T_dis_C_in}°C")
    print(f"制冷剂类型 (REFRIGERANT_TYPE): {sp.REFRIGERANT_TYPE}")
    print("----------------------------------------------------")

    # --- 1. Calculate Refrigeration COP ---
    cop_value, cycle_data = rc.calculate_refrigeration_cop(
        sp.T_suc_C_in, sp.T_cond_sat_C_in, sp.T_be_C_in,
        sp.T_evap_sat_C_in, sp.T_dis_C_in, sp.REFRIGERANT_TYPE
    )
    # cycle_data can be logged or used if needed

    # --- 2. Initialize and Run Simulation ---
    print("\n--- Simulation ---")
    engine = SimulationEngine(sp, cop_value)
    raw_simulation_results = engine.run_simulation()
    print("Simulation finished in main.")

    # --- 3. Post-Process and Analyze Results ---
    print("\n--- Results Processing and Analysis ---")
    analyzer = ResultsAnalyzer(raw_simulation_results, sp)
    processed_plot_data = analyzer.post_process_data()
    print("Results processing finished.")

    # --- 4. Plotting Results ---
    print("\n--- Plotting ---")
    # The plot_results function in plotting.py expects data in a specific format.
    # The processed_plot_data from ResultsAnalyzer should now match this.
    all_temperature_extrema = plotting.plot_results(
        time_data=processed_plot_data['time_data'],
        temperatures=processed_plot_data['temperatures'],
        ac_power_log=processed_plot_data['ac_power_log'],
        cabin_cool_power_log=processed_plot_data['cabin_cool_power_log'],
        speed_profile=processed_plot_data['speed_profile'],
        heat_gen_profiles=processed_plot_data['heat_gen_profiles'],
        battery_power_profiles=processed_plot_data['battery_power_profiles'],
        sim_params=processed_plot_data['sim_params_dict'], # This is the sim_params_dict
        cop_value=cop_value,
        cooling_system_logs=processed_plot_data['cooling_system_logs']
    )
    print("Plotting finished.")

    # --- 5. Print Analysis from Analyzer ---
    analyzer.print_temperature_extrema(all_temperature_extrema)
    analyzer.analyze_chiller_transitions()
    end_start_time = time.time()
    time_duration = start_time - end_start_time
    print(f"Total execution time:{time_duration}")
    print("\nProgram finished successfully.")

if __name__ == "__main__":
    main()
