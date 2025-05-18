# -*- coding: utf-8 -*-
# main.py
import time
import simulation_parameters as sp
import refrigeration_cycle as rc
from simulation_engine import SimulationEngine
from results_analyzer import ResultsAnalyzer
from plotting import SimulationPlotter
import sys
import os

# --- 自定义 Tee 类，用于同时输出到多个流 ---
class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, message):
        for stream in self.streams:
            stream.write(message)
            stream.flush() # 确保立即写入

    def flush(self):
        for stream in self.streams:
            stream.flush()

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
            # 这个 print 也会通过 Tee 输出到控制台和日志文件
            print(f"Created directory for ini: {output_dir}")

        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f_out:
            f_out.write(f"--- Content of {ini_filename} ---\n\n")
            f_out.write(config_content)
        # 这个 print 也会通过 Tee 输出
        print(f"Saved content of {ini_filename} to {output_path}")
    except FileNotFoundError:
        print(f"Error: {ini_filename} not found. Cannot save its content.")
    except Exception as e:
        print(f"Error saving {ini_filename} content: {e}")

def main():
    start_time = time.time()

    # --- 动态确定输出文件夹和日志文件路径 ---
    # 从 simulation_parameters 获取步长和持续时间来构建文件夹名
    # 注意：此时 sp 模块应该已经被导入并已加载参数
    dt_value = sp.dt
    sim_duration_value = sp.sim_duration
    output_folder_name = f"simulation_plots_{dt_value}_{sim_duration_value}"

    # 创建输出文件夹（如果尚不存在）
    if not os.path.exists(output_folder_name):
        # 这个打印发生在 sys.stdout 重定向之前，所以只会到原始控制台
        # 为了统一，我们可以在 Tee 设置后再进行这个打印，或者接受它只在控制台显示一次
        os.makedirs(output_folder_name)
        # print(f"Created output directory: {output_folder_name}") # 可选

    log_file_path = os.path.join(output_folder_name, "main_execution_log.txt")

    # --- 设置 Tee 重定向 ---
    original_stdout = sys.stdout  # 保存原始的 stdout (控制台)
    
    # 以追加模式 ('a') 或写入模式 ('w') 打开日志文件
    # 使用 'w' 会在每次运行时覆盖日志文件
    # 使用 'a' 会在每次运行时追加到日志文件末尾
    try:
        log_file_handle = open(log_file_path, 'w', encoding='utf-8')
    except IOError as e:
        print(f"Error: Could not open log file {log_file_path} for writing: {e}", file=original_stdout)
        print("All output will go to console only.", file=original_stdout)
        log_file_handle = None # 表示无法写入文件

    if log_file_handle:
        # 如果日志文件成功打开，则创建Tee对象，同时输出到控制台和文件
        tee_stream = Tee(original_stdout, log_file_handle)
        sys.stdout = tee_stream # 重定向 stdout 到 Tee 对象
    else:
        # 如果日志文件打开失败，则所有输出仅到原始控制台
        sys.stdout = original_stdout


    # 确保目录创建的消息也被记录（如果之前没有通过Tee打印）
    if not os.path.exists(output_folder_name): # 再次检查以防并发创建
        try:
            os.makedirs(output_folder_name)
        except FileExistsError:
            pass # 目录可能在第一次检查和 makedirs 之间被创建
    print(f"Output directory is: {output_folder_name}")
    print(f"Logging to: {log_file_path if log_file_handle else 'Console Only'}")


    print("\nProgram Started:")

    # --- 0. 打印输入的制冷循环参数 ---
    print("\n--- 初始制冷循环输入参数 ---")
    print(f"压缩机入口过热度 (T_suc_C_in): {sp.T_suc_C_in}°C")
    print(f"冷凝饱和温度 (T_cond_sat_C_in): {sp.T_cond_sat_C_in}°C")
    print(f"冷凝器出口温度 (T_be_C_in): {sp.T_be_C_in}°C")
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
    # 如果希望 SimulationEngine 内部的 print 也通过 Tee，则不需要额外操作
    # 如果 SimulationEngine 内部有自己的 stdout 操作，则需要相应调整
    print("\n--- Simulation ---")
    engine = SimulationEngine(sp, cop_value) # 假设 SimulationEngine 使用当前的 sys.stdout
    raw_simulation_results = engine.run_simulation()
    print("Simulation finished in main.")

    # --- 3. Post-Process and Analyze Results ---
    print("\n--- Results Processing and Analysis ---")
    analyzer = ResultsAnalyzer(raw_simulation_results, sp)
    processed_plot_data = analyzer.post_process_data()
    print("Results processing finished.")
    mid_time = time.time()
    time_dur_mid = mid_time - start_time
    print(f"Mid time:{time_dur_mid:.4f}s")

    # --- 在这里调用保存INI文件内容的函数 ---
    # save_ini_content 现在会使用当前的 sys.stdout (即 Tee 对象)
    save_ini_content(output_folder_name, ini_filename=sp.config_file_path)

    # --- 4. Plotting Results using SimulationPlotter class ---
    # 打印绘图提示信息
    print("\n----------------------------------------------------")
    print("开始绘制图表，请等待...")
    print("----------------------------------------------------")
    # sys.stdout.flush() # Tee 类内部的 write 已经 flush 了

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
    all_temperature_extrema = plotter.generate_all_plots()
    print("Plotting finished.")

    # --- 5. Print Analysis from Analyzer ---
    analyzer.analyze_chiller_transitions()
    analyzer.print_average_values()
    
    end_start_time = time.time()
    time_duration = end_start_time - start_time
    print(f"Total execution time:{time_duration:.2f}s")
    print("\nProgram finished successfully.")

    # --- 恢复原始 stdout 并关闭日志文件 ---
    sys.stdout = original_stdout  # 恢复原始的 stdout
    if log_file_handle:
        log_file_handle.close()
        print(f"\nMain execution log saved to {log_file_path}") # 这条只打印到控制台
    else:
        print("\nLog file was not opened. No log file saved.")


if __name__ == "__main__":
    main()