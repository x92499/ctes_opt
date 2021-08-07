# buildings.py
# CTES Optimization Processor
# Process building energy simulation files
# Karl Heine, kheine@mines.edu, heinek@erau.edu
# July 2021

import csv
import esoreader
import json
import os
import sys

import data_writer

def run(project, log):
    log.info('Executing buildings.run')
    # Create dictionary for all preprocess data
    preprocess = {}
    district_flag = False
    # Load program_manager.json to obtain timestep information
    with open(os.path.join(project, 'program_manager.json'), 'r') as f:
        preprocess['program_manager'] = json.load(f)
    f.close()
    # Load community_schema.json and initialize indices
    with open(os.path.join('ctes_resources', 'schemas',
        'community_schema.json'), 'r') as f:
        preprocess['community'] = json.load(f)
    f.close()
    # Get weather data
    log.info("Getting weather data")
    wx = os.listdir(os.path.join(project, 'weather_files'))
    if len(wx) > 1:
        msg = 'Too many weather files present. Only one .epw allowed'
        log.error(msg)
        sys.exit(msg)
    else:
        preprocess["weather"] = weather(os.path.join(
            project, 'weather_files', wx[0]),
            preprocess['program_manager']['timesteps'], log)
    # Open ctes_district.csv and begin processing building energy simulation
    # data files
    with open(os.path.join(project, 'ctes_district.csv'), 'r') as p:
        # Skip header
        line = p.readline().strip("\n")
        # Get first building id, name, ctes type
        line = p.readline().strip("\n")
        # Iterate through buildings in .csv file
        while len(line.split(",")) > 1:
            # Parse line
            [id, bldg, type] = line.split(",")
            preprocess['community']['building_names'].append(bldg)
            # Call appropriate method
            if type == 'rtu':
                # Call rtu method
                preprocess = rtu(preprocess, bldg, log)
            elif type == 'chiller':
                # Call chiller method
                preprocess = chiller(preprocess, bldg, log)
            elif type == "SET BEFORE RUNNING!":
                print("Error! Must specify HVAC/CTES type before running.")
            else:
                # Call district cooling aggregator
                district_flag = True
                preprocess = district_aggregator(preprocess, bldg, type, log)
                if type not in preprocess['community']['district_plant_names']:
                    preprocess['community']['district_plant_names'].append(type)
            # Advance to the next building
            line = p.readline().strip("\n")
        # Execute district loop setup actions if flag exists
        if district_flag:
            msg = "District cooling loop identified. Program will exit so " \
                "that you may perform district plant simulations before " \
                "proceeding."
            print(msg)
            log.warning(msg)
            for d in preprocess['community']['district_plant_names']:
                data_writer.plant_load_profiles(d, preprocess[d],
                    os.path.join(project, "project_workspace"), log)
    return preprocess
#-------------------------------------------------------------------------------
# Method to process buildings with district cooling
def district_aggregator(prep, bldg, type, log):
    print("District Coolings")
    log.info("Processing {} for district cooling".format(bldg))
    # Setup useful objects
    prep[bldg] = {}
    ts = prep['program_manager']['timesteps']
    # Open and read .eso file:
    dd, data = esoreader.read(os.path.join(
        prep['program_manager']['project_name'],'building_simulations',
        bldg + '.eso'))
    log.info(" Loaded .eso file")
    # Get total facility electricity and check file length
    key = dd.index["TimeStep", None, "Electricity:Facility"]
    interpolate, aggregate = check_file_length(data, key, ts, log)
    # Load total facility electricity data into preprocessor dictionary
    prep[bldg]["rate_electricity_W"] = get_timestep_values(data[key], ts,
        aggregate, interpolate, True, log)
    # Load district cooling rate
    key = dd.index["TimeStep", None, "DistrictCooling:Facility"]
    prep[bldg]["rate_cooling_district_Wt"] = get_timestep_values(
        data[key], ts, aggregate, interpolate, True, log)
    # Load district cooling mass flow rate
    dmf = dd.find_variable("District Cooling Mass Flow Rate")[0]
    key = dd.index[dmf]
    prep[bldg]["mass_flow_district_kg_s"] = get_timestep_values(
        data[key], ts, aggregate, interpolate, False, log)
    # Log summary values for easy/later reference and verification
    log.info(" Peak Cooling Thermal Load [kWt]: {}".format(
        round(max(prep[bldg]["rate_cooling_district_Wt"]) /
            1000, 2)))
    log.info(" Total Cooling Thermal Energy [MWht]: {}".format(
        round(sum(prep[bldg]["rate_cooling_district_Wt"]) /
            1e6, 2)))
    log.info(" Maximum district cooling mass flow rate " \
        "[kg/s]: {}".format(
            round(max(prep[bldg]["mass_flow_district_kg_s"]), 2)))
    # Create district (if it doesn't exist)
    if type in prep:
        pass
    else:
        prep[type] = {}
        prep[type]["rate_cooling_district_Wt"] = [0 for i in range(len(
            prep[bldg]["rate_cooling_district_Wt"]))]
        prep[type]["mass_flow_district_kg_s"] = [0 for i in range(len(
            prep[bldg]["mass_flow_district_kg_s"]))]
    # Aggregate results
    for t in range(len(prep[bldg]["rate_cooling_district_Wt"])):
        prep[type]["rate_cooling_district_Wt"][t] += (
            prep[bldg]["rate_cooling_district_Wt"][t])
        prep[type]["mass_flow_district_kg_s"][t] += (
            prep[bldg]["mass_flow_district_kg_s"][t])
    return prep
#-------------------------------------------------------------------------------
# Method to process buildings with chillers
def chiller(prep, bldg, log):
    log.info("Processing {} for central CTES optimization".format(bldg))
    # Setup useful objects
    prep[bldg] = {}
    ts = prep['program_manager']['timesteps']
    # Open and read .eso file:
    dd, data = esoreader.read(os.path.join(
        prep['program_manager']['project_name'],'building_simulations',
        bldg + '.eso'))
    log.info(" Loaded .eso file")
    # Get total facility electricity and check file length
    key = dd.index["TimeStep", None, "Electricity:Facility"]
    interpolate, aggregate = check_file_length(data, key, ts, log)
    # Load total facility electricity data into preprocessor dictionary
    prep[bldg]["rate_electricity_W"] = get_timestep_values(data[key], ts,
        aggregate, interpolate, True, log)
    prep[bldg]['rate_elec_cooling_W'] = [0 for i in range(len(
        prep[bldg]['rate_electricity_W']))]
    prep[bldg]['rate_elec_non_cooling_W'] = prep[bldg]['rate_electricity_W']
    # Get chiller cooling rates and extract chiller names
    cecr = dd.find_variable("Chiller Evaporator Cooling Rate")
    chiller_names = [v[1] for v in cecr]
    # Iterate through chillers
    for idx in range(len(chiller_names)):
        # Short chiller name variable
        cname = chiller_names[idx]
        # Advance indices
        prep['community']['chiller_count'] += 1
        prep['community']['plant_count'] += 1
        # Setup chiller schema
        c = "chiller{}".format(idx)
        with open(os.path.join('ctes_resources', 'schemas',
            'chiller_schema.json'), 'r') as f:
            prep[bldg][c] = json.load(f)
        f.close()
        # Set constants
        prep[bldg][c]['building'] = bldg
        prep[bldg][c]['name'] = cname
        prep[bldg][c]['index'] = prep['community']['plant_count']
        # Load values from chillerXX.dat file
        prep[bldg][c] = chiller_data(prep[bldg][c], bldg, c, os.path.join(
            prep['program_manager']['project_name'], 'building_simulations'),
            log)
        # Load timeseries data
        # Chiller evaporator cooling rate
        key = dd.index["TimeStep", cname, "Chiller Evaporator Cooling Rate"]
        prep[bldg][c]["rate_cooling_Wt"] = get_timestep_values(
        data[key], ts, aggregate, interpolate, False, log)
        # Chiller electricity rate (cooling electricity)
        key = dd.index["TimeStep", cname, "Chiller Electricity Rate"]
        prep[bldg][c]["rate_electricity_W"] = get_timestep_values(
        data[key], ts, aggregate, interpolate, False, log)
        # Chiller part load ratio
        key = dd.index["TimeStep", cname, "Chiller Part Load Ratio"]
        prep[bldg][c]["plr"] = get_timestep_values(
        data[key], ts, aggregate, interpolate, False, log)
        # Chiller mass flow rate
        key = dd.index["TimeStep", cname, "Chiller Evaporator Mass Flow Rate"]
        prep[bldg][c]["mass_flow_evap_kg_s"] = get_timestep_values(
            data[key], ts, aggregate, interpolate, False, log)
        # Chiller evaporator inlet temperature
        key = dd.index["TimeStep", cname,"Chiller Evaporator Inlet Temperature"]
        prep[bldg][c]["temp_evap_inlet_C"] = get_timestep_values(
            data[key], ts, aggregate, interpolate, False, log)
        # Chiller evaporator outlet temperature (assume 44F if missing)
        try:
            key = dd.index["TimeStep", cname,
                "Chiller Evaporator Outlet Temperature"]
            prep[bldg][c]["temp_evap_inlet_C"] = get_timestep_values(
                data[key], ts, aggregate, interpolate, False, log)
        except:
            prep[bldg][c]["temp_evap_outlet_C"] = [
                6.67 for i in range(len(prep[bldg][c]["rate_cooling_Wt"]))]
        # Calculate chiller cop for the timestep
        prep[bldg][c]["cop"] = [i / j if j > 0 else 99 for i,j in zip(
            prep[bldg][c]["rate_electricity_W"],
            prep[bldg][c]["rate_cooling_Wt"])]
        # Total cooling electricity and non-cooling electricity rates
        for t in range(len(prep[bldg][c]['rate_electricity_W'])):
            prep[bldg]['rate_elec_cooling_W'][t] += (
                prep[bldg][c]['rate_electricity_W'][t])
            prep[bldg]['rate_elec_non_cooling_W'][t] += -(
                prep[bldg][c]['rate_electricity_W'][t])
            if prep[bldg][c]['rate_electricity_W'][t] > 0:
                prep[bldg][c]['timesteps_load'].append(t+1)
    return prep
#-------------------------------------------------------------------------------
# Method to get chiller data from chillerXX.dat files
def chiller_data(chiller, building_name, chiller_name, path, log):
    # Open .dat file - error if missing
    try:
        with open(os.path.join(path, "{}_{}.dat".format(building_name,
            chiller_name)), 'r') as f:
            # Get chiller name - used as dict key
            name = f.readline().strip("\n").upper()
            log.info("Processing chiller: {}".format(name))
            # chiller rated COP and minimum PLR
            v = f.readline().split(",")
            chiller["cop_reference"] = float(v[0])
            chiller["curves"]["plr_min"] = float(v[1])
            # chiller type (air vs water-cooled) and condenser multiplier
            v = f.readline().split(",")
            chiller["type"] = v[0]
            chiller["condenser_fan_power_fraction"] = float(v[1])
            # Cap_fT coefficients
            v = f.readline().split(",")
            chiller['curves']["coeffs_cap_ft"] = [float(k) for k in v]
            # Cap_fT limits and warnings - get min ambient temp
            v = f.readline().split(",")
            if float(v[0]) > 0:
                log.warning(" The capacity as a function of temperature " \
                    "curve for chiller '{}' does not extend below " \
                    "freezing. The curve will be extrapolated by this script." \
                    "Users must verify the validity of this " \
                    "assumption.".format(name))
            chiller['curves']["temp_min_C"] = float(v[2])
            # Eir_fT coefficients
            v = f.readline().split(",")
            chiller['curves']["coeffs_eir_ft"] = [float(k) for k in v]
            # Eir_fT limits and warnings - get min ambient temp
            v = f.readline().split(",")
            if float(v[0]) > 0:
                log.warning(" The EIR as a function of temperature " \
                    "curve for chiller '{}' does not extend below " \
                    " freezing. The curve will be extrapolated by " \
                    "this script. Users must verify the validity " \
                    "of this assumption.".format(name))
            chiller['curves']["eir_ft_minT"] = max(float(v[2]),
                chiller['curves']["temp_min_C"])
            # Eir_fPLR coefficients
            v = f.readline().split(",")
            chiller['curves']["coeffs_eir_plr"] = [float(k) for k in v]
    except:
        log.error("Chiller data file missing for {}: {}".format(
            building_name, chiller_name))
    return chiller
#-------------------------------------------------------------------------------
# Method to process buildings with RTU's
def rtu(prep, bldg, log):
    log.info("Processing {} for UTSS optimization".format(bldg))
    # Setup useful objects
    prep[bldg] = {}
    ts = prep['program_manager']['timesteps']
    # Open and read .eso file:
    dd, data = esoreader.read(os.path.join(
        prep['program_manager']['project_name'],'building_simulations',
        bldg + '.eso'))
    log.info(" Loaded .eso file")
    # Get total facility electricity and check file length
    key = dd.index["TimeStep", None, "Electricity:Facility"]
    interpolate, aggregate = check_file_length(data, key, ts, log)
    # Load total facility electricity data into preprocessor dictionary
    prep[bldg]['rate_electricity_W'] = get_timestep_values(data[key], ts,
        aggregate, interpolate, True, log)
    prep[bldg]['rate_elec_cooling_W'] = [0 for i in range(len(
        prep[bldg]['rate_electricity_W']))]
    prep[bldg]['rate_elec_non_cooling_W'] = prep[bldg]['rate_electricity_W']
    # Collect data variables from .eso
    cr = dd.find_variable('Cooling Coil Total Cooling Rate')
    er = dd.find_variable('Cooling Coil Electricity Rate')
    wb = dd.find_variable('System Node Wetbulb Temperature')
    # Iterate through all rtu's
    for j in range(len(cr)):
        # Advance indices
        prep['community']['rtu_count'] += 1
        prep['community']['plant_count'] += 1
        # Setup rtu schema
        rtu = "rtu{}".format(j)
        with open(os.path.join('ctes_resources', 'schemas',
            'rtu_schema.json'), 'r') as r:
            prep[bldg][rtu] = json.load(r)
        r.close()
        # Load constants
        prep[bldg][rtu]['building'] = bldg
        prep[bldg][rtu]['name'] = cr[j][1]
        prep[bldg][rtu]['index'] = prep['community']['plant_count']
        log.info(" Processing RTU '{}'".format(prep[bldg][rtu]['name']))
        # Load timeseries values - all are required
        # Cooling rate
        key = dd.index[cr[j]]
        prep[bldg][rtu]['rate_cooling_Wt'] = get_timestep_values(
            data[key], ts, aggregate, interpolate, False, log)
        # RTU electricity rate (cooling electricity)
        key = dd.index[er[j]]
        prep[bldg][rtu]['rate_electricity_W'] = (get_timestep_values(
                data[key], ts, aggregate, interpolate, False, log))
        # Evaporator inlet wetbulb temperature
        key = dd.index[wb[j]]
        prep[bldg][rtu]['temp_wb_evaporator_C'] = (get_timestep_values(
                data[key], ts, aggregate, interpolate, False, log))
        # COP
        prep[bldg][rtu]['cop'] = [c / e if e > 0 else 99 for c,e in zip(
            prep[bldg][rtu]['rate_cooling_Wt'],
            prep[bldg][rtu]['rate_electricity_W'])]
        # Total cooling electricity and non-cooling electricity rates
        for t in range(len(prep[bldg][rtu]['rate_electricity_W'])):
            prep[bldg]['rate_elec_cooling_W'][t] += (
                prep[bldg][rtu]['rate_electricity_W'][t])
            prep[bldg]['rate_elec_non_cooling_W'][t] += -(
                prep[bldg][rtu]['rate_electricity_W'][t])
            if prep[bldg][rtu]['rate_electricity_W'][t] > 0:
                prep[bldg][rtu]['timesteps_load'].append(t+1)
    return prep
#-------------------------------------------------------------------------------
def check_file_length(data, key, ts, log):
    # This script checks the .eso for length and timestep
    # Can't handle .eso's with multiple run periods though...
    interpolate = 0
    aggregate = 0
    if len(data[key]) < 8760 or len(data[key]) % 8760 != 0:
        log.error(" .eso file does not contain a 1-year simulation")
        log.info("Program terminated early!")
        sys.exit("Failed in 'get_sim_data' module")
    elif len(data[key]) < 8760 * ts:
        log.warning(" Building simulation timestep is greater than the " \
                    "desired optimization timestep. " \
                    "Program will continue, data will be interpolated. " \
                    "It is HIGHLY recommended that simulation fidelity " \
                    "be greater than optimization fidelity.")
        if (8760 * ts) % len(data[key]) == 0:
            interpolate = (8760 * ts) // len(data[key])
        else:
            log.error(" Building simulation and optimization timesteps " \
                "must be factors of each other")
            log.info("Program terminated early!")
            sys.exit("Timestep mis-match (interpolator)")
    elif len(data[key]) > 8760 * ts:
        log.info(" Building simulation data is of greater precision than " \
                 "the optimization timestep; data will be aggregated " \
                 "and averaged")
        if (len(data[key]) % (8760 * ts)) == 0:
            aggregate = len(data[key]) // (8760 * ts)
        else:
            log.error(" Building simulation and optimization timesteps " \
                "must be factors of each other")
            log.info("Program terminated early!")
            sys.exit("Timestep mis-match (aggregator)")
    elif len(data[key]) == 8760 * ts:
        aggregate = 1
        log.info(" Simulation and optimization timesteps match")
    # Report timesteps
    log.info(" Detected simulation timestep: {} per hour".format(
        len(data[key]) // 8760))
    return interpolate, aggregate
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
    return
#-------------------------------------------------------------------------------
def get_timestep_values(values, ts, aggregate, interpolate,
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
        for i in range((ts * 8760)):
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
# Method to get wet and drybulb temps from weather file (.epw)
def weather(wx, ts, log):
    log.info("Obtaining temperatures from weather file")
    Tdb = []
    Twb = []
    with open(wx, 'r', newline="") as f:
        rdr = csv.reader(f, delimiter=",")
        [next(rdr) for i in range(8)]
        for row in rdr:
            if len(Tdb) == 0:
                for i in range(ts):
                    Tdb.append(float(row[7]))
                    Twb.append(float(row[6]))
            else:
                wb, db = [float(v) for v in row[6:8]]
                for i in range(ts):
                    Tdb.append(Tdb[-1] + ((i+1)/ts * (db-Tdb[-1])))
                    Twb.append(Twb[-1] + ((i+1)/ts * (wb-Twb[-1])))
    # Log info and check data lengths
    if ts > 1:
        log.info("The hourly weather data was linearly interpolated " \
                 "according to the optimization timestep.")
    if len(Tdb) != len(Twb):
        log.error("The wetbulb and drybulb temperature arrays are not of " \
                  "equal length.")
        log.info("Program terminated early!")
        sys.exit("Failed in 'get_wx' module.")
    log.info("The following data was extracted from the weather file:")
    log.info(" * {} wetbulb temperatures".format(len(Twb)))
    log.info(" * {} drybulb temperatures".format(len(Tdb)))
    weather = {
        "dry_bulb_C": Tdb,
        "wet_bulb_C": Twb
    }
    return weather
#-------------------------------------------------------------------------------
# Method to process buildings with district cooling
# To be built!
