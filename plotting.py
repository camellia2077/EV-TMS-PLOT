# plotting.py
import matplotlib.pyplot as plt
import matplotlib as mpl
import os
import numpy as np
from scipy.signal import argrelextrema # 导入 scipy.signal

# 设置 matplotlib 支持中文显示
mpl.rcParams['font.sans-serif'] = ['SimHei'] # 或者 'Microsoft YaHei', 'WenQuanYi Micro Hei' 等
mpl.rcParams['axes.unicode_minus'] = False

def ensure_profile_length(profile, target_length):
    """Ensures a data profile has the target length by repeating the last value if necessary."""
    current_length = len(profile)
    if current_length < target_length:
        last_value = profile[-1] if current_length > 0 else 0
        extension = np.full(target_length - current_length, last_value)
        return np.concatenate((profile, extension))
    return profile[:target_length]

def plot_local_extrema(ax, time_minutes, data, color, label_prefix, text_fontsize=8): # 新增 text_fontsize 参数
    """
    在给定的轴上用文本标注数据的局部最小值和最大值点，并返回这些点的坐标。

    参数:
    ax: matplotlib.axes.Axes 对象，用于绘图。
    time_minutes: 时间数据 (x轴)。
    data: 温度数据 (y轴)。
    color: 文本标注的颜色。
    label_prefix: 用于识别数据系列的标签。
    text_fontsize: 局部极值点文本标注的字体大小。

    返回:
    一个字典，包含 'minima' 和 'maxima'，它们的值是包含 (时间, 温度) 坐标元组的列表。
    例如: {'minima': [(t1, temp1), (t2, temp2)], 'maxima': [...]}
    """
    local_min_indices = argrelextrema(data, np.less)[0]
    local_max_indices = argrelextrema(data, np.greater)[0]

    extrema_coords = {'minima': [], 'maxima': []}

    if len(local_min_indices) > 0:
        for i in local_min_indices:
            # 确保索引在数据范围内
            if 0 <= i < len(time_minutes) and 0 <= i < len(data):
                ax.text(time_minutes[i], data[i], f'{data[i]:.1f}°C\n({time_minutes[i]:.1f}min)',
                        fontsize=text_fontsize, color=color, ha='center', va='top') # 使用 text_fontsize
                extrema_coords['minima'].append((time_minutes[i], data[i]))

    if len(local_max_indices) > 0:
        for i in local_max_indices:
            if 0 <= i < len(time_minutes) and 0 <= i < len(data):
                ax.text(time_minutes[i], data[i], f'{data[i]:.1f}°C\n({time_minutes[i]:.1f}min)',
                        fontsize=text_fontsize, color=color, ha='center', va='bottom') # 使用 text_fontsize
                extrema_coords['maxima'].append((time_minutes[i], data[i]))
    return extrema_coords


def plot_results(time_data, temperatures, ac_power_log, cabin_cool_power_log,
                 speed_profile, heat_gen_profiles, battery_power_profiles,
                 sim_params, cop_value, cooling_system_logs,
                 output_dir="simulation_plots",
                 extrema_text_fontsize=16): # 新增用于控制极值文本大小的参数 最大最小值
    """
    Generates and saves all simulation plots.
    Returns a dictionary of all found local extrema for relevant temperatures.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    plt_figure_size = (sim_params.get('figure_width_inches', 18),
                       sim_params.get('figure_height_inches', 8))
    plt_dpi = sim_params.get('figure_dpi', 300)
    legend_font_size = sim_params.get('legend_font_size', 10)
    axis_label_fs = sim_params.get('axis_label_font_size', 12)
    tick_label_fs = sim_params.get('tick_label_font_size', 10)
    title_fs = sim_params.get('title_font_size', 14)

    time_minutes = time_data / 60
    n_total_points = len(time_data)

    T_motor = ensure_profile_length(temperatures['motor'], n_total_points)
    T_inv = ensure_profile_length(temperatures['inv'], n_total_points)
    T_batt = ensure_profile_length(temperatures['batt'], n_total_points)
    T_cabin = ensure_profile_length(temperatures['cabin'], n_total_points)
    T_coolant = ensure_profile_length(temperatures['coolant'], n_total_points)

    chiller_active_log = ensure_profile_length(cooling_system_logs['chiller_active'], n_total_points)
    radiator_effectiveness_log = ensure_profile_length(cooling_system_logs['radiator_effectiveness'], n_total_points)
    Q_coolant_radiator_log = ensure_profile_length(cooling_system_logs['Q_radiator'], n_total_points)
    Q_powertrain_chiller_log = ensure_profile_length(cooling_system_logs['Q_chiller_powertrain'], n_total_points)
    Q_cabin_evap_log = ensure_profile_length(cooling_system_logs['Q_cabin_evap'], n_total_points)


    P_comp_elec_profile = ensure_profile_length(ac_power_log, n_total_points)
    # cabin_cool_power_log is the same as Q_cabin_evap_log, passed from main
    # Q_cabin_cool_profile = ensure_profile_length(cabin_cool_power_log, n_total_points)
    v_vehicle_profile = ensure_profile_length(speed_profile, n_total_points)

    Q_gen_motor_profile = ensure_profile_length(heat_gen_profiles['motor'], n_total_points)
    Q_gen_inv_profile = ensure_profile_length(heat_gen_profiles['inv'], n_total_points)
    Q_gen_batt_profile = ensure_profile_length(heat_gen_profiles['batt'], n_total_points)
    Q_cabin_load_profile = ensure_profile_length(heat_gen_profiles['cabin_load'], n_total_points)


    P_inv_in_profile = ensure_profile_length(battery_power_profiles['inv_in'], n_total_points)
    P_elec_total_profile = ensure_profile_length(battery_power_profiles['total_elec'], n_total_points)

    all_extrema_data = {} # 用于存储所有组件的极值点

    # --- Plot 1: Temperatures ---
    fig_temp, ax_temp = plt.subplots(figsize=plt_figure_size)
    ax_temp.plot(time_minutes, T_motor, label='电机温度 (°C)', color='blue')
    ax_temp.plot(time_minutes, T_inv, label='逆变器温度 (°C)', color='orange')
    ax_temp.plot(time_minutes, T_batt, label='电池温度 (°C)', color='green')
    ax_temp.plot(time_minutes, T_cabin, label='座舱温度 (°C)', color='red')
    ax_temp.plot(time_minutes, T_coolant, label='冷却液温度 (°C)', color='purple', alpha=0.6)

    all_extrema_data['电机'] = plot_local_extrema(ax_temp, time_minutes, T_motor, 'blue', '电机', text_fontsize=extrema_text_fontsize)
    all_extrema_data['逆变器'] = plot_local_extrema(ax_temp, time_minutes, T_inv, 'orange', '逆变器', text_fontsize=extrema_text_fontsize)
    all_extrema_data['电池'] = plot_local_extrema(ax_temp, time_minutes, T_batt, 'green', '电池', text_fontsize=extrema_text_fontsize)
    all_extrema_data['冷却液'] = plot_local_extrema(ax_temp, time_minutes, T_coolant, 'purple', '冷却液', text_fontsize=extrema_text_fontsize)
    all_extrema_data['座舱'] = plot_local_extrema(ax_temp, time_minutes, T_cabin, 'red', '座舱', text_fontsize=extrema_text_fontsize)


    ax_temp.axhline(sim_params['T_motor_target'], color='blue', linestyle='--', alpha=0.7, label=f'电机目标 ({sim_params["T_motor_target"]}°C)')
    ax_temp.axhline(sim_params['T_inv_target'], color='orange', linestyle='--', alpha=0.7, label=f'逆变器目标 ({sim_params["T_inv_target"]}°C)')
    ax_temp.axhline(sim_params['T_batt_target_high'], color='green', linestyle='--', alpha=0.7, label=f'电池制冷启动 ({sim_params["T_batt_target_high"]}°C)')
    if 'T_batt_stop_cool' in sim_params:
        ax_temp.axhline(sim_params['T_batt_stop_cool'], color='green', linestyle=':', alpha=0.7, label=f'电池制冷停止 ({sim_params["T_batt_stop_cool"]:.1f}°C)')
    ax_temp.axhline(sim_params['T_cabin_target'], color='red', linestyle='--', alpha=0.7, label=f'座舱目标 ({sim_params["T_cabin_target"]}°C)')

    if 'cabin_cooling_temp_thresholds' in sim_params and 'cabin_cooling_power_levels' in sim_params:
        thresholds = sim_params['cabin_cooling_temp_thresholds']
        levels = sim_params['cabin_cooling_power_levels']
        plotted_threshold_labels = set() # To avoid duplicate labels
        for idx, temp_thresh in enumerate(thresholds):
            label_text = None
            if levels[idx] > 0 and temp_thresh < 99:
                if idx > 0 and levels[idx-1] == 0:
                    label_text = f'座舱启动P({levels[idx]}W)@{thresholds[idx-1]}-{temp_thresh}°C'
                elif idx == 0 and levels[idx] > 0 : # First level is cooling
                     label_text = f'座舱P({levels[idx]}W)至{temp_thresh}°C'
                elif idx > 0 and levels[idx] > 0 and levels[idx] != levels[idx-1]: # Power step up
                    label_text = f'座舱升档P({levels[idx]}W)@{thresholds[idx-1]}-{temp_thresh}°C'

            elif idx == 0 and levels[idx] == 0 and len(thresholds) > 1:
                 label_text = f'座舱OFF至{temp_thresh}°C'

            if label_text and label_text not in plotted_threshold_labels:
                 ax_temp.axhline(temp_thresh, color='salmon', linestyle=':', alpha=0.4, label=label_text)
                 plotted_threshold_labels.add(label_text)
            elif temp_thresh < 99 and not label_text : # Default unlabeled line if conditions not met for specific label
                 ax_temp.axhline(temp_thresh, color='salmon', linestyle=':', alpha=0.4)


    ax_temp.axhline(sim_params['T_ambient'], color='grey', linestyle=':', alpha=0.7, label=f'环境温度 ({sim_params["T_ambient"]}°C)')
    ax_temp.set_ylabel('温度 (°C)', fontsize=axis_label_fs)
    ax_temp.set_xlabel('时间 (分钟)', fontsize=axis_label_fs)
    ax_temp.tick_params(axis='x', labelsize=tick_label_fs)
    ax_temp.tick_params(axis='y', labelsize=tick_label_fs)
    ax_temp.set_xlim(left=0, right=sim_params['sim_duration']/60)
    ax_temp.set_title(f'部件估算温度 (环境={sim_params["T_ambient"]}°C, COP={cop_value:.2f})', fontsize=title_fs)
    ax_temp.legend(loc='best', fontsize=legend_font_size)
    ax_temp.grid(True)
    plt.tight_layout()
    filename1 = os.path.join(output_dir, "plot_temperatures.png")
    plt.savefig(filename1, dpi=plt_dpi)
    plt.close(fig_temp)
    print(f"Saved: {filename1}")

    # --- Plot 2: Cooling System Operation ---
    fig, ax1 = plt.subplots(figsize=plt_figure_size)
    ax1.plot(time_minutes, chiller_active_log, label='动力总成Chiller状态 (1=ON)', color='black', drawstyle='steps-post', alpha=0.7)
    ax1.plot(time_minutes, radiator_effectiveness_log, label=f'散热器效能因子 (UA/UA_max)', color='brown', drawstyle='steps-post', linestyle='--', alpha=0.7)
    ax1.set_xlabel('时间 (分钟)', fontsize=axis_label_fs)
    ax1.set_ylabel('状态 / 效能因子', fontsize=axis_label_fs)
    ax1.tick_params(axis='x', labelsize=tick_label_fs)
    ax1.tick_params(axis='y', labelsize=tick_label_fs)
    ax1.set_ylim(-0.1, 1.1)
    ax1.grid(True, linestyle=':', alpha=0.6)

    ax2 = ax1.twinx()
    ax2.plot(time_minutes, P_comp_elec_profile, label=f'空调压缩机总电耗 (W)', color='cyan', alpha=0.8, linestyle='-')
    ax2.plot(time_minutes, Q_coolant_radiator_log, label=f'散热器实际散热 (W)', color='orange', alpha=0.8, linestyle='-.')
    ax2.set_ylabel('功率 (W)', color='gray', fontsize=axis_label_fs)
    ax2.tick_params(axis='y', labelcolor='gray', labelsize=tick_label_fs)
    min_power_y2 = 0
    max_power_y2 = max(np.max(P_comp_elec_profile) if len(P_comp_elec_profile)>0 else 0,
                       np.max(Q_coolant_radiator_log) if len(Q_coolant_radiator_log)>0 else 0)
    ax2.set_ylim(min_power_y2, max_power_y2 * 1.1 if max_power_y2 > 0 else 100)


    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='best', fontsize=legend_font_size)

    plt.title('制冷系统运行状态、散热器效能及相关功率', fontsize=title_fs)
    plt.tight_layout()
    filename2 = os.path.join(output_dir, "plot_cooling_system_operation.png")
    plt.savefig(filename2, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename2}")


    # --- Plot 3: Vehicle Speed ---
    plt.figure(figsize=plt_figure_size)
    plt.plot(time_minutes, v_vehicle_profile, label='车速 (km/h)', color='magenta')
    plt.ylabel('车速 (km/h)', fontsize=axis_label_fs)
    plt.xlabel('时间 (分钟)', fontsize=axis_label_fs)
    plt.xticks(fontsize=tick_label_fs)
    plt.yticks(fontsize=tick_label_fs)
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    v_min_plot = 0
    v_max_plot = max(sim_params['v_start'], sim_params['v_end']) + 10 if len(v_vehicle_profile) > 0 else 10
    plt.ylim(v_min_plot, v_max_plot)
    plt.title(f'车辆速度变化曲线 ({sim_params["v_start"]}到{sim_params["v_end"]}km/h)', fontsize=title_fs)
    plt.grid(True)
    plt.tight_layout()
    plt.legend(loc='best', fontsize=legend_font_size)
    filename3 = os.path.join(output_dir, "plot_vehicle_speed.png")
    plt.savefig(filename3, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename3}")

    # --- Plot 4: Powertrain Heat Generation ---
    plt.figure(figsize=plt_figure_size)
    plt.plot(time_minutes, Q_gen_motor_profile, label='电机产热 (W)', color='blue', alpha=0.8)
    plt.plot(time_minutes, Q_gen_inv_profile, label='逆变器产热 (W)', color='orange', alpha=0.8)
    plt.plot(time_minutes, Q_gen_batt_profile, label='电池产热 (W)', color='green', alpha=0.8) # Label updated
    plt.ylabel('产热功率 (W)', fontsize=axis_label_fs)
    plt.xlabel('时间 (分钟)', fontsize=axis_label_fs)
    plt.xticks(fontsize=tick_label_fs)
    plt.yticks(fontsize=tick_label_fs)
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    max_heat_gen = max(np.max(Q_gen_motor_profile) if len(Q_gen_motor_profile)>0 else 0,
                       np.max(Q_gen_inv_profile) if len(Q_gen_inv_profile)>0 else 0,
                       np.max(Q_gen_batt_profile) if len(Q_gen_batt_profile)>0 else 0)
    plt.ylim(0, max_heat_gen * 1.1 if max_heat_gen > 0 else 100)
    plt.title('动力总成部件产热功率', fontsize=title_fs) # Title updated
    plt.grid(True)
    plt.legend(loc='best', fontsize=legend_font_size)
    plt.tight_layout()
    filename4 = os.path.join(output_dir, "plot_powertrain_heat_generation.png") # Filename updated
    plt.savefig(filename4, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename4}")

    # --- Plot 5: Battery Power Output Breakdown ---
    plt.figure(figsize=plt_figure_size)
    plt.plot(time_minutes, P_inv_in_profile, label='驱动用电功率 (逆变器输入 W)', color='brown', alpha=0.7) # Label updated
    plt.plot(time_minutes, P_comp_elec_profile, label='空调压缩机电功率 (W)', color='cyan', alpha=0.7) # Label updated
    plt.plot(time_minutes, P_elec_total_profile, label='总电池输出功率 (W)', color='green', linestyle='-')
    plt.xlabel('时间 (分钟)', fontsize=axis_label_fs)
    plt.ylabel('功率 (W)', fontsize=axis_label_fs)
    plt.xticks(fontsize=tick_label_fs)
    plt.yticks(fontsize=tick_label_fs)
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    max_batt_power = np.max(P_elec_total_profile) if len(P_elec_total_profile)>0 else 0
    plt.ylim(0, max_batt_power*1.1 if max_batt_power > 0 else 100)
    plt.title('电池输出功率分解', fontsize=title_fs)
    plt.grid(True)
    plt.legend(loc='best', fontsize=legend_font_size)
    plt.tight_layout()
    filename5 = os.path.join(output_dir, "plot_battery_power.png")
    plt.savefig(filename5, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename5}")


    # --- Plot: Cabin Cooling Power (already Q_cabin_evap_log) ---
    plt.figure(figsize=plt_figure_size)
    plt.plot(time_minutes, Q_cabin_evap_log, label='座舱蒸发器制冷功率 (W)', color='teal', drawstyle='steps-post') # Using Q_cabin_evap_log
    plt.ylabel('座舱制冷功率 (W)', fontsize=axis_label_fs)
    plt.xlabel('时间 (分钟)', fontsize=axis_label_fs)
    plt.xticks(fontsize=tick_label_fs)
    plt.yticks(fontsize=tick_label_fs)
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    if 'cabin_cooling_power_levels' in sim_params:
        min_power_val = 0
        max_power_val = max(sim_params['cabin_cooling_power_levels']) if sim_params['cabin_cooling_power_levels'] else 100
        plt.ylim(min_power_val - 0.1 * abs(max_power_val) if max_power_val != 0 else -100 , max_power_val + 0.1 * max_power_val + 100)
    else:
        max_evap_power = np.max(Q_cabin_evap_log) if len(Q_cabin_evap_log)>0 else 0
        plt.ylim(0, max_evap_power * 1.1 if max_evap_power > 0 else 100)
    plt.title('座舱实际制冷功率变化', fontsize=title_fs)
    plt.grid(True)
    plt.legend(loc='best', fontsize=legend_font_size)
    plt.tight_layout()
    filename_cabin_cool_power = os.path.join(output_dir, "plot_cabin_cooling_power.png")
    plt.savefig(filename_cabin_cool_power, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename_cabin_cool_power}")


    # --- Plot 6: Temperatures vs. Vehicle Speed (ACCELERATION PHASE ONLY) ---
    plt.figure(figsize=plt_figure_size)
    ramp_up_steps = int(sim_params['ramp_up_time_sec'] / sim_params.get('dt', 1)) if sim_params.get('dt', 1) > 0 else 0
    ramp_up_index = min(ramp_up_steps, len(v_vehicle_profile) -1 )

    if ramp_up_index > 0 and len(v_vehicle_profile) > ramp_up_index:
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
        plt.xlabel('车速 (km/h)', fontsize=axis_label_fs)
        plt.ylabel('温度 (°C)', fontsize=axis_label_fs)
        plt.xticks(fontsize=tick_label_fs)
        plt.yticks(fontsize=tick_label_fs)
        plt.title(f'加速阶段部件温度随车速变化轨迹 ({sim_params["v_start"]}到{sim_params["v_end"]} km/h)', fontsize=title_fs)
        plt.legend(loc='best', fontsize=legend_font_size)
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
        print("Warning: No or insufficient acceleration phase data to generate Plot 6 (Temp vs Speed Accel).")


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
            plt.xlabel('时间 (分钟)', fontsize=axis_label_fs)
            plt.ylabel('温度 (°C)', fontsize=axis_label_fs)
            plt.xticks(fontsize=tick_label_fs)
            plt.yticks(fontsize=tick_label_fs)
            plt.title(f'部件温度变化 (匀速 {sim_params["v_end"]} km/h 阶段)', fontsize=title_fs)
            plt.legend(loc='best', fontsize=legend_font_size)
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

    # --- 新增图表：总热负荷 vs 总散热功率 ---
    # 确保所有参与计算的数组长度一致
    Q_gen_motor_profile = ensure_profile_length(Q_gen_motor_profile, n_total_points)
    Q_gen_inv_profile = ensure_profile_length(Q_gen_inv_profile, n_total_points)
    Q_gen_batt_profile = ensure_profile_length(Q_gen_batt_profile, n_total_points)
    Q_cabin_load_profile = ensure_profile_length(Q_cabin_load_profile, n_total_points)
    Q_coolant_radiator_log = ensure_profile_length(Q_coolant_radiator_log, n_total_points)
    Q_powertrain_chiller_log = ensure_profile_length(Q_powertrain_chiller_log, n_total_points)
    Q_cabin_evap_log = ensure_profile_length(Q_cabin_evap_log, n_total_points)


    Q_total_heat_load = Q_gen_motor_profile + Q_gen_inv_profile + Q_gen_batt_profile + Q_cabin_load_profile
    Q_total_heat_rejection = Q_coolant_radiator_log + Q_powertrain_chiller_log + Q_cabin_evap_log

    plt.figure(figsize=plt_figure_size)
    plt.plot(time_minutes, Q_total_heat_load, label='总热负荷功率 (W)', color='maroon', linestyle='-')
    plt.plot(time_minutes, Q_total_heat_rejection, label='总散热系统散热功率 (W)', color='darkcyan', linestyle='--')

    # 可选: 绘制分量图
    # plt.stackplot(time_minutes,
    #               Q_gen_motor_profile, Q_gen_inv_profile, Q_gen_batt_profile, Q_cabin_load_profile,
    #               labels=['电机产热 (W)', '逆变器产热 (W)', '电池产热 (W)', '座舱热负荷 (W)'],
    #               colors=['lightcoral', 'sandybrown', 'lightgreen', 'lightpink'], alpha=0.7)
    #
    # plt.stackplot(time_minutes,
    #               Q_coolant_radiator_log, Q_powertrain_chiller_log, Q_cabin_evap_log,
    #               labels=['散热器散热 (W)', '动力Chiller散热 (W)', '座舱蒸发器制冷 (W)'],
    #               colors=['mediumturquoise', 'cadetblue', 'powderblue'], alpha=0.5, baseline='zero')


    plt.xlabel('时间 (分钟)', fontsize=axis_label_fs)
    plt.ylabel('功率 (W)', fontsize=axis_label_fs)
    plt.xticks(fontsize=tick_label_fs)
    plt.yticks(fontsize=tick_label_fs)
    plt.xlim(left=0, right=sim_params['sim_duration']/60)
    # 动态调整Y轴范围
    max_load_val = np.max(Q_total_heat_load) if len(Q_total_heat_load) > 0 else 0
    max_rejection_val = np.max(Q_total_heat_rejection) if len(Q_total_heat_rejection) > 0 else 0
    overall_max_power = max(max_load_val, max_rejection_val)
    plt.ylim(0, overall_max_power * 1.1 if overall_max_power > 0 else 100)

    plt.title('总热负荷功率 vs 总散热系统散热功率', fontsize=title_fs)
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend(loc='best', fontsize=legend_font_size)
    plt.tight_layout()
    filename_heat_balance = os.path.join(output_dir, "plot_total_heat_balance.png")
    plt.savefig(filename_heat_balance, dpi=plt_dpi)
    plt.close()
    print(f"Saved: {filename_heat_balance}")
    # --- 结束新增图表 ---


    print("All plots generation attempt finished.")
    return all_extrema_data
