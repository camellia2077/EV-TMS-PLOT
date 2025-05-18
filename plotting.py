# plotting.py
import matplotlib.pyplot as plt
import matplotlib as mpl
import os
import numpy as np

# 设置 matplotlib 支持中文显示
mpl.rcParams['font.sans-serif'] = ['SimSun'] # 或者 'Microsoft YaHei', 'WenQuanYi Micro Hei' 等
mpl.rcParams['axes.unicode_minus'] = False

class SimulationPlotter:
    def __init__(self, time_data, temperatures, ac_power_log, cabin_cool_power_log,
                 speed_profile, heat_gen_profiles, battery_power_profiles,
                 sim_params, cop_value, cooling_system_logs,
                 output_dir="simulation_plots",
                 extrema_text_fontsize=16):
        """
        Initializes the SimulationPlotter with all necessary data and parameters.
        """
        self.time_data_raw = time_data
        self.temperatures_raw = temperatures
        self.ac_power_log_raw = ac_power_log
        self.cabin_cool_power_log_raw = cabin_cool_power_log # This is Q_cabin_evap
        self.speed_profile_raw = speed_profile
        self.heat_gen_profiles_raw = heat_gen_profiles
        self.battery_power_profiles_raw = battery_power_profiles
        self.sim_params = sim_params # This should be a dictionary
        self.cop_value = cop_value
        self.cooling_system_logs_raw = cooling_system_logs
        self.output_dir = output_dir
        self.extrema_text_fontsize = extrema_text_fontsize

        self.common_settings = self._setup_common_plot_settings()
        self.prepared_data = self._prepare_plot_data()
        self.time_minutes = self.prepared_data['time_minutes']
        self.all_extrema_data = {}


    @staticmethod
    def _ensure_profile_length(profile, target_length):
        """Ensures a data profile has the target length by repeating the last value if necessary."""
        current_length = len(profile)
        if current_length < target_length:
            last_value = profile[-1] if current_length > 0 else 0
            extension = np.full(target_length - current_length, last_value)
            return np.concatenate((profile, extension))
        return profile[:target_length]

    @staticmethod
    def _plot_local_extrema(ax, time_minutes, data, color, label_prefix, text_fontsize=8):
        """
        Marks local extrema on the given axes and returns their coordinates using custom logic.
        If label_prefix is '座舱', annotations are not plotted.
        查找极值
        """
        extrema_coords = {'minima': [], 'maxima': []}
        n = len(data)
        if n < 3: # Need at least 3 points to find a local extremum
            return extrema_coords

        for i in range(1, n - 1):
            # Check for local maximum
            if data[i] > data[i-1] and data[i] > data[i+1]:
                if 0 <= i < len(time_minutes): # Check index bounds
                    extrema_coords['maxima'].append((time_minutes[i], data[i]))
            # Check for local minimum
            elif data[i] < data[i-1] and data[i] < data[i+1]:
                if 0 <= i < len(time_minutes): # Check index bounds
                    extrema_coords['minima'].append((time_minutes[i], data[i]))

        return extrema_coords

    def _setup_common_plot_settings(self):
        """Helper method to return common plot settings from sim_params."""
        return {
            'figure_size': (self.sim_params.get('figure_width_inches', 18),
                            self.sim_params.get('figure_height_inches', 8)),
            'dpi': self.sim_params.get('figure_dpi', 300),
            'legend_font_size': self.sim_params.get('legend_font_size', 10),
            'axis_label_fs': self.sim_params.get('axis_label_font_size', 12),
            'tick_label_fs': self.sim_params.get('tick_label_font_size', 10),
            'title_fs': self.sim_params.get('title_font_size', 14)
        }

    def _prepare_plot_data(self):
        """Helper method to ensure all data profiles have the correct length."""
        n_total_points = len(self.time_data_raw)
        prepared_data = {}
        prepared_data['time_minutes'] = self.time_data_raw / 60

        _ensure = SimulationPlotter._ensure_profile_length # Shortcut for static method

        prepared_data['T_motor'] = _ensure(self.temperatures_raw.get('motor', np.array([])), n_total_points)
        prepared_data['T_inv'] = _ensure(self.temperatures_raw.get('inv', np.array([])), n_total_points)
        prepared_data['T_batt'] = _ensure(self.temperatures_raw.get('batt', np.array([])), n_total_points)
        prepared_data['T_cabin'] = _ensure(self.temperatures_raw.get('cabin', np.array([])), n_total_points)
        prepared_data['T_coolant'] = _ensure(self.temperatures_raw.get('coolant', np.array([])), n_total_points)

        
        prepared_data['chiller_active_log'] = _ensure(self.cooling_system_logs_raw.get('chiller_active', np.array([])), n_total_points)
        
        # 旧的散热器效能日志，现在用 LTR 效能日志替代
        
        prepared_data['LTR_level_log'] = _ensure(self.cooling_system_logs_raw.get('LTR_level', np.array([])), n_total_points)
        prepared_data['P_LTR_fan_log'] = _ensure(self.cooling_system_logs_raw.get('P_LTR_fan', np.array([])), n_total_points)


        # 旧的散热器散热量日志，现在用 LTR 散热量替代
        prepared_data['Q_LTR_to_ambient_log'] = _ensure(self.cooling_system_logs_raw.get('Q_LTR_to_ambient', np.array([])), n_total_points) # 新键

        # Chiller 从冷却液吸收的热量
        prepared_data['Q_coolant_to_chiller_log'] = _ensure(self.cooling_system_logs_raw.get('Q_coolant_to_chiller', np.array([])), n_total_points) # 更新的键
        # 座舱蒸发器吸收的热量
        prepared_data['Q_cabin_evap_cooling_log'] = _ensure(self.cooling_system_logs_raw.get('Q_cabin_evap_cooling', np.array([])), n_total_points) # 更新的键
        # --- 添加这行来处理 LTR 效能因子 ---
        prepared_data['LTR_effectiveness_log'] = _ensure(self.cooling_system_logs_raw.get('LTR_effectiveness_factor_equiv', np.array([])), n_total_points)
        # Ensure ac_power_log_raw is an array before passing to _ensure
        ac_power_log_data = self.ac_power_log_raw if isinstance(self.ac_power_log_raw, np.ndarray) else np.array(self.ac_power_log_raw)
        prepared_data['P_comp_elec_profile'] = _ensure(ac_power_log_data, n_total_points)

        speed_profile_data = self.speed_profile_raw if isinstance(self.speed_profile_raw, np.ndarray) else np.array(self.speed_profile_raw)
        prepared_data['v_vehicle_profile'] = _ensure(speed_profile_data, n_total_points)

        prepared_data['Q_gen_motor_profile'] = _ensure(self.heat_gen_profiles_raw.get('motor', np.array([])), n_total_points)
        prepared_data['Q_gen_inv_profile'] = _ensure(self.heat_gen_profiles_raw.get('inv', np.array([])), n_total_points)
        prepared_data['Q_gen_batt_profile'] = _ensure(self.heat_gen_profiles_raw.get('batt', np.array([])), n_total_points)
        prepared_data['Q_cabin_load_profile'] = _ensure(self.heat_gen_profiles_raw.get('cabin_load', np.array([])), n_total_points)

        prepared_data['P_inv_in_profile'] = _ensure(self.battery_power_profiles_raw.get('inv_in', np.array([])), n_total_points)
        prepared_data['P_elec_total_profile'] = _ensure(self.battery_power_profiles_raw.get('total_elec', np.array([])), n_total_points)

        return prepared_data

    def plot_temperatures(self):
        """
        部件估算温度
        Plots component temperatures and prints their average values.
        """
        fig_temp, ax_temp = plt.subplots(figsize=self.common_settings['figure_size'])
        data = self.prepared_data
        chart_title = f'部件估算温度 (环境={self.sim_params["T_ambient"]}°C, COP={self.cop_value:.2f})' # 这是图表的标题
        print("\nStart----------------------------------------------------")
        print(f"--- 图表: {chart_title} ---")
        print("--- 以下为此图表内各项数据的平均值 ---")

        ax_temp.plot(self.time_minutes, data['T_motor'], label='电机温度 (°C)', color='blue')


        ax_temp.plot(self.time_minutes, data['T_inv'], label='逆变器温度 (°C)', color='orange')

        
        ax_temp.plot(self.time_minutes, data['T_batt'], label='电池温度 (°C)', color='green')

        
        ax_temp.plot(self.time_minutes, data['T_cabin'], label='座舱温度 (°C)', color='red')

        ax_temp.plot(self.time_minutes, data['T_coolant'], label='冷却液温度 (°C)', color='purple', alpha=0.6)
        # --- 添加计算和打印平均值的代码 ---
        if len(data['T_motor']) > 0:
            print(f"平均电机温度: {np.mean(data['T_motor']):.2f} °C")
        if len(data['T_inv']) > 0:
            print(f"平均逆变器温度: {np.mean(data['T_inv']):.2f} °C")
        if len(data['T_batt']) > 0:
            print(f"平均电池温度: {np.mean(data['T_batt']):.2f} °C")
        if len(data['T_cabin']) > 0:
            print(f"平均座舱温度: {np.mean(data['T_cabin']):.2f} °C")
        if len(data['T_coolant']) > 0:
            print(f"平均冷却液温度: {np.mean(data['T_coolant']):.2f} °C")
        self.all_extrema_data['电机'] = self._plot_local_extrema(ax_temp, self.time_minutes, data['T_motor'], 'blue', '电机', self.extrema_text_fontsize)
        self.all_extrema_data['逆变器'] = self._plot_local_extrema(ax_temp, self.time_minutes, data['T_inv'], 'orange', '逆变器', self.extrema_text_fontsize)
        self.all_extrema_data['电池'] = self._plot_local_extrema(ax_temp, self.time_minutes, data['T_batt'], 'green', '电池', self.extrema_text_fontsize)
        self.all_extrema_data['冷却液'] = self._plot_local_extrema(ax_temp, self.time_minutes, data['T_coolant'], 'purple', '冷却液', self.extrema_text_fontsize)
        self.all_extrema_data['座舱'] = self._plot_local_extrema(ax_temp, self.time_minutes, data['T_cabin'], 'red', '座舱', self.extrema_text_fontsize)

        ax_temp.axhline(self.sim_params['T_motor_target'], color='magenta', linestyle='--', alpha=0.7, label=f'电机/逆变器目标 ({self.sim_params["T_motor_target"]}°C)')

        ax_temp.axhline(self.sim_params['T_cabin_target'], color='red', linestyle='--', alpha=0.7, label=f'座舱目标 ({self.sim_params["T_cabin_target"]}°C)')

        ax_temp.axhline(self.sim_params['T_ambient'], color='black', linestyle='-', alpha=1, label=f'环境温度 ({self.sim_params["T_ambient"]}°C)')
        ax_temp.set_ylabel('温度 (°C)', fontsize=self.common_settings['axis_label_fs'])
        ax_temp.set_xlabel('时间 (分钟)', fontsize=self.common_settings['axis_label_fs'])
        ax_temp.tick_params(axis='x', labelsize=self.common_settings['tick_label_fs'])
        ax_temp.tick_params(axis='y', labelsize=self.common_settings['tick_label_fs'])
        ax_temp.set_xlim(left=0, right=self.sim_params['sim_duration']/60)
        ax_temp.set_title(f'部件估算温度 (环境={self.sim_params["T_ambient"]}°C, COP={self.cop_value:.2f})', fontsize=self.common_settings['title_fs'])
        ax_temp.legend(loc='best', fontsize=self.common_settings['legend_font_size'])
        ax_temp.grid(True)
        plt.tight_layout()
        filename = os.path.join(self.output_dir, "plot_temperatures.png")
        plt.savefig(filename, dpi=self.common_settings['dpi'])
        plt.close(fig_temp)
        print(f"Saved: {filename}")
        print("Finished----------------------------------------------------\n")

    def plot_cooling_system_operation(self):
        """
        制冷/散热系统相关功率
        Plots cooling system related powers and prints their average values.
        """
        fig, ax1 = plt.subplots(figsize=self.common_settings['figure_size']) # 只创建一个轴
        data = self.prepared_data
        chart_title = '制冷/散热系统相关功率' # 更新图表标题
        print(f"--- 图表: {chart_title} ---")
        print("--- 以下为此图表内各项数据的平均值 ---")
        print("--- Average Values for Cooling System Operation Plot ---")

        # 设置 X 轴从 0 开始
        if len(self.time_minutes) > 0:
            ax1.set_xlim(left=0, right=max(self.time_minutes) if len(self.time_minutes) > 1 else 10)
        else:
            ax1.set_xlim(left=0, right=10)

        ax1.set_xlabel('时间 (分钟)', fontsize=self.common_settings['axis_label_fs'])
        ax1.set_ylabel('功率 (W)', fontsize=self.common_settings['axis_label_fs']) # Y轴统一为功率
        ax1.tick_params(axis='x', labelsize=self.common_settings['tick_label_fs'])
        ax1.tick_params(axis='y', labelsize=self.common_settings['tick_label_fs'])
        ax1.grid(True, linestyle=':', alpha=0.6)
        p_comp_elec_data = data.get('P_comp_elec_profile', [])
        if len(p_comp_elec_data) > 0:
            print(f"Average AC Compressor Total Electrical Power: {np.mean(p_comp_elec_data):.2f} W")
            ax1.plot(self.time_minutes, p_comp_elec_data, label=f'空调压缩机总电耗 (W)', color='cyan', alpha=0.8, linestyle='-')
        else:
            ax1.plot([], [], label=f'空调压缩机总电耗 (W)', color='cyan', alpha=0.8, linestyle='-')

        q_ltr_to_ambient_data = data.get('Q_LTR_to_ambient_log', [])
        if len(q_ltr_to_ambient_data) > 0:
            print(f"Average Actual LTR Heat Dissipation: {np.mean(q_ltr_to_ambient_data):.2f} W")
            ax1.plot(self.time_minutes, q_ltr_to_ambient_data, label=f'LTR实际散热 (W)', color='orange', alpha=0.8, linestyle='-.')
        else:
            ax1.plot([], [], label=f'LTR实际散热 (W)', color='orange', alpha=0.8, linestyle='-.')

        max_p_comp = np.max(p_comp_elec_data) if len(p_comp_elec_data) > 0 else 0
        max_q_ltr = np.max(q_ltr_to_ambient_data) if len(q_ltr_to_ambient_data) > 0 else 0
        max_power_y = max(max_p_comp, max_q_ltr) # 现在只有一个Y轴
        ax1.set_ylim(bottom=0, top=max_power_y * 1.1 if max_power_y > 0 else 100)

        # 获取并设置图例 (现在只从 ax1 获取)
        lines, labels = ax1.get_legend_handles_labels()
        if lines: # 确保有图例项
            ax1.legend(lines, labels, loc='best', fontsize=self.common_settings['legend_font_size'])

        plt.title(chart_title, fontsize=self.common_settings['title_fs'])
        plt.tight_layout()
        filename = os.path.join(self.output_dir, "plot_cooling_system_operation.png")
        plt.savefig(filename, dpi=self.common_settings['dpi'])
        plt.close(fig)
        print(f"Saved: {filename}")
        print("Finished----------------------------------------------------\n")

    def plot_vehicle_speed(self):
        """
        车辆速度变化曲线
        Plots vehicle speed profile and prints its average value.
        """
        plt.figure(figsize=self.common_settings['figure_size'])
        v_vehicle_profile = self.prepared_data['v_vehicle_profile']
        print("\nStart---------------------------------------------------")
        chart_title = f'车辆速度变化曲线 ({self.sim_params.get("v_start", "N/A")}到{self.sim_params.get("v_end","N/A")}km/h)'
        print(f"--- 图表: {chart_title} ---")
        print("--- 以下为此图表内各项数据的平均值 ---")
        print("--- Average Values for Vehicle Speed Plot ---")

        print(f"Average Vehicle Speed: {np.mean(v_vehicle_profile):.2f} km/h")
        plt.plot(self.time_minutes, v_vehicle_profile, label='车速 (km/h)', color='magenta')
        plt.ylabel('车速 (km/h)', fontsize=self.common_settings['axis_label_fs'])
        plt.xlabel('时间 (分钟)', fontsize=self.common_settings['axis_label_fs'])
        plt.xticks(fontsize=self.common_settings['tick_label_fs'])
        plt.yticks(fontsize=self.common_settings['tick_label_fs'])
        plt.xlim(left=0, right=self.sim_params['sim_duration']/60)
        v_min_plot = 0
        v_max_plot = max(self.sim_params.get('v_start', 0), self.sim_params.get('v_end', 0)) + 10 if len(v_vehicle_profile) > 0 else 10
        plt.ylim(v_min_plot, v_max_plot)
        plt.title(f'车辆速度变化曲线 ({self.sim_params.get("v_start", "N/A")}到{self.sim_params.get("v_end","N/A")}km/h)', fontsize=self.common_settings['title_fs'])
        plt.grid(True)
        plt.tight_layout()
        plt.legend(loc='best', fontsize=self.common_settings['legend_font_size'])
        filename = os.path.join(self.output_dir, "plot_vehicle_speed.png")
        plt.savefig(filename, dpi=self.common_settings['dpi'])
        plt.close()
        print(f"Saved: {filename}")#输出保存图片名称
        print("Finished----------------------------------------------------\n")

    def plot_powertrain_heat_generation(self):
        """
        动力总成部件产热功率
        Plots powertrain component heat generation and prints their average values.
        """
        plt.figure(figsize=self.common_settings['figure_size'])
        data = self.prepared_data
        Q_gen_motor_profile = data['Q_gen_motor_profile']
        Q_gen_inv_profile = data['Q_gen_inv_profile']
        Q_gen_batt_profile = data['Q_gen_batt_profile']
        chart_title = '动力总成部件产热功率'
        print("\nStart---------------------------------------------------")
        print(f"--- 图表: {chart_title} ---")
        print("--- 以下为此图表内各项数据的平均值 ---")
        print("--- Average Values for Powertrain Heat Generation Plot ---")

        print(f"Average Motor Heat Generation: {np.mean(Q_gen_motor_profile):.2f} W")
        plt.plot(self.time_minutes, Q_gen_motor_profile, label='电机产热 (W)', color='blue', alpha=0.8)


        print(f"Average Inverter Heat Generation: {np.mean(Q_gen_inv_profile):.2f} W")
        plt.plot(self.time_minutes, Q_gen_inv_profile, label='逆变器产热 (W)', color='orange', alpha=0.8)

        print(f"Average Battery Heat Generation: {np.mean(Q_gen_batt_profile):.2f} W")
        plt.plot(self.time_minutes, Q_gen_batt_profile, label='电池产热 (W)', color='green', alpha=0.8)

        plt.ylabel('产热功率 (W)', fontsize=self.common_settings['axis_label_fs'])
        plt.xlabel('时间 (分钟)', fontsize=self.common_settings['axis_label_fs'])
        plt.xticks(fontsize=self.common_settings['tick_label_fs'])
        plt.yticks(fontsize=self.common_settings['tick_label_fs'])
        plt.xlim(left=0, right=self.sim_params['sim_duration']/60)
        max_heat_gen = max(np.max(Q_gen_motor_profile) if len(Q_gen_motor_profile)>0 else 0,
                           np.max(Q_gen_inv_profile) if len(Q_gen_inv_profile)>0 else 0,
                           np.max(Q_gen_batt_profile) if len(Q_gen_batt_profile)>0 else 0)
        plt.ylim(0, max_heat_gen * 1.1 if max_heat_gen > 0 else 100)
        plt.title('动力总成部件产热功率', fontsize=self.common_settings['title_fs'])
        plt.grid(True)
        plt.legend(loc='best', fontsize=self.common_settings['legend_font_size'])
        plt.tight_layout()
        filename = os.path.join(self.output_dir, "plot_powertrain_heat_generation.png")
        plt.savefig(filename, dpi=self.common_settings['dpi'])
        plt.close()
        print(f"Saved: {filename}")
        print("Finished----------------------------------------------------\n")

    def plot_battery_power(self):
        """
        电池输出功率分解
        Plots battery power output breakdown and prints their average values.
        """
        plt.figure(figsize=self.common_settings['figure_size'])
        data = self.prepared_data
        P_inv_in_profile = data['P_inv_in_profile']
        P_comp_elec_profile = data['P_comp_elec_profile'] # Already printed in cooling_system_operation
        P_elec_total_profile = data['P_elec_total_profile']
        chart_title = '电池输出功率分解'
        print("\nStart---------------------------------------------------")
        print(f"--- 图表: {chart_title} ---")
        print("--- 以下为此图表内各项数据的平均值 ---")
        print("--- Average Values for Battery Power Plot ---")

        print(f"Average Drive Power (Inverter Input): {np.mean(P_inv_in_profile):.2f} W")
        plt.plot(self.time_minutes, P_inv_in_profile, label='驱动用电功率 (逆变器输入 W)', color='brown', alpha=0.7)

        plt.plot(self.time_minutes, P_comp_elec_profile, label='空调压缩机电功率 (W)', color='cyan', alpha=0.7)

        if len(P_elec_total_profile) > 0:
            print(f"Average Total Battery Output Power: {np.mean(P_elec_total_profile):.2f} W")
        plt.plot(self.time_minutes, P_elec_total_profile, label='总电池输出功率 (W)', color='green', linestyle='-')
        
        plt.xlabel('时间 (分钟)', fontsize=self.common_settings['axis_label_fs'])
        plt.ylabel('功率 (W)', fontsize=self.common_settings['axis_label_fs'])
        plt.xticks(fontsize=self.common_settings['tick_label_fs'])
        plt.yticks(fontsize=self.common_settings['tick_label_fs'])
        plt.xlim(left=0, right=self.sim_params['sim_duration']/60)
        max_batt_power = np.max(P_elec_total_profile) if len(P_elec_total_profile)>0 else 0
        plt.ylim(0, max_batt_power*1.1 if max_batt_power > 0 else 100)
        plt.title('电池输出功率分解', fontsize=self.common_settings['title_fs'])
        plt.grid(True)
        plt.legend(loc='best', fontsize=self.common_settings['legend_font_size'])
        plt.tight_layout()
        filename = os.path.join(self.output_dir, "plot_battery_power.png")
        plt.savefig(filename, dpi=self.common_settings['dpi'])
        plt.close()
        print(f"Saved: {filename}")
        print("Finished----------------------------------------------------\n")

    def plot_cabin_cooling_power(self):
        """
        座舱实际制冷功率变化
        Plots actual cabin cooling power and prints its average value.
        """
        plt.figure(figsize=self.common_settings['figure_size'])
        Q_cabin_evap_log = self.prepared_data.get('Q_cabin_evap_cooling_log', []) # 使用新的键名并添加 .get()
        
        chart_title = '座舱实际制冷功率变化'
        print("\nStart---------------------------------------------------")
        print(f"--- 图表: {chart_title} ---")
        print("--- 以下为此图表内各项数据的平均值 ---")
        print("--- Average Values for Cabin Cooling Power Plot ---")
        
     
        print(f"Average Cabin Evaporator Cooling Power: {np.mean(Q_cabin_evap_log):.2f} W")
        plt.plot(self.time_minutes, Q_cabin_evap_log, label='座舱蒸发器制冷功率 (W)', color='teal', drawstyle='steps-post')
        if Q_cabin_evap_log is None or len(Q_cabin_evap_log) == 0 or np.all(Q_cabin_evap_log == 0): # 添加条件判断
            print("Warning: 'Q_cabin_evap_cooling_log' not found or empty in prepared_data. Plot will be empty.")


        plt.ylabel('座舱制冷功率 (W)', fontsize=self.common_settings['axis_label_fs'])
        plt.xlabel('时间 (分钟)', fontsize=self.common_settings['axis_label_fs'])
        plt.xticks(fontsize=self.common_settings['tick_label_fs'])
        plt.yticks(fontsize=self.common_settings['tick_label_fs'])
        plt.xlim(left=0, right=self.sim_params['sim_duration']/60)
        
        min_power_val = 0
        max_power_val = 0
        if 'cabin_cooling_power_levels' in self.sim_params and self.sim_params['cabin_cooling_power_levels']:
            max_power_val = max(self.sim_params['cabin_cooling_power_levels'])
        elif len(Q_cabin_evap_log) > 0:
             max_power_val = np.max(Q_cabin_evap_log)
        
        # 确保 Y 轴范围合理
        if max_power_val > 0 :
            plt.ylim(min_power_val - 0.1 * abs(max_power_val) if min_power_val < 0 else 0 , max_power_val * 1.1 + 100)
        elif max_power_val == 0 and min_power_val == 0 and len(Q_cabin_evap_log) > 0 : # 如果数据全为0
             plt.ylim(-100, 100)
        else: # 默认范围或无数据的情况
            plt.ylim(0, 1000)


        plt.title('座舱实际制冷功率变化', fontsize=self.common_settings['title_fs'])
        plt.grid(True)
        plt.legend(loc='best', fontsize=self.common_settings['legend_font_size'])
        plt.tight_layout()
        filename = os.path.join(self.output_dir, "plot_cabin_cooling_power.png")
        plt.savefig(filename, dpi=self.common_settings['dpi'])
        plt.close()
        print(f"Saved: {filename}")
        print("Finished----------------------------------------------------\n")

    def plot_temp_vs_speed_accel(self):
        """
        加速阶段部件温度随车速变化轨迹
        Plots temperatures vs. vehicle speed during acceleration phase and prints their average values.
        """
        plt.figure(figsize=self.common_settings['figure_size'])
        data = self.prepared_data
        ramp_up_time_sec = self.sim_params.get('ramp_up_time_sec', 0)
        dt_sim = self.sim_params.get('dt', 1)
        ramp_up_steps = int(ramp_up_time_sec / dt_sim) if dt_sim > 0 else 0
        max_possible_index = len(data['v_vehicle_profile']) -1
        ramp_up_index = min(ramp_up_steps, max_possible_index)
        # --- 获取环境温度 ---
        t_ambient = self.sim_params.get('T_ambient', None) # 从 sim_params 获取环境温度
        chart_title = f'加速阶段部件温度随车速变化轨迹 ({self.sim_params.get("v_start", "N/A")}到{self.sim_params.get("v_end","N/A")} km/h)'
        print("\nStart---------------------------------------------------")
        print(f"--- 图表: {chart_title} ---")
        print("--- 以下为此图表内各项数据的平均值 (加速阶段) ---")
        print("--- Average Values for Temperature vs. Speed (Acceleration) Plot ---")
        if ramp_up_index > 0 and len(data['v_vehicle_profile']) > ramp_up_index :
            v_accel = data['v_vehicle_profile'][0:ramp_up_index + 1]
            T_motor_accel = data['T_motor'][0:ramp_up_index + 1]
            T_inv_accel = data['T_inv'][0:ramp_up_index + 1]
            T_batt_accel = data['T_batt'][0:ramp_up_index + 1]
            T_cabin_accel = data['T_cabin'][0:ramp_up_index + 1]
            T_coolant_accel = data['T_coolant'][0:ramp_up_index + 1]


            print(f"Average Motor Temperature (Accel): {np.mean(T_motor_accel):.2f} °C")
            plt.plot(v_accel, T_motor_accel, label='电机温度 (°C)', color='blue', marker='.', markersize=1, linestyle='-')

            print(f"Average Inverter Temperature (Accel): {np.mean(T_inv_accel):.2f} °C")
            plt.plot(v_accel, T_inv_accel, label='逆变器温度 (°C)', color='orange', marker='.', markersize=1, linestyle='-')

            print(f"Average Battery Temperature (Accel): {np.mean(T_batt_accel):.2f} °C")
            plt.plot(v_accel, T_batt_accel, label='电池温度 (°C)', color='green', marker='.', markersize=1, linestyle='-')

            print(f"Average Cabin Temperature (Accel): {np.mean(T_cabin_accel):.2f} °C")
            plt.plot(v_accel, T_cabin_accel, label='座舱温度 (°C)', color='red', marker='.', markersize=1, linestyle='-')

            print(f"Average Coolant Temperature (Accel): {np.mean(T_coolant_accel):.2f} °C")
            plt.plot(v_accel, T_coolant_accel, label='冷却液温度 (°C)', color='purple', marker='.', markersize=1, linestyle='-', alpha=0.6)

            plt.axhline(self.sim_params['T_motor_target'], color='magenta', linestyle='--', alpha=0.7, label=f'电机/逆变器目标 ({self.sim_params["T_motor_target"]}°C)')

            T_ambient_values = np.full_like(v_accel, t_ambient)
            plt.plot(v_accel, T_ambient_values, label=f'环境温度 ({t_ambient}°C)', color='black', linestyle='-', alpha=1.0)

            plt.axhline(self.sim_params['T_cabin_target'], color='red', linestyle='--', alpha=0.7, label=f'座舱目标 ({self.sim_params["T_cabin_target"]}°C)')
            plt.xlabel('车速 (km/h)', fontsize=self.common_settings['axis_label_fs'])
            plt.ylabel('温度 (°C)', fontsize=self.common_settings['axis_label_fs'])
            plt.xticks(fontsize=self.common_settings['tick_label_fs'])
            plt.yticks(fontsize=self.common_settings['tick_label_fs'])
            plt.title(f'加速阶段部件温度随车速变化轨迹 ({self.sim_params.get("v_start", "N/A")}到{self.sim_params.get("v_end","N/A")} km/h)', fontsize=self.common_settings['title_fs'])
            
            from collections import OrderedDict
            handles, labels = plt.gca().get_legend_handles_labels()
            by_label = OrderedDict(zip(labels, handles))
            plt.legend(by_label.values(), by_label.keys(), loc='best', fontsize=self.common_settings['legend_font_size'])
            
            plt.grid(True)
            if len(v_accel) > 1 :
                plt.xlim(left=min(v_accel), right=max(v_accel))
            elif len(v_accel) == 1:
                plt.xlim(left=v_accel[0]-5, right=v_accel[0]+5)

            plt.tight_layout()
            filename = os.path.join(self.output_dir, "plot_temp_vs_speed_accel.png")
            plt.savefig(filename, dpi=self.common_settings['dpi'])
            plt.close()
            print(f"Saved: {filename}")#输出保存图片名称
            print("Finished----------------------------------------------------\n")
        else:
            print("Warning: No or insufficient acceleration phase data to generate plot_temp_vs_speed_accel and print averages.")

    def plot_temp_at_const_speed(self):
        """
        部件温度变化
        Plots temperatures during constant speed phase and prints their average values.
        """
        plt.figure(figsize=self.common_settings['figure_size'])
        data = self.prepared_data
        ramp_up_steps = int(self.sim_params['ramp_up_time_sec'] / self.sim_params.get('dt', 1)) if self.sim_params.get('dt', 1) > 0 else 0
        const_speed_start_index = min(ramp_up_steps + 1, len(self.time_minutes))
        chart_title = f'部件温度变化 (匀速 {self.sim_params.get("v_end","N/A")} km/h 阶段)'
        print("\nStart---------------------------------------------------")
        print(f"--- 图表: {chart_title} ---")
        print("--- 以下为此图表内各项数据的平均值 (匀速阶段) ---")
        print("--- Average Values for Temperature at Constant Speed Plot ---")
        if const_speed_start_index < len(self.time_minutes):
            time_const_speed_minutes = self.time_minutes[const_speed_start_index:]

            if len(time_const_speed_minutes) > 0:
                _ensure = SimulationPlotter._ensure_profile_length
                T_motor_const_speed = _ensure(data['T_motor'][const_speed_start_index:], len(time_const_speed_minutes))
                T_inv_const_speed = _ensure(data['T_inv'][const_speed_start_index:], len(time_const_speed_minutes))
                T_batt_const_speed = _ensure(data['T_batt'][const_speed_start_index:], len(time_const_speed_minutes))
                T_cabin_const_speed = _ensure(data['T_cabin'][const_speed_start_index:], len(time_const_speed_minutes))
                T_coolant_const_speed = _ensure(data['T_coolant'][const_speed_start_index:], len(time_const_speed_minutes))


                print(f"Average Motor Temperature (Const Speed): {np.mean(T_motor_const_speed):.2f} °C")
                plt.plot(time_const_speed_minutes, T_motor_const_speed, label='电机温度 (°C)', color='blue')

                print(f"Average Inverter Temperature (Const Speed): {np.mean(T_inv_const_speed):.2f} °C")
                plt.plot(time_const_speed_minutes, T_inv_const_speed, label='逆变器温度 (°C)', color='orange')

                print(f"Average Battery Temperature (Const Speed): {np.mean(T_batt_const_speed):.2f} °C")
                plt.plot(time_const_speed_minutes, T_batt_const_speed, label='电池温度 (°C)', color='green')

                print(f"Average Cabin Temperature (Const Speed): {np.mean(T_cabin_const_speed):.2f} °C")
                plt.plot(time_const_speed_minutes, T_cabin_const_speed, label='座舱温度 (°C)', color='red')

                print(f"Average Coolant Temperature (Const Speed): {np.mean(T_coolant_const_speed):.2f} °C")
                plt.plot(time_const_speed_minutes, T_coolant_const_speed, label='冷却液温度 (°C)', color='purple', alpha=0.6)
                
                ax_temp = plt.gca()
                ax_temp.axhline(self.sim_params['T_motor_target'], color='magenta', linestyle='--', alpha=0.7, label=f'电机/逆变器目标 ({self.sim_params["T_motor_target"]}°C)')


                ax_temp.axhline(self.sim_params['T_cabin_target'], color='red', linestyle='--', alpha=0.7, label=f'座舱目标 ({self.sim_params["T_cabin_target"]}°C)')
                ax_temp.axhline(self.sim_params['T_ambient'], color='black', linestyle='-', alpha=1, label=f'环境温度 ({self.sim_params["T_ambient"]}°C)')
                plt.xlabel('时间 (分钟)', fontsize=self.common_settings['axis_label_fs'])
                plt.ylabel('温度 (°C)', fontsize=self.common_settings['axis_label_fs'])
                plt.xticks(fontsize=self.common_settings['tick_label_fs'])
                plt.yticks(fontsize=self.common_settings['tick_label_fs'])
                plt.title(f'部件温度变化 (匀速 {self.sim_params.get("v_end","N/A")} km/h 阶段)', fontsize=self.common_settings['title_fs'])
                
                from collections import OrderedDict
                handles, labels = ax_temp.get_legend_handles_labels()
                by_label = OrderedDict(zip(labels, handles))
                ax_temp.legend(by_label.values(), by_label.keys(), loc='best', fontsize=self.common_settings['legend_font_size'])
                plt.grid(True)
                if len(time_const_speed_minutes) > 0:
                    plt.xlim(left=time_const_speed_minutes[0], right=self.time_minutes[-1])

                plt.tight_layout()
                filename = os.path.join(self.output_dir, "plot_temp_at_const_speed.png")
                plt.savefig(filename, dpi=self.common_settings['dpi'])
                plt.close()
                print(f"Saved: {filename}")
                print("Finished----------------------------------------------------\n")
            else:
                print("Warning: No data points in constant speed phase for plot_temp_at_const_speed and printing averages.")
        else:
            print("Warning: No constant speed phase data found to generate plot_temp_at_const_speed and print averages.")
       

    def plot_total_heat_balance(self):
        """
        总热负荷功率 vs 总散热系统散热功率
        Plots total heat load vs. total heat rejection and prints their average values.
        """
        plt.figure(figsize=self.common_settings['figure_size'])
        data = self.prepared_data

        # 总热负荷功率的计算保持不变
        Q_total_heat_load = data['Q_gen_motor_profile'] + data['Q_gen_inv_profile'] + \
                            data['Q_gen_batt_profile'] + data['Q_cabin_load_profile']

        q_ltr = data.get('Q_LTR_to_ambient_log', np.zeros_like(self.time_minutes))
        q_chiller = data.get('Q_coolant_to_chiller_log', np.zeros_like(self.time_minutes))
        q_cabin_evap = data.get('Q_cabin_evap_cooling_log', np.zeros_like(self.time_minutes))
        min_len = min(len(q_ltr), len(q_chiller), len(q_cabin_evap))
        q_ltr = q_ltr[:min_len]
        q_chiller = q_chiller[:min_len]
        q_cabin_evap = q_cabin_evap[:min_len]
        
        Q_total_heat_rejection_system_effort = q_ltr + q_chiller + q_cabin_evap
        print("\nStart---------------------------------------------------")

        Q_total_heat_load_plot = Q_total_heat_load[:min_len]
        print(f"Average Total Heat Load: {np.mean(Q_total_heat_load_plot):.2f} W")
        plt.plot(self.time_minutes[:min_len], Q_total_heat_load_plot, label='总热负荷功率 (W)', color='maroon', linestyle='-')
        chart_title = '总热负荷功率 vs 总散热系统散热功率'
        print(f"--- 图表: {chart_title} ---")
        print("--- 以下为此图表内各项数据的平均值 ---")
        print("--- Average Values for Total Heat Balance Plot ---")


        print(f"Average Total Heat Rejection (System Effort): {np.mean(Q_total_heat_rejection_system_effort):.2f} W")
        plt.plot(self.time_minutes[:min_len], Q_total_heat_rejection_system_effort, label='总散热系统移除功率 (W)', color='darkcyan', linestyle='--')
        plt.xlabel('时间 (分钟)', fontsize=self.common_settings['axis_label_fs'])
        plt.ylabel('功率 (W)', fontsize=self.common_settings['axis_label_fs'])
        plt.xticks(fontsize=self.common_settings['tick_label_fs'])
        plt.yticks(fontsize=self.common_settings['tick_label_fs'])
        current_xlim_right = self.sim_params['sim_duration']/60
        if min_len < len(self.time_minutes) and min_len > 0:
            current_xlim_right = self.time_minutes[min_len-1]
        plt.xlim(left=0, right=current_xlim_right)

        max_load_val = np.max(Q_total_heat_load_plot) if len(Q_total_heat_load_plot) > 0 else 0
        max_rejection_val = np.max(Q_total_heat_rejection_system_effort) if len(Q_total_heat_rejection_system_effort) > 0 else 0
        overall_max_power = max(max_load_val, max_rejection_val)
        plt.ylim(0, overall_max_power * 1.1 if overall_max_power > 0 else 100)

        plt.title('总热负荷功率 vs 总散热系统散热功率', fontsize=self.common_settings['title_fs'])
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.legend(loc='best', fontsize=self.common_settings['legend_font_size'])
        plt.tight_layout()
        filename = os.path.join(self.output_dir, "plot_total_heat_balance.png")
        plt.savefig(filename, dpi=self.common_settings['dpi'])
        plt.close()
        print(f"Saved: {filename}")
        print("Finished----------------------------------------------------\n")

    def plot_ac_chiller_specific(self):
        """
        空调压缩机总电耗与动力总成Chiller状态
        Plots AC Compressor Power and Powertrain Chiller Status specifically, and prints their average values.
        """
        fig, ax1 = plt.subplots(figsize=self.common_settings['figure_size'])
        data = self.prepared_data
        time_minutes = self.time_minutes
        max_time = np.max(time_minutes) if len(time_minutes) > 0 else 1
        ax1.set_xlim(0, max_time)
        print("\nStart---------------------------------------------------")
        chart_title = '空调压缩机总电耗与动力总成Chiller状态'
        print(f"--- 图表: {chart_title} ---")
        print("--- 以下为此图表内各项数据的平均值 ---")
        print("--- Average Values for AC Chiller Specific Plot ---")
        

        print(f"Average Powertrain Chiller Status: {np.mean(data['chiller_active_log']):.2f} (1=ON)") # Duplicate from cooling_system_operation
        ax1.plot(time_minutes, data['chiller_active_log'], label='动力总成Chiller状态 (1=ON)', color='black', drawstyle='steps-post', alpha=0.7)
        
        ax1.set_xlabel('时间 (分钟)', fontsize=self.common_settings['axis_label_fs'])
        ax1.set_ylabel('动力总成Chiller状态', color='black', fontsize=self.common_settings['axis_label_fs'])
        ax1.tick_params(axis='y', labelcolor='black', labelsize=self.common_settings['tick_label_fs'])
        ax1.tick_params(axis='x', labelsize=self.common_settings['tick_label_fs'])
        ax1.set_ylim(0, 1.1)
        ax1.grid(True, linestyle=':', alpha=0.6)

        ax2 = ax1.twinx()
        if data['P_comp_elec_profile'] is not None and len(data['P_comp_elec_profile']) > 0:
            print(f"Average AC Compressor Total Electrical Power: {np.mean(data['P_comp_elec_profile']):.2f} W") # Duplicate
        ax2.plot(time_minutes, data['P_comp_elec_profile'], label='空调压缩机总电耗 (W)', color='cyan', alpha=0.8, linestyle='-')

        ax2.set_ylabel('空调压缩机总电耗 (W)', color='cyan', fontsize=self.common_settings['axis_label_fs'])
        ax2.tick_params(axis='y', labelcolor='cyan', labelsize=self.common_settings['tick_label_fs'])
        min_power_y2 = 0
        max_val_p_comp = 0
        if data['P_comp_elec_profile'] is not None and len(data['P_comp_elec_profile']) > 0:
            max_val_p_comp = np.max(data['P_comp_elec_profile'])
        ax2.set_ylim(min_power_y2, max_val_p_comp * 1.1 if max_val_p_comp > 0 else 100)

        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        if labels or labels2:
            ax2.legend(lines + lines2, labels + labels2, loc='best', fontsize=self.common_settings['legend_font_size'])

        plt.title('空调压缩机总电耗与动力总成Chiller状态', fontsize=self.common_settings['title_fs'])
        plt.tight_layout()
        filename = os.path.join(self.output_dir, "plot_ac_chiller_specific.png")
        plt.savefig(filename, dpi=self.common_settings['dpi'])
        plt.close(fig)
        print(f"Saved: {filename}")#输出保存图片名称
        print("Finished----------------------------------------------------\n")


    def generate_all_plots(self):
        """
        生成图的函数
        Generates and saves all simulation plots by calling individual plotting methods.
        Returns a dictionary of all found local extrema for relevant temperatures.
        """
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created directory: {self.output_dir}")

        self.plot_temperatures() 
        self.plot_cooling_system_operation()
        self.plot_vehicle_speed()
        self.plot_powertrain_heat_generation()
        self.plot_battery_power()
        self.plot_cabin_cooling_power()
        self.plot_temp_vs_speed_accel()
        self.plot_temp_at_const_speed()
        self.plot_total_heat_balance()
        self.plot_ac_chiller_specific()

        print("\nAll plots generation attempt finished.")
        print("Average values for each plot have been printed above the plot generation messages.")
        return self.all_extrema_data