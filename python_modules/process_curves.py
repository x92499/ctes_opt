## Performance Curve Pre-Process for CTES Optimizatoin
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Initiated: May 14, 2021
# Completed:
# Revised:

## Description:
# This script loads the performance curve data for chillers and processes
# all the curves for chiller, and ctes performance

import csv
import numpy as np
import os
import sys

# Custom Modules
from curves import Quad, BiQuad

#-------------------------------------------------------------------------------
## Get the chiller data from files
def load_chiller_models(buildings, p, loop, dir, log):
    log.info("\n Processing plant loop: {}".format(p))
    # Load all the chiller data files:
    for file in os.listdir(dir):
        if file.startswith("{}_chiller".format(p)):
            with open(os.path.join(dir, file), "r") as f:
                # Get chiller name - used as dict key
                name = f.readline().strip("\n").upper()
                log.info("Processing chiller: {}".format(name))
                log.info("Chiller data loaded from {}".format(
                    os.path.join(dir, file)))
                # chiller rated COP and minimum PLR
                v = f.readline().split(",")
                loop[name]["rated_cop"] = float(v[0])
                loop[name]["plr_min"] = float(v[1])
                # chiller type (air vs water-cooled) and condenser multiplier
                v = f.readline().split(",")
                loop[name]["type"] = v[0]
                loop[name]["Pc_fan"] = float(v[1])
                # Cap_fT coefficients
                v = f.readline().split(",")
                loop[name]["coeffs_cap_ft"] = [
                    float(k) for k in v]
                # Cap_fT limits and warnings - get min ambient temp
                v = f.readline().split(",")
                if float(v[0]) > 0:
                    log.warning(" The capacity as a function of " \
                        "temperature curve for chiller '{}' does not " \
                        "extend below freezing. The curve will be " \
                        "extrapolated by this script. Users " \
                        "must verify the validity of this " \
                        "assumption.".format(name))
                loop[name]["cap_ft_minT"] = float(v[2])
                # Eir_fT coefficients
                v = f.readline().split(",")
                loop[name]["coeffs_eir_ft"] = [
                    float(k) for k in v]
                # Eir_fT limits and warnings - get min ambient temp
                v = f.readline().split(",")
                if float(v[0]) > 0:
                    log.warning(" The EIR as a function of temperature " \
                        "curve for chiller '{}' does not extend below " \
                        " freezing. The curve will be extrapolated by " \
                        "this script. Users must verify the validity " \
                        "of this assumption.".format(name))
                loop[name]["eir_ft_minT"] = float(v[2])
                # Eir_fPLR coefficients
                v = f.readline().split(",")
                loop[name]["coeffs_eir_plr"] = [
                    float(k) for k in v]

    return loop
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
        val = BiQuad(c_cT, v, Tdb)
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
    Te_o = np.linspace(Tl_s, Te_o_max, 30)
    cap_fT = []
    for v in Te_o:
        val = BiQuad(c_cT, v, Tdb)
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
        val = Quad(c_eP, v)
        eir_fP.append(val)

    # Generate Eir_fT curve
    for v in Te_o:
        val = BiQuad(c_eT, v, Tdb)
        eir_fT.append(val)

    ## Get chiller power - evaporator component
    for i in range(len(Te_o)):
        Pe.append(Q_av[i] / cop_ref * eir_fT[i] * eir_fP[i])

    ## Get chiller power - condensor component
    Pc = [Pe[i] * Pc_fan for i in range(len(Te_o))]

    ## Get total chiller power (modified to be a change in chiller power as load is shed)
    P = (Pe[0] + Pc[0]) - [Pe[i] + Pc[i] for i in range(len(Te_o))]

    ## Get load shed from Te_o
    Y = m_dot * cp * (Te_i - Te_o)
    Y = Y[::-1]

    # Get linear regression over region above min plr
    seg_sz = len(Te_o)//segs
    slopes = []
    ranges = []

    for i in range(segs):
        ranges.append(Y[(i+1)*seg_sz-1] - Y[i*seg_sz])
        slopes.append(np.polyfit(Y[i*seg_sz:(i+1)*seg_sz+1], P[i*seg_sz:(i+1)*seg_sz+1], 1)[0])

    return slopes, ranges
#-------------------------------------------------------------------------------
def chiller_electric_eir_charging(Q_ref, cop_ref, c_cT, c_eT, c_eP, m_dot,
    P_current, Q_current, Pc_fan, Tdb, Te_i, Te_chg, cp_loop, cp_chg):
    # This method calculates the available chiller capacity for ice charging
    # and the coefficient for determining increased power demand when charging
    # PLR is assumed to be 1.0 during ice charing

    # Define cp ratio
    cp_ratio = cp_chg/cp_loop

    # Penalize condenser (indirectly the pumps...)
    Pc_fan += 0.05

    # Find Q_av at charging conditions
    cap_fT = BiQuad(c_cT, Te_chg, Tdb)
    Q_av = Q_ref * cap_fT

    # Determine the excess capacity available for ice making at t
    chg_av = max([Q_av - (Q_current / cp_ratio), 0])

    # Find Power required at ice charging conditions (min 1 kW)
    eir_fT = BiQuad(c_eT, Te_chg, Tdb)
    eir_fP = Quad(c_eP, 1.0)
    P_chg = Q_av / cop_ref * eir_fT * eir_fP
    P_chg += Pc_fan * P_chg
    if chg_av > 1000:
        chg_coeff = (P_chg - P_current) / chg_av    #kWe/kWth
    else:
        chg_av = 0
        chg_coeff = 10

    return chg_av, chg_coeff
#-------------------------------------------------------------------------------
def set_properties(chiller, fluid):
    # Sets the ratio of the properties of the working fluid between charging
    # and normal operating conditions (property at T_chg / property at T_ls)
    # T_chg is here assumed to be -5C and T_ls is assumed 6.67C. These provide
    # conservative estimates to the property ratios.

    chiller["fluid"] = fluid
    if fluid == "GlycolEth30":
        chiller["cp_Tl_s"] = 3778  # units: J/kg-K
        chiller["cp_T_chg"] = 3753
        #maybe add viscocity ratios to adjust pump power!
    elif fluid == "GlycolEth40":
        chiller["cp_Tl_s"] = 3612  # units: J/kg-K
        chiller["cp_T_chg"] = 3582

    # Set charge temperature
    chiller["T_charge"] = -5   #C

    return chiller
#-------------------------------------------------------------------------------
def build_chiller_curves(p, chiller, segments, Twb, Tdb, log):
    # Set up empty arrays
    chiller["charge_capacity"] = []
    chiller["charge_power"] = []
    chiller["charge_timesteps"] = []
    chiller["full_storage_timesteps"] = []
    chiller["partial_storage_timesteps"] = []
    chiller["segment_slopes"] = []
    chiller["segment_ranges"] = []

    # Create short name variables for non time-dependent values
    capacity = max(chiller["evap_cooling_rate"])
    c_cT = chiller["coeffs_cap_ft"]
    c_eP = chiller["coeffs_eir_plr"]
    c_eT = chiller["coeffs_eir_ft"]
    cp_chg = chiller["cp_T_chg"]
    cp_loop = chiller["cp_Tl_s"]
    cop_ref = chiller["rated_cop"]
    Pc_fan = chiller["Pc_fan"]
    plr_min = chiller["plr_min"]
    T_chg = chiller["T_charge"]
    Tc_min = chiller["cap_ft_minT"]
    Te_min = chiller["eir_ft_minT"]

    ## Iterate through all timesteps
    for t in range(len(chiller["evap_cooling_rate"])):
        # Create short-name variables for use in this program:
        m_dot = chiller["mass_flow_rate"][t]
        load = chiller["evap_cooling_rate"][t]
        plr = chiller["part_load_ratio"][t]
        power = chiller["electricity_rate"][t]
        Te_i = chiller["evap_inlet_temp"][t]
        Tl_s = chiller["evap_outlet_temp"][t]

        # Select proper temperature value based on chiller type
        if chiller["type"] == "AirCooled":
            Ta = Tdb[t]
        elif chiller["type"] == "WaterCooled":
            Ta = Twb[t]
        else:
            log.warning("Chiller type error. Assuming air-cooled model.")
            Ta = Tdb[t]
        # Check for minimum temperature limits
        Ta = max(max(Ta, Tc_min), Te_min)

        ## Create segmented discharge curve
        if t == 0:
            log.info(" Building segmented chiller load reduction " \
                "curve (Discharge)")
        # Prep to build curve over cooling load region
        Te_o = np.linspace(Tl_s, Te_i, 100)
        # Get segment slopes and ranges
        slopes, ranges = chiller_electric_eir(capacity, cop_ref, plr_min,
            c_cT, c_eT, c_eP, m_dot, power, load, cp_loop, Pc_fan, Ta,  Tl_s,
            Te_i, Te_o, segments, t)
        chiller["segment_slopes"].append(slopes)
        chiller["segment_ranges"].append(ranges)
        # Build indexed sets for full/partial storage
        if load > 0:
            chiller["full_storage_timesteps"].append(t+1)
            if sum(ranges) > 0:
                chiller["partial_storage_timesteps"].append(t+1)

        ## Get chiller performance at charging conditions
        charge_capacity, charge_power = chiller_electric_eir_charging(
            capacity, cop_ref, c_cT, c_eT, c_eP, m_dot, power, load, Pc_fan,
            Ta, Te_i, T_chg, cp_loop, cp_chg)

    return chiller
#-------------------------------------------------------------------------------
def run(buildings, plant_loops, input_path, segments, Twb, Tdb, log):

    # Iterate through each plant loop:
    for p in plant_loops:
        # Set appropriate directory:
        if p in buildings:
            dir = os.path.join(input_path, "building_sim")
        else:
            dir = os.path.join(input_path, "district_sim")
        # Get chiller data files
        plant_loops[p] = load_chiller_models(buildings, p, plant_loops[p],
            dir, log)
        # Iterate through chillers:
        for c in plant_loops[p]:
            # Skip the district level data  and only iterate through chillers
            if c in ["district_cooling_load", "district_mass_flow",
                "total_power"]:
                continue

            # Set working fluid properties
            plant_loops[p][c] = set_properties(plant_loops[p][c], "GlycolEth40")
            # Build chiller load reduction curves
            plant_loops[p][c] = build_chiller_curves(p, plant_loops[p][c],
                segments, Twb, Tdb, log)


            # with open("check_ranges.csv", "w", newline="") as f:
            #     wtr = csv.writer(f, dialect="excel")
            #     for v in plant_loops[p][c]["segment_ranges"]:
            #         wtr.writerow([v])
            # sys.exit()

    return plant_loops
