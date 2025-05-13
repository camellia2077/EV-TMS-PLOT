# -*- coding: utf-8 -*-
# main.py
import time
import simulation_parameters as sp # Parameters are loaded when this module is imported
import refrigeration_cycle as rc
from simulation_engine import SimulationEngine
from results_analyzer import ResultsAnalyzer
from plotting import SimulationPlotter
import io # 导入 io 模块
import sys # 导入 sys 模块
import os # 导入 os 模块

def save_ini_content(output_dir, ini_filename="config.ini", output_filename="config_used.txt"):
    """
    读取INI文件内容并保存到指定输出目录的TXT文件中。
    """
    config_content = ""
    try:
        with open(ini_filename, 'r', encoding='utf-8') as f_ini:
            config_content = f_ini.read()
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory for ini: {output_dir}")

        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f_out:
            f_out.write(f"--- Content of {ini_filename} ---\n\n")
            f_out.write(config_content)
        print(f"Saved content of {ini_filename} to {output_path}")
    except FileNotFoundError:
        print(f"Error: {ini_filename} not found. Cannot save its content.")
    except Exception as e:
        print(f"Error saving {ini_filename} content: {e}")

def main():
    # --- 准备重定向 print 输出 ---
    old_stdout = sys.stdout  # 保存原始的 stdout
    sys.stdout = captured_output = io.StringIO() # 重定向 stdout 到 StringIO 对象

    start_time = time.time()
    print("\nPProgram started.") # 这条及后续 print 会被捕获

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

    # 从 simulation_parameters 获取步长和持续时间
    dt_value = sp.dt
    sim_duration_value = sp.sim_duration

    # 构建新的输出文件夹名称
    output_folder_name = f"simulation_plots_{dt_value}_{sim_duration_value}"

    # 在这里调用保存INI文件内容的函数
    # 需要先将捕获的输出暂时恢复，打印创建目录的消息，然后再切换回去
    sys.stdout = old_stdout # 恢复原始 stdout
    save_ini_content(output_folder_name, ini_filename=sp.config_file_path) # 假设 sp 中有 config_file_path
    sys.stdout = captured_output # 再次重定向

    plotter = SimulationPlotter(
        time_data=processed_plot_data['time_data'],
        temperatures=processed_plot_data['temperatures'],
        ac_power_log=processed_plot_data['ac_power_log'],
        cabin_cool_power_log=processed_plot_data['cabin_cool_power_log'],
        speed_profile=processed_plot_data['speed_profile'],
        heat_gen_profiles=processed_plot_data['heat_gen_profiles'],
        battery_power_profiles=processed_plot_data['battery_power_profiles'],
        sim_params=processed_plot_data['sim_params_dict'],
        cop_value=cop_value,
        cooling_system_logs=processed_plot_data['cooling_system_logs'],
        output_dir=output_folder_name,
        extrema_text_fontsize=16
    )
    all_temperature_extrema = plotter.generate_all_plots() # generate_all_plots 内部的 print 也会被捕获
    print("Plotting finished.") # 这条也会被捕获

    # --- 5. Print Analysis from Analyzer ---
    # analyzer 内部的 print 也会被捕获
    analyzer.print_temperature_extrema(all_temperature_extrema)
    analyzer.analyze_chiller_transitions()
    analyzer.print_average_values()
    
    end_start_time = time.time()
    time_duration = end_start_time - start_time
    print(f"Total execution time:{time_duration:.2f}s") # 这条也会被捕获
    print("\nProgram finished successfully.") # 这条也会被捕获

    # --- 恢复 stdout 并保存捕获的输出 ---
    sys.stdout = old_stdout # 恢复原始 stdout
    main_log_content = captured_output.getvalue() # 获取所有被捕获的 print 内容

    # 确保输出目录存在 (plotter.generate_all_plots() 应该已经创建了)
    if not os.path.exists(output_folder_name):
        os.makedirs(output_folder_name)
        print(f"Created directory for main log: {output_folder_name}") # 这条会打印到控制台

    log_file_path = os.path.join(output_folder_name, "main_execution_log.txt")
    try:
        with open(log_file_path, 'w', encoding='utf-8') as f_log:
            f_log.write(main_log_content)
        print(f"Main execution log saved to {log_file_path}") # 这条会打印到控制台
    except Exception as e:
        print(f"Error saving main execution log: {e}") # 这条会打印到控制台
    
    # 主日志内容，可以取消下面这行的注释
    print("\n--- Main Execution Log ---")
    print(main_log_content)


if __name__ == "__main__":
    main()
