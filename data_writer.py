# data_writer.py
# CTES Optimization Processor
# Writes necessary output files in the correct format and units
# Karl Heine, kheine@mines.edu, heinek@erau.edu
# July 2021

import csv
import json
import os

#-------------------------------------------------------------------------------
def write_json(dictionary, path, filename, log):
    log.info("Writing file: {}".format(filename))
    with open(os.path.join(path,filename), 'w') as f:
        json.dump(dictionary, f)
    f.close()
    return
#-------------------------------------------------------------------------------
def plant_load_profiles(dname, district, path, log):
    log.info("Writing plant loop load and mass flow profiles for district " \
        "simulation")
    for k in district.keys():
        multiline(district[k], path, "{}_{}.csv".format(dname, k), log)
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
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
def ampl(prep, log):
    # Writes all the files for use by AMPL

#     # Get just the chillers for convenience
#     chillers = {}
#     idx = 0
#     for p in plant_loops:
#         for c in plant_loops[p]:
#             if c not in ["district_cooling_load", "district_mass_flow",
#                 "total_power"]:
#                 chillers[idx] = plant_loops[p][c]
#                 idx += 1
#
#     ## Write constants file (fixed_params.dat)
#     #constants(ampl_path, chillers, buildings, erates, segments, ts_opt, log)
#     # Write variables that have single values per timestep:
#     for idx in range(len(chillers)):
#         k = idx + 1
#         # Sets for partial, full, and charge timesteps
#         Tsets = []
#         Tsets.append(chillers[idx]["partial_storage_timesteps"])
#         Tsets.append(chillers[idx]["full_storage_timesteps"])
#         Tsets.append(chillers[idx]["charge_timesteps"])
#         multiline_lists(Tsets, ampl_path, "Tsets{}.dat".format(k), log)
#
#         # Cooling load served by plant at each timestep (Wth -> kWth)
#         vals = [round(v / 1000, 2) for v in chillers[idx]["evap_cooling_rate"]]
#         multiline(vals, ampl_path, "l{}.dat".format(k), log)
#         # Chiller electric power at time t (W -> kW)
#         vals = [round(v / 1000, 2) for v in chillers[idx]["electricity_rate"]]
#         multiline(vals, ampl_path, "pN{}.dat".format(k), log)
#         # Chiller excess capacity available for ice making at t (Wth -> kWth)
#         vals = [round(v / 1000, 2) for v in chillers[idx]["charge_capacity"]]
#         multiline(vals, ampl_path, "qNX{}.dat".format(k), log)
#         # Chiller power increase slope for making ice at t (kWe/kWth)
#         vals = [round(v, 3) for v in chillers[idx]["charge_power"]]
#         multiline(vals, ampl_path, "lambdaX{}.dat".format(k), log)
#         # Maximum rate of ice discharge at time t (kWth)
#         vals = [round(v / 1000, 3) for v in chillers[idx]["ctes"]["max_discharge"]]
#         multiline(vals, ampl_path, "qIY{}.dat".format(k), log)
#
#         # Partial storage power reduction segment slopes (kWe/kWth)
#         vals = []
#         for s in range(len(chillers[idx]["segment_slopes"])):
#             vals.append(
#                 [round(i, 5) for i in chillers[idx]["segment_slopes"][s]])
#         multiline_lists(vals, ampl_path, "lambdaY{}.dat".format(k), log)
#         # Partial storage power reduction segment lengths (ranges) (kWe/kWth)
#         vals = []
#         for s in range(len(chillers[idx]["segment_ranges"])):
#             vals.append([round(
#                 i / 1000, 2) for i in chillers[idx]["segment_ranges"][s]])
#         multiline_lists(vals, ampl_path, "lbar{}.dat".format(k), log)
#
#         # Total community power usage
#         vals = [round(v / 1000, 2) for v in community["electricity_rate"]]
#         multiline(vals, ampl_path, "p.dat".format(k), log)
#         # Electricity cost profile ($/kWh)
#         vals = erates["energy_cost"]
#         multiline(vals, ampl_path, "cost_elec.dat", log)
#         # Demand period timestep sets
#         vals = erates["demand_pd_timesteps"]
#         multiline_lists(vals, ampl_path, "Td.dat", log)
#         # Demand Response timestep set
#         vals = erates["DR_timesteps"]
#         multiline(vals, ampl_path, "Tr.dat", log)
#
    return
#-------------------------------------------------------------------------------
def data_structure(dictionary, path, log):
    log.info("Writing data summary in project workspace folder")
    # iterate through dictionary levels:
    with open(path, "w") as f:
        for l1, v1 in dictionary.items():
            f.write("\n  {}: ".format(l1))
            if isinstance(v1, list):
                f.write("{} items".format(len(v1)))
            elif isinstance(v1, float):
                f.write("float")
            elif isinstance(v1, int):
                f.write("integer")
            elif isinstance(v1, str):
                f.write("string")
            elif isinstance(v1, dict):
                for l2, v2 in v1.items():
                    f.write("\n    {}: ".format(l2))
                    if isinstance(v2, list):
                        f.write("{} items".format(len(v2)))
                    elif isinstance(v2, float):
                        f.write("float")
                    elif isinstance(v2, int):
                        f.write("integer")
                    elif isinstance(v2, str):
                        f.write("string")
                    elif isinstance(v2, dict):
                        for l3, v3 in v2.items():
                            f.write("\n      {}: ".format(l3))
                            if isinstance(v3, list):
                                f.write("{} items".format(len(v3)))
                            elif isinstance(v3, float):
                                f.write("float")
                            elif isinstance(v3, int):
                                f.write("integer")
                            elif isinstance(v3, str):
                                f.write("string")
                            elif isinstance(v3, dict):
                                for l4, v4 in v3.items():
                                    f.write("\n        {}: ".format(l4))
                                    if isinstance(v4, list):
                                        f.write("{} items".format(len(v4)))
                                    elif isinstance(v4, float):
                                        f.write("float")
                                    elif isinstance(v4, int):
                                        f.write("integer")
                                    elif isinstance(v4, str):
                                        f.write("string")
                                    elif isinstance(v4, dict):
                                        f.write("dict")
