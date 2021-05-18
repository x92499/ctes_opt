## parameter_writer.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# March 11, 2021
#
## The purpose of this script is to write out all the required parameters for
# the central ice optimization program
#
## Required inputs are the community and bldgs hashes/dicts

import csv
import os

def community(out_path, ts_opt, community, ctes, erates, segs, log):
    ## Write the main fixed_params.dat file (sets optimization constants)
    log.info("**Writing community-level data files**")
    with open(os.path.join(out_path, "fixed_params.dat"), "w", newline="") as f:
        wtr = csv.writer(f, dialect="excel", delimiter=",")
        wtr.writerow([round(1 / ts_opt, 3)])    # delta, ts in hrs
        wtr.writerow([community["building_count"]]) # B, # bldgs
        wtr.writerow([len(erates["demand_pd_ts_ct"])])  # D, # demand pds
        wtr.writerow([1]) # I, # CTES types
        wtr.writerow([community["plant_count"]])    # N, # chiller plants
        wtr.writerow([segs])    # S, # segments for linearization
        wtr.writerow([int(8760 * ts_opt)])  # T, # timesteps
        wtr.writerow(erates["demand_pd_ts_ct"])    # TP_d, # ts in ea dmd pd
        wtr.writerow(erates["demand_cost"])  # c_d, demand charge per pd

    ## Write the community-level aggretated parameters
    # Total electricity (Convert W to kW)
    with open(os.path.join(out_path, "p_tilde.dat"), "w", newline="") as f:
        wtr = csv.writer(f, dialect="excel", delimiter=" ")
        for t in range(len(community['total_elec'])):
            wtr.writerow([round(community['total_elec'][t] / 1000, 2)])

    ## Write electricity cost profile ($/kWh)
    with open(os.path.join(out_path, "cost_elec.dat"), "w", newline="") as f:
        wtr = csv.writer(f, dialect="excel")
        for v in erates["energy_cost"]:
            wtr.writerow([round(v, 7)])

    ## Write demand period timestep sets
    with open(os.path.join(out_path, "Tdmd.dat"), "w", newline="") as f:
        wtr = csv.writer(f, dialect="excel", delimiter=",")
        for d in erates["demand_pd_timesteps"]:
            wtr.writerow(d)

    ## Write baseline costs
    # Peak demand value by period
    with open(os.path.join(out_path, "../results", "p_hat_base.dat"), "w",
        newline="") as f:
        wtr = csv.writer(f, dialect="excel", delimiter=" ")
        for v in community["peak_demand"]:
            wtr.writerow([v])
    # Summary of cost components
    with open(os.path.join(out_path, "../results", "base_costs.dat"), "w",
        newline="") as f:
        wtr = csv.writer(f, dialect="excel", delimiter=",")
        wtr.writerow([round(erates["baseline_total"], 2)])
        wtr.writerow([round(erates["baseline_energy"], 2)])
        wtr.writerow([round(v, 2) for v in erates["baseline_demand"]])

    # ## Write district cooling chiller performance data
    # # Partial storage slope coefficients
    # with open(os.path.join(out_path, "lambda_alpha0.dat"),
    #     "w", newline="") as f:
    #     wtr = csv.writer(f, dialect="excel", delimiter=" ")
    #     for i in range(len(community["district_slopes"])):
    #         vals = [round(v, 5) for v in community["district_slopes"][i]]
    #         wtr.writerow(vals)
    #
    # # Partial storage limits for each segment (W_th -> kW_th)
    # with open(os.path.join(out_path, "y_bar_alpha0.dat"), "w", newline="") as f:
    #     wtr = csv.writer(f, dialect="excel", delimiter=" ")
    #     for i in range(len(community["district_ranges"])):
    #         vals = [round(v / 1000, 2) for v in community["district_ranges"][i]]
    #         wtr.writerow(vals)
    #
    # # Cooling load served by plant at each timestep (W_th -> kW_th)
    # with open(os.path.join(out_path, "l0.dat"), "w", newline="") as f:
    #     wtr = csv.writer(f, dialect="excel", delimiter=" ")
    #     for i in range(len(community["district_cool"])):
    #         val = [round(community["district_cool"][i] / 1000, 2)]
    #         wtr.writerow(val)
    #
    # # Chiller electric power at time t (W -> kW)
    # with open(os.path.join(out_path, "p_tildeN0.dat"), "w", newline="") as f:
    #     wtr = csv.writer(f, dialect="excel", delimiter=" ")
    #     for i in range(len(community["district_cool_elec"])):
    #         val = [round(community["district_cool_elec"][i] / 1000, 2)]
    #         wtr.writerow(val)
    #
    # # Chiller excess capacity available for ice making at t (Wth -> kWth)
    # with open(os.path.join(out_path, "q_dot_X0.dat"),
    #     "w", newline="") as f:
    #     wtr = csv.writer(f, dialect="excel", delimiter=" ")
    #     for i in range(len(community["district_charge"])):
    #         val = [round(community["district_charge"][i] / 1000, 2)]
    #         wtr.writerow(val)

    # Chiller excess capacity available for ice making at t
    # with open(os.path.join(out_path, "lambda_X0.dat"),
    #     "w", newline="") as f:
    #     wtr = csv.writer(f, dialect="excel", delimiter=" ")
    #     for i in range(len(community["district_charge_power"])):
    #         val = [round(community["district_charge_power"][i], 3)]
    #         wtr.writerow(val)
    #
    # # Timestep sets
    # with open(os.path.join(out_path, "Tsets0.dat"), "w", newline="") as f:
    #     wtr = csv.writer(f, dialect="excel", delimiter=" ")
    #     wtr.writerow(community["partial_storage_timesteps"])
    #     wtr.writerow(community["full_storage_timesteps"])
    #     wtr.writerow(community["charge_timesteps"])

    return

def chillers(out_path, community, bldgs, log):
    # log progress
    log.info("**Writing chiller-level data files**")
    # Iterate through chillers and write parameter values:
    chiller_count = 1
    Tpartial_count = []
    Tfull_count = []
    Tcharge_count = []
    for b in bldgs:
        for c in bldgs[b]["chillers"]:
            # Partial storage slope coefficients
            with open(os.path.join(out_path, "lambda_alpha{}.dat".format(
                chiller_count)), "w", newline="") as f:
                wtr = csv.writer(f, dialect="excel", delimiter=" ")
                for i in range(len(bldgs[b]["chillers"][c]["segment_slopes"])):
                    vals = [round(v, 5) for v in
                        bldgs[b]["chillers"][c]["segment_slopes"][i]]
                    wtr.writerow(vals)

            # Partial storage limits for each segment (W_th -> kW_th)
            with open(os.path.join(out_path, "y_bar_alpha{}.dat".format(
                chiller_count)), "w", newline="") as f:
                wtr = csv.writer(f, dialect="excel", delimiter=" ")
                for i in range(len(bldgs[b]["chillers"][c]["segment_ranges"])):
                    vals = [round(v / 1000, 2) for v in
                        bldgs[b]["chillers"][c]["segment_ranges"][i]]
                    wtr.writerow(vals)

            # Cooling load served by plant at each timestep (W_th -> kW_th)
            with open(os.path.join(out_path, "l{}.dat".format(
                chiller_count)), "w", newline="") as f:
                wtr = csv.writer(f, dialect="excel", delimiter=" ")
                for i in range(len(bldgs[b]["chillers"][c]["load"])):
                    val = [round(bldgs[b]["chillers"][c]["load"][i] / 1000, 2)]
                    wtr.writerow(val)

            # Chiller electric power at time t (W -> kW)
            with open(os.path.join(out_path, "p_tildeN{}.dat".format(
                chiller_count)), "w", newline="") as f:
                wtr = csv.writer(f, dialect="excel", delimiter=" ")
                for i in range(len(bldgs[b]["chillers"][c]["power"])):
                    val = [round(bldgs[b]["chillers"][c]["power"][i] / 1000, 2)]
                    wtr.writerow(val)

            # Chiller excess capacity available for ice making at t (Wth -> kWth)
            with open(os.path.join(out_path, "q_dot_X{}.dat".format(
                chiller_count)), "w", newline="") as f:
                wtr = csv.writer(f, dialect="excel", delimiter=" ")
                for i in range(len(bldgs[b]["chillers"][c]["charge_capacity"])):
                    val = [round(bldgs[b]["chillers"][c]["charge_capacity"][i] /
                        1000, 2)]
                    wtr.writerow(val)

            # Chiller excess capacity available for ice making at t
            with open(os.path.join(out_path, "lambda_X{}.dat".format(
                chiller_count)), "w", newline="") as f:
                wtr = csv.writer(f, dialect="excel", delimiter=" ")
                for i in range(len(bldgs[b]["chillers"][c]["charge_power"])):
                    val = [round(bldgs[b]["chillers"][c]["charge_power"][i], 3)]
                    wtr.writerow(val)

            # Partial, full storage, and charging timesteps
            Tpartial_count.append(
                len(bldgs[b]["chillers"][c]["partial_storage_timesteps"]))
            Tfull_count.append(
                len(bldgs[b]["chillers"][c]["full_storage_timesteps"]))
            Tcharge_count.append(
                len(bldgs[b]["chillers"][c]["charge_timesteps"]))

            with open(os.path.join(out_path, "Tsets{}.dat".format(
                chiller_count)), "w", newline="") as f:
                wtr = csv.writer(f, dialect="excel", delimiter=" ")
                wtr.writerow(
                    bldgs[b]["chillers"][c]["partial_storage_timesteps"])
                wtr.writerow(bldgs[b]["chillers"][c]["full_storage_timesteps"])
                wtr.writerow(bldgs[b]["chillers"][c]["charge_timesteps"])

            chiller_count += 1

    # Iterate through district loops and write plant data
    for d in community["district_loops"]:
        # Partial storage slope coefficients
        with open(os.path.join(out_path, "lambda_alpha{}.dat".format(
            chiller_count)), "w", newline="") as f:
            wtr = csv.writer(f, dialect="excel", delimiter=" ")
            for i in range(
                len(community["district_loops"][d]["segment_slopes"])):
                vals = [round(v, 5) for v in
                    community["district_loops"][d]["segment_slopes"][i]]
                wtr.writerow(vals)

        # Partial storage limits for each segment (W_th -> kW_th)
        with open(os.path.join(out_path, "y_bar_alpha{}.dat".format(
            chiller_count)), "w", newline="") as f:
            wtr = csv.writer(f, dialect="excel", delimiter=" ")
            for i in range(
                len(community["district_loops"][d]["segment_ranges"])):
                vals = [round(v / 1000, 2) for v in
                    community["district_loops"][d]["segment_ranges"][i]]
                wtr.writerow(vals)

        # Cooling load served by plant at each timestep (W_th -> kW_th)
        with open(os.path.join(out_path, "l{}.dat".format(
            chiller_count)), "w", newline="") as f:
            wtr = csv.writer(f, dialect="excel", delimiter=" ")
            for i in range(len(community["district_loops"][d]["load"])):
                val = [round(
                    community["district_loops"][d]["load"][i] / 1000, 2)]
                wtr.writerow(val)

        # Chiller electric power at time t (W -> kW)
        with open(os.path.join(out_path, "p_tildeN{}.dat".format(
            chiller_count)), "w", newline="") as f:
            wtr = csv.writer(f, dialect="excel", delimiter=" ")
            for i in range(len(community["district_loops"][d]["power"])):
                val = [round(
                    community["district_loops"][d]["power"][i] / 1000, 2)]
                wtr.writerow(val)

        # Chiller excess capacity available for ice making at t (Wth -> kWth)
        with open(os.path.join(out_path, "q_dot_X{}.dat".format(
            chiller_count)), "w", newline="") as f:
            wtr = csv.writer(f, dialect="excel", delimiter=" ")
            for i in range(
                len(community["district_loops"][d]["charge_capacity"])):
                val = [round(
                    community["district_loops"][d]["charge_capacity"][i] /
                    1000, 2)]
                wtr.writerow(val)

        # Chiller excess capacity available for ice making at t
        with open(os.path.join(out_path, "lambda_X{}.dat".format(
            chiller_count)), "w", newline="") as f:
            wtr = csv.writer(f, dialect="excel", delimiter=" ")
            for i in range(len(community["district_loops"][d]["charge_power"])):
                val = [round(
                    community["district_loops"][d]["charge_power"][i], 3)]
                wtr.writerow(val)

        # Partial, full storage, and charging timesteps
        Tpartial_count.append(
            len(community["district_loops"][d]["partial_storage_timesteps"]))
        Tfull_count.append(
            len(community["district_loops"][d]["full_storage_timesteps"]))
        Tcharge_count.append(
            len(community["district_loops"][d]["charge_timesteps"]))

        with open(os.path.join(out_path, "Tsets{}.dat".format(
            chiller_count)), "w", newline="") as f:
            wtr = csv.writer(f, dialect="excel", delimiter=" ")
            wtr.writerow(
                community["district_loops"][d]["partial_storage_timesteps"])
            wtr.writerow(
                community["district_loops"][d]["full_storage_timesteps"])
            wtr.writerow(community["district_loops"][d]["charge_timesteps"])

        chiller_count += 1

    # Complete the fixed_params.dat file with sizes for indexed sets of T
    with open(os.path.join(out_path, "fixed_params.dat"), "a", newline="") as f:
        wtr = csv.writer(f, dialect="excel", delimiter=",")
        wtr.writerow(Tpartial_count)
        wtr.writerow(Tfull_count)
        wtr.writerow(Tcharge_count)

    return

def ctes(out_path, ctes, log):
    # Write the max charge and discharge rates
    with open(os.path.join(out_path, "fixed_params.dat"), "a", newline="") as f:
        wtr = csv.writer(f, dialect="excel", delimiter=",")
        wtr.writerow([round(max(ctes["max_charge"][0]) / 1000, 2)])
        wtr.writerow([round(ctes["capacity"] / 1000, 2)])
    # Write max charge and discharge rates for each chiller plant and timestep
    for idx in ctes["max_discharge"]:
        with open(os.path.join(out_path, "q_dot_IY{}.dat".format(
            idx+1)), "w", newline="") as f:
            wtr = csv.writer(f, dialect="excel", delimiter=" ")
            for i in range(len(ctes["max_discharge"][idx])):
                wtr.writerow([round(ctes["max_discharge"][idx][i] / 1000, 2)])

    return
