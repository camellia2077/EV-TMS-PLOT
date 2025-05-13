# simulation_engine.py
import numpy as np
import heat_vehicle as hv
from heat_cabin_class import CabinHeatCalculator


class SimulationEngine:
    def __init__(self, sp, cop_value):
        self.sp = sp # import simulation_parameters as sp,在main函数中引用
        self.cop = cop_value #制冷循环性能系数
        self.n_steps = int(sp.sim_duration / sp.dt)#整数 计算整个仿真过程需要执行的总步数，仿真总时长/步长
        #np.linspace(start, stop, num) 函数的作用是在 start 和 stop（包含这两个端点）之间生成 num 个等间隔的点。
        #使用NumPy库的linspace函数创建了一个一维数组，该数组包含从0秒(仿真开始)到sp.sim_duration秒(仿真结束)之间所有离散的时间点。
        self.time_sim = np.linspace(0, sp.sim_duration, self.n_steps + 1)# + 1是因为平均分的点从0开始

        # --- 初始化温度历史数组 ---
        """
        因为仿真从t = 0开始,为了记录从仿真开始时刻 (t=0) 到仿真结束时刻 (t = self.n_steps * sp.dt) 的所有状态，我们需要 self.n_steps 个时间间隔，以及这些间隔的端点。
        这就意味着我们需要 self.n_steps + 1 个数据点来存储这些时刻的温度值。
        """
        #存储电机在每个离散时间点的温度值的
        self.T_motor_hist = np.zeros(self.n_steps + 1)
        self.T_inv_hist = np.zeros(self.n_steps + 1)
        self.T_batt_hist = np.zeros(self.n_steps + 1)
        self.T_cabin_hist = np.zeros(self.n_steps + 1)
        self.T_coolant_hist = np.zeros(self.n_steps + 1)

        # --- 控制状态 Logs ---
        self.powertrain_chiller_active_log = np.zeros(self.n_steps + 1)
        self.LTR_level_log = np.zeros(self.n_steps + 1)
        self.P_LTR_fan_actual_hist = np.zeros(self.n_steps + 1)
        self.LTR_effectiveness_log = np.zeros(self.n_steps + 1)

        # --- 热流量记录 ---
        # (这部分代码初始化用于存储仿真过程中各种热量流动情况的数组)
        # LTR (低温散热器) 的散热量历史记录数组
        self.Q_LTR_hist = np.zeros(self.n_steps + 1)
        # 从LCC(液体冷却冷凝器)到冷却液的热量历史记录数组
        self.Q_coolant_from_LCC_hist = np.zeros(self.n_steps + 1)
        # 冷却液到 Chiller的实际热量历史记录数组
        self.Q_coolant_chiller_actual_hist = np.zeros(self.n_steps + 1)
        self.Q_cabin_load_total_hist = np.zeros(self.n_steps + 1)
        self.Q_cabin_cool_actual_hist = np.zeros(self.n_steps + 1)

        # --- 产热记录 ---
        self.v_vehicle_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_motor_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_inv_profile_hist = np.zeros(self.n_steps + 1)
        self.Q_gen_batt_profile_hist = np.zeros(self.n_steps + 1)
        self.P_comp_elec_profile_hist = np.zeros(self.n_steps + 1)

        # --- 初始化 CabinHeatCalculator ---
        try:
            # 从 sp (simulation_parameters) 中获取 CabinHeatCalculator 所需的参数
            self.cabin_heat_calculator = CabinHeatCalculator(
                N_passengers=sp.N_passengers,
                v_air_internal_mps=sp.v_air_in_mps, # 确保 sp 中有 v_air_in_mps 且其含义正确
                A_body=sp.A_body,
                R_body=sp.R_body,
                A_glass=sp.A_glass,
                R_glass=sp.R_glass,
                SHGC=sp.SHGC,
                A_glass_sun=sp.A_glass_sun,
                W_out_summer=sp.W_out_summer,
                W_in_target=sp.W_in_target,
                fraction_fresh_air=sp.fresh_air_fraction,
                cp_air=sp.cp_air, # 可以从 sp 获取，或者使用 CabinHeatCalculator 中的默认值
                h_fg=getattr(sp, 'h_fg_water', 2.45e6), # 假设 sp 中可能有 h_fg_water，否则用默认值
                Q_powertrain=getattr(sp, 'Q_cabin_powertrain_invasion', 50), # 假设的参数名
                Q_electronics=getattr(sp, 'Q_cabin_electronics', 100),       # 假设的参数名
                q_person=getattr(sp, 'q_person_heat', 100)                   # 假设的参数名
            )
            print("CabinHeatCalculator initialized successfully.")
        except AttributeError as e:
            print(f"Error initializing CabinHeatCalculator: Missing parameter in 'sp' or CabinHeatCalculator init. {e}")
            self.cabin_heat_calculator = None
        except Exception as e:
            print(f"An unexpected error occurred during CabinHeatCalculator initialization: {e}")
            self.cabin_heat_calculator = None


        # --- Set initial values (t=0) ---
        self.T_motor_hist[0] = sp.T_motor_init
        self.T_inv_hist[0] = sp.T_inv_init
        self.T_batt_hist[0] = sp.T_batt_init
        self.T_cabin_hist[0] = sp.T_cabin_init
        self.T_coolant_hist[0] = sp.T_coolant_init
        self.v_vehicle_profile_hist[0] = sp.v_start

        # Initial LTR state
        initial_coolant_temp_for_ltr = self.T_coolant_hist[0]
        current_ltr_level_idx = 0
        # 确保 LTR_coolant_temp_thresholds 和 LTR_UA_values_at_levels 在 sp 中存在且长度正确
        if hasattr(sp, 'LTR_coolant_temp_thresholds') and hasattr(sp, 'LTR_UA_values_at_levels'):
            for lvl_idx_init in range(len(sp.LTR_coolant_temp_thresholds)):
                if initial_coolant_temp_for_ltr > sp.LTR_coolant_temp_thresholds[lvl_idx_init]:
                    current_ltr_level_idx = lvl_idx_init + 1
                else:
                    break
            if current_ltr_level_idx < len(sp.LTR_UA_values_at_levels):
                 initial_UA_LTR_effective = sp.LTR_UA_values_at_levels[current_ltr_level_idx]
                 initial_P_LTR_fan = sp.LTR_fan_power_levels[current_ltr_level_idx]
            else: # Fallback if index is out of bounds (e.g. thresholds not covering all levels)
                print(f"Warning: current_ltr_level_idx {current_ltr_level_idx} out of bounds for LTR_UA_values_at_levels. Using level 0.")
                current_ltr_level_idx = 0
                initial_UA_LTR_effective = sp.LTR_UA_values_at_levels[0]
                initial_P_LTR_fan = sp.LTR_fan_power_levels[0]
        else:
            print("Warning: LTR control parameters (LTR_coolant_temp_thresholds or LTR_UA_values_at_levels) not found in sp. Using default LTR values.")
            current_ltr_level_idx = 0
            initial_UA_LTR_effective = 0 # Default or a safe value
            initial_P_LTR_fan = 0

        self.LTR_level_log[0] = current_ltr_level_idx
        self.P_LTR_fan_actual_hist[0] = initial_P_LTR_fan

        if hasattr(sp, 'UA_LTR_max') and sp.UA_LTR_max > 0:
            self.LTR_effectiveness_log[0] = initial_UA_LTR_effective / sp.UA_LTR_max
        else:
            self.LTR_effectiveness_log[0] = 1.0 if initial_UA_LTR_effective > 0 else 0.0

        Q_LTR_init = max(0, initial_UA_LTR_effective * (initial_coolant_temp_for_ltr - sp.T_ambient))
        self.Q_LTR_hist[0] = Q_LTR_init

        # Initial cabin cooling power
        initial_cabin_temp_for_cooling = self.T_cabin_hist[0]
        Q_cabin_cool_initial = 0 # Default to off
        if hasattr(sp, 'cabin_cooling_power_levels') and hasattr(sp, 'cabin_cooling_temp_thresholds') and sp.cabin_cooling_power_levels:
            Q_cabin_cool_initial = sp.cabin_cooling_power_levels[-1] # Default to max power of defined levels
            for j in range(len(sp.cabin_cooling_temp_thresholds)):
                if initial_cabin_temp_for_cooling <= sp.cabin_cooling_temp_thresholds[j]:
                    Q_cabin_cool_initial = sp.cabin_cooling_power_levels[j]
                    break
        self.Q_cabin_cool_actual_hist[0] = max(0, Q_cabin_cool_initial)


        # Initial cabin heat load using CabinHeatCalculator
        if self.cabin_heat_calculator:
            try:
                self.Q_cabin_load_total_hist[0] = self.cabin_heat_calculator.calculate_total_cabin_heat_load(
                    T_outside=sp.T_ambient,
                    T_inside=initial_cabin_temp_for_cooling,
                    v_vehicle_kmh=self.v_vehicle_profile_hist[0],
                    I_solar=getattr(sp, 'I_solar_summer', 0) # Get I_solar_summer from sp, default to 0
                )
            except Exception as e:
                print(f"Warning: Error calculating initial cabin heat load with CabinHeatCalculator: {e}. Initial cabin load set to 0.")
                self.Q_cabin_load_total_hist[0] = 0
        else:
            print("Warning: CabinHeatCalculator not initialized. Initial cabin load set to 0.")
            self.Q_cabin_load_total_hist[0] = 0


        self.powertrain_chiller_on = False # State variable for chiller
        self.powertrain_chiller_active_log[0] = 0
        self.Q_coolant_chiller_actual_hist[0] = 0.0

        # Initial compressor power and LCC heat
        Q_evap_total_needed_init = self.Q_cabin_cool_actual_hist[0] + self.Q_coolant_chiller_actual_hist[0]
        P_comp_elec_init = 0.0
        P_comp_mech_init = 0.0
        if Q_evap_total_needed_init > 0 and self.cop > 0 and hasattr(sp, 'eta_comp_drive') and sp.eta_comp_drive > 0:
             P_comp_mech_init = Q_evap_total_needed_init / self.cop
             P_comp_elec_init = P_comp_mech_init / sp.eta_comp_drive
        self.P_comp_elec_profile_hist[0] = P_comp_elec_init
        self.Q_coolant_from_LCC_hist[0] = Q_evap_total_needed_init + P_comp_mech_init # Qcond = Qevap + Wcomp

        # Initial heat generation for powertrain components
        P_inv_in_init = 0
        P_elec_total_batt_out_init = 0
        try:
            P_wheel_init = hv.P_wheel_func(self.v_vehicle_profile_hist[0], sp.m_vehicle, sp.T_ambient)
            P_motor_in_init = hv.P_motor_func(P_wheel_init, sp.eta_motor)
            P_inv_in_init = P_motor_in_init / sp.eta_inv if sp.eta_inv > 0 else 0

            self.Q_gen_motor_profile_hist[0] = hv.Q_mot_func(P_motor_in_init, sp.eta_motor)
            self.Q_gen_inv_profile_hist[0] = hv.Q_inv_func(P_motor_in_init, sp.eta_inv)

            P_elec_total_batt_out_init = P_inv_in_init + P_comp_elec_init + initial_P_LTR_fan
            self.Q_gen_batt_profile_hist[0] = hv.Q_batt_func(P_elec_total_batt_out_init, sp.u_batt, sp.R_int_batt)
        except AttributeError as e:
            print(f"Warning: Powertrain heat functions missing in hv or parameters in sp. {e}. Initial generations set to 0.")
            self.Q_gen_motor_profile_hist[0] = 0
            self.Q_gen_inv_profile_hist[0] = 0
            self.Q_gen_batt_profile_hist[0] = 0
        except Exception as e:
            print(f"An unexpected error occurred during initial powertrain heat generation: {e}. Initial generations set to 0.")
            self.Q_gen_motor_profile_hist[0] = 0
            self.Q_gen_inv_profile_hist[0] = 0
            self.Q_gen_batt_profile_hist[0] = 0


    def run_simulation(self):
        sp = self.sp # For convenience
        print(f"Starting simulation loop (using CabinHeatCalculator) for {self.n_steps} steps...")

        for i in range(self.n_steps):
            # --- 0. Get current states from previous time step (or initial for i=0) ---
            current_time_sec = self.time_sim[i]
            current_cabin_temp = self.T_cabin_hist[i]
            current_T_motor = self.T_motor_hist[i]
            current_T_inv = self.T_inv_hist[i]
            current_T_batt = self.T_batt_hist[i]
            current_T_coolant = self.T_coolant_hist[i]

            # --- 1. External Inputs & Heat Generation ---
            # Vehicle speed profile
            if current_time_sec <= sp.ramp_up_time_sec:
                # Ensure ramp_up_time_sec is not zero to avoid division by zero
                speed_increase_ratio = (current_time_sec / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 1.0
                v_vehicle_current = sp.v_start + (sp.v_end - sp.v_start) * speed_increase_ratio
            else:
                v_vehicle_current = sp.v_end
            # Clamp speed to be within v_start and v_end in case of over/undershoot or unusual ramp_up_time
            v_vehicle_current = max(min(sp.v_start, sp.v_end), min(max(sp.v_start, sp.v_end), v_vehicle_current))
            self.v_vehicle_profile_hist[i] = v_vehicle_current


            # Powertrain heat generation (Motor, Inverter)
            P_inv_in = 0; Q_gen_motor = 0; Q_gen_inv = 0
            try:
                P_wheel = hv.P_wheel_func(v_vehicle_current, sp.m_vehicle, sp.T_ambient)
                P_motor_in = hv.P_motor_func(P_wheel, sp.eta_motor)
                P_inv_in = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0
                Q_gen_motor = hv.Q_mot_func(P_motor_in, sp.eta_motor)
                Q_gen_inv = hv.Q_inv_func(P_motor_in, sp.eta_inv)
            except AttributeError as e:
                 print(f"Warning at t={current_time_sec:.2f}s: Heat generation functions missing/error in heat_vehicle.py. {e}")
            except Exception as e:
                 print(f"Warning at t={current_time_sec:.2f}s: Unexpected error in powertrain heat gen. {e}")
            self.Q_gen_motor_profile_hist[i] = Q_gen_motor
            self.Q_gen_inv_profile_hist[i] = Q_gen_inv

            # Cabin heat load calculation using CabinHeatCalculator
            Q_cabin_load_total = 0
            if self.cabin_heat_calculator:
                try:
                    Q_cabin_load_total = self.cabin_heat_calculator.calculate_total_cabin_heat_load(
                        T_outside=sp.T_ambient,
                        T_inside=current_cabin_temp,
                        v_vehicle_kmh=v_vehicle_current,
                        I_solar=getattr(sp, 'I_solar_summer', 0) # Get I_solar_summer from sp
                    )
                except Exception as e:
                    print(f"Warning at t={current_time_sec:.2f}s: Error calculating cabin heat load with CabinHeatCalculator. {e}")
            else:
                print(f"Warning at t={current_time_sec:.2f}s: CabinHeatCalculator not available for cabin load calculation.")
            self.Q_cabin_load_total_hist[i] = Q_cabin_load_total

            # --- 2. Cooling System Control & Heat Transfer ---
            # 2a. Cabin Evaporator Cooling Control
            Q_cabin_cool_actual = 0 # Default to off
            if hasattr(sp, 'cabin_cooling_power_levels') and hasattr(sp, 'cabin_cooling_temp_thresholds') and sp.cabin_cooling_power_levels:
                Q_cabin_cool_actual = sp.cabin_cooling_power_levels[-1] # Default to max power if no threshold met below
                for j in range(len(sp.cabin_cooling_temp_thresholds)):
                    if current_cabin_temp <= sp.cabin_cooling_temp_thresholds[j]:
                        Q_cabin_cool_actual = sp.cabin_cooling_power_levels[j]
                        break
            Q_cabin_cool_actual = max(0, Q_cabin_cool_actual) # Ensure non-negative
            self.Q_cabin_cool_actual_hist[i] = Q_cabin_cool_actual


            # 2b. Powertrain Chiller Control Logic (hysteresis)
            # Ensure target temperatures are available in sp
            T_motor_target = getattr(sp, 'T_motor_target', float('inf'))
            T_inv_target = getattr(sp, 'T_inv_target', float('inf'))
            T_batt_target_high = getattr(sp, 'T_batt_target_high', float('inf'))
            T_motor_stop_cool = getattr(sp, 'T_motor_stop_cool', float('-inf'))
            T_inv_stop_cool = getattr(sp, 'T_inv_stop_cool', float('-inf'))
            T_batt_stop_cool = getattr(sp, 'T_batt_stop_cool', float('-inf'))

            start_cooling_powertrain = (current_T_motor > T_motor_target) or \
                                       (current_T_inv > T_inv_target) or \
                                       (current_T_batt > T_batt_target_high)
            stop_cooling_powertrain = (current_T_motor < T_motor_stop_cool) and \
                                      (current_T_inv < T_inv_stop_cool) and \
                                      (current_T_batt < T_batt_stop_cool)

            if start_cooling_powertrain:
                self.powertrain_chiller_on = True
            elif stop_cooling_powertrain:
                self.powertrain_chiller_on = False
            # Otherwise, maintain current state (hysteresis)
            self.powertrain_chiller_active_log[i] = 1 if self.powertrain_chiller_on else 0


            # 2c. Chiller Heat Transfer (from coolant to refrigerant)
            Q_chiller_potential = 0
            if current_T_coolant > sp.T_evap_sat_for_UA_calc: # T_evap_sat_for_UA_calc is refrigerant temp
                 Q_chiller_potential = sp.UA_coolant_chiller * (current_T_coolant - sp.T_evap_sat_for_UA_calc)
            Q_chiller_potential = max(0, Q_chiller_potential) # Heat flow must be positive or zero
            Q_coolant_chiller_actual = min(Q_chiller_potential, sp.max_chiller_cool_power) if self.powertrain_chiller_on else 0
            self.Q_coolant_chiller_actual_hist[i] = Q_coolant_chiller_actual


            # 2d. Total Refrigerant Evaporation Load (Cabin Evap + Powertrain Chiller)
            Q_evap_total_needed = Q_cabin_cool_actual + Q_coolant_chiller_actual


            # 2e. Compressor Power Calculation
            P_comp_elec = 0.0; P_comp_mech = 0.0
            if Q_evap_total_needed > 0 and self.cop > 0 and hasattr(sp, 'eta_comp_drive') and sp.eta_comp_drive > 0:
                P_comp_mech = Q_evap_total_needed / self.cop
                P_comp_elec = P_comp_mech / sp.eta_comp_drive
            self.P_comp_elec_profile_hist[i] = P_comp_elec


            # 2f. LCC Heat Transfer (from refrigerant to coolant) = Q_condenser_total for refrigeration cycle
            Q_coolant_from_LCC = Q_evap_total_needed + P_comp_mech # Q_cond = Q_evap + W_comp
            self.Q_coolant_from_LCC_hist[i] = Q_coolant_from_LCC


            # 2g. LTR Fan Control (based on coolant temperature) and Heat Rejection
            current_ltr_level_idx = 0
            UA_LTR_effective = 0
            P_LTR_fan_actual = 0
            if hasattr(sp, 'LTR_coolant_temp_thresholds') and hasattr(sp, 'LTR_UA_values_at_levels') and hasattr(sp, 'LTR_fan_power_levels'):
                for lvl_idx in range(len(sp.LTR_coolant_temp_thresholds)):
                    if current_T_coolant > sp.LTR_coolant_temp_thresholds[lvl_idx]:
                        current_ltr_level_idx = lvl_idx + 1
                    else:
                        break
                if current_ltr_level_idx < len(sp.LTR_UA_values_at_levels):
                    UA_LTR_effective = sp.LTR_UA_values_at_levels[current_ltr_level_idx]
                    P_LTR_fan_actual = sp.LTR_fan_power_levels[current_ltr_level_idx]
                else: # Fallback for safety
                    current_ltr_level_idx = 0
                    UA_LTR_effective = sp.LTR_UA_values_at_levels[0]
                    P_LTR_fan_actual = sp.LTR_fan_power_levels[0]

            self.LTR_level_log[i] = current_ltr_level_idx
            self.P_LTR_fan_actual_hist[i] = P_LTR_fan_actual

            Q_LTR_potential = UA_LTR_effective * (current_T_coolant - sp.T_ambient)
            Q_LTR_to_ambient = max(0, Q_LTR_potential) # Heat flow must be positive or zero
            self.Q_LTR_hist[i] = Q_LTR_to_ambient

            # Log LTR effectiveness factor (0-1)
            if hasattr(sp, 'UA_LTR_max') and sp.UA_LTR_max > 0:
                self.LTR_effectiveness_log[i] = UA_LTR_effective / sp.UA_LTR_max
            else:
                self.LTR_effectiveness_log[i] = 1.0 if UA_LTR_effective > 0 else 0.0


            # 2h. Battery Heat Generation (includes LTR fan power and compressor power)
            P_elec_total_batt_out = P_inv_in + P_comp_elec + P_LTR_fan_actual
            Q_gen_batt = 0
            try:
                Q_gen_batt = hv.Q_batt_func(P_elec_total_batt_out, sp.u_batt, sp.R_int_batt)
            except AttributeError as e:
                print(f"Warning at t={current_time_sec:.2f}s: Q_batt_func missing or error. {e}")
            except Exception as e:
                print(f"Warning at t={current_time_sec:.2f}s: Unexpected error in Q_batt_func. {e}")
            self.Q_gen_batt_profile_hist[i] = Q_gen_batt


            # 2i. Heat Transfer from Powertrain Components to Coolant
            Q_motor_to_coolant = sp.UA_motor_coolant * (current_T_motor - current_T_coolant)
            Q_inv_to_coolant = sp.UA_inv_coolant * (current_T_inv - current_T_coolant)
            Q_batt_to_coolant = sp.UA_batt_coolant * (current_T_batt - current_T_coolant)

            # --- 3. Temperature Updates (Euler forward method) ---
            # 3a. Coolant Temperature Update
            # Heat into coolant: LCC, Motor, Inv, Batt
            # Heat out of coolant: LTR, Chiller
            Q_coolant_net = (Q_coolant_from_LCC + Q_motor_to_coolant + Q_inv_to_coolant + Q_batt_to_coolant) \
                          - (Q_LTR_to_ambient + Q_coolant_chiller_actual)
            dT_coolant_dt = Q_coolant_net / sp.mc_coolant if sp.mc_coolant > 0 else 0

            # 3b. Component Temperature Updates
            dT_motor_dt = (Q_gen_motor - Q_motor_to_coolant) / sp.mc_motor if sp.mc_motor > 0 else 0
            dT_inv_dt = (Q_gen_inv - Q_inv_to_coolant) / sp.mc_inverter if sp.mc_inverter > 0 else 0
            dT_batt_dt = (Q_gen_batt - Q_batt_to_coolant) / sp.mc_battery if sp.mc_battery > 0 else 0
            dT_cabin_dt = (Q_cabin_load_total - Q_cabin_cool_actual) / sp.mc_cabin if sp.mc_cabin > 0 else 0

            # --- 4. Store results for the next time step (i+1) ---
            # These will be the 'current' values for the next iteration's start
            if i + 1 <= self.n_steps:
                self.T_motor_hist[i+1] = current_T_motor + dT_motor_dt * sp.dt
                self.T_inv_hist[i+1] = current_T_inv + dT_inv_dt * sp.dt
                self.T_batt_hist[i+1] = current_T_batt + dT_batt_dt * sp.dt
                self.T_cabin_hist[i+1] = current_cabin_temp + dT_cabin_dt * sp.dt
                self.T_coolant_hist[i+1] = current_T_coolant + dT_coolant_dt * sp.dt


        print(f"Simulation loop finished after {self.n_steps} steps.")
        self._fill_last_step_values() # Fill values for the (n_steps+1)-th point

        # --- 5. Prepare results dictionary ---
        simulation_results = {
            "time_sim": self.time_sim,
            "temperatures_data": {
                'motor': self.T_motor_hist, 'inv': self.T_inv_hist, 'batt': self.T_batt_hist,
                'cabin': self.T_cabin_hist, 'coolant': self.T_coolant_hist
            },
            "heat_gen_data": {
                'motor': self.Q_gen_motor_profile_hist,
                'inv': self.Q_gen_inv_profile_hist,
                'batt': self.Q_gen_batt_profile_hist,
                'cabin_load': self.Q_cabin_load_total_hist # This is now populated by CabinHeatCalculator
            },
            "cooling_system_logs": {
                'chiller_active': self.powertrain_chiller_active_log,
                'LTR_level': self.LTR_level_log,
                'P_LTR_fan': self.P_LTR_fan_actual_hist,
                'LTR_effectiveness_factor_equiv': self.LTR_effectiveness_log,
                'Q_LTR_to_ambient': self.Q_LTR_hist,
                'Q_coolant_from_LCC': self.Q_coolant_from_LCC_hist,
                'Q_coolant_to_chiller': self.Q_coolant_chiller_actual_hist,
                'Q_cabin_evap_cooling': self.Q_cabin_cool_actual_hist
            },
            "ac_power_log": self.P_comp_elec_profile_hist, # This is total compressor power
            "speed_profile": self.v_vehicle_profile_hist
        }
        return simulation_results

    def _fill_last_step_values(self):
        # This method ensures the last entry in history arrays (index n_steps) is populated,
        # typically by copying the state from the last calculated step or recalculating if needed.
        sp = self.sp
        n = self.n_steps # This is the last index

        # Vehicle speed for the last point
        current_time_sec_last = self.time_sim[n]
        if current_time_sec_last <= sp.ramp_up_time_sec:
            speed_increase_ratio_last = (current_time_sec_last / sp.ramp_up_time_sec) if sp.ramp_up_time_sec > 0 else 1.0
            v_last = sp.v_start + (sp.v_end - sp.v_start) * speed_increase_ratio_last
        else:
            v_last = sp.v_end
        v_last = max(min(sp.v_start, sp.v_end), min(max(sp.v_start, sp.v_end), v_last))
        self.v_vehicle_profile_hist[n] = v_last

        # For logs that are determined within the loop, copy from the last computed step (n-1) to n
        # or re-evaluate based on the state at T_hist[n]
        if n > 0: # If there was at least one simulation step
            # Temperatures are already calculated up to n_steps by the loop's T_hist[i+1]
            # Control and heat flow logs for step 'n'
            T_cabin_last = self.T_cabin_hist[n]
            T_coolant_last = self.T_coolant_hist[n]

            # Recalculate cabin cooling for the last step
            Q_cabin_cool_last = 0
            if hasattr(sp, 'cabin_cooling_power_levels') and hasattr(sp, 'cabin_cooling_temp_thresholds') and sp.cabin_cooling_power_levels:
                Q_cabin_cool_last = sp.cabin_cooling_power_levels[-1]
                for j in range(len(sp.cabin_cooling_temp_thresholds)):
                    if T_cabin_last <= sp.cabin_cooling_temp_thresholds[j]:
                        Q_cabin_cool_last = sp.cabin_cooling_power_levels[j]
                        break
            self.Q_cabin_cool_actual_hist[n] = max(0, Q_cabin_cool_last)

            # Powertrain chiller active log
            self.powertrain_chiller_active_log[n] = self.powertrain_chiller_active_log[n-1] # Assumes state persists

            # Chiller heat
            Q_chiller_potential_last = 0
            if T_coolant_last > sp.T_evap_sat_for_UA_calc:
                 Q_chiller_potential_last = sp.UA_coolant_chiller * (T_coolant_last - sp.T_evap_sat_for_UA_calc)
            Q_chiller_potential_last = max(0, Q_chiller_potential_last)
            self.Q_coolant_chiller_actual_hist[n] = min(Q_chiller_potential_last, sp.max_chiller_cool_power) if self.powertrain_chiller_active_log[n] == 1 else 0

            # Total evap and compressor power
            Q_evap_total_needed_last = self.Q_cabin_cool_actual_hist[n] + self.Q_coolant_chiller_actual_hist[n]
            P_comp_elec_last = 0.0; P_comp_mech_last = 0.0
            if Q_evap_total_needed_last > 0 and self.cop > 0 and hasattr(sp, 'eta_comp_drive') and sp.eta_comp_drive > 0:
                P_comp_mech_last = Q_evap_total_needed_last / self.cop
                P_comp_elec_last = P_comp_mech_last / sp.eta_comp_drive
            self.P_comp_elec_profile_hist[n] = P_comp_elec_last
            self.Q_coolant_from_LCC_hist[n] = Q_evap_total_needed_last + P_comp_mech_last

            # LTR state for the last step
            current_ltr_level_idx_last = 0
            UA_LTR_effective_last = 0
            P_LTR_fan_actual_last = 0
            if hasattr(sp, 'LTR_coolant_temp_thresholds') and hasattr(sp, 'LTR_UA_values_at_levels') and hasattr(sp, 'LTR_fan_power_levels'):
                for lvl_idx in range(len(sp.LTR_coolant_temp_thresholds)):
                    if T_coolant_last > sp.LTR_coolant_temp_thresholds[lvl_idx]:
                        current_ltr_level_idx_last = lvl_idx + 1
                    else:
                        break
                if current_ltr_level_idx_last < len(sp.LTR_UA_values_at_levels):
                    UA_LTR_effective_last = sp.LTR_UA_values_at_levels[current_ltr_level_idx_last]
                    P_LTR_fan_actual_last = sp.LTR_fan_power_levels[current_ltr_level_idx_last]
                else:
                    current_ltr_level_idx_last = 0
                    UA_LTR_effective_last = sp.LTR_UA_values_at_levels[0]
                    P_LTR_fan_actual_last = sp.LTR_fan_power_levels[0]
            self.LTR_level_log[n] = current_ltr_level_idx_last
            self.P_LTR_fan_actual_hist[n] = P_LTR_fan_actual_last
            self.Q_LTR_hist[n] = max(0, UA_LTR_effective_last * (T_coolant_last - sp.T_ambient))
            if hasattr(sp, 'UA_LTR_max') and sp.UA_LTR_max > 0:
                self.LTR_effectiveness_log[n] = UA_LTR_effective_last / sp.UA_LTR_max
            else:
                self.LTR_effectiveness_log[n] = 1.0 if UA_LTR_effective_last > 0 else 0.0


            # Powertrain heat generation for the last step
            P_inv_in_last_fill = 0
            try:
                P_wheel_last_fill = hv.P_wheel_func(self.v_vehicle_profile_hist[n], sp.m_vehicle, sp.T_ambient)
                P_motor_in_last_fill = hv.P_motor_func(P_wheel_last_fill, sp.eta_motor)
                P_inv_in_last_fill = P_motor_in_last_fill / sp.eta_inv if sp.eta_inv > 0 else 0
                self.Q_gen_motor_profile_hist[n] = hv.Q_mot_func(P_motor_in_last_fill, sp.eta_motor)
                self.Q_gen_inv_profile_hist[n] = hv.Q_inv_func(P_motor_in_last_fill, sp.eta_inv)
            except AttributeError: pass # Already printed warnings in loop/init
            except Exception: pass

            P_elec_total_batt_out_last_fill = P_inv_in_last_fill + self.P_comp_elec_profile_hist[n] + self.P_LTR_fan_actual_hist[n]
            try:
                self.Q_gen_batt_profile_hist[n] = hv.Q_batt_func(P_elec_total_batt_out_last_fill, sp.u_batt, sp.R_int_batt)
            except AttributeError: pass
            except Exception: pass

            # Cabin heat load for the last step
            if self.cabin_heat_calculator:
                try:
                    self.Q_cabin_load_total_hist[n] = self.cabin_heat_calculator.calculate_total_cabin_heat_load(
                        T_outside=sp.T_ambient,
                        T_inside=T_cabin_last,
                        v_vehicle_kmh=self.v_vehicle_profile_hist[n],
                        I_solar=getattr(sp, 'I_solar_summer', 0)
                    )
                except Exception: # Catch all for safety
                    self.Q_cabin_load_total_hist[n] = self.Q_cabin_load_total_hist[n-1] if n>0 else 0 # Fallback
            else: # Fallback
                 self.Q_cabin_load_total_hist[n] = self.Q_cabin_load_total_hist[n-1] if n>0 else 0

        elif n == 0: # Simulation had only one point (t=0), values already initialized.
            # Ensure all relevant logs for step 0 are set, which should be done in __init__
            pass