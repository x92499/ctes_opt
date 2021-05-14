## Building Pre-processor for CTES Optimizatoin
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Re-consctruted from pre_opt.py to facilitate program reorganization
# Initiated: May 13, 2021
# Completed:
# Revised:

## Description:
# This script parses the .eso files and populates information into the buildings
# and plant_loops dictionaries (if applicable)

import csv
import esoreader
import os
import sys

#-------------------------------------------------------------------------------
def missing_variable(key, required, log):
    # This method reports on missing variables and terminates the program
    if required:
        log.error(" Timestep data for the required variable '{}' was not " \
            "found in the .eso".format(key))
        log.info("Program terminated early!")
        sys.exit("Failed to find all required simulation output variables")
    else:
        log.info(" Timestep data for optional variable '{}' was not " \
            "found in the .eso".format(key))
#-------------------------------------------------------------------------------
def get_timestep_values(values, ts_opt, aggregate, interpolate,
    convertJtoW, log):
    # This method gets the pertinent timestep values and processes them either
    # by aggregation/averaging or interpolation

    # perform conversion from energy [J] to power [W]
    if convertJtoW:
        ts_sim = len(values) // 8760
        values = [v * ts_sim / 3600 for v in values]

    # perform aggregation (all terms must be in units of power)
    if aggregate >= 1:
        opt_vals = []
        for i in range((ts_opt * 8760)):
            v = 0
            for j in range(aggregate):
                v += float(values[i*aggregate + j]) / aggregate
            opt_vals.append(v)

    # perform interpolation (all terms must be in units of power)
    if interpolate > 1:
        opt_vals = []
        for i in range(len(values)):
            if len(opt_vals) == 0:
                for j in range(interpolate):
                    opt_vals.append(values[i])
            else:
                delta = (values[i] - values[i-1]) / interpolate
                for j in range(interpolate):
                    opt_vals.append(opt_vals[-1] + delta)

    return opt_vals
#-------------------------------------------------------------------------------
def get_chiller_data(loop, dd, data, ts_opt, aggregate, interpolate, log):
    # This method gets all the timestep data for each chiller, if the building
    # model has its own chiller(s)

    # Get evaporator cooling rate and determine chiller count
    chiller_count = 0
    chiller_names = []
    try:
        idxs = dd.find_variable("Chiller Evaporator Cooling Rate")
        # Count the number of chillers
        for i in idxs:
            if i[0] == "TimeStep":
                chiller_count += 1
                chiller_names.append(i[1])
                loop[i[1]] = {}
        log.info(" Chillers found: {}".format(
            chiller_count))
        for c in chiller_names:
            key = dd.index["TimeStep", c, "Chiller Evaporator Cooling Rate"]
            loop[c]["evap_cooling_rate"] = get_timestep_values(
            data[key], ts_opt, aggregate, interpolate, False, log)
    except:
        missing_variable("Chiller Evaporator Cooling Rate [W]", True,
            log)

    # Get return water temperature (evap in)
    try:
        for c in chiller_names:
            key = dd.index["TimeStep", c,
                "Chiller Evaporator Inlet Temperature"]
            loop[c]["evap_inlet_temp"] = get_timestep_values(
            data[key], ts_opt, aggregate, interpolate, False, log)
    except:
        missing_variable("Chiller Evaporator Inlet Temperature [C]", True,
            log)

    # Get supply water temperature (evap out) Assumes 6.67 if not specified
    try:
        for c in chiller_names:
            key = dd.index["TimeStep", c,
                "Chiller Evaporator Outlet Temperature"]
            loop[c]["evap_outlet_temp"] = get_timestep_values(
                data[key], ts_opt, aggregate, interpolate, False, log)
    except:
        missing_variable("Chiller Evaporator Outlet Temperature [C]", False,
            log)
        log.info(" Assuming a chilled water loop temperature of 6.67 [C] " \
            "(44 [F])")
        for c in chiller_names:
            loop[c]["evap_outlet_temp"] = [6.67 for i in range(8760*ts_opt)]

    # Get evaporator mass flow rate
    try:
        for c in chiller_names:
            key = dd.index["TimeStep", c, "Chiller Evaporator Mass Flow Rate"]
            loop[c]["mass_flow_rate"] = get_timestep_values(
                data[key], ts_opt, aggregate, interpolate, False, log)
    except:
        missing_variable("Chiller Evaporator Mass Flow Rate [kg/s]", True,
            log)

    # Get evaporator part load ratio
    try:
        for c in chiller_names:
            key = dd.index["TimeStep", c, "Chiller Part Load Ratio"]
            loop[c]["part_load_ratoi"] = get_timestep_values(
                data[key], ts_opt, aggregate, interpolate, False, log)
    except:
        missing_variable("Chiller Part Load Ratio [-]", False, log)

    # Get chiller electric power consumption
    try:
        for c in chiller_names:
            key = dd.index["TimeStep", c, "Chiller Electricity Rate"]
            loop[c]["electricity_rate"] = get_timestep_values(
                data[key], ts_opt, aggregate, interpolate, False, log)
    except:
        missing_variable("Chiller Electricity Rate [W]", False, log)

    return loop
#-------------------------------------------------------------------------------
def check_file_length(data, key, ts_opt, log):
    # This script checks the .eso for length and timestep
    # Can't handle .eso's with multiple run periods though...

    interpolate = 0
    aggregate = 0

    if len(data[key]) < 8760 or len(data[key]) % 8760 != 0:
        log.error(" .eso file does not contain a 1-year simulation")
        log.info("Program terminated early!")
        sys.exit("Failed in 'get_sim_data' module")
    elif len(data[key]) < 8760 * ts_opt:
        log.warning(" Building simulation timestep is greater than the " \
                    "desired optimization timestep. " \
                    "Program will continue, data will be interpolated. " \
                    "It is HIGHLY recommended that simulation fidelity " \
                    "be greater than optimization fidelity.")
        if (8760 * ts_opt) % len(data[key]) == 0:
            interpolate = (8760 * ts_opt) // len(data[key])
        else:
            log.error(" Building simulation and optimization timesteps " \
                "must be factors of each other")
            log.info("Program terminated early!")
            sys.exit("Timestep mis-match (interpolator)")
    elif len(data[key]) > 8760 * ts_opt:
        log.info(" Building simulation data is of greater precision than " \
                 "the optimization timestep; data will be aggregated " \
                 "and averaged")
        if (len(data[key]) % (8760 * ts_opt)) == 0:
            aggregate = len(data[key]) // (8760 * ts_opt)
        else:
            log.error(" Building simulation and optimization timesteps " \
                "must be factors of each other")
            log.info("Program terminated early!")
            sys.exit("Timestep mis-match (aggregator)")
    elif len(data[key]) == 8760 * ts_opt:
        aggregate = 1
        log.info(" Simulation and optimization timesteps match")

    # Report timesteps
    log.info(" Detected simulation timestep: {} per hour".format(
        len(data[key]) // 8760))

    return interpolate, aggregate
#-------------------------------------------------------------------------------
def bldgs(input_path, buildings, plant_loops, ts_opt, log):
    # load building data
    for b in buildings:
        try:
            log.info("\n Loading {}...".format(b))
            dd,data = esoreader.read(os.path.join(
                input_path, "building_sim", "{}.eso".format(b)))
            log.info("...completed")
        except:
            log.error("Failed to find or load .eso file for specified building")
            log.info("Program terminated early!")
            sys.exit("See log file")

        # Get total facility electricity and check file length
        key = dd.index["TimeStep", None, "Electricity:Facility"]
        interpolate, aggregate = check_file_length(data, key, ts_opt, log)

        ## Get facility total electric power at ts_opt
        buildings[b]["total_power"] = get_timestep_values(
            data[key], ts_opt, aggregate, interpolate, True, log)
        # Log summary values for easy/later reference and verification
        log.info(" Peak Electric Demand [kW]: {}".format(
            round(max(buildings[b]["total_power"])/1000, 2)))
        log.info(" Total Electric Energy [MWh]: {}".format(
            round(sum(buildings[b]["total_power"])/1e6, 2)))

        ## Get district cooling data if applicable
        if buildings[b]["plant_loop"] not in ["", "None"]:
            # cooling load, convert J -> kW avg per timestep
            try:
                key = dd.index["TimeStep", None, "DistrictCooling:Facility"]
                buildings[b]["total_cooling_load"] = []
                buildings[b]["total_cooling_load"] = get_timestep_values(
                    data[key], ts_opt, aggregate, interpolate, True, log)
            except:
                missing_variable("DistrictCooling:Facility (J)", True,
                    log)
            # mass flow rate
            try:
                idx = dd.find_variable("District Cooling Mass Flow Rate")[0]
                key = dd.index[idx]
                buildings[b]["mass_flow_rate"] = []
                buildings[b]["mass_flow_rate"] = get_timestep_values(
                    data[key], ts_opt, aggregate, interpolate, False, log)
            except:
                missing_variable("District Cooling Mass Flow Rate (kg/s)", True,
                    log)

            # Verify that district cooling exists if a building is assigned to a
            # district loop
            if sum(buildings[b]["total_cooling_load"]) == 0:
                log.warning(" No district cooling was found for {}".format(
                    b))
            else:
                # Log summary values for easy/later reference and verification
                log.info(" Peak Cooling Thermal Load [kWt]: {}".format(
                    round(max(buildings[b]["total_cooling_load"]) /
                        1000, 2)))
                log.info(" Total Cooling Thermal Energy [MWht]: {}".format(
                    round(sum(buildings[b]["total_cooling_load"]) /
                        1e6, 2)))
                log.info(" Maximum district cooling mass flow rate " \
                    "[kg/s]: {}".format(
                        round(max(buildings[b]["mass_flow_rate"]), 2)))
        else:
            log.info(" No district loop assigned. Ignoring any district " \
                "cooling data in the .eso. Looking for local chiller data.")
            # Go get all the chiller timestep specs
            plant_loops[b] = get_chiller_data(plant_loops[b], dd, data,
                ts_opt, aggregate, interpolate, log)

    # Aggregate the district cooling data for load and flow
    for p in plant_loops:
        if p not in buildings:
            load = [0 for i in range(8760*ts_opt)]
            flow = [0 for i in range(8760*ts_opt)]
            for b in buildings:
                if buildings[b]["plant_loop"] == p:
                    for t in range(8760*ts_opt):
                        load[t] += buildings[b]["total_cooling_load"][t]
                        flow[t] += buildings[b]["mass_flow_rate"][t]

            plant_loops[p]["district_cooling_load"] = load
            plant_loops[p]["district_mass_flow"] = flow

    return buildings, plant_loops
#-------------------------------------------------------------------------------
def plants(input_path, buildings, plant_loops, ts_opt, log):
    # get plant loop data from .eso's in district_sim folder

    for p in plant_loops:
        # Skip if not a district loop
        if p in buildings:
            break
        # Load .eso
        try:
            log.info("\n Loading {}...".format(p))
            dd,data = esoreader.read(os.path.join(
                input_path, "district_sim", "{}.eso".format(p)))
            log.info("...completed")
        except:
            log.error("Failed to find or load .eso file for specified plant")
            log.info("Program terminated early!")
            sys.exit("See log file")
            
        # Get total facility electricity and check file length
        key = dd.index["TimeStep", None, "Electricity:Facility"]
        interpolate, aggregate = check_file_length(data, key, ts_opt, log)

        ## Get facility total electric power at ts_opt
        # For the plant loops this will include both chillers and pumps
        # All other electric loads should be zero
        plant_loops[p]["total_power"] = get_timestep_values(
            data[key], ts_opt, aggregate, interpolate, True, log)
        # Log summary values for easy/later reference and verification
        log.info(" Peak Electric Demand [kW]: {}".format(
            round(max(plant_loops[p]["total_power"])/1000, 2)))
        log.info(" Total Electric Energy [MWh]: {}".format(
            round(sum(plant_loops[p]["total_power"])/1e6, 2)))

        # Go get all the chiller timestep specs
        plant_loops[p] = get_chiller_data(plant_loops[p], dd, data,
            ts_opt, aggregate, interpolate, log)

    return plant_loops
