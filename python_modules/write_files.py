## write_files.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Initiated: May 17, 2021
# Completed:
# Revised:
# This code is a revision of parameter_writer.py from Marcy 11, 2021

## The purpose of this script is to write out all the required parameters for
# the central ice optimization program

# Imports
import csv
import os
import sys
#-------------------------------------------------------------------------------
def constants(path, chillers, buildings, erates, segments, ts_opt, log):
    log.info(" Writing time-invariant parameters to 'fixed_params.dat'")
    filepath = os.path.join(path, "fixed_params.dat")
    with open(filepath, "w", newline="") as f:
        wtr = csv.writer(f, dialect="excel", delimiter=",")
        wtr.writerow([round(1 / ts_opt, 3)])    # delta, ts in hrs
        wtr.writerow([len(buildings)]) # B, # bldgs
        wtr.writerow([len(erates["demand_pd_ts_ct"])])  # D, # demand pds
        wtr.writerow([1]) # I, # CTES types
        wtr.writerow([len(chillers)])    # N, # chillers
        wtr.writerow([segments])    # S, # segments for linearization
        wtr.writerow([int(8760 * ts_opt)])  # T, # timesteps
        wtr.writerow(erates["demand_pd_ts_ct"])    # TP_d, # ts in ea dmd pd
        wtr.writerow(erates["demand_cost"])  # c_d, demand charge per pd
        wtr.writerow([len(
            chillers[c]["partial_storage_timesteps"]) for c in chillers])
        wtr.writerow([len(
            chillers[c]["full_storage_timesteps"]) for c in chillers])
        wtr.writerow([len(
            chillers[c]["charge_timesteps"]) for c in chillers])
        wtr.writerow([round(max(chillers[0]["ctes"]["max_discharge"]) / 1000, 2)])
        wtr.writerow([round(chillers[0]["ctes"]["capacity"] / 1000, 2)])

    return
#-------------------------------------------------------------------------------
def multiline(vals, path, filename, log):
    with open(os.path.join(path, filename), "w", newline="") as f:
        wtr = csv.writer(f, delimiter=" ")
        for i in range(len(vals)):
            wtr.writerow([vals[i]])

    log.info(" Successfully wrote {} values to file '{}' in '{}'".format(
        len(vals), filename, path))
    return
#-------------------------------------------------------------------------------
def multiline_lists(vals, path, filename, log):
    with open(os.path.join(path, filename), "w", newline="") as f:
        wtr = csv.writer(f, delimiter=",")
        for i in range(len(vals)):
            wtr.writerow(vals[i])

    log.info(" Successfully wrote {} lists to file '{}' in '{}'".format(
        len(vals), filename, path))
    return
#-------------------------------------------------------------------------------
def run(input_path, community, plant_loops, buildings, erates, segments,
    ts_opt, log):

    # Create AMPL files folder if needed:
    try:
        os.path.isdir(os.path.join(input_path, "ampl_files"))
    except:
        print(False)
        os.mkdir(os.path.join(input_path, "ampl_files"))
    ampl_path = os.path.join(input_path, "ampl_files")

    # Get just the chillers for convenience
    chillers = {}
    idx = 0
    for p in plant_loops:
        for c in plant_loops[p]:
            if c not in ["district_cooling_load", "district_mass_flow",
                "total_power"]:
                chillers[idx] = plant_loops[p][c]
                idx += 1

    # Write constants file (fixed_params.dat)
    constants(ampl_path, chillers, buildings, erates, segments, ts_opt, log)
    # Write variables that have single values per timestep:
    for idx in range(len(chillers)):
        k = idx + 1
        # Sets for partial, full, and charge timesteps
        Tsets = []
        Tsets.append(chillers[idx]["partial_storage_timesteps"])
        Tsets.append(chillers[idx]["full_storage_timesteps"])
        Tsets.append(chillers[idx]["charge_timesteps"])
        multiline_lists(Tsets, ampl_path, "Tsets{}.dat".format(k), log)

        # Cooling load served by plant at each timestep (Wth -> kWth)
        vals = [round(v / 1000, 2) for v in chillers[idx]["evap_cooling_rate"]]
        multiline(vals, ampl_path, "l{}.dat".format(k), log)
        # Chiller electric power at time t (W -> kW)
        vals = [round(v / 1000, 2) for v in chillers[idx]["electricity_rate"]]
        multiline(vals, ampl_path, "p_tildeN{}.dat".format(k), log)
        # Chiller excess capacity available for ice making at t (Wth -> kWth)
        vals = [round(v / 1000, 2) for v in chillers[idx]["charge_capacity"]]
        multiline(vals, ampl_path, "q_dotX{}.dat".format(k), log)
        # Chiller power increase slope for making ice at t (kWe/kWth)
        vals = [round(v, 3) for v in chillers[idx]["charge_power"]]
        multiline(vals, ampl_path, "lambdaX{}.dat".format(k), log)
        # Maximum rate of ice discharge at time t (kWth)
        vals = [round(v, 3) for v in chillers[idx]["ctes"]["max_discharge"]]
        multiline(vals, ampl_path, "q_dotIY{}.dat".format(k), log)

        # Partial storage power reduction segment slopes (kWe/kWth)
        vals = []
        for s in range(len(chillers[idx]["segment_slopes"])):
            vals.append(
                [round(i, 5) for i in chillers[idx]["segment_slopes"][s]])
        multiline_lists(vals, ampl_path, "lambdaY{}.dat".format(k), log)
        # Partial storage power reduction segment lengths (ranges) (kWe/kWth)
        vals = []
        for s in range(len(chillers[idx]["segment_ranges"])):
            vals.append([round(
                i / 1000, 2) for i in chillers[idx]["segment_ranges"][s]])
        multiline_lists(vals, ampl_path, "y_bar{}.dat".format(k), log)

        # Total community power usage
        vals = [round(v / 1000, 2) for v in community["electricity_rate"]]
        multiline(vals, ampl_path, "p_tilde.dat".format(k), log)
        # Electricity cost profile ($/kWh)
        vals = erates["energy_cost"]
        multiline(vals, ampl_path, "cost_elec.dat", log)
        # Demand period timestep sets
        vals = erates["demand_pd_timesteps"]
        multiline_lists(vals, ampl_path, "Tdmd.dat", log)

    return
