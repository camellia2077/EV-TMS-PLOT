# simulation_core.py
import numpy as np
import vehicle_physics as vp
import heat_transfer as ht
import simulation_parameters as sp # 导入 sp 以便访问参数

def run_simulation(cop_value):
    """
    执行车辆热管理模拟的核心逻辑。

    参数:
    cop_value (float): 制冷循环的性能系数 (COP)。

    返回:
    tuple: 包含以下元素的元组:
        - time_sim (np.array): 模拟时间点数组。
        - temperatures_data (dict): 包含各部件温度历史的字典。
        - powertrain_chiller_active_log (np.array): 动力总成冷却器活动日志。
        - P_comp_elec_profile_hist (np.array): 压缩机电功率历史。
        - v_vehicle_profile_hist (np.array): 车速历史。
        - heat_gen_data (dict): 包含各部件产热历史的字典。
        - battery_power_data (dict): 包含电池功率相关历史的字典。
        - sim_params_dict (dict): 传递给绘图模块的仿真参数字典。
    """
    print("Starting simulation core...")

    # --- 2. Simulation Setup --- (从 main.py 移入)
    n_steps = int(sp.sim_duration / sp.dt)
    time_sim = np.linspace(0, sp.sim_duration, n_steps + 1)

    # Initialize arrays for storing results
    T_motor_hist = np.zeros(n_steps + 1)
    T_inv_hist = np.zeros(n_steps + 1)
    T_batt_hist = np.zeros(n_steps + 1)
    T_cabin_hist = np.zeros(n_steps + 1)
    T_coolant_hist = np.zeros(n_steps + 1)
    powertrain_chiller_active_log = np.zeros(n_steps + 1)
    v_vehicle_profile_hist = np.zeros(n_steps + 1)
    Q_gen_motor_profile_hist = np.zeros(n_steps + 1)
    Q_gen_inv_profile_hist = np.zeros(n_steps + 1)
    Q_gen_batt_profile_hist = np.zeros(n_steps + 1)
    P_comp_elec_profile_hist = np.zeros(n_steps + 1)

    # Set initial values from simulation_parameters.py
    T_motor_hist[0] = sp.T_motor_init
    T_inv_hist[0] = sp.T_inv_init
    T_batt_hist[0] = sp.T_batt_init
    T_cabin_hist[0] = sp.T_cabin_init
    T_coolant_hist[0] = sp.T_coolant_init
    v_vehicle_profile_hist[0] = sp.v_start

    # --- 3. Simulation Loop --- (从 main.py 移入)
    powertrain_chiller_on = False # Initialize Chiller state
    print("Starting simulation loop in simulation_core...")
    for i in range(n_steps):
        current_time_sec = time_sim[i]

        # 3.1. Calculate current vehicle speed
        if current_time_sec <= sp.ramp_up_time_sec:
            speed_increase = (sp.v_end - sp.v_start) * (current_time_sec / sp.ramp_up_time_sec)
            v_vehicle_current = sp.v_start + speed_increase
        else:
            v_vehicle_current = sp.v_end
        v_vehicle_current = max(sp.v_start, min(sp.v_end, v_vehicle_current))
        v_vehicle_profile_hist[i] = v_vehicle_current

        # 3.2. Calculate instantaneous PROPULSION power and heat generation
        P_wheel = vp.P_wheel_func(v_vehicle_current, sp.m_vehicle, sp.T_ambient)
        P_motor_in = vp.P_motor_func(P_wheel, sp.eta_motor)
        P_inv_in = P_motor_in / sp.eta_inv if sp.eta_inv > 0 else 0

        Q_gen_motor = vp.Q_mot_func(P_motor_in, sp.eta_motor)
        Q_gen_inv = vp.Q_inv_func(P_motor_in, sp.eta_inv)
        Q_gen_motor_profile_hist[i] = Q_gen_motor
        Q_gen_inv_profile_hist[i] = Q_gen_inv

        # 3.3. Calculate Cabin Heat Loads
        Q_cabin_internal = ht.heat_universal_func(sp.N_passengers)
        Q_cabin_conduction_body = ht.heat_body_func(sp.T_ambient, T_cabin_hist[i], v_vehicle_current, sp.v_air_in_mps, sp.A_body, sp.R_body)
        Q_cabin_conduction_glass = ht.heat_glass_func(sp.T_ambient, T_cabin_hist[i], sp.I_solar_summer, v_vehicle_current, sp.v_air_in_mps, sp.A_glass, sp.R_glass, sp.SHGC, sp.A_glass_sun)
        Q_cabin_ventilation = ht.heat_vent_summer_func(sp.N_passengers, sp.T_ambient, T_cabin_hist[i], sp.W_out_summer, sp.W_in_target, sp.fresh_air_fraction)
        Q_cabin_load_total = Q_cabin_internal + Q_cabin_conduction_body + Q_cabin_conduction_glass + Q_cabin_ventilation

        # MODIFIED SECTION FOR COOLING LOGIC (3.4, 3.6, 3.7 combined and reordered for priority)

        # 3.4. Cabin Cooling Demand Calculation
        cabin_temp_error = T_cabin_hist[i] - sp.T_cabin_target
        gain_cabin_cool = 1000 # Proportional gain for cabin cooling
        Q_cabin_cool_demand = gain_cabin_cool * cabin_temp_error if cabin_temp_error > 0 and T_cabin_hist[i] > sp.T_cabin_target else 0
        # Preliminary cabin cooling request, limited by its own max power
        Q_cabin_cool_requested = min(Q_cabin_cool_demand, sp.max_cabin_cool_power)

        # 3.5. Heat Transfer between Components and Coolant (Original placement, no change here)
        Q_motor_to_coolant = sp.UA_motor_coolant * (T_motor_hist[i] - T_coolant_hist[i])
        Q_inv_to_coolant = sp.UA_inv_coolant * (T_inv_hist[i] - T_coolant_hist[i])
        Q_batt_to_coolant = sp.UA_batt_coolant * (T_batt_hist[i] - T_coolant_hist[i])
        Q_coolant_absorb = Q_motor_to_coolant + Q_inv_to_coolant + Q_batt_to_coolant

        # 3.6. Coolant Cooling Demand (Radiator and Chiller)
        Q_radiator_potential = sp.UA_coolant_radiator * (T_coolant_hist[i] - sp.T_ambient)
        Q_coolant_radiator = max(0, Q_radiator_potential) # Radiator always works if temp diff allows

        start_cooling_powertrain = (T_motor_hist[i] > sp.T_motor_target) or \
                                   (T_inv_hist[i] > sp.T_inv_target) or \
                                   (T_batt_hist[i] > sp.T_batt_target_high)
        stop_cooling_powertrain = (T_motor_hist[i] < sp.T_motor_stop_cool) and \
                                  (T_inv_hist[i] < sp.T_inv_stop_cool) and \
                                  (T_batt_hist[i] < sp.T_batt_stop_cool)
        if start_cooling_powertrain:
            powertrain_chiller_on = True
        elif stop_cooling_powertrain:
            powertrain_chiller_on = False

        Q_chiller_demand_potential = 0
        if powertrain_chiller_on:
            Q_chiller_demand_potential = sp.UA_coolant_chiller * (T_coolant_hist[i] - sp.T_evap_sat_for_UA_calc) if T_coolant_hist[i] > sp.T_evap_sat_for_UA_calc else 0
            Q_chiller_demand_potential = max(0, Q_chiller_demand_potential) # Ensure non-negative
        # Preliminary coolant chiller request, limited by its own max power
        Q_coolant_chiller_requested = min(Q_chiller_demand_potential, sp.max_chiller_cool_power) if powertrain_chiller_on else 0

        # 3.7. Refrigeration Power Allocation and Compressor Power Calculation (MODIFIED FOR PRIORITY)
        Q_out_cabin = 0  # Actual cooling power provided to cabin
        Q_coolant_chiller_actual = 0 # Actual cooling power provided to coolant by chiller

        # Priority 1: Cabin Cooling
        # Actual cabin cooling is limited by its request AND the total available evaporator power
        Q_out_cabin = min(Q_cabin_cool_requested, sp.max_total_evaporator_power)

        # Calculate remaining evaporator power after cabin cooling
        remaining_evaporator_power = sp.max_total_evaporator_power - Q_out_cabin

        # Priority 2: Powertrain Coolant Chiller
        # Chiller gets what's requested, limited by remaining evaporator power
        if powertrain_chiller_on and remaining_evaporator_power > 0:
            Q_coolant_chiller_actual = min(Q_coolant_chiller_requested, remaining_evaporator_power)
        else:
            Q_coolant_chiller_actual = 0 # No chiller if not on or no power left

        powertrain_chiller_active_log[i] = 1 if Q_coolant_chiller_actual > 0 else 0
        Q_coolant_reject = Q_coolant_chiller_actual + Q_coolant_radiator # Total heat rejected from coolant loop

        # Calculate total actual evaporator load and compressor power
        P_comp_elec = 0.0
        Q_evap_total_actual = Q_out_cabin + Q_coolant_chiller_actual # This is the actual total cooling done by evaporator

        if Q_evap_total_actual > 0:
            if cop_value > 0 and cop_value != float('inf') and sp.eta_comp_drive > 0:
                P_comp_mech = Q_evap_total_actual / cop_value
                P_comp_elec = P_comp_mech / sp.eta_comp_drive
            else:
                P_comp_elec = 3000 # Fallback, consider more robust error handling or a warning
        P_comp_elec_profile_hist[i] = P_comp_elec

        # END OF MODIFIED COOLING LOGIC SECTION

        # 3.8. Update Battery Load & Heat Generation (Original, uses P_comp_elec)
        P_elec_total_batt_out = P_inv_in + P_comp_elec
        Q_gen_batt = vp.Q_batt_func(P_elec_total_batt_out, sp.u_batt, sp.R_int_batt)
        Q_gen_batt_profile_hist[i] = Q_gen_batt

        # 3.9. Calculate Temperature Derivatives (Original, uses Q_out_cabin and Q_coolant_reject)
        dT_motor_dt = (Q_gen_motor - Q_motor_to_coolant) / sp.mc_motor if sp.mc_motor > 0 else 0
        dT_inv_dt = (Q_gen_inv - Q_inv_to_coolant) / sp.mc_inverter if sp.mc_inverter > 0 else 0
        dT_batt_dt = (Q_gen_batt - Q_batt_to_coolant) / sp.mc_battery if sp.mc_battery > 0 else 0
        dT_cabin_dt = (Q_cabin_load_total - Q_out_cabin) / sp.mc_cabin if sp.mc_cabin > 0 else 0 # Uses Q_out_cabin
        dT_coolant_dt = (Q_coolant_absorb - Q_coolant_reject) / sp.mc_coolant if sp.mc_coolant > 0 else 0 # Uses Q_coolant_reject

        # 3.10. Update Temperatures using Euler forward method (Original)
        T_motor_hist[i+1] = T_motor_hist[i] + dT_motor_dt * sp.dt
        T_inv_hist[i+1] = T_inv_hist[i] + dT_inv_dt * sp.dt
        T_batt_hist[i+1] = T_batt_hist[i] + dT_batt_dt * sp.dt
        T_cabin_hist[i+1] = T_cabin_hist[i] + dT_cabin_dt * sp.dt
        T_coolant_hist[i+1] = T_coolant_hist[i] + dT_coolant_dt * sp.dt

    print("Simulation loop finished in simulation_core.")

    # --- 4. Post-processing for Plots (从 main.py 移入) ---
    current_time_sec_last = time_sim[n_steps]
    if current_time_sec_last <= sp.ramp_up_time_sec:
        speed_increase_last = (sp.v_end - sp.v_start) * (current_time_sec_last / sp.ramp_up_time_sec)
        v_vehicle_profile_hist[n_steps] = max(sp.v_start, min(sp.v_end, sp.v_start + speed_increase_last))
    else:
        v_vehicle_profile_hist[n_steps] = sp.v_end

    if n_steps > 0:
        powertrain_chiller_active_log[n_steps] = powertrain_chiller_active_log[n_steps-1]
        Q_gen_motor_profile_hist[n_steps] = Q_gen_motor_profile_hist[n_steps-1]
        Q_gen_inv_profile_hist[n_steps] = Q_gen_inv_profile_hist[n_steps-1]
        Q_gen_batt_profile_hist[n_steps] = Q_gen_batt_profile_hist[n_steps-1]
        P_comp_elec_profile_hist[n_steps] = P_comp_elec_profile_hist[n_steps-1]
    elif n_steps == 0: # Handle case with only one time step (n_steps=0)
        # For a single point in time, values are already set at index 0
        # The post-processing for the last step [n_steps] is mainly for plotting continuity
        # If n_steps is 0, then the loop for i in range(n_steps) does not run.
        # Initial values are in [0], and we might want to fill [1] (or [n_steps]) if sim_duration > 0
        # However, if n_steps = 0, len(time_sim) = 1. The arrays are n_steps + 1.
        # So if sim_duration = 0 or dt is very large, n_steps can be 0.
        # Let's assume if n_steps = 0, the simulation effectively ran for 0 duration or 1 point.
        # The existing logic for n_steps > 0 handles array filling for plotting.
        # If n_steps == 0, ensure the [0] index has the calculated values from the (not run) loop's first iteration logic.
        # This section might need refinement if sim_duration=0 or very small dt is a common use case.
        # For now, 'pass' is acceptable as the initial state is already set.
        pass


    P_inv_in_profile_hist = np.zeros(n_steps + 1)
    for idx in range(n_steps + 1): # Should be n_steps + 1 to cover the last point
        P_wheel_i = vp.P_wheel_func(v_vehicle_profile_hist[idx], sp.m_vehicle, sp.T_ambient)
        P_motor_in_i = vp.P_motor_func(P_wheel_i, sp.eta_motor)
        P_inv_in_profile_hist[idx] = P_motor_in_i / sp.eta_inv if sp.eta_inv > 0 else 0
    P_elec_total_profile_hist = P_inv_in_profile_hist + P_comp_elec_profile_hist

    # Prepare data dictionaries for the plotting function (从 main.py 移入)
    temperatures_data = {
        'motor': T_motor_hist, 'inv': T_inv_hist, 'batt': T_batt_hist,
        'cabin': T_cabin_hist, 'coolant': T_coolant_hist
    }
    heat_gen_data = {
        'motor': Q_gen_motor_profile_hist, 'inv': Q_gen_inv_profile_hist, 'batt': Q_gen_batt_profile_hist
    }
    battery_power_data = {
        'inv_in': P_inv_in_profile_hist,
        'comp_elec': P_comp_elec_profile_hist,
        'total_elec': P_elec_total_profile_hist
    }
    sim_params_dict = {
        'T_ambient': sp.T_ambient,
        'T_motor_target': sp.T_motor_target,
        'T_inv_target': sp.T_inv_target,
        'T_batt_target_high': sp.T_batt_target_high,
        'T_batt_stop_cool': sp.T_batt_stop_cool,
        'T_cabin_target': sp.T_cabin_target,
        'v_start': sp.v_start,
        'v_end': sp.v_end,
        'sim_duration': sp.sim_duration,
        'dt': sp.dt,
        'eta_comp_drive': sp.eta_comp_drive,
        'ramp_up_time_sec': sp.ramp_up_time_sec,
        'max_total_evaporator_power': sp.max_total_evaporator_power # Pass for potential plotting/info
    }
    print("Simulation core finished.")
    return (time_sim, temperatures_data, powertrain_chiller_active_log,
            P_comp_elec_profile_hist, v_vehicle_profile_hist, heat_gen_data,
            battery_power_data, sim_params_dict)
