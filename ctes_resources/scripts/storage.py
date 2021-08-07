# storage.py
# CTES Optimization Processor
# Process cool thermal energy storage models
# Karl Heine, kheine@mines.edu, heinek@erau.edu
# July 2021

import csv
import json
import numpy as np
import os
import sys

import curves

#-------------------------------------------------------------------------------
def run(project, preprocess, log):
    # load ctes_types.json
    with open(os.path.join('ctes_resources', 'data',
        'ctes_types.json'), 'r') as f:
        ctes_types = json.load(f)
    f.close()
    # iterate through buildings
    for bldg in preprocess['community']['building_names']:
        for k in preprocess[bldg].keys():
            if 'rtu' in k:
                preprocess[bldg][k] = utss(
                    preprocess[bldg][k],
                    preprocess['weather'],
                    ctes_types[preprocess['program_manager']['utss']],
                    preprocess['program_manager']['timesteps'],
                    log)
            elif 'chiller' in k:
                preprocess[bldg][k] = central(
                    preprocess[bldg][k],
                    preprocess['weather'],
                    ctes_types[preprocess['program_manager']['ctes']],
                    preprocess['program_manager']['timesteps'],
                    preprocess['program_manager']['segments'],
                    log)
    # Iterate through district plants
    for dist in preprocess['community']['district_plant_names']:
        if 'chiller' in k:
            preprocess[dist][k] = central(
                preprocess[dist][k],
                preprocess['weather'],
                ctes_types[preprocess['program_manager']['ctes']],
                preprocess['program_manager']['timesteps'],
                preprocess['program_manager']['segments'],
                log)

    return preprocess
#-------------------------------------------------------------------------------
# Method to process central CTES model for a given chiller
def central(chiller, wx, ctes, ts, segments, log):
    log.info("Processing CTES for Chiller {}".format(chiller["name"]))
    # Set cost, capacity, and lifespan
    chiller['ctes']['cost_per_kWt'] = ctes['cost_per_kWt']
    chiller['ctes']['lifespan_yrs'] = ctes['lifespan_yrs']
    chiller['ctes']['capacity_nominal_Wt'] = ctes['capacity_nominal_Wt']
    # Get chiller capacity
    capacity = max(chiller['rate_cooling_Wt'])
    max_index = chiller['rate_cooling_Wt'].index(capacity)
    plr_at_index = chiller['plr'][max_index]
    capacity = capacity / plr_at_index
    # Set useful short-name variables for constants
    c_cT = chiller["curves"]["coeffs_cap_ft"]
    c_eP = chiller["curves"]["coeffs_eir_plr"]
    c_eT = chiller["curves"]["coeffs_eir_ft"]
    cop_ref = chiller["cop_reference"]
    Pc_fan = chiller["condenser_fan_power_fraction"]
    plr_min = chiller["curves"]["plr_min"]
    T_chg = ctes["temp_charge_C"]
    T_min = chiller["curves"]["temp_min_C"]
    # Set fluid properties (Could make an external action)
    # Assume 40% Ethylene Glycol
    chiller['fluid'] = 'GlycolEth40'
    cp_chg = 3582   # kJ/kg-K
    cp_loop = 3612  # kJ/kg-K
    ## Iterate through all timesteps
    for t in range(len(chiller["rate_cooling_Wt"])):
        # Create short-name variables for use in this program:
        m_dot = chiller["mass_flow_evap_kg_s"][t]
        load = chiller["rate_cooling_Wt"][t]
        plr = chiller["plr"][t]
        power = chiller["rate_electricity_W"][t]
        Te_i = chiller["temp_evap_inlet_C"][t]
        Tl_s = chiller["temp_evap_outlet_C"][t]
        # Select proper temperature value based on chiller type
        if chiller["type"] == "AirCooled":
            Ta = wx["dry_bulb_C"][t]
        elif chiller["type"] == "WaterCooled":
            Ta = wx["wet_bulb_C"][t]
        else:
            log.warning("Chiller type error. Assuming air-cooled model.")
            Ta = wx["dry_bulb_C"][t]
        # Check for minimum temperature limits
        Ta = max(Ta, T_min)
        ## Create segmented discharge curve
        if t == 0:
            log.info(" Building segmented chiller load reduction " \
                "curve (Discharge)")
        # Prep to build curve over cooling load region
        Te_o = np.linspace(Tl_s, Te_i, 100)
        slopes, ranges = chiller_electric_eir(capacity, cop_ref, plr_min,
            c_cT, c_eT, c_eP, m_dot, power, load, cp_loop, Pc_fan, Ta,  Tl_s,
            Te_i, Te_o, segments, t)
        chiller['discharging_performance']['slopes'].append(slopes)
        chiller['discharging_performance']['ranges'].append(ranges)
        # Populate discharge timestep arrays
        if load > 0:
            chiller['discharging_performance']['timesteps'].append(t+1)
            if sum(ranges) > 0:
                chiller['discharging_performance'][
                    'timesteps_partial_storage'].append(t+1)
            else:
                chiller['discharging_performance'][
                    'timesteps_full_storage'].append(t+1)
        # Set maximum charging rate restricted by the tank (arbitrarily set at
        # C/4)
        chiller["discharging_performance"]["rate_discharge_max_Wt"].append(
            ctes["capacity_nominal_Wt"] / 4)
        ## Get chiller performance at charging conditions
        charge_capacity, charge_power = chiller_electric_eir_charging(
            capacity, cop_ref, c_cT, c_eT, c_eP, m_dot, power, load, Pc_fan,
            Ta, Te_i, T_chg, cp_loop, cp_chg)
        chiller["charging_performance"]["rate_cooling_max_Wt"].append(
            charge_capacity)
        chiller["charging_performance"]["slope"].append(
            charge_power)
        # Set minimum charging capacity to > 1000 W_th
        if charge_capacity > 1000:
            chiller["charging_performance"]["timesteps"].append(t+1)
        # Check for negative charge power coefficients
        neg_count = 0
        for v in chiller["charging_performance"]["slope"]:
            if v < 0:
                neg_count += 1
        if neg_count > 0:
            log.warning("Negative chiller power coefficients for ice " \
                "charging occured {} times; verify curves".format(
                neg_count))
            log.info("This issue is often resolved by using shorter " \
                "optimization timesteps (eg. use '-t 4') which avoids " \
                "the impact of part-load factors from simulation.")
    # Determine the maximum number of UTSS that can be installed
    # Get max cooling load and add 20% buffer
    mx = max(chiller['rate_cooling_Wt']) * 1.2
    chiller['ctes']['install_limit'] = int(mx //
        max(chiller["discharging_performance"]["rate_discharge_max_Wt"]))
    return chiller

#-------------------------------------------------------------------------------
# Method to process UTSS model for a given RTU
def utss(rtu, wx, utss, ts, log):
    log.info("Processing UTSS for RTU '{}'".format(rtu["name"]))
    # Set cost and lifespan
    rtu['utss']['cost_per_kWt'] = utss['cost_per_kWt']
    rtu['utss']['lifespan_yrs'] = utss['lifespan_yrs']
    rtu['utss']['capacity_nominal_Wt'] = utss['capacity_nominal_Wt']
    # Set useful variables
    q = utss['capacity_nominal_Wt']
    q_c = utss['rate_charge_nominal_Wt']
    q_d = utss['rate_discharge_nominal_Wt']
    cop = utss['cop_charge']
    E = utss['coeffs_eir_ft']
    C = utss['coeffs_cap_ft']
    D = utss['coeffs_cap_discharge']
    soc = utss['median_soc']
    loss = utss['rate_thermal_loss_W_K']
    # Set constants
    rtu['utss']['type'] = utss['full_name']
    # Calculate timeseries values for drybulb dependent variables
    for db in wx['dry_bulb_C']:
        # Calculate EIR and cap multipliers for charging
        eir = (E[0] + (E[1] * soc) + (E[2] * soc**2) + (E[3] * db) +
            (E[4] * db**2) + (E[5] * soc * db))
        cap = (C[0] + (C[1] * soc) + (C[2] * soc**2) + (C[3] * db) +
            (C[4] * db**2) + (C[5] * soc * db))
        # Populate dictionary
        rtu['utss']['cop_charge'].append(cop / eir)
        rtu['utss']['rate_charge_max_Wt'].append(q_c * cap)
        rtu['utss']['thermal_loss_efficiency'].append(
            1 - ((loss * db) / (q * ts)))
    # Calculate timeseries values for wetbulb dependent variables
    for wb in rtu['temp_wb_evaporator_C']:
        # Calculate cap multiplier for discharging
        dcap = D[0] + (D[1] * wb) + (D[2] * wb**2)
        dcap = max(dcap, 0)
        rtu['utss']['rate_discharge_max_Wt'].append(q_d * dcap)
    # Determine the maximum number of UTSS that can be installed
    # Get max cooling load and add 20% buffer to help cover duration
    mx = max(rtu['rate_cooling_Wt']) * 1.2
    rtu['utss']['install_limit'] = int((mx // q_d) + 1)
    # Calculate discharge effectiveness by timestep
    for v in rtu['cop']:
        rtu['utss']['discharge_effectiveness'].append(1 -
            (v / utss['cop_discharge']))
    return rtu
#-------------------------------------------------------------------------------
## Generate discharge curves using the chiller_electric_eir model
def chiller_electric_eir(Q_ref, cop_ref, plr_min, c_cT, c_eT, c_eP, m_dot,
    P_current, Q_current, cp, Pc_fan, Tdb,  Tl_s, Te_i, Te_o, segs, t):
    # This method takes chiller data from the current timestep, generates
    # the power change as a function of load reduction curve, and then approx-
    # imates the curve using a specified number of piecewise linear segments

    # Set up arrays
    cap_fT = []
    eir_fT = []
    eir_fP = []
    load = []
    Pc = []
    Pe = []
    plr = []
    Q_av = []

    ## Find the MAXIMUM evaporator outlet temperature before crossing the
    # plr_min threshold

    # Generate Cap_fT curve over full Te_o range (setpoint to entering temp)
    for v in Te_o:
        val = curves.BiQuad(c_cT, v, Tdb)
        cap_fT.append(val)
    # Generate Eir_fPLR curve
    Te_o_max = Tl_s
    plr_min_idx = 0
    for i in range(len(Te_o)):
        load.append(m_dot * cp * (Te_i - Te_o[i]))
        Q_av.append(Q_ref * cap_fT[i])
        plr.append(load[i] / Q_av[i])

        if plr_min_idx == 0 and plr[i] < plr_min:
            Te_o_max = Te_o[i-1]
            plr_min_idx = i-1
            break
    ## Return early if calculated PLR is below minimum or too close for calcs
    # buffer = 5 / 100 data points = 5%
    if plr_min_idx < 5:
        slopes = [0 for s in range(segs)]
        ranges = [0 for s in range(segs)]
        return slopes, ranges
    ## Redefine the Te_o range to only encompass Te_o_max
    Te_o = np.linspace(Tl_s, Te_o_max, 60)
    cap_fT = []
    for v in Te_o:
        val = curves.BiQuad(c_cT, v, Tdb)
        cap_fT.append(val)

    load = []
    Q_av = []
    plr = []
    for i in range(len(Te_o)):
        load.append(m_dot * cp * (Te_i - Te_o[i]))
        Q_av.append(Q_ref * cap_fT[i])
        plr.append(load[i] / Q_av[i])
        # Return early if calculated load exceeds current load
        if load[-1] > Q_current:
            slopes = [0 for s in range(segs)]
            ranges = [0 for s in range(segs)]
            return slopes, ranges
    for v in plr:
        val = curves.Quad(c_eP, v)
        eir_fP.append(val)
    # Generate Eir_fT curve
    for v in Te_o:
        val = curves.BiQuad(c_eT, v, Tdb)
        eir_fT.append(val)
    ## Get chiller power - evaporator component
    for i in range(len(Te_o)):
        Pe.append(Q_av[i] / cop_ref * eir_fT[i] * eir_fP[i])
    ## Get chiller power - condensor component
    Pc = [Pe[i] * Pc_fan for i in range(len(Te_o))]
    ## Get total chiller power (modified to be a change in chiller power as load is shed)
    P = (Pe[0] + Pc[0]) - [Pe[i] + Pc[i] for i in range(len(Te_o))]
    #P = P[::-1]
    ## Get load shed from Te_o
    Y = m_dot * cp * (Te_i - Te_o)
    Y = Y[::-1]
    Y = Y - Y[0]
    # Get linear regression over region above min plr
    seg_sz = len(Te_o)//segs
    slopes = []
    ranges = []
    for i in range(segs):
        # ranges.append(Y[(i+1)*seg_sz-1] - Y[i*seg_sz])
        ranges.append((Y[-1] - Y[0]) / segs)
        slopes.append(np.polyfit(Y[i*seg_sz:(i+1)*seg_sz+1], P[i*seg_sz:(i+1)*seg_sz+1], 1)[0])

    # check = True
    # if check and P_current > 150000:
    #     with open("chiller_curve.csv", "w", newline="") as file:
    #         wtr = csv.writer(file, delimiter=",")
    #         for i in range(len(Te_o)):
    #             wtr.writerow([Y[i], P[i], plr[i]])
    #     print(P_current, Q_current)
    #     print(P,Y)
    #     print(slopes)
    #     sys.exit()

    return slopes, ranges
#-------------------------------------------------------------------------------
def chiller_electric_eir_charging(Q_ref, cop_ref, c_cT, c_eT, c_eP, m_dot,
    P_current, Q_current, Pc_fan, Tdb, Te_i, Te_chg, cp_loop, cp_chg):
    # This method calculates the available chiller capacity for ice charging
    # and the coefficient for determining increased power demand when charging
    # PLR is assumed to be 1.0 during ice charing

    # Define cp ratio
    cp_ratio = cp_chg/cp_loop
    # Penalize condenser (indirectly the pumps...Do this with epsilon instead)
    # Pc_fan += 0.05
    # Find Q_av at charging conditions
    cap_fT = curves.BiQuad(c_cT, Te_chg, Tdb)
    Q_av = Q_ref * cap_fT
    # Determine the excess capacity available for ice making at t
    chg_av = max([Q_av - (Q_current / cp_ratio), 0])
    # Find Power required at ice charging conditions (min 1 kW)
    eir_fT = curves.BiQuad(c_eT, Te_chg, Tdb)
    eir_fP = curves.Quad(c_eP, 1.0)
    P_chg = Q_av / cop_ref * eir_fT * eir_fP
    P_chg += Pc_fan * P_chg
    if chg_av > 1000:
        chg_coeff = (P_chg - P_current) / chg_av    #kWe/kWth
    else:
        chg_av = 0
        chg_coeff = 10

    return chg_av, chg_coeff
