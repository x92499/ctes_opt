## Electric Rate Generator Script
# Generates 15-minute electric rate pricing ($ per kWh)
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Original: March 2020
## REVISED May 2021 for Central TES Optimization

### Might be good to use the URDB format and API????####

# Imports
import csv
import datetime
import os
import random
import sys

def run(ts_opt, log):
    # set up eSrates hash/dict:
    erates = {"energy_cost": [],
        "demand_cost": [],
        "demand_pd_ts_ct": [],
        "demand_pd_timesteps": [],
        "DR_timesteps": []
    }

    ## set up pricing structure (possibly move?)
    #Time of Use vs. Real Time Pricing
    tou = True
    dmd = True

    log.info(" Energy charges are time-variant over the year: {}".format(tou))
    log.info(" Demand charges are present: {}".format(dmd))

    # Mines Energy Rates, as provided by Mohammad
    # Electricity rates and peak periods
    e_off = 0.0  # $/kWh
    e_tou = [0.04264, 0.05552, (0.0573 - 0.00868), 0.07018]
    e_months = [list(range(1,13)), list(range(1,13)),
        list(range(5,11)), list(range(5,11))]
    e_dom = [list(range(1,32)), list(range(1,32)),
        list(range(1,32)), list(range(1,32))]
    e_peak = [list(range(24)), list(range(15,20)),
        list(range(24)), list(range(15,20))]

    # Demand charge rates and peak periods
    d_cost = [3.272 for i in range(12)] + [11.70 for i in range(12)]
    d_months = [[m] for m in range(1,13)] + [[m] for m in range(1,13)]
    d_days = [list(range(1,32)) for i in range(12)] + [list(range(1,32)) for i in range(12)]
    d_peak = [list(range(15)) + list(range(20,24)) for i in range(12)] +  [list(range(15,20)) for i in range(12)]

    # Special demand periods
    # d_cost.extend([11.34 for i in range(4)])
    # d_months.extend([[6], [7], [8], [9]])
    # d_days.extend([[13,27,28], [3,11,13,18,19],
    #     [3,9,14,15,19,25,31], [1,2,5,20,29]])
    # d_peak.extend([list(range(12,20)) for i in range(4)])
    # log.info(" Demand response events are signaled via demand charges")

    # Special energy charge periods
    e_tou.extend([0.25 for i in range(4)])
    e_months.extend([[6], [7], [8], [9]])
    e_dom.extend([[7,16,30], [11,18,26],
        [4,23,30], [7,20,26]])
    e_peak.extend([list(range(15,20)) for i in range(4)])
    log.info(" Demand response events are signaled via TOU energy charges")

    # Determine total number of timesteps from ts per hour
    opt_steps = int(8760 * ts_opt)

    ## TOU Calcs
    if tou:
        rate = [e_off for j in range(opt_steps)]
        dtg_ref = datetime.datetime(2006,1,1,0,0,0,0)

        for t in range(opt_steps):
            tdelta = datetime.timedelta(minutes= 60 / ts_opt * t)
            dtg = dtg_ref + tdelta
            m = dtg.month
            dom = dtg.day
            h = dtg.hour
            for j in range(len(e_peak)):
                try:
                    if h in e_peak[j] and dom in e_dom[j] and m in e_months[j]:
                        # Add random perturbations
                        # perturb = random.uniform(-.0001, 0.0001)
                        # Add time-of-day escalating perturbations
                        perturb = (h % 23) * 0.00001
                        rate[t] = e_tou[j] + perturb
                        if rate[t] > 0.24:
                            erates["DR_timesteps"].append(t + 1)
                except:
                    log.error("Failed to generate TOU energy rates.")
                    log.info("Program terminated early!")
                    sys.exit("See log file.")

        erates["energy_cost"].extend(rate)

        # log demand periods:
        log.info(" {} different energy charge values were used".format(
            len(e_tou)))

    ## Demand period timestep assignments
    if dmd:
        dtg_ref = datetime.datetime(2006,1,1,0,0,0,0)  # Need to modify if AMY used
        d_sets = [[] for i in range(len(d_cost))]
        d_counts = [[] for i in range(len(d_cost))]
        for t in range(opt_steps):
            tdelta = datetime.timedelta(minutes= 60 / ts_opt * t)
            dtg = dtg_ref + tdelta
            for idx in range(len(d_sets)):
                m = dtg.month
                d = dtg.day
                h = dtg.hour
                if m in d_months[idx] and h in d_peak[idx] and d in d_days[idx]:
                    d_sets[idx].append(t + 1)
                    if idx >= 24:
                        erates["DR_timesteps"].append(t + 1)

        # Get total number of timesteps in each demand period, off-peak is first in list
        for s in range(len(d_sets)):
            d_counts[s] = len(d_sets[s])

        erates["demand_cost"].extend(d_cost)
        erates["demand_pd_ts_ct"].extend(d_counts)
        erates["demand_pd_timesteps"].extend(d_sets)

        # log demand periods:
        log.info(" {} demand periods were created".format(len(d_sets)))

    return erates

    #
    #
    #     file3 = open('ampl inputs/Tp.dat', 'w', newline='')
    #     with file3:
    #         writer = csv.writer(file3, dialect='excel')
    #         for j in range(len(d_peak)):
    #             writer.writerow([i for i in d_sets[j]])
    #
    #     file0 = open(amp_path + 'fixed_params.dat', 'a', newline='')
    #     with file0:
    #         wrt = csv.writer(file0, dialect='excel')
    #         wrt.writerow([len(d_counts)])
    #         wrt.writerow(d_cost)
    #         wrt.writerow(d_counts)
    #     log.info("The fixed parameter file was successfully updated.")
    #
    # ## Calculate baseline electricity costs
    # profile = []
    # with open(amp_path + 'district_power.dat', 'r', newline='') as file4:
    #     for line in file4:
    #         profile.append(float(line.rstrip()))
    # if len(profile) != opt_steps:
    #     print("Array Length ERROR!!! Line 114")
    # base_d_cost = [0 for i in range(len(d_cost))]
    # base_e_cost = sum([profile[i] * rate[i] / ts_opt for i in range(len(profile))])
    # for i in range(len(d_cost)):
    #     base_d_cost[i] = d_cost[i] * max([profile[j-1] for j in d_sets[i]])
    #
    # ## Write baseline costs to file
    # with open(pre_path + 'basecosts.dat', 'w') as file0:
    #     file0.write(str(round(sum(base_d_cost, base_e_cost),2)) + "\n")
    #     file0.write(str(round(base_e_cost,2)) + "\n")
    #     file0.write(str(round(sum(base_d_cost),2)))
    #
    # ## Calculate baseline non-cooling electricity costs
    # profile_cool = []
    # with open(pre_path + 'district_power_coils.dat', 'r', newline='') as file5:
    #     for line in file5:
    #         profile_cool.append(float(line.rstrip()))
    # profile_nocool = [(profile[i] - profile_cool[i]) for i in range(len(profile))]
    # if len(profile_nocool) != opt_steps:
    #     print("Array Length ERROR!!! Line 133")
    # nocool_d_cost = [0 for i in range(len(d_cost))]
    # nocool_e_cost = sum([profile_nocool[i] * rate[i] / ts_opt for i in range(len(profile_nocool))])
    # for i in range(len(d_cost)):
    #     nocool_d_cost[i] = d_cost[i] * max([profile_nocool[j-1] for j in d_sets[i]])
    #
    # ## Calculate baseline costs due exclusively to cooling
    # cool_e_cost = base_e_cost - nocool_e_cost
    # cool_d_cost = [base_d_cost[i] - nocool_d_cost[i] for i in range(len(base_d_cost))]
    #
    # ## Write baseline cooling costs to file
    # with open(pre_path + 'basecosts_cool.dat', 'w') as file9:
    #     file9.write(str(round(sum(cool_d_cost, cool_e_cost),2)) + "\n")
    #     file9.write(str(round(cool_e_cost,2)) + "\n")
    #     file9.write(str(round(sum(cool_d_cost),2)))
