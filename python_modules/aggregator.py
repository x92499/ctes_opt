## aggregator.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Initiated: May 17, 2021
# Copmleted: may 17, 2021
# Revised:

## The purpose of this code is to aggregate the total electric power, the total
# electric power required for cooling, and the total cooling rate for the
# full community scenario

def run(buildings, plant_loops, ts_opt, log):
    log.info(" Aggregating cooling and electricity values for comminity")
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

    return community
