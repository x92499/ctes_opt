## aggregator.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Initiated: May 17, 2021
# Copmleted: may 17, 2021
# Revised:

## The purpose of this code is to aggregate the total electric power, the total
# electric power required for cooling, and the total cooling rate for the
# full community scenario

import datetime

## Populate a datetime array
def get_dtg(input_path, ts_opt, log):
    # This method creates datetime group for simulation period
    ts_min = 60 / ts_opt

    if ts_opt == 1.0:
        dtg = [datetime.datetime(2006,1,1,0,0,0,0) +
            t*datetime.timedelta(hours=1) for t in range(8760)]
    else:
        dtg = [datetime.datetime(2019,1,1,0,0,0,0) +
            t*datetime.timedelta(minutes=ts_min) for t in range(8760 * ts_opt)]

    return dtg

def run(buildings, plant_loops, input_path, ts_opt, log):
    log.info(" Aggregating cooling and electricity values for community")
    # build dictionary
    community = {}
    # create empty lists
    pwr = [0 for i in range(8760 * ts_opt)]
    pwr_non_cool = [0 for i in range(8760 * ts_opt)]
    pwr_cool = [0 for i in range(8760 * ts_opt)]
    cooling = [0 for i in range(8760 * ts_opt)]
    # iterate through timesteps
    for b in buildings:
        for t in range(8760*ts_opt):
            pwr[t] += buildings[b]["total_power"][t]
            pwr_non_cool[t] += buildings[b]["total_power"][t]

    for p in plant_loops:
        for t in range(8760 * ts_opt):
            if p in buildings:
                for c in plant_loops[p]:
                    pwr_cool[t] += plant_loops[p][c]["electricity_rate"][t]
                    cooling[t] += plant_loops[p][c]["evap_cooling_rate"][t]
            else:
                pwr[t] += plant_loops[p]["total_power"][t]
                pwr_cool[t] += plant_loops[p]["total_power"][t]
                cooling[t] += plant_loops[p]["district_cooling_load"][t]

    #populate dictionary
    community["electricity_rate"] = pwr
    community["non_cooling_electricity_rate"] = pwr_non_cool
    community["cooling_electricity_rate"] = pwr_cool
    community["cooling_thermal_rate"] = cooling
    community["dtg"] = get_dtg(input_path, ts_opt, log)

    return community
