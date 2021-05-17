## get_ctes_params.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# March 17, 2021
#
## The purpose of this module is the calculate the maximum rates of charge
# and discharge for a CTES tank of given capcity for each timestep based on
# the maximum LMTD and flow rate for each tank.
#
## This script is based on ice-on-coil CTES tanks, but can be altered for dif-
# ferent CTES types if performance data is available.

## Import
from curves import Poly5
import numpy as np
import sys

## Method for "Simple" model
# Reference: EnergyPlus ThermalStorage:Ice:Simple object
# Engineering Reference v. 9.4, Section 15.1, Pages 790 ff.
# E+ 9.4 Source Code: IceThermalStorage.cc, CalcUAIce method, lines 1622-1655

def define_type(type, log):
    # Setup ctes container/dict and define parameters
    ctes = {}
    if type == 1:
        # Type 1:
        log.info(" Selected ice tank: CALMAC 1190C, 162 ton-hours nominal")
        ctes["name"] = "1190C"
        ctes["capacity"] = 570000  # Wh (162 ton-hours)
        ctes["model"] = "simple"
        ctes["melt"] = "internal"
        ctes["cost"] = 22690
        ctes["T_fz"] = 0
    else:
        log.error("No CTES model type defined.")
        log.info("Program terminated early!")
        sys.exit("See log file")

    return ctes

def simpleIce(melt, cap, T_fz, T_in, T_out, T_chg):
    # Note: capacity must be in J, all temps in C

    # set curve coefficient values - these are fixed by the model
    if melt == "internal":
        c_charge = [1.3879, -7.6333, 26.3423, -47.6084, 41.8498, -14.2948]
        c_discharge = c_charge
    elif melt == "external":
        c_charge = [1.3879, -7.6333, 26.3423, -47.6084, 41.8498, -14.2948]
        c_discharge = [1.1756, -5.3689, 17.3602, -30.1077, 25.6387, -8.5102]

    # determine max rate of discharge
    max_discharge = []
    max_charge = []
    for s in np.linspace(0.05,0.95,19):
        ua_discharge = Poly5(c_discharge, s) * cap / 3600 / 10 # W/C
        max_discharge.append(ua_discharge * (T_in - T_out) /
            np.log((T_in - T_fz) / (T_out - T_fz)))

        ua_charge = Poly5(c_charge, (1-s)) * cap / 3600 / 10
        max_charge.append(ua_charge * (-1 - T_chg) /
            np.log((T_chg - T_fz) / (-1 - T_fz)))

    return np.median(max_discharge), np.median(max_charge)

## Method for Detailed ice model

def detailedIce(melt, cap, c_chg, c_dchg):

    pass

    return


def run(plant_loops, ts_opt, type, log):
    # The CTES parameters are dependent on the plant loop to which they will be
    # attached. Therefore this module must iterate over each chiller. The CTES
    # dictionaries will be appended to the appropriate chiller dictionary.

    for p in plant_loops:
        for c in plant_loops[p]:
            #skip if c is not a chiller:
            if c in ["district_cooling_load", "district_mass_flow",
                "total_power"]:
                continue
            log.info(" Processing CTES model performance at plant '{}' " \
                "and chiller '{}'".format(p, c))

            # Define CTES type and set parameters
            type = 1
            ctes = define_type(type, log)
            log.info(ctes)
            discharge = []
            charge = []
            for t in range(8760 * ts_opt):
                if ctes["model"] == "simple":
                    dchg, chg = simpleIce(
                        ctes["melt"],
                        ctes["capacity"] * 3.6e3,   # Must convert Wh to J
                        ctes["T_fz"],
                        plant_loops[p][c]["evap_inlet_temp"][t],
                        plant_loops[p][c]["evap_outlet_temp"][t],
                        plant_loops[p][c]["T_charge"])
                else:
                    log.error("No thermal storage model defined.")
                    log.info("Program terminated early!")
                    sys.exit("See log file.")
                # Populate lists
                charge.append(chg)
                discharge.append(dchg)

            # Populate and append ctes to chiller dictionary
            ctes["max_charge"] = charge
            ctes["max_discharge"] = discharge
            plant_loops[p][c]["ctes"] = ctes

    return plant_loops
