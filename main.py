# -*- coding: utf-8 -*-
# main.py
import time
import simulation_parameters as sp # Parameters are loaded when this module is imported
import refrigeration_cycle as rc
from simulation_engine import SimulationEngine
from results_analyzer import ResultsAnalyzer
from plotting import SimulationPlotter 

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

    # --- 2. Initialize and Run Simulation ---
    print("\n--- Simulation ---")
    engine = SimulationEngine(sp, cop_value)
    raw_simulation_results = engine.run_simulation()
    print("Simulation finished in main.")

    # --- 3. Post-Process and Analyze Results ---
    print("\n--- Results Processing and Analysis ---")
    analyzer = ResultsAnalyzer(raw_simulation_results, sp)
    processed_plot_data = analyzer.post_process_data() # This now returns a dictionary
    print("Results processing finished.")
    mid_time = time.time()
    time_dur_mid = mid_time - start_time
    print(f"Mid time:{time_dur_mid:.4f}s")

    # --- 4. Plotting Results using SimulationPlotter class ---
    print("\n--- Plotting ---")
    plotter = SimulationPlotter(
        time_data=processed_plot_data['time_data'],
        temperatures=processed_plot_data['temperatures'],
        ac_power_log=processed_plot_data['ac_power_log'],
        cabin_cool_power_log=processed_plot_data['cabin_cool_power_log'], # This is Q_cabin_evap_log
        speed_profile=processed_plot_data['speed_profile'],
        heat_gen_profiles=processed_plot_data['heat_gen_profiles'],
        battery_power_profiles=processed_plot_data['battery_power_profiles'],
        sim_params=processed_plot_data['sim_params_dict'], # Pass the dictionary
        cop_value=cop_value,
        cooling_system_logs=processed_plot_data['cooling_system_logs'],
        output_dir="simulation_plots_oop",  # Optional: specify different output directory
        extrema_text_fontsize=16            # Optional: specify font size for extrema
    )
    all_temperature_extrema = plotter.generate_all_plots()
    print("Plotting finished.")

    # --- 5. Print Analysis from Analyzer ---
    analyzer.print_temperature_extrema(all_temperature_extrema)
    analyzer.analyze_chiller_transitions()
    analyzer.print_average_values()
    
    end_start_time = time.time()
    time_duration = end_start_time - start_time
    print(f"Total execution time:{time_duration:.2f}s")
    print("\nProgram finished successfully.")

if __name__ == "__main__":
    main()