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
import numpy as np
import curves
import sys

## Method for "Simple" model
# Reference: EnergyPlus ThermalStorage:Ice:Simple object
# Engineering Reference v. 9.4, Section 15.1, Pages 790 ff.
# E+ 9.4 Source Code: IceThermalStorage.cc, CalcUAIce method, lines 1622-1655

def define_types():
    # Setup ctes container/dict - need to nest for multiple types
    ctes = {
        "name": "",
        "capacity": None,
        "model": "",
        "melt": "",
        "max_charge": None,
        "max_discharge": None,
        "cost": 2269,    #$/yr for 10years
        "max_charge": {},
        "max_discharge": {}
    }

    # Type 1:
    ctes["name"] = "1190C"
    ctes["capacity"] = 570000  # Wh (162 ton-hours)
    ctes["model"] = "simple"
    ctes["melt"] = "internal"

    return ctes

def simpleIce(melt, cap, T_in):

    # Set ice freezing temperature [C]
    T_fz = 0
    #T_in = 12.22
    T_out = 6.667
    T_chg = -3.7

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
        ua_discharge = curves.Poly5(c_discharge, s) * cap / 3600 / 10 # W/C
        max_discharge.append(ua_discharge * (T_in - T_out) /
            np.log((T_in - T_fz) / (T_out - T_fz)))

        ua_charge = curves.Poly5(c_charge, (1-s)) * cap / 3600 / 10
        max_charge.append(ua_charge * (-1 - T_chg) /
            np.log((T_chg - T_fz) / (-1 - T_fz)))

    return np.median(max_discharge), np.median(max_charge)

## Method for Detailed ice model

def detailedIce(melt, cap, c_chg, c_dchg):

    pass

    return


def run(community, bldgs, ts_opt, log):
    # Set some constants --> These need to move to main program (setup file,
    # pehaps put them __init__.py???)
    # model = "simple"
    # melt = "internal"
    # capacity = 486  # ton hours
    # capacity = capacity * 3.5168528421  # kWh
    # capacity = capacity * 3600000 # J

    # Define CTES types
    ctes = define_types()
    for i in range(community["plant_count"]):
        ctes["max_discharge"][i] = []
        ctes["max_charge"][i] = []

    # Only 1 CTES type so far!!
    if ctes["model"] == "simple":
        counter = 0
        for b in bldgs:
            for c in bldgs[b]["chillers"]:
                ctes["max_discharge"][counter]: []
                ctes["max_charge"][counter]: []
                for t in range(8760 * ts_opt):
                    d, c = simpleIce(ctes["melt"],
                        ctes["capacity"] * 3.6e3,
                        bldgs[b][c]["T_e_in"][t])
                    ctes["max_discharge"][counter].append(d)
                    ctes["max_charge"][counter].append(c)

                counter += 1

        for dist in community["district_loops"]:
            ctes["max_discharge"][counter]: []
            ctes["max_charge"][counter]: []
            for t in range(8760 * ts_opt):
                d, c = simpleIce(ctes["melt"],
                    ctes["capacity"] * 3.6e3,
                    community["district_loops"][dist]["T_e_in"][t])
                ctes["max_discharge"][counter].append(d)
                ctes["max_charge"][counter].append(c)

            counter += 1

    return ctes
