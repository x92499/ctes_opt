## get_base_costs.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# March 30, 2021
# Revised: May 18, 2021
#
## The purpose of this script is to calculate the energy costs of the baseline
# power profile for the connected community.

## Imports
import csv
import os
import sys

## Method to calculate energy charges
def energy_charges(c, t, p):

    bill = 0
    for i in range(len(c)):
        bill += (c[i] * p[i] / t)

    return bill

## Method to calculate demand charges
def demand_charges(sets, c, p):

    bill = [0 for d in range(len(sets))]
    peaks = [0 for d in range(len(sets))]
    for d in range(len(sets)):
        demand_timestep_values = []
        for i in sets[d]:
            demand_timestep_values.append(p[i-1])

        peaks[d] = max(demand_timestep_values)
        bill[d] = peaks[d] * c[d]

    return bill, peaks

## Main method
def run(community, erates, ts_opt, log):
    # create needed lists in dictionaries:
    erates["baseline_demand"] = []
    community["peak_demand"] = []
    # simple variable names
    c_e = erates["energy_cost"]
    c_p = erates["demand_cost"]
    d_sets = erates["demand_pd_timesteps"]
    p = [round(v / 1000, 3) for v in community["electricity_rate"]] #kW

    # Double check array lengths
    try:
        len(c_e) == len(p)
    except:
        sys.exit("Cost Error")

    # calculate energy costs
    erates["baseline_energy"] = energy_charges(c_e, ts_opt, p)
    #calculate demand charges, capture peak demand values
    [d_bill, peaks] = demand_charges(d_sets, c_p, p)
    # populate hash/dicts
    erates["baseline_demand"].extend(d_bill)
    erates["baseline_total"] = erates["baseline_energy"] + sum(erates["baseline_demand"])
    community["peak_demand"].extend(peaks)

    return erates, community
