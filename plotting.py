# plotting.py
import matplotlib.pyplot as plt
import matplotlib as mpl
import os
import numpy as np
#画图
# 设置 matplotlib 支持中文显示
mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False

def ensure_profile_length(profile, target_length):
    """Ensures a data profile has the target length by repeating the last value if necessary."""
    current_length = len(profile)
    if current_length < target_length:
        last_value = profile[-1] if current_length > 0 else 0
        extension = np.full(target_length - current_length, last_value)
        return np.concatenate((profile, extension))
    return profile[:target_length]

def plot_results(time_data, temperatures, chiller_log, ac_power_log, cabin_cool_power_log,
                 speed_profile, heat_gen_profiles, battery_power_profiles,
                 sim_params, cop_value, output_dir="simulation_plots"):
    """
    Generates and saves all simulation plots.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    plt_figure_size = (18, 8)
    plt_dpi = 600
    time_minutes = time_data / 60
    n_total_points = len(time_data)

    T_motor = ensure_profile_length(temperatures['motor'], n_total_points)
    T_inv = ensure_profile_length(temperatures['inv'], n_total_points)
    T_batt = ensure_profile_length(temperatures['batt'], n_total_points)
    T_cabin = ensure_profile_length(temperatures['cabin'], n_total_points)
    T_coolant = ensure_profile_length(temperatures['coolant'], n_total_points)

    chiller_active_log = ensure_profile_length(chiller_log, n_total_points)
    P_comp_elec_profile = ensure_profile_length(ac_power_log, n_total_points)
    Q_cabin_cool_profile = ensure_profile_length(cabin_cool_power_log, n_total_points)
    v_vehicle_profile = ensure_profile_length(speed_profile, n_total_points)
    
    Q_gen_motor_profile = ensure_profile_length(heat_gen_profiles['motor'], n_total_points)
    Q_gen_inv_profile = ensure_profile_length(heat_gen_profiles['inv'], n_total_points)
    Q_gen_batt_profile = ensure_profile_length(heat_gen_profiles['batt'], n_total_points)

    P_inv_in_profile = ensure_profile_length(battery_power_profiles['inv_in'], n_total_points)
    P_elec_total_profile = ensure_profile_length(battery_power_profiles['total_elec'], n_total_points)


    # --- Plot 1: Temperatures ---
    plt.figure(figsize=plt_figure_size)
    plt.plot(time_minutes, T_motor, label='电机温度 (°C)', color='blue')
    plt.plot(time_minutes, T_inv, label='逆变器温度 (°C)', color='orange')
    plt.plot(time_minutes, T_batt, label='电池温度 (°C)', color='green')
    plt.plot(time_minutes, T_cabin, label='座舱温度 (°C)', color='red')
    plt.plot(time_minutes, T_coolant, label='冷却液温度 (°C)', color='purple', alpha=0.6)
    plt.axhline(sim_params['T_motor_target'], color='blue', linestyle='--', alpha=0.7, label=f'电机目标 ({sim_params["T_motor_target"]}°C)')
    plt.axhline(sim_params['T_inv_target'], color='orange', linestyle='--', alpha=0.7, label=f'逆变器目标 ({sim_params["T_inv_target"]}°C)')
    plt.axhline(sim_params['T_batt_target_high'], color='green', linestyle='--', alpha=0.7, label=f'电池制冷启动 ({sim_params["T_batt_target_high"]}°C)')
    if 'T_batt_stop_cool' in sim_params: # Check if T_batt_stop_cool is available
        plt.axhline(sim_params['T_batt_stop_cool'], color='green', linestyle=':', alpha=0.7, label=f'电池制冷停止 ({sim_params["T_batt_stop_cool"]:.1f}°C)')
    plt.axhline(sim_params['T_cabin_target'], color='red', linestyle='--', alpha=0.7, label=f'座舱目标 ({sim_params["T_cabin_target"]}°C)')
    
    # Remove or adapt plotting of old cabin control thresholds
    # if 'T_cabin_cool_off_threshold' in sim_params:
    #     plt.axhline(sim_params['T_cabin_cool_off_threshold'], color='red', linestyle=':', alpha=0.5, label=f'座舱低温点 ({sim_params["T_cabin_cool_off_threshold"]:.1f}°C)')
    # if 'T_cabin_cool_on_threshold' in sim_params:
    #     plt.axhline(sim_params['T_cabin_cool_on_threshold'], color='red', linestyle='-.', alpha=0.5, label=f'座舱高温点 ({sim_params["T_cabin_cool_on_threshold"]:.1f}°C)')

    # Optionally, plot the new cabin temperature thresholds if desired (can be many)
    if 'cabin_cooling_temp_thresholds' in sim_params and 'cabin_cooling_power_levels' in sim_params:
        thresholds = sim_params['cabin_cooling_temp_thresholds']
        levels = sim_params['cabin_cooling_power_levels']
        for idx, temp_thresh in enumerate(thresholds):
            if levels[idx] > 0 and temp_thresh < 99 : # Don't plot for 0W or the "infinity" threshold
                 label_text = f'座舱P={levels[idx]}W上限@{temp_thresh}°C'
                 # Check if previous power level was 0 to indicate a "turn-on" type threshold
                 if idx > 0 and levels[idx-1] == 0:
                     label_text = f'座舱启动P={levels[idx]}W@{thresholds[idx-1]}-{temp_thresh}°C'
                 elif idx == 0 and levels[idx] == 0 and len(thresholds) > 1: # First threshold is for OFF
                     label_text = f'座舱OFF至{temp_thresh}°C'

                 plt.axhline(temp_thresh, color='salmon', linestyle=':', alpha=0.4, label=label_text if idx < 2 else None) # Only label first few to avoid clutter

    plt.axhline(sim_params['T_ambient'], color='grey', linestyle=':', alpha=0.7, label=f'环境温度 ({sim_params["T_ambient"]}°C)')
    plt.ylabel('温度 (°C)')
    plt.xlabel('时间 (分钟)')
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    plt.title(f'车辆估算温度 (线性加速 {sim_params["v_start"]}-{sim_params["v_end"]}km/h, 含空调, COP={cop_value:.2f}, 环境={sim_params["T_ambient"]}°C)')
    plt.legend(loc='best', fontsize='small')
    plt.grid(True)
    plt.tight_layout()
    filename1 = os.path.join(output_dir, "plot_temperatures.png")
    plt.savefig(filename1, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename1}")

    # --- Plot 2: Chiller State & AC Power ---
    fig, ax1 = plt.subplots(figsize=plt_figure_size)
    ax2 = ax1.twinx()
    ax1.plot(time_minutes, chiller_active_log, label='动力总成Chiller状态 (1=ON)', color='black', drawstyle='steps-post')
    ax2.plot(time_minutes, P_comp_elec_profile, label=f'空调压缩机总电耗 (W, $\\eta_{{comp}}={sim_params["eta_comp_drive"]}$)', color='cyan', alpha=0.8)
    ax1.set_xlabel('时间 (分钟)')
    ax1.set_ylabel('Chiller 状态 (0/1)')
    ax2.set_ylabel('压缩机功率 (W)', color='cyan')
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    ax1.set_ylim(-0.1, 1.1)
    ax2.set_ylim(bottom=0)
    ax2.tick_params(axis='y', labelcolor='cyan')
    ax1.grid(True)
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='best')
    plt.title('制冷系统状态和总功耗')
    plt.tight_layout()
    filename2 = os.path.join(output_dir, "plot_chiller_ac_power.png")
    plt.savefig(filename2, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename2}")

    # --- Plot 3: Vehicle Speed ---
    plt.figure(figsize=plt_figure_size)
    plt.plot(time_minutes, v_vehicle_profile, label='车速 (km/h)', color='magenta')
    plt.ylabel('车速 (km/h)')
    plt.xlabel('时间 (分钟)')
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    v_min_plot = min(sim_params['v_start'], sim_params['v_end']) - 5 if sim_params['v_start'] != sim_params['v_end'] else sim_params['v_start'] - 5
    v_max_plot = max(sim_params['v_start'], sim_params['v_end']) + 5 if sim_params['v_start'] != sim_params['v_end'] else sim_params['v_start'] + 5
    plt.ylim(max(0, v_min_plot), v_max_plot) # Ensure y starts at 0 or just below min speed
    plt.title(f'车辆速度变化曲线 ({sim_params["v_start"]}到{sim_params["v_end"]}km/h)')
    plt.grid(True)
    plt.legend(loc='best')
    plt.tight_layout()
    filename3 = os.path.join(output_dir, "plot_vehicle_speed.png")
    plt.savefig(filename3, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename3}")

    # --- Plot 4: Powertrain Heat Generation ---
    plt.figure(figsize=plt_figure_size)
    plt.plot(time_minutes, Q_gen_motor_profile, label='电机产热 (W)', color='blue', alpha=0.8)
    plt.plot(time_minutes, Q_gen_inv_profile, label='逆变器产热 (W)', color='orange', alpha=0.8)
    plt.plot(time_minutes, Q_gen_batt_profile, label='电池产热 (W, 含空调负载)', color='green', alpha=0.8)
    plt.ylabel('产热功率 (W)')
    plt.xlabel('时间 (分钟)')
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    plt.ylim(bottom=0)
    plt.title('主要部件产热功率')
    plt.grid(True)
    plt.legend(loc='best')
    plt.tight_layout()
    filename4 = os.path.join(output_dir, "plot_heat_generation.png")
    plt.savefig(filename4, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename4}")

    # --- Plot 5: Battery Power Output Breakdown ---
    plt.figure(figsize=plt_figure_size)
    plt.plot(time_minutes, P_inv_in_profile, label='驱动功率 (逆变器输入 W)', color='brown', alpha=0.7)
    plt.plot(time_minutes, P_comp_elec_profile, label='空调功率 (W)', color='cyan', alpha=0.7)
    plt.plot(time_minutes, P_elec_total_profile, label='总电池输出功率 (W)', color='black', linestyle='--')
    plt.xlabel('时间 (分钟)')
    plt.ylabel('功率 (W)')
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    plt.ylim(bottom=0)
    plt.title('电池输出功率分解')
    plt.grid(True)
    plt.legend(loc='best')
    plt.tight_layout()
    filename5 = os.path.join(output_dir, "plot_battery_power.png")
    plt.savefig(filename5, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename5}")

    # --- Plot: Cabin Cooling Power ---
    plt.figure(figsize=plt_figure_size)
    plt.plot(time_minutes, Q_cabin_cool_profile, label='座舱制冷功率 (W)', color='teal', drawstyle='steps-post')
    plt.ylabel('座舱制冷功率 (W)')
    plt.xlabel('时间 (分钟)')
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    # Set y-limits based on defined power levels for better visualization
    if 'cabin_cooling_power_levels' in sim_params:
        min_power = min(sim_params['cabin_cooling_power_levels'])
        max_power = max(sim_params['cabin_cooling_power_levels'])
        plt.ylim(min_power - 0.1 * abs(min_power) if min_power != 0 else -100 , max_power + 0.1 * max_power + 100) # Add some padding
    else:
        plt.ylim(bottom=0)
    plt.title('座舱实际制冷功率变化')
    plt.grid(True)
    plt.legend(loc='best')
    plt.tight_layout()
    filename_cabin_cool_power = os.path.join(output_dir, "plot_cabin_cooling_power.png")
    plt.savefig(filename_cabin_cool_power, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename_cabin_cool_power}")


    # --- Plot 6: Temperatures vs. Vehicle Speed (ACCELERATION PHASE ONLY) ---
    plt.figure(figsize=plt_figure_size)
    ramp_up_steps = int(sim_params['ramp_up_time_sec'] / sim_params['dt']) if sim_params['dt'] > 0 else 0
    ramp_up_index = min(ramp_up_steps, len(v_vehicle_profile) -1 )

    if ramp_up_index > 0 :
        v_accel = v_vehicle_profile[0:ramp_up_index + 1]
        T_motor_accel = T_motor[0:ramp_up_index + 1]
        T_inv_accel = T_inv[0:ramp_up_index + 1]
        T_batt_accel = T_batt[0:ramp_up_index + 1]
        T_cabin_accel = T_cabin[0:ramp_up_index + 1]
        T_coolant_accel = T_coolant[0:ramp_up_index + 1]

        plt.plot(v_accel, T_motor_accel, label='电机温度 (°C)', color='blue', marker='.', markersize=1, linestyle='-')
        plt.plot(v_accel, T_inv_accel, label='逆变器温度 (°C)', color='orange', marker='.', markersize=1, linestyle='-')
        plt.plot(v_accel, T_batt_accel, label='电池温度 (°C)', color='green', marker='.', markersize=1, linestyle='-')
        plt.plot(v_accel, T_cabin_accel, label='座舱温度 (°C)', color='red', marker='.', markersize=1, linestyle='-')
        plt.plot(v_accel, T_coolant_accel, label='冷却液温度 (°C)', color='purple', marker='.', markersize=1, linestyle='-', alpha=0.6)
        plt.xlabel('车速 (km/h)')
        plt.ylabel('温度 (°C)')
        plt.title(f'部件温度随车速变化轨迹 (仅加速阶段 {sim_params["v_start"]} 到 {sim_params["v_end"]} km/h)')
        plt.legend(loc='best')
        plt.grid(True)
        if len(v_accel) > 1 :
             plt.xlim(left=min(v_accel), right=max(v_accel))
        elif len(v_accel) == 1:
             plt.xlim(left=v_accel[0]-5, right=v_accel[0]+5)

        plt.tight_layout()
        filename6 = os.path.join(output_dir, "plot_temp_vs_speed_accel.png")
        plt.savefig(filename6, dpi=plt_dpi)
        plt.close()
        print(f"Saved: {filename6}")
    else:
        print("Warning: No acceleration phase data to generate Plot 6 (Temp vs Speed Accel).")


    # --- Plot 7: Temperatures vs. Time (CONSTANT SPEED PHASE ONLY) ---
    plt.figure(figsize=plt_figure_size)
    const_speed_start_index = ramp_up_index + 1
    
    if const_speed_start_index < n_total_points:
        time_const_speed_minutes = time_data[const_speed_start_index:] / 60
        if len(time_const_speed_minutes) > 0:
            T_motor_const_speed = ensure_profile_length(T_motor[const_speed_start_index:], len(time_const_speed_minutes))
            T_inv_const_speed = ensure_profile_length(T_inv[const_speed_start_index:], len(time_const_speed_minutes))
            T_batt_const_speed = ensure_profile_length(T_batt[const_speed_start_index:], len(time_const_speed_minutes))
            T_cabin_const_speed = ensure_profile_length(T_cabin[const_speed_start_index:], len(time_const_speed_minutes))
            T_coolant_const_speed = ensure_profile_length(T_coolant[const_speed_start_index:], len(time_const_speed_minutes))

            plt.plot(time_const_speed_minutes, T_motor_const_speed, label='电机温度 (°C)', color='blue')
            plt.plot(time_const_speed_minutes, T_inv_const_speed, label='逆变器温度 (°C)', color='orange')
            plt.plot(time_const_speed_minutes, T_batt_const_speed, label='电池温度 (°C)', color='green')
            plt.plot(time_const_speed_minutes, T_cabin_const_speed, label='座舱温度 (°C)', color='red')
            plt.plot(time_const_speed_minutes, T_coolant_const_speed, label='冷却液温度 (°C)', color='purple', alpha=0.6)
            plt.axhline(sim_params['T_motor_target'], color='blue', linestyle='--', alpha=0.7, label=f'电机目标 ({sim_params["T_motor_target"]}°C)')
            plt.axhline(sim_params['T_inv_target'], color='orange', linestyle='--', alpha=0.7, label=f'逆变器目标 ({sim_params["T_inv_target"]}°C)')
            plt.axhline(sim_params['T_batt_target_high'], color='green', linestyle='--', alpha=0.7, label=f'电池制冷启动 ({sim_params["T_batt_target_high"]}°C)')
            plt.axhline(sim_params['T_cabin_target'], color='red', linestyle='--', alpha=0.7, label=f'座舱目标 ({sim_params["T_cabin_target"]}°C)')
            plt.axhline(sim_params['T_ambient'], color='grey', linestyle=':', alpha=0.7, label=f'环境温度 ({sim_params["T_ambient"]}°C)')
            plt.xlabel('时间 (分钟)')
            plt.ylabel('温度 (°C)')
            plt.title(f'部件温度变化 (匀速 {sim_params["v_end"]} km/h 阶段)')
            plt.legend(loc='best')
            plt.grid(True)
            if len(time_const_speed_minutes) > 0:
                plt.xlim(left=min(time_const_speed_minutes), right=max(time_const_speed_minutes))
            plt.tight_layout()
            filename7 = os.path.join(output_dir, "plot_temp_at_const_speed.png")
            plt.savefig(filename7, dpi=plt_dpi)
            plt.close()
            print(f"Saved: {filename7}")
        else:
            print("Warning: No data points in constant speed phase for Plot 7.")
    else:
        print("Warning: No constant speed phase data found to generate Plot 7.")

    print("All plots generation attempt finished.")
