# results_analyzer.py
# 该模块负责对仿真引擎 (simulation_engine.py) 生成的原始结果数据进行后处理、分析和准备，
# 以便进行可视化 (plotting.py) 和结果解读。
# 主要功能包括：
# 1. 计算派生数据：例如，根据车速和部件效率计算逆变器输入功率、电池总输出功率等。
# 2. 数据结构转换：将原始的、可能分散的数据整理成更适合绘图和分析的结构化格式。
# 3. 分析特定事件：例如，识别Chiller（冷却器）状态的转变点。
# 4. 计算统计值：例如，计算各个物理量在仿真期间的平均值。
# 5. 提取极值：供绘图模块标记和分析模块打印。

import numpy as np # 导入NumPy库，用于高效的数值计算，特别是数组操作
import heat_vehicle as hv # 导入自定义的 heat_vehicle 模块，用于计算车辆行驶相关的功率和热量
from plotting import SimulationPlotter # 导入 SimulationPlotter 类，主要用于调用其静态方法 _ensure_profile_length

class ResultsAnalyzer: # 定义 ResultsAnalyzer 类
    """
    ResultsAnalyzer 类：
    用于处理和分析车辆热管理仿真结果的核心类。
    它接收来自 SimulationEngine 的原始仿真数据和仿真参数 (sp) 对象，
    并提供方法来派生新数据、格式化数据以供绘图，以及执行初步的分析。
    """
    def __init__(self, simulation_results, sp): #类的构造函数，接收仿真结果和仿真参数作为输入
        """
        初始化 ResultsAnalyzer 对象。

        参数:
            simulation_results (dict): 从 SimulationEngine 的 run_simulation 方法返回的原始仿真结果字典。
                                       包含时间序列、各部件温度历史、产热历史、冷却系统日志等。
            sp (module): simulation_parameters 模块的实例，包含了从配置文件加载和派生的所有仿真参数。
                         用于访问配置值，如目标温度、部件特性、仿真设置等。
        """
        self.raw_results = simulation_results # 存储原始仿真结果的引用
        self.sp = sp # 存储仿真参数对象的引用
        # 根据仿真总时长和时间步长计算总的仿真步数
        # 注意：通常历史数组的长度是 n_steps + 1 (包含初始 t=0 时刻)
        self.n_steps = int(sp.sim_duration / sp.dt) # 计算仿真步数
        self.time_sim = simulation_results["time_sim"] # 获取仿真的时间序列数组
        self.processed_data = {} # 初始化一个空字典，用于存储后处理过的数据

    def post_process_data(self): # 定义后处理数据的方法
        """
        对原始仿真数据进行后处理，计算派生数据，并将所有数据整理成结构化的字典，
        方便后续的绘图和分析。

        派生数据计算主要包括：
        - P_inv_in_profile_hist: 逆变器输入功率历史。根据车速剖面、车辆参数和电机/逆变器效率计算。
        - P_elec_total_profile_hist: 电池总输出电功率历史。等于逆变器输入功率加上空调压缩机的电功率。

        数据结构整理包括：
        - 将原始结果中的各个数据流（温度、功率、热量、日志等）提取并组织到 self.processed_data 字典中，
          使用更清晰的键名，并确保数据格式统一。
        - 创建一个 sim_params_dict，从 sp 对象中提取绘图和分析时可能需要的关键参数，
          使其能方便地传递给绘图模块。

        返回:
            dict: 包含所有处理后数据的字典 (self.processed_data)。
                  这个字典将作为 SimulationPlotter 类的主要数据输入。
        """
        # 从原始结果中获取车速剖面和空调压缩机电功率剖面
        v_vehicle_profile = self.raw_results['speed_profile'] # 获取车速剖面数据
        P_comp_elec_profile = self.raw_results['ac_power_log'] # 获取空调压缩机电功率剖面数据
        n_points = len(v_vehicle_profile) # 获取数据点的数量，应等于 n_steps + 1

        # --- 计算逆变器输入功率 (P_inv_in_profile_hist) ---
        P_inv_in_profile_hist = np.zeros(n_points) # 初始化存储逆变器输入功率历史的数组
        for idx in range(n_points): # 遍历每个时间点
            # 1. 计算当前车速下，车轮处克服行驶阻力所需的功率
            P_wheel_i = hv.P_wheel_func(v_vehicle_profile[idx], self.sp.m_vehicle, self.sp.T_ambient) # 计算车轮功率
            # 2. 根据车轮功率和电机效率，计算电机的输入功率
            P_motor_in_i = hv.P_motor_func(P_wheel_i, self.sp.eta_motor) # 计算电机输入功率
            # 3. 根据电机输入功率和逆变器效率，计算逆变器的输入功率
            #    注意处理逆变器效率为0的情况，防止除零错误
            P_inv_in_profile_hist[idx] = P_motor_in_i / self.sp.eta_inv if self.sp.eta_inv > 0 else 0 # 计算逆变器输入功率，并处理效率为0的情况

        # --- 计算电池总输出电功率 (P_elec_total_profile_hist) ---
        # 假设电池总输出功率等于驱动用电（逆变器输入）加上空调压缩机用电
        # 注意：更精确的模型可能还会包括其他附件用电，如LTR风扇等，这里是简化处理。
        # 在 simulation_engine 中计算电池产热时，P_elec_total_batt_out 包含了 LTR 风扇功率。
        # 这里的 P_elec_total_profile_hist 主要用于绘图展示电池输出的主要构成。
        P_elec_total_profile_hist = P_inv_in_profile_hist + P_comp_elec_profile # 计算电池总输出电功率

        # --- 整理和填充 processed_data 字典 ---
        # 将原始数据和派生数据存入 self.processed_data，使用易于理解的键名
        self.processed_data['time_data'] = self.raw_results['time_sim'] # 存储时间序列数据
        self.processed_data['temperatures'] = self.raw_results['temperatures_data'] # 存储各部件温度历史数据
        self.processed_data['ac_power_log'] = self.raw_results['ac_power_log'] # 存储空调压缩机电功率历史数据
        # 座舱蒸发器实际制冷功率历史
        self.processed_data['cabin_cool_power_log'] = self.raw_results['cooling_system_logs']['Q_cabin_evap_cooling'] # 存储座舱蒸发器实际制冷功率历史数据
        self.processed_data['speed_profile'] = self.raw_results['speed_profile'] # 存储车速历史数据
        self.processed_data['heat_gen_profiles'] = self.raw_results['heat_gen_data'] # 存储各部件产热/负荷历史数据
        # 电池相关功率历史
        self.processed_data['battery_power_profiles'] = { # 存储电池相关功率历史数据
            'inv_in': P_inv_in_profile_hist,    # 逆变器输入功率 (驱动用电)
            'comp_elec': P_comp_elec_profile,   # 空调压缩机电功率
            'total_elec': P_elec_total_profile_hist # (简化的)电池总输出功率
        }
        self.processed_data['cooling_system_logs'] = self.raw_results['cooling_system_logs'] # 存储冷却系统详细日志数据

        # --- 创建一个包含关键仿真参数的字典 (sim_params_dict) ---
        # 这个字典方便将参数传递给绘图模块，避免直接传递整个 sp 对象
        self.processed_data['sim_params_dict'] = { # 创建包含关键仿真参数的字典
            # 环境和目标温度
            'T_ambient': self.sp.T_ambient, # 环境温度
            'T_motor_target': self.sp.T_motor_target, # 电机目标温度
            'T_inv_target': self.sp.T_inv_target, # 逆变器目标温度
            'T_batt_target_high': self.sp.T_batt_target_high, # 电池高温启动Chiller的目标
            'T_batt_stop_cool': self.sp.T_batt_stop_cool,     # 电池低温停止Chiller的目标
            'T_cabin_target': self.sp.T_cabin_target, # 座舱目标温度
            # 速度剖面参数
            'v_start': self.sp.v_start, # 初始速度
            'v_end': self.sp.v_end, # 最终速度
            'ramp_up_time_sec': self.sp.ramp_up_time_sec, # 加速时间
            # 仿真基本参数
            'sim_duration': self.sp.sim_duration, # 仿真总时长
            'dt': self.sp.dt, # 时间步长
            # 效率参数
            'eta_comp_drive': self.sp.eta_comp_drive, # 压缩机驱动效率
            # 座舱冷却控制参数
            'cabin_cooling_temp_thresholds': self.sp.cabin_cooling_temp_thresholds, # 座舱冷却温度阈值
            'cabin_cooling_power_levels': self.sp.cabin_cooling_power_levels, # 座舱冷却功率等级
            # 绘图参数
            'figure_width_inches': self.sp.figure_width_inches, # 图表宽度
            'figure_height_inches': self.sp.figure_height_inches, # 图表高度
            'figure_dpi': self.sp.figure_dpi, # 图表DPI
            'legend_font_size': self.sp.legend_font_size, # 图例字体大小
            'axis_label_font_size': self.sp.axis_label_font_size, # 坐标轴标签字体大小
            'tick_label_font_size': self.sp.tick_label_font_size, # 刻度标签字体大小
            'title_font_size': self.sp.title_font_size, # 图表标题字体大小
            # 低温散热器 (LTR) 和低温冷凝器 (LCC) 相关参数
            # 使用 getattr 以处理这些参数在旧版配置文件中可能不存在的情况，提供 None作为默认值
            'UA_LTR_max': getattr(self.sp, 'UA_LTR_max', None), # LTR最大UA值
            'LTR_effectiveness_levels': getattr(self.sp, 'LTR_effectiveness_levels', None), # LTR效能等级数量
            # 'LTR_effectiveness_factors' 似乎在 sp 中没有直接定义，而是派生或直接使用 LTR_UA_values_at_levels
            'LTR_coolant_temp_thresholds': getattr(self.sp, 'LTR_coolant_temp_thresholds', None), # LTR冷却液温度阈值
            'UA_coolant_LCC': getattr(self.sp, 'UA_coolant_LCC', None), # 冷却液与LCC的UA值
        }
        return self.processed_data # 返回处理后的数据字典

    def analyze_chiller_transitions(self): # 定义分析Chiller状态转变的方法
        """
        分析动力总成Chiller（冷却器）状态的转变事件。
        遍历Chiller激活状态日志，识别从 OFF 到 ON 以及从 ON 到 OFF 的转变点，
        并打印这些转变发生的时间（秒和分钟）。
        """
        print("\n--- Chiller 状态 Transition Points (Analyzed) ---") # 打印分析标题
        # 从原始结果中获取动力总成Chiller的激活状态日志和时间序列
        powertrain_chiller_active_log = self.raw_results['cooling_system_logs']['chiller_active'] # 获取Chiller激活状态日志
        time_sim = self.raw_results['time_sim'] # 获取时间序列数据
        n_points = len(powertrain_chiller_active_log) # 数据点总数

        if n_points <= 1: # 如果数据点不足以判断转变，则直接返回
            print("  Simulation has less than 2 steps, cannot detect transitions.") # 打印提示信息
            return # 返回

        found_transitions = False # 标记是否找到任何转变事件，初始化为False
        # 从第二个点开始遍历 (索引k=1)，与前一个点 (k-1) 进行比较
        for k in range(1, n_points): # 遍历Chiller状态日志
            current_chiller_state = powertrain_chiller_active_log[k] # 当前点的Chiller状态
            previous_chiller_state = powertrain_chiller_active_log[k-1] # 前一个点的Chiller状态

            # 如果当前状态与前一状态不同，则发生了转变
            if current_chiller_state != previous_chiller_state: # 判断Chiller状态是否发生转变
                transition_time_sec = time_sim[k] # 转变发生的时间 (秒)
                transition_time_min = transition_time_sec / 60 # 转变发生的时间 (分钟)
                if current_chiller_state == 1 and previous_chiller_state == 0: # 从 OFF (0) 转变为 ON (1)
                    print(f"  Transition: OFF (0) -> ON (1) at Time: {transition_time_sec:.2f} s ({transition_time_min:.2f} min)") # 打印转变信息
                    found_transitions = True # 标记已找到转变
                elif current_chiller_state == 0 and previous_chiller_state == 1: # 从 ON (1) 转变为 OFF (0)
                    print(f"  Transition: ON (1) -> OFF (0) at Time: {transition_time_sec:.2f} s ({transition_time_min:.2f} min)") # 打印转变信息
                    found_transitions = True # 标记已找到转变

        if not found_transitions: # 如果整个仿真过程中没有Chiller状态转变
            print("  No powertrain chiller state transitions recorded during the simulation.") # 打印提示信息

    def print_average_values(self): # 定义打印各项数据平均值的方法
        """
        计算并打印仿真期间各项关键数据的平均值。
        这为快速评估系统在整个仿真过程中的总体表现提供了依据。
        打印内容包括：
        - 各部件的平均温度。
        - 制冷系统相关的平均功率/热量（压缩机电耗、LTR散热、LCC吸热、Chiller吸热）。
        - 平均车速。
        - 各部件的平均产热/负荷功率。
        - 电池相关的平均功率（驱动用电、压缩机用电、总输出）。
        - 平均座舱蒸发器制冷功率。
        - 平均总热负荷与总散热/制冷功率的对比。
        """
        print("\n--- 各项数据平均值 ---") # 打印标题
        processed_data = self.processed_data # 获取已处理的数据字典

        # --- 平均温度 ---
        if 'temperatures' in processed_data: # 检查是否存在温度数据
            print("\n  平均温度 (°C):") # 打印平均温度标题
            for component, temp_data in processed_data['temperatures'].items(): # 遍历各部件温度数据
                if temp_data is not None and len(temp_data) > 0: # 确保数据存在且不为空
                    avg_temp = np.mean(temp_data) # 计算平均值
                    print(f"    {component.capitalize()}温度: {avg_temp:.2f} °C") # 打印部件平均温度

        # --- 制冷系统运行相关平均值 ---
        print("\n  制冷系统运行相关平均值:") # 打印制冷系统运行相关平均值标题
        # 空调压缩机总电耗
        if 'ac_power_log' in processed_data and processed_data['ac_power_log'] is not None and len(processed_data['ac_power_log']) > 0: # 检查空调压缩机电耗数据是否存在
            avg_ac_power = np.mean(processed_data['ac_power_log']) # 计算平均空调压缩机电耗
            print(f"    空调压缩机总电耗: {avg_ac_power:.2f} W") # 打印平均空调压缩机电耗

        cooling_logs = processed_data.get('cooling_system_logs', {}) # 获取冷却系统日志子字典
        # 外置散热器 (LTR) 实际散热功率
        q_ltr_to_ambient = cooling_logs.get('Q_LTR_to_ambient') # 获取LTR实际散热功率数据
        if q_ltr_to_ambient is not None and len(q_ltr_to_ambient) > 0: # 检查数据是否存在
            avg_q_ltr = np.mean(q_ltr_to_ambient) # 计算平均LTR散热功率
            print(f"    外置散热器(LTR)实际散热功率: {avg_q_ltr:.2f} W") # 打印平均LTR散热功率

        # 低温冷凝器 (LCC) 从制冷剂吸收并传递给冷却液的热量
        q_coolant_from_lcc = cooling_logs.get('Q_coolant_from_LCC') # 获取LCC传递给冷却液的热量数据
        if q_coolant_from_lcc is not None and len(q_coolant_from_lcc) > 0: # 检查数据是否存在
            avg_q_lcc = np.mean(q_coolant_from_lcc) # 计算平均LCC传递热量
            print(f"    LCC从制冷剂吸收热量(传递给冷却液): {avg_q_lcc:.2f} W") # 打印平均LCC传递热量，调整描述更准确

        # 动力总成冷却器 (Chiller) 从冷却液吸收的热量
        q_coolant_to_chiller = cooling_logs.get('Q_coolant_to_chiller') # 获取Chiller从冷却液吸收的热量数据
        if q_coolant_to_chiller is not None and len(q_coolant_to_chiller) > 0: # 检查数据是否存在
            avg_q_chiller = np.mean(q_coolant_to_chiller) # 计算平均Chiller吸收热量
            print(f"    冷却液到Chiller的热量: {avg_q_chiller:.2f} W") # 打印平均Chiller吸收热量

        # --- 平均车速 ---
        if 'speed_profile' in processed_data and processed_data['speed_profile'] is not None and len(processed_data['speed_profile']) > 0: # 检查车速数据是否存在
            avg_speed = np.mean(processed_data['speed_profile']) # 计算平均车速
            print(f"\n  平均车速: {avg_speed:.2f} km/h") # 打印平均车速

        # --- 平均产热功率 ---
        if 'heat_gen_profiles' in processed_data: # 检查产热功率数据是否存在
            print("\n  平均产热功率 (W):") # 打印平均产热功率标题
            # 定义一个映射，用于将内部键名转换为更易读的显示名称
            name_map_heat = { # 定义产热部件名称映射
                'motor': '电机产热',
                'inv': '逆变器产热',
                'batt': '电池产热',
                'cabin_load': '座舱热负荷'
            }
            for component, heat_data in processed_data['heat_gen_profiles'].items(): # 遍历各部件产热数据
                if heat_data is not None and len(heat_data) > 0: # 确保数据存在且不为空
                    avg_heat = np.mean(heat_data) # 计算平均产热功率
                    display_name = name_map_heat.get(component, component.capitalize()) # 获取显示名称
                    print(f"    {display_name}: {avg_heat:.2f} W") # 打印部件平均产热功率

        # --- 平均电池相关功率 ---
        if 'battery_power_profiles' in processed_data: # 检查电池相关功率数据是否存在
            print("\n  平均电池相关功率 (W):") # 打印平均电池相关功率标题
            # 定义一个映射，用于将内部键名转换为更易读的显示名称
            name_map_battery = { # 定义电池功率名称映射
                'inv_in': '驱动用电功率 (逆变器输入)',
                'comp_elec': '空调压缩机电功率', # 注意：这个值与上面的 avg_ac_power 重复
                'total_elec': '总电池输出功率 (驱动+压缩机)' # 描述这个特定计算的含义
            }
            for profile_name, power_data in processed_data['battery_power_profiles'].items(): # 遍历电池相关功率数据
                if power_data is not None and len(power_data) > 0: # 确保数据存在且不为空
                    avg_power = np.mean(power_data) # 计算平均功率
                    display_name = name_map_battery.get(profile_name, profile_name.capitalize()) # 获取显示名称
                    # 避免重复打印压缩机功率，因为它已在 "制冷系统运行相关平均值" 部分打印
                    if profile_name != 'comp_elec' or 'ac_power_log' not in processed_data: # 避免重复打印
                         print(f"    {display_name}: {avg_power:.2f} W") # 打印平均功率

        # --- 平均座舱蒸发器制冷功率 ---
        if 'cabin_cool_power_log' in processed_data and processed_data['cabin_cool_power_log'] is not None and len(processed_data['cabin_cool_power_log']) > 0: # 检查座舱蒸发器制冷功率数据是否存在
            avg_cabin_cool_power = np.mean(processed_data['cabin_cool_power_log']) # 计算平均座舱蒸发器制冷功率
            print(f"\n  平均座舱蒸发器制冷功率: {avg_cabin_cool_power:.2f} W") # 打印平均座舱蒸发器制冷功率

        # --- 计算并打印平均总热负荷 vs 总散热/制冷功率 ---
        # 这是一个宏观的热平衡检查
        try: # 使用try-except块处理可能的错误
            # 获取各部件的产热/负荷数据
            q_motor = processed_data['heat_gen_profiles']['motor'] # 获取电机产热数据
            q_inv = processed_data['heat_gen_profiles']['inv'] # 获取逆变器产热数据
            q_batt = processed_data['heat_gen_profiles']['batt'] # 获取电池产热数据
            q_cabin_load = processed_data['heat_gen_profiles']['cabin_load'] # 获取座舱热负荷数据

            # 获取散热/制冷系统从热源处移除的热量数据 (使用更新后的键名)
            q_ltr_cb = cooling_logs.get('Q_LTR_to_ambient')      # LTR 散热到环境
            q_pt_chiller_cb = cooling_logs.get('Q_coolant_to_chiller') # Chiller 从冷却液吸收热量
            q_cabin_evap_cb = cooling_logs.get('Q_cabin_evap_cooling') # 座舱蒸发器从座舱空气吸收热量
            # 注意：LCC 的热量 Q_coolant_from_LCC 是从制冷剂流向冷却液的，对于总热平衡来说，
            # 它不直接是 "散热" 到外部，而是系统内部的热量转移。
            # 总热负荷应指进入系统的净热量，总散热应指系统排到外界的净热量。
            # 因此，这里 total_heat_rejection_cooling 主要关注直接排外的LTR和通过制冷循环间接排外的部分。

            # 检查所有需要的数据是否都存在且不为空
            all_components_present = all( # 检查所有必需的数据是否存在
                d is not None and len(d) > 0 for d in
                [q_motor, q_inv, q_batt, q_cabin_load, q_ltr_cb, q_pt_chiller_cb, q_cabin_evap_cb]
            )

            if all_components_present: # 如果所有数据都存在
                target_len = len(self.time_sim) # 获取标准长度

                # 确保所有数组长度一致，不足则用 SimulationPlotter 的静态方法补齐
                # 这是为了防止因数据记录问题导致数组长度不一致而无法进行元素级运算
                q_motor_arr = SimulationPlotter._ensure_profile_length(np.array(q_motor), target_len) # 统一电机产热数组长度
                q_inv_arr = SimulationPlotter._ensure_profile_length(np.array(q_inv), target_len) # 统一逆变器产热数组长度
                q_batt_arr = SimulationPlotter._ensure_profile_length(np.array(q_batt), target_len) # 统一电池产热数组长度
                q_cabin_load_arr = SimulationPlotter._ensure_profile_length(np.array(q_cabin_load), target_len) # 统一座舱热负荷数组长度
                q_ltr_arr = SimulationPlotter._ensure_profile_length(np.array(q_ltr_cb), target_len) # 统一LTR散热数组长度
                q_pt_chiller_arr = SimulationPlotter._ensure_profile_length(np.array(q_pt_chiller_cb), target_len) # 统一Chiller吸热数组长度
                q_cabin_evap_arr = SimulationPlotter._ensure_profile_length(np.array(q_cabin_evap_cb), target_len) # 统一座舱蒸发器吸热数组长度

                # 总产热/负荷 = 电机产热 + 逆变器产热 + 电池产热 + 座舱热负荷 (进入系统的总热量)
                total_heat_load = q_motor_arr + q_inv_arr + q_batt_arr + q_cabin_load_arr # 计算总产热/负荷
                # 总散热系统移除功率 = LTR直接散热 + Chiller从冷却液吸热(最终会通过冷凝器排到环境) + 座舱蒸发器吸热(最终会通过冷凝器排到环境)
                # 注意：q_pt_chiller_arr 和 q_cabin_evap_arr 是蒸发侧的吸热量，
                # 对应的冷凝侧放热量会更大 (等于吸热量+压缩机功)。
                # 更精确的 "总散热" 应考虑冷凝器的总放热。这里简化为蒸发侧吸热总量+LTR散热。
                total_heat_rejection_cooling_effort = q_ltr_arr + q_pt_chiller_arr + q_cabin_evap_arr # 计算总散热系统移除功率

                avg_total_load = np.mean(total_heat_load) # 平均总产热/负荷
                avg_total_rejection_cooling_effort = np.mean(total_heat_rejection_cooling_effort) # 平均总散热系统移除功率

                print("\n  平均总热负荷 vs 总散热系统移除功率 (W):") # 打印标题
                print(f"    总产热/负荷功率: {avg_total_load:.2f} W") # 打印平均总产热/负荷功率
                print(f"    总散热系统移除功率 (LTR吸热+Chiller吸热+CabinEvap吸热): {avg_total_rejection_cooling_effort:.2f} W") # 打印平均总散热系统移除功率
        except KeyError as e: # 捕获因缺少数据键导致的错误
            print(f"\n  注意: 无法计算平均总热平衡，缺少数据: {e}") # 打印错误信息
        except Exception as e: # 捕获其他计算错误
            print(f"\n  计算平均总热平衡时发生错误: {e}") # 打印错误信息

        print("\n--- 平均值打印结束 ---") # 打印结束信息
