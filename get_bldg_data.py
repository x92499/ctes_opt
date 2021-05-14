## get_bldg_data.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# March 5, 2021
#
## The purpose of this code is to open all the .eso files and parse them to
# get essential building-related data:
# * total facility electric load
# * cooling loads by chiller (thermal)
# * cooling electric loads by chiller
# * temperature setpoint data by chiller/plant loop (if available)
# * district cooling loads (thermal, if available)

import csv
import esoreader
import os
import sys

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

def get_community_totals(community, bldgs, ts_opt, log):
    # This module sums up all the data from each building into community totals

    for t in range(8760 * ts_opt):
        # total community electric power
        v = sum([bldgs[b]["facility"]["total_elec"][t] for b in bldgs])
        community["total_elec"].append(v)
        # total cooling electric power (not including district cooling)
        cv = 0
        for b in bldgs:
            bv = 0
            for c in bldgs[b]["chillers"]:
                bv += bldgs[b]["chillers"][c]["power"][t]
            bldgs[b]["facility"]["cool_elec"].append(bv)
            cv += bv
        community["cool_elec"].append(cv)

        # get cooling loads by district plant loop
        for d in community["district_loops"]:
            dv = 0
            mv = 0
            for b in bldgs:
                if len(bldgs[b]["facility"]["district_cool"]) > 0:
                    if b.strip(".eso") in community["district_loops"][d]["bldgs"]:
                        dv += bldgs[b]["facility"]["district_cool"][t]
                        try:
                            mv += bldgs[b]["facility"]["district_cool_m_dot"][t]
                        except:
                            mv += 0
            community["district_loops"][d]["load"].append(dv)
            community["district_loops"][d]["m_dot"].append(mv)

        # district cooling load and mass flow rate
        cv = 0
        mv = 0
        for b in bldgs:
            if len(bldgs[b]["facility"]["district_cool"]) > 0:
                cv += bldgs[b]["facility"]["district_cool"][t]
        community["district_cool"].append(cv)

        ## district cooling electric power -> In calc_chiller_params

        # total cooling load (W_th)
        cv = 0
        for b in bldgs:
            bv = 0
            for c in bldgs[b]["chillers"]:
                bv += bldgs[b]["chillers"][c]["load"][t]
            bldgs[b]["facility"]["cool_load"].append(bv)
            cv += bv
        community["cool_load"].append(cv)

    # number of chiller plants
    cv = 0
    for b in bldgs:
        cv += len(bldgs[b]["chillers"])
    for d in community["district_loops"]:
        cv += 1
    community["plant_count"] = cv
    # number of buildings
    community["building_count"] = len(bldgs)

    return community

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

def get_chiller_specs(in_path, b, i, log):
    # This method gets all the pertinent chiller data from the chiller.dat file
    # b is the dict containing all the building data, i is the .eso file name,
    # which also serves as the building identifier
    for j in b[i]["chillers"]:
        with open(os.path.join(in_path, j), "r") as f:
            # chiller name
            name = f.readline().strip("\n")
            b[i]["chillers"][j]["name"] = name.upper()
            # chiller rated COP and minimum PLR
            v = f.readline().split(",")
            b[i]["chillers"][j]["rated_cop"] = float(v[0])
            b[i]["chillers"][j]["plr_min"] = float(v[1])
            # Skip the line containing type and condenser multiplier - UNUSED
            f.readline()
            # Cap_fT coefficients
            v = f.readline().split(",")
            b[i]["chillers"][j]["coeffs_cap_ft"] = [float(k) for k in v]
            # Cap_fT limits and warnings - get min ambient temp
            v = f.readline().split(",")
            if float(v[0]) > 0:
                log.warning(" The capacity as a function of temperature " \
                    "curve for chiller '{}' does not extend below freezing. " \
                    "The curve will be extrapolated by this script. Users " \
                    "must verify the validity of this assumption.".format(
                        name))
            b[i]["chillers"][j]["cap_ft_minT"] = v[2]
            # Eir_fT coefficients
            v = f.readline().split(",")
            b[i]["chillers"][j]["coeffs_eir_ft"] = [float(k) for k in v]
            # Eir_fT limits and warnings - get min ambient temp
            v = f.readline().split(",")
            if float(v[0]) > 0:
                log.warning(" The EIR as a function of temperature " \
                    "curve for chiller '{}' does not extend below freezing. " \
                    "The curve will be extrapolated by this script. Users " \
                    "must verify the validity of this assumption.".format(
                        name))
            b[i]["chillers"][j]["eir_ft_minT"] = v[2]
            # Eir_fPLR coefficients
            v = f.readline().split(",")
            b[i]["chillers"][j]["coeffs_eir_plr"] = [float(k) for k in v]

    return b

def run(in_path, bldgs, chillers, ts_opt, log):
    # log progress
    log.info("** Getting building simulation results **")

    ## create index of desired variables:
    # [short name, .eso variable name, required?]
    timestep_variables = [
        ["load", "Chiller Evaporator Cooling Rate", True],
        ["power", "Chiller Electricity Rate", True],
        ["plr", "Chiller Part Load Ratio", False],
        ["cop", "Chiller COP", False],
        ["T_e_in", "Chiller Evaporator Inlet Temperature", True],
        ["T_e_out", "Chiller Evaporator Outlet Temperature", False],
        ["m_dot", "Chiller Evaporator Mass Flow Rate", True]]

    ## set up empty hashes and arrays
    b = {}
    community = {
        "total_elec": [],
        "cool_elec": [],
        "cool_load": [],
        "district_cool": [],
        "plant_count": None,
        "building_count": None,
        "peak_demand": [],
        "district_loops": {}
    }
    # get district loop assignments and create empty district hashes
    with open(os.path.join(in_path, "districts.dat"), "r", newline="") as f:
        rdr = csv.reader(f, dialect="excel", delimiter=",")
        for row in rdr:
            community["district_loops"][row[0]] = {
                "bldgs": [i.replace(" ","") for i in row[1:]],
                "capacity": None,
                "rated_cop": None,
                "plr_min": None,
                "load": [],
                "power": [],
                "plr": [],
                "cop": [],
                "T_e_in": [],
                "T_e_out": [],
                "m_dot": [],
                "coeffs_cap_ft": [],
                "cap_ft_minT": [],
                "coeffs_eir_ft": [],
                "limits_eir_ft": [],
                "coeffs_eir_plr": [],
                "segment_slopes": [],
                "segment_ranges": [],
                "partial_storage_timesteps": [],
                "full_storage_timesteps": [],
                "charge_capacity": [],
                "charge_power": [],
                "charge_timesteps": []
            }
    for i in bldgs:
        b[i] = {
            "facility": {
                "bldg_name": i.split(".")[0],
                "total_elec": [],
                "cool_elec": [],
                "cool_load": [],
                "district_cool": [],
                "district_cool_m_dot": []
            },
            "chillers": {}
        }
        for j in chillers:
            if i.strip(".eso") in j:
                b[i]["chillers"][j] = {
                    "name": "",
                    "capacity": None,
                    "rated_cop": None,
                    "plr_min": None,
                    "coeffs_cap_ft": [],
                    "cap_ft_minT": [],
                    "coeffs_eir_ft": [],
                    "limits_eir_ft": [],
                    "coeffs_eir_plr": [],
                    "segment_slopes": [],
                    "segment_ranges": [],
                    "partial_storage_timesteps": [],
                    "full_storage_timesteps": [],
                    "charge_capacity": [],
                    "charge_power": [],
                    "charge_timesteps": []}
                for tv in timestep_variables:
                    b[i]["chillers"][j][tv[0]] = []

    ## Iterate through each building and capture data
    for i in b:
        log.info("Loading '{}'...".format(i))
        print("Loading '{}'".format(i))

        # load .eso
        try:
            dd, data = esoreader.read(os.path.join(in_path, i))
            log.info("Complete".format(i))
        except:
            log.warning("Load failed! Building will not be included.")

        interpolate = 0
        aggregate = 0

        # Get total facility electricity and check file length
        key = dd.index["TimeStep", None, "Electricity:Facility"]

        if len(data[key]) < 8760 or len(data[key]) % 8760 != 0:
            log.error(" .eso file does not contain a 1-year simulation")
            log.info("Program terminated early!")
            sys.exit("Failed in 'get_bldg_data' module")
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

        ## Get non-timestep chiller data
        b = get_chiller_specs(in_path, b, i, log)

        ## Get timestep facility and chiller data
        # Get facility total electric power at ts_opt
        b[i]["facility"]["total_elec"] = get_timestep_values(
            data[key], ts_opt, aggregate, interpolate, True, log)
        print(" Peak Non-Cooling Electric [kW]: {}".format(
            round(max(b[i]["facility"]["total_elec"])/1000, 2)))
        print(" Total Non-Cooling Electric [MWh]: {}".format(
            round(sum(b[i]["facility"]["total_elec"])/1e6, 2)))
        # Get district cooling at ts_opt (OPTIONAL)
        try:
            key = dd.index["TimeStep", "DISTRICT COOLING",
                "District Cooling Chilled Water Rate"]
            b[i]["facility"]["district_cool"] = get_timestep_values(
                data[key], ts_opt, aggregate, interpolate, False, log)
        except:
            missing_variable("District Cooling Rate (W)", False, log)
            log.info("Trying 'DistrictCooling:Facility (J)' instead")
            try:
                key = dd.index["TimeStep", None, "DistrictCooling:Facility"]
                b[i]["facility"]["district_cool"] = get_timestep_values(
                    data[key], ts_opt, aggregate, interpolate, True, log)
            except:
                missing_variable("DistrictCooling:Facility (J)", False, log)

        # Get district cooling mass flow at ts_opt (OPTIONAL)
        try:
            key = dd.index["TimeStep", "DISTRICT COOLING",
                "District Cooling Mass Flow Rate"]
            b[i]["facility"]["district_cool_m_dot"] = get_timestep_values(
                data[key], ts_opt, aggregate, interpolate, False, log)
        except:
            missing_variable("District Cooling Mass Flow Rate (kg/s)", False, log)

        print(" Peak Cooling Load [kW_th]: {}".format(
            round(max(b[i]["facility"]["district_cool"])/1000, 2)))
        print(" Total Cooling Load [MWh_th]: {}".format(
            round(sum(b[i]["facility"]["district_cool"])/1e6, 2)))

        # get chiller variables at ts_opt
        idx = 0
        for j in b[i]["chillers"]:

            # get nominal capacity (reported by timestep, saved as scalar)
            try:
                key = dd.index["RunPeriod", "EMS",
                    "Chiller{} Nominal Capacity".format(idx)]
                cap = round(float(data[key][0]), 3)
                b[i]["chillers"][j]["capacity"] = cap
            except:
                missing_variable("Chiller{} Nominal Capacity".format(idx),
                    True, log)

            # get the desired variables
            for tv in timestep_variables:
                try:
                    key = dd.index["TimeStep",
                        b[i]["chillers"][j]["name"], tv[1]]
                    b[i]["chillers"][j][tv[0]] = get_timestep_values(
                        data[key], ts_opt, aggregate, interpolate, False, log)
                except:
                    missing_variable(tv[1], tv[2], log)

            idx += 1

        # Report no chillers if applicable:
        if len(b[i]["chillers"]) == 0:
            log.info(" No chiller data loaded for this building; using " \
                "district cooling instead")
            if sum(b[i]["facility"]["district_cool"]) == 0:
                log.info(" No district cooling found either; this may be a " \
                    "candidate for packaged thermal storage")

    community = get_community_totals(community, b, ts_opt, log)

    return b, community
