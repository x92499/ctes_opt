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
def ampl(prep, log):
    # Writes all the files for use by AMPL
    # Create useful variables, lists, and locally-used dictionaries
    segments = []
    T_full_ct = []
    T_part_ct = []
    yrs = {'utss': 0, 'central': 0}
    k = {'utss': 0, 'central': 0}
    z_bar = {'utss': [], 'central': []}
    qbar = {'utss': 0, 'central': 0}
    # Define write path
    project_path = prep['program_manager']['project_name']
    ampl_path = os.path.join(project_path, 'ampl_files')
    ## Timeseries values
    # Community aggregate power demand profile (W->kW)
    vals = [round(v / 1000, 2) for v in prep['community']['rate_electricity_W']]
    multiline(vals, ampl_path, "p.dat", log)
    # Electricity rate by timestep ($/kWh)
    vals = prep['utility_rate']['energy_cost']
    multiline(vals, ampl_path, "cost_elec.dat", log)
    # Demand period timestep sets
    vals = prep['utility_rate']["demand_pd_timesteps"]
    multiline_lists(vals, ampl_path, "Td.dat", log)
    # Demand Response timestep set
    vals = prep['utility_rate']["DR_timesteps"]
    multiline(vals, ampl_path, "Tr.dat", log)
    # Timeseries by cooling plant (rtu, chiller, or district plant)
    for b in prep['community']['building_names']:
        for n in prep[b]:
            if 'rtu' in n:
                # Electricity Rate (W->kW)
                vals = [round(v / 1000, 2) for v in
                    prep[b][n]['rate_electricity_W']]
                multiline(vals, ampl_path, "pN{}.dat".format(
                    prep[b][n]['index']), log)
                # Cooling Rate (Wt->kWt)
                vals = [round(v / 1000, 2) for v in
                    prep[b][n]['rate_cooling_Wt']]
                multiline(vals, ampl_path, "lN{}.dat".format(
                    prep[b][n]['index']), log)
                # Max Charging Rate (Wt->kWt)
                vals = [round(v / 1000, 2) for v in
                    prep[b][n]['utss']['rate_charge_max_Wt']]
                multiline(vals, ampl_path, "q_dotX{}.dat".format(
                    prep[b][n]['index']), log)
                # Max Discharging Rate (Wt->kWt)
                vals = [round(v / 1000, 2) for v in
                    prep[b][n]['utss']['rate_discharge_max_Wt']]
                multiline(vals, ampl_path, "q_dotIY{}.dat".format(
                    prep[b][n]['index']), log)
                multiline(vals, ampl_path, "y_bar{}.dat".format(
                    prep[b][n]['index']), log)
                segments.append(1)
                # Charging Efficiency
                vals = [round(1/v, 5) for v in prep[b][n]['utss']['cop_charge']]
                multiline(vals, ampl_path, "lambdaX{}.dat".format(
                    prep[b][n]['index']), log)
                # Discharging Efficiency
                vals = [round(1/v, 5) for v in prep[b][n]['cop']]
                multiline(vals, ampl_path, "lambdaY{}.dat".format(
                    prep[b][n]['index']), log)
                # Tsets
                Tsets = []
                T_full_ct.append(len(prep[b][n]['timesteps_load']))
                T_part_ct.append(len(prep[b][n]['timesteps_load']))
                Tsets.append(prep[b][n]['timesteps_load'])
                Tsets.append(prep[b][n]['timesteps_load'])
                Tsets.append([i for i in range(
                    8760 * prep['program_manager']['timesteps'])])
                multiline_lists(Tsets, ampl_path, "Tsets{}.dat".format(
                    prep[b][n]['index']), log)
                # Get lifespan of utss
                if yrs['utss'] == 0:
                    yrs['utss'] = prep[b][n]['utss']['lifespan_yrs']
                    k['utss'] = prep[b][n]['utss']['cost_per_kWt']
                    qbar['utss'] = round(
                        prep[b][n]['utss']['capacity_nominal_Wt'] / 1000, 2)
                # Set z_bar values
                z_bar['utss'].append(prep[b][n]['utss']['install_limit'])
                z_bar['central'].append(0)
            elif 'chiller' in n:
                # Electricity Rate (W->kW)
                vals = [round(v / 1000, 2) for v in
                    prep[b][n]['rate_electricity_W']]
                multiline(vals, ampl_path, "pN{}.dat".format(
                    prep[b][n]['index']), log)
                # Cooling Rate (Wt->kWt)
                vals = [round(v / 1000, 2) for v in
                    prep[b][n]['rate_cooling_Wt']]
                multiline(vals, ampl_path, "lN{}.dat".format(
                    prep[b][n]['index']), log)
                # Max Charging Rate (Wt->kWt)
                vals = [round(v / 1000, 2) for v in
                    prep[b][n]['charging_performance']['rate_cooling_max_Wt']]
                multiline(vals, ampl_path, "q_dotX{}.dat".format(
                    prep[b][n]['index']), log)
                # Max Discharging Rate
                vals = [round(v / 1000, 2) for v in prep[b][n]
                    ['discharging_performance']['rate_discharge_max_Wt']]
                multiline(vals, ampl_path, "q_dotIY{}.dat".format(
                    prep[b][n]['index']), log)
                # Charging Efficiency
                vals = [round(v, 5) for v in
                    prep[b][n]['charging_performance']['slope']]
                multiline(vals, ampl_path, "lambdaX{}.dat".format(
                    prep[b][n]['index']), log)
                # Discharging Efficiency
                vals = []
                for s in range(len(prep[b][n]
                    ['discharging_performance']['slopes'])):
                    vals.append([round(i, 5) for i in prep[b][n]
                        ['discharging_performance']['slopes'][s]])
                multiline_lists(vals, ampl_path, "lambdaY{}.dat".format(
                    prep[b][n]['index']), log)
                # Discharging Efficiency Ranges (Wt->kWt)
                vals = []
                for s in range(len(prep[b][n]
                    ['discharging_performance']['ranges'])):
                    vals.append([round(i / 1000, 5) for i in prep[b][n]
                        ['discharging_performance']['ranges'][s]])
                multiline_lists(vals, ampl_path, "y_bar{}.dat".format(
                    prep[b][n]['index']), log)
                segments.append(prep['program_manager']['segments'])
                # Tsets
                Tsets = []
                T_full_ct.append(len(prep[b][n]['discharging_performance']
                    ['timesteps_full_storage']))
                T_part_ct.append(len(prep[b][n]['timesteps_load']))
                Tsets.append(prep[b][n]['timesteps_load'])
                Tsets.append(prep[b][n]['discharging_performance']
                    ['timesteps_full_storage'])
                Tsets.append(prep[b][n]['charging_performance']
                    ['timesteps'])
                multiline_lists(Tsets, ampl_path, "Tsets{}.dat".format(
                    prep[b][n]['index']), log)
                # Get lifespan of utss
                if yrs['central'] == 0:
                    yrs['central'] = prep[b][n]['ctes']['lifespan_yrs']
                    k['central'] = prep[b][n]['ctes']['cost_per_kWt']
                    qbar['central'] = round(
                        prep[b][n]['ctes']['capacity_nominal_Wt'] / 1000, 2)
                # Set z_bar values
                z_bar['utss'].append(0)
                z_bar['central'].append(prep[b][n]['ctes']['install_limit'])

    ## Constants and set sizes
    # read D, I, N, T, {d in 1..D} Td_ct[d], {n in 1..N} TYf_ct[n], {n in 1..N} TYp_ct[n], Tr_ct, delta, {i in 1..I} yrs[i], {n in UTSS} zbar[1,n], {d in 1..D} c_d[d] < fixed_params.dat;
    vals = []
    vals.append([len(prep['utility_rate']['demand_pd_ts_ct'])])
    vals.append([2])
    vals.append([prep['community']['plant_count']])
    vals.append([prep['program_manager']['timesteps'] * 8760])
    vals.append(prep['utility_rate']['demand_pd_ts_ct'])
    vals.append(T_full_ct)
    vals.append(T_part_ct)
    vals.append([len(prep['utility_rate']['DR_timesteps'])])
    vals.append([1 / prep['program_manager']['timesteps']])
    vals.append([yrs['utss'], yrs['central']])
    vals.append([k['utss'], k['central']])
    vals.append(prep['utility_rate']['demand_cost'])
    vals.append(z_bar['utss'])
    vals.append(z_bar['central'])
    vals.append(segments)
    vals.append([qbar['utss'], qbar['central']])

    multiline_lists(vals, ampl_path, "fixed_params.dat", log)

#
#     ## Write constants file (fixed_params.dat)
#     #constants(ampl_path, chillers, buildings, erates, segments, ts_opt, log)

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
