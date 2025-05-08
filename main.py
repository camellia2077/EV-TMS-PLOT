# -*- coding: utf-8 -*-
# main.py
print("Starting---------------------")

# Import standard libraries
import numpy as np

# Import functions from modules
import refrigeration_cycle as rc
import simulation_parameters as sp
# import plotting # Plotting is no longer directly called for charts
import simulation_core

def main():
    """
    主程序入口，协调整个模拟流程。
    """
    print("Executing main function...")

    # --- 1. Calculate Refrigeration COP ---
    cop, _ = rc.calculate_refrigeration_cop(
        sp.T_suc_C_in, sp.T_cond_sat_C_in, sp.T_be_C_in,
        sp.T_evap_sat_C_in, sp.T_dis_C_in, sp.REFRIGERANT_TYPE
    )
    if cop is None or cop == float('inf') or cop <= 0:
        print(f"Warning: Invalid COP calculated ({cop}). Using a default fallback or exiting might be necessary.")
        # cop = 2.5 # Example: set a default value
        # return    # Or exit

    # --- 2. Run Core Simulation ---
    (time_sim, temperatures_data, powertrain_chiller_active_log,
     P_comp_elec_profile_hist, v_vehicle_profile_hist, heat_gen_data,
     battery_power_data, sim_params_dict) = simulation_core.run_simulation(cop)

    # --- 3. Output Data at t=1s instead of Plotting ---
    # The call to plotting.plot_results is removed/commented out:
    # plotting.plot_results(
    #     time_sim, temperatures_data, powertrain_chiller_active_log, P_comp_elec_profile_hist,
    # v_vehicle_profile_hist, heat_gen_data, battery_power_data,
    # sim_params_dict, cop
    # )

    target_time_seconds = 1.0  # Desired time in seconds

    # Find the index in the time_sim array that is closest to target_time_seconds
    # sp.dt is the time step from simulation_parameters.py
    time_index = -1
    actual_time_found_at_index = -1

    if sp.dt <= 0:
        print("Error: Simulation time step (dt) must be positive.")
        return

    # Check if target_time_seconds is within the simulation duration
    if target_time_seconds < 0 or target_time_seconds > sp.sim_duration:
        print(f"Error: Target time t={target_time_seconds}s is outside the simulation range [0, {sp.sim_duration}s].")
        return

    try:
        # Find the index of the time value closest to target_time_seconds
        time_index = (np.abs(time_sim - target_time_seconds)).argmin()
        actual_time_found_at_index = time_sim[time_index]

        # Optional: Check if the found time is reasonably close to the target time
        if abs(actual_time_found_at_index - target_time_seconds) > sp.dt: # If it's more than one time step away, it might indicate an issue or very coarse dt
            print(f"Warning: Closest time found is {actual_time_found_at_index:.3f}s for target {target_time_seconds}s. This might be due to the simulation time step (dt={sp.dt}s).")

    except Exception as e:
        print(f"Error finding time index for t={target_time_seconds}s: {e}")
        return

    # Ensure the index is valid for data arrays
    if 0 <= time_index < len(temperatures_data['motor']): # Check against one of the arrays
        print(f"\n--- Simulation Data at t = {actual_time_found_at_index:.3f} seconds ---")
        try:
            motor_temp = temperatures_data['motor'][time_index]
            inverter_temp = temperatures_data['inv'][time_index]
            battery_temp = temperatures_data['batt'][time_index]
            cabin_temp = temperatures_data['cabin'][time_index]
            coolant_temp = temperatures_data['coolant'][time_index]
            chiller_status_numeric = powertrain_chiller_active_log[time_index]
            chiller_status_str = "ON" if chiller_status_numeric == 1 else "OFF"

            print(f"Motor Temperature: {motor_temp:.2f} °C")
            print(f"Inverter Temperature: {inverter_temp:.2f} °C")
            print(f"Battery Temperature: {battery_temp:.2f} °C")
            print(f"Cabin Temperature: {cabin_temp:.2f} °C")
            print(f"Coolant Temperature: {coolant_temp:.2f} °C")
            # As per your request, inverter and cabin temperatures are listed again.
            # Since the values are the same, they are effectively covered by the lines above.
            # If distinct outputs were needed for the repeated items, they would be identical.
            print(f"Chiller Status: {chiller_status_str}")

        except IndexError:
            print(f"Error: Data arrays are shorter than expected. Index {time_index} is out of bounds.")
        except KeyError as e:
            print(f"Error: A data key was not found: {e}. Check the data structure from simulation_core.py.")
    else:
        print(f"Error: Could not retrieve data. Invalid time index ({time_index}) or simulation duration too short.")
        print(f"Simulation ran for {sp.sim_duration}s with {len(time_sim)} time steps.")


    print("\nMain script finished with data output.")

if __name__ == "__main__":
    main()