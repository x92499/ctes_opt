## calc_chiller_params.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# March 9, 2021
#
## The purpose of this script is to calculate the timeseries parameters for
# each chiller to be used in the optimization program.
#
## References: Chiller models are available with the EnergyPlus installation
# in the file: 'DataSets/Chillers.idf'
#
## Variable Definitions
# cap_fT = chiller capacity as a function of temperatures
# c_cT = coefficients for capacity as a function of temperuture curve
# c_eT = coefficients for energy input ratio as a function of temperature Curve
# c_eP = coefficients for energy input ratio as a function of part load ratio
# cop_ref = nominal chiller COP
# cp = specific heat capacity of water/working fluid
# eir_fP = chiller energy input ratio as a function of part load ratio
# eir_fT = chiller energy input ratio as a function of temperatures
# load = chiller thermal load (m_dot*cp*(Te_in-Te_out))
# m_dot = mass flow rate of water through the evaporator
# P = chiller electric power (total)
# P_e = chiller electric power (evaporator side)
# P_c = chiller electric power (condensor side)
# plr = chiller part load ratio
# plr_current = current chiller part load ratio
# plr_min = minimum part load ratio
# Q_av = chiller capacity available
# Q_ref = nominal chiller capacity
# Te_i = Temp of water entering evaporator
# Te_o = Temp of water leaving the evaporator
# Te_o_min = Temp of water leaving evaporator at the minimum PLR
# Tl_s = Temp of loop (setpoint)
# Tc_i = Temp of water entering condensor
# Tc_o = Temp of water leaving the condensor
# Tdb = Temp of outside air (drybulb)
# Twb = Temp of outside air (wetbulb)
# Y = load shed (calc from Te_o)

from curves import Quad, BiQuad
import numpy as np
import plotly.graph_objects as go
import sys

def chiller_electric_eir_charging(Q_ref, cop_ref, c_cT, c_eT, c_eP, m_dot,
    P_current, Q_current, Pc_fan, Tdb, Te_i, Te_chg):
    # This method calculates the available chiller capacity for ice charging
    # and the coefficient for determining increased power demand when charging
    # PLR is assumed to be 1.0 during ice charing

    # Set parameters (maybe move?)
    cp_chg = 3742   #J/kg-K for 30% ethylene glycol at -10C
    cp_ratio = cp_chg/4180
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
    # buffer = 5 / 50 data points = 10%
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

def chillers(bldgs, segs, Tdb, Twb, log):
    # log progress
    log.info("**Calculating chiller performance parameters**")

    # fix constants (may be overridden later)
    cp = 4179.6         #J/kg-K
    Tl_s = 6.6667       #C
    Te_chg = -3.7       #C
    Pc_fan = 0          #W_fan/W_chiller (NEED TO ADD TO DICT)
    type = "AirCooled"  #(NEED TO ADD TO DICT)
    partial_storage_cutoff = 0.2    # Minimum PLR allowed for partial storage opn

    # Iterate through each building and chiller
    for b in bldgs:
        for c in bldgs[b]["chillers"]:

            # Iterate through each timestep
            for t in range(len(bldgs[b]["chillers"][c]["load"])):

                # Get chiller evaporator leaving temperature (= loop setpoint)
                # overwrites 42F/6.67C default if variable is present
                if len(bldgs[b]["chillers"][c]["T_e_out"]) > 0:
                    Tl_s = bldgs[b]["chillers"][c]["T_e_out"][t]
                # Get chiller evaporator entering temperature (= return temp)
                Te_i = bldgs[b]["chillers"][c]["T_e_in"][t]
                # Create linspace of temperatures from Te_i to Tl_s
                Te_o = np.linspace(Tl_s, Te_i, 50)

                ## Process curves for discharging
                if bldgs[b]["chillers"][c]["load"][t] > 0:

                    # Check current part load ratio
                    plr_current = bldgs[b]["chillers"][c]["load"][t] / bldgs[b]["chillers"][c]["capacity"]

                    # check minimum temperatures for cap/eir curves
                    Tc = float(bldgs[b]["chillers"][c]["cap_ft_minT"])
                    Te = float(bldgs[b]["chillers"][c]["eir_ft_minT"])
                    if Tdb[t] < Tc or Tdb[t] < Te:
                        Tambient = max([Tc, Te])
                    else:
                        Tambient = Tdb[t]

                    if plr_current >= partial_storage_cutoff:
                        # Get slope coefficients and max turn-down ranges
                        # It is possible to be below the partial storage cutoff
                        # but we need to calculate Q_av (from cap_fT) first
                        slopes, ranges = chiller_electric_eir(
                            bldgs[b]["chillers"][c]["capacity"],
                            bldgs[b]["chillers"][c]["rated_cop"],
                            partial_storage_cutoff,
                            bldgs[b]["chillers"][c]["coeffs_cap_ft"],
                            bldgs[b]["chillers"][c]["coeffs_eir_ft"],
                            bldgs[b]["chillers"][c]["coeffs_eir_plr"],
                            bldgs[b]["chillers"][c]["m_dot"][t],
                            bldgs[b]["chillers"][c]["power"][t],
                            bldgs[b]["chillers"][c]["load"][t],
                            cp,
                            Pc_fan,
                            Tambient,
                            Tl_s,
                            Te_i,
                            Te_o,
                            segs,
                            t
                        )
                    else:
                        # Load exists, but only full storage mode available
                        slopes = [0 for s in range(segs)]
                        ranges = [0 for s in range(segs)]

                    # Create indexed sets for full/partial storage
                    bldgs[b]["chillers"][c]["full_storage_timesteps"].append(t+1)
                    if sum(ranges) > 0:
                        bldgs[b]["chillers"][c]["partial_storage_timesteps"].append(t+1)

                else:
                    slopes = [0 for s in range(segs)]
                    ranges = [0 for s in range(segs)]

                # populate hash/dict for partial storage
                bldgs[b]["chillers"][c]["segment_slopes"].append(slopes)
                bldgs[b]["chillers"][c]["segment_ranges"].append(ranges)

                ## Now get charging values
                chg_av, chg_coeff = chiller_electric_eir_charging(
                    bldgs[b]["chillers"][c]["capacity"],
                    bldgs[b]["chillers"][c]["rated_cop"],
                    bldgs[b]["chillers"][c]["coeffs_cap_ft"],
                    bldgs[b]["chillers"][c]["coeffs_eir_ft"],
                    bldgs[b]["chillers"][c]["coeffs_eir_plr"],
                    bldgs[b]["chillers"][c]["m_dot"][t],
                    bldgs[b]["chillers"][c]["power"][t],
                    bldgs[b]["chillers"][c]["load"][t],
                    Pc_fan,
                    Tdb[t],
                    Te_i,
                    Te_chg
                )
                bldgs[b]["chillers"][c]["charge_capacity"].append(chg_av)
                bldgs[b]["chillers"][c]["charge_power"].append(chg_coeff)
                if chg_av > 10:
                    bldgs[b]["chillers"][c]["charge_timesteps"].append(t+1)

            # Check for negative charge power coefficients
            neg_count = 0
            for v in bldgs[b]["chillers"][c]["charge_power"]:
                if v < 0:
                    neg_count += 1
            if neg_count > 0:
                log.warning("Negative chiller power coefficients for ice " \
                    "charging occured {} times; verify curves".format(
                    neg_count))
                log.info("This issue is often resolved by using shorter " \
                    "optimization timesteps (eg. use '-t 4') which avoids " \
                    "the impact of part-load factors from simulation.")

    return bldgs

def district(community, segs, Tdb, Twb, season, log):
    # This method calculates the chiller/plant parameters for the district
    # cooling load

    # Iterate over the district loops
    for d in community["district_loops"]:

        # Assume a chiller model:

        # ElectricEIRChiller York YK 2275kW/6.32COP/Vanes_2
        coeffs_cap_ft = [1.034673E+00,-1.091064E-02,9.019479E-04,
            9.686229E-03,-9.160783E-04,2.045641E-03]
        coeffs_eir_ft = [8.326094E-01,-6.056615E-03,-3.016626E-04,
            -2.498578E-03,4.933363E-04,-3.125632E-04]
        coeffs_eir_plr = [2.735485E-01,2.163041E-01,5.099054E-01]
        temp = Twb
        t_min = 15.56
        kWperTon = 0.51
        cop_ref = 3.5168525 / kWperTon
        Pc_fan = 0.9
        plr_min = 0.13
        load_multiplier = 1.3

        if d == "CP7":
            load_multiplier = .72
            kWperTon = .8
            cop_ref = 3.5168525 / kWperTon

        # if d == "CP7":
        #     # WaterCooled_PositiveDisplacement_Chiller_GT150_2010_PathA_CAPFT
        #     coeffs_cap_ft = [9.061E-01,2.923E-02,-3.647E-04,
        #         -9.709E-04,-9.050E-05,2.527E-04]
        #     coeffs_eir_ft = [3.773E-01,-2.290E-02,1.650E-03,
        #         1.182E-02,4.345E-04,-1.013E-03]
        #     coeffs_eir_plr = [2.221E-01,5.032E-01,2.569E-01]
        #     temp = Twb
        #     t_min = 17.78
        #     cop_ref = 6.9
        #     Pc_fan = 0.45
        #     plr_min = 0.4
        #     load_multiplier = 1.5

        # get the required mass flow rate
        cp = 4179.6         #J/kg-K for water
        deltaT = 5.6667     #K
        max_load = max(community["district_loops"][d]["load"])      #W
        m_dot = max_load / cp / deltaT

        print(m_dot)

        ## Populate some district loop data
        community["district_loops"][d]["capacity"] = max_load
        community["district_loops"][d]["rated_cop"] = cop_ref
        community["district_loops"][d]["plr_min"] = plr_min
        community["district_loops"][d]["coeffs_cap_ft"] = coeffs_cap_ft
        community["district_loops"][d]["coeffs_eir_ft"] = coeffs_eir_ft
        community["district_loops"][d]["coeffs_eir_plr"] = coeffs_eir_plr
        community["district_loops"][d]["m_dot"] = m_dot

        # assume a loop temperature and charging temperature
        Te_o = 6.6667
        Te_chg = -3.7

        for t in range(len(community["district_loops"][d]["load"])):
            community["district_loops"][d]["load"][t] = (
                community["district_loops"][d]["load"][t] * load_multiplier)

            # check operating season
            if t >= season[0] and t < season[1]:
                community["district_loops"][d]["load"][t] = (
                    community["district_loops"][d]["load"][t] * load_multiplier)
                load = community["district_loops"][d]["load"][t]
            else:
                load = 0
                community["district_loops"][d]["load"][t] = 0

            # Find chiller electric power at current timestep
            cap_fT = BiQuad(coeffs_cap_ft, Te_o, max(temp[t],t_min))
            eir_fT = BiQuad(coeffs_eir_ft, Te_o, max(temp[t],t_min))
            Te_i = load / cp / m_dot + deltaT
            Q_av = max_load * cap_fT
            plr = load / Q_av
            plr = min(1.0, plr)
            plr = max(0, plr)
            eir_fP = Quad(coeffs_eir_plr, plr)

            if plr == 0:
                community["district_loops"][d]["load"][t] = 0
                load = 0

            ## Get chiller power - evaporator component
            if load > 0 and plr >= plr_min:
                Pe = Q_av / cop_ref * eir_fT * eir_fP
            elif load > 0 and plr < plr_min:
                Pe = load / cop_ref * 2
            else:
                Pe = 0

            ## Get chiller power - condensor component
            Pc = Pe * Pc_fan

            ## Get total chiller power
            P = Pe + Pc
            community["district_loops"][d]["power"].append(P)
            community["total_elec"][t] += P

            ## Populate district loop data
            community["district_loops"][d]["plr"].append(plr)
            cop = load / P if P > 0 else 0
            community["district_loops"][d]["cop"].append(cop)
            community["district_loops"][d]["T_e_in"].append(Te_i)
            community["district_loops"][d]["T_e_out"].append(Te_o)

            # Calculate the slope coefficients and max turn-down ranges (ignore
            # PLF or cycling induced by minimum PLR) above minimum part load ratio
            if plr > 0:
                slopes, ranges = chiller_electric_eir(
                    community["district_loops"][d]["capacity"],
                    community["district_loops"][d]["rated_cop"],
                    community["district_loops"][d]["plr_min"],
                    community["district_loops"][d]["coeffs_cap_ft"],
                    community["district_loops"][d]["coeffs_eir_ft"],
                    community["district_loops"][d]["coeffs_eir_plr"],
                    community["district_loops"][d]["m_dot"],
                    community["district_loops"][d]["power"][t],
                    community["district_loops"][d]["load"][t],
                    cp,
                    Pc_fan,
                    max(temp[t], t_min),
                    community["district_loops"][d]["T_e_out"][t],
                    community["district_loops"][d]["T_e_in"][t],
                    np.linspace(Te_o, Te_i, 50),
                    segs,
                    t
                )
                community["district_loops"][d][
                    "partial_storage_timesteps"].append(t+1)
                community["district_loops"][d][
                    "full_storage_timesteps"].append(t+1)
            elif plr > 0:
                slopes = [0 for s in range(segs)]
                ranges = [0 for s in range(segs)]
                community["district_loops"][d][
                    "full_storage_timesteps"].append(t+1)
            else:
                slopes = [0 for s in range(segs)]
                ranges = [0 for s in range(segs)]

            # Popluate hash with slopes and ranges
            community["district_loops"][d]["segment_slopes"].append(slopes)
            community["district_loops"][d]["segment_ranges"].append(ranges)

            # Get charging values
            chg_av, chg_coeff = chiller_electric_eir_charging(
                community["district_loops"][d]["capacity"],
                community["district_loops"][d]["rated_cop"],
                community["district_loops"][d]["coeffs_cap_ft"],
                community["district_loops"][d]["coeffs_eir_ft"],
                community["district_loops"][d]["coeffs_eir_plr"],
                community["district_loops"][d]["m_dot"],
                community["district_loops"][d]["power"][t],
                community["district_loops"][d]["load"][t],
                Pc_fan,
                max(temp[t], t_min),
                community["district_loops"][d]["T_e_in"][t],
                Te_chg
            )
            community["district_loops"][d]["charge_capacity"].append(chg_av)
            community["district_loops"][d]["charge_power"].append(chg_coeff)
            if chg_av > 10:
                community["district_loops"][d]["charge_timesteps"].append(t+1)

        # Check for negative charge power coefficients
        neg_count = 0
        for v in community["district_loops"][d]["charge_power"]:
            if v < 0:
                neg_count += 1
        if neg_count > 0:
            log.warning("Negative chiller power coefficients for ice " \
                "charging occured {} times; verify curves".format(
                neg_count))
            log.info("This issue is often resolved by using shorter " \
                "optimization timesteps (eg. use '-t 4') which avoids " \
                "the impact of part-load factors from simulation.")

    return community
