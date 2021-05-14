## post_opt.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# March 22, 2021

## The purpose of this script is the post-process the results of an optimization
# run for the central thermal energy storage optimization.

# The script will look for files in the 'ampl_inputs' and 'results' folders.

## Import
import csv
import datetime
import os
import sys
from plotly import graph_objects as go
from plotly.subplots import make_subplots as sp

## Populate a datetime array
def get_dtg():
    # This method creates the x-axis date time values for the results

    # Get optimization timestep
    with open("ampl_inputs/fixed_params.dat", "r", newline="") as f:
        ts = float(f.readline())
        [f.readline() for i in range(3)]
        N = int(f.readline())

    ts_min = int(ts * 60)

    if ts == 1.0:
        dtg = [datetime.datetime(2006,1,1,0,0,0,0) +
            t*datetime.timedelta(hours=1) for t in range(8760)]
    else:
        dtg = [datetime.datetime(2019,1,1,0,0,0,0) +
            t*datetime.timedelta(minutes=ts_min) for t in range(int(8760/ts))]

    return dtg, N

## Power profile comparison figures
def total_power(dtg):
    # This method plots the power profiles for the community

    with open("ampl_inputs/p_tilde.dat", "r", newline="") as f:
        base = [float(i) for i in f.readlines()]

    with open("results/P.out", "r", newline="") as f:
        opt = [float(i) for i in f.readlines()]

    fig = go.Figure(go.Scatter(x=dtg, y=base, name="Baseline"))
    fig.add_trace(go.Scatter(x=dtg, y=opt, name="Optimal"))
    fig.update_layout(title="Electric Power (Avg per timestep) [kWe]",
                    showlegend=True)
    fig.show()

    fig = go.Figure(go.Bar(y=[sum(base)/(len(dtg)/8760)], name="Baseline"))
    fig.add_trace(go.Bar(y=[sum(opt)/(len(dtg)/8760)], name="Optimal"))
    fig.update_layout(title="Total Community Electric Energy")
    fig.show()

    print("Total Electric Energy (Base): {}".format(sum(base)))
    print("Total Electric Energy (Optimal): {}".format(sum(opt)))

    return

def chiller_cooling(dtg, N):
    # This method plots the total cooling load profiles for each chiller

    # base = []
    # opt = []
    # for n in range(N):
    #     with open("ampl_inputs/l{}.dat".format(n+1), "r", newline="") as f:
    #         base.append([float[i] for i in f.readlines()])
    #
    #     with open("results/.dat".format(n+1), "r", newline="") as f:
    #
    #         base.append([float[i] for i in f.readlines()])

    return

def soc(dtg, N):
    # This method plots the state of charge of each TES

    opt = [[] for n in range(N)]
    with open("results/Q.out", "r", newline="") as f:
        rdr = csv.reader(f, delimiter=" ")
        for row in rdr:
            for n in range(N):
                opt[n].append(float(row[n]))

    fig = sp(rows=N, cols=1, shared_xaxes=True)
    for n in range(N):
        vals = [float(i) for i in opt[n]]
        fig.add_trace(go.Scatter(
            x=dtg, y=opt[n], name="Chiller {}".format(n+1)),
            row=n+1, col=1)
    fig.update_layout(title="Thermal Storage Inventory [kW_th]")
    fig.show()

    return

def dispatch(dtg):

    # build new cooling load and electric profiles for each chiller
    baseloads = []
    basepower = []
    optloads = []
    optpower = []
    shed_e = 0
    add_e = 0
    shed_c = 0
    add_c = 0

    # get baseline cooling and power profiles
    for n in range(N):
        with open("ampl_inputs/l{}.dat".format(n+1), "r", newline="") as f:
            baseloads.append([float(v) for v in f.readlines()])
        optloads.append([v for v in baseloads[n]])
        with open("ampl_inputs/p_tildeN{}.dat".format(n+1), "r", newline="") as f:
            basepower.append(([float(v) for v in f.readlines()]))
        optpower.append([v for v in basepower[n]])

    # add charging rates
    with open("results/X.out", "r", newline="") as f:
        rdr = csv.reader(f, delimiter=" ")
        idx = 0
        for row in rdr:
            for n in range(N):
                optloads[n][idx] += float(row[n])
                add_c += float(row[n])
            idx += 1

    # subtract full storage discharging
    with open("results/Yfull.out", "r", newline="") as f:
        rdr = csv.reader(f, delimiter=" ")
        idx = 0
        for row in rdr:
            for n in range(N):
                optloads[n][idx] += -float(row[n])
                shed_c += float(row[n])
            idx += 1

    # subtract partial storage discharging
    with open("results/Ypart.out", "r", newline="") as f:
        rdr = csv.reader(f, delimiter=" ")
        idx = 0
        for row in rdr:
            for n in range(N):
                optloads[n][idx] += -float(row[n])
                shed_c += float(row[n])
            idx += 1

    # create figure comparing the cooling load profiles
    fig = sp(rows=N, cols=1, shared_xaxes=True)
    for n in range(N):
        fig.add_trace(go.Scatter(x=dtg, y=baseloads[n],
                                name="Chiller {}: Base".format(n+1)),
                    row=n+1, col=1)
        fig.add_trace(go.Scatter(x=dtg, y=optloads[n],
                                name="Chiller {}: Optimal".format(n+1)),
                    row=n+1, col=1)
    fig.update_layout(title="Chiller Evaporator Cooling Profiles [kW_th]")
    fig.show()

    # add charging power
    with open("results/PX.out", "r", newline="") as f:
        rdr = csv.reader(f, delimiter=" ")
        idx = 0
        for row in rdr:
            for n in range(N):
                optpower[n][idx] += float(row[n])
                add_e += float(row[n])
            idx += 1

    # subtract full storage discharging power
    with open("results/PYfull.out", "r", newline="") as f:
        rdr = csv.reader(f, delimiter=" ")
        idx = 0
        for row in rdr:
            for n in range(N):
                optpower[n][idx] += -float(row[n])
                shed_e += float(row[n])
            idx += 1

    # subtract partial storage discharging power
    with open("results/PYpart.out", "r", newline="") as f:
        rdr = csv.reader(f, delimiter=" ")
        idx = 0
        for row in rdr:
            for n in range(N):
                optpower[n][idx] += -float(row[n])
                shed_e += float(row[n])
            idx += 1

    # create figure comparing the cooling load profiles
    fig = sp(rows=N, cols=1, shared_xaxes=True)
    for n in range(N):
        fig.add_trace(go.Scatter(x=dtg, y=basepower[n],
                                name="Chiller {}: Base".format(n+1)),
                    row=n+1, col=1)
        fig.add_trace(go.Scatter(x=dtg, y=optpower[n],
                                name="Chiller {}: Optimal".format(n+1)),
                    row=n+1, col=1)
    fig.update_layout(title="Chiller Power [kWe]")
    fig.show()

    print("Load Shift Efficiency: {}".format(shed_e/add_e))
    print("Cooling Shed/Add Ratio: {}".format(shed_c/add_c))

    return

def peak(dtg):
    # this module creates a bar chart comparing peak demand values
    with open("results/p_hat_base.dat", "r", newline="") as f:
        base = [float(i) for i in f.readlines()]

    with open("results/p_hat.out", "r", newline="") as f:
        opt = [float(i) for i in f.readlines()]

    fig = go.Figure(go.Bar(y=base, name="Base"))
    fig.add_trace(go.Bar(y=opt, name="Optimal"))
    fig.update_layout(title="Peak Electric Power Demand by Period [kW_max]")
    fig.show()

def parameters(dtg):
    # this module plots the charge and discharge cost parameters by ts for insp.
    with open("ampl_inputs/lambda_X1.dat", "r", newline="") as f:
        lambdaX1 = [float(i) for i in f.readlines()]

    with open("ampl_inputs/p_tildeN1.dat", "r", newline="") as f:
        pN1 = [float(i) for i in f.readlines()]

    with open("ampl_inputs/l1.dat", "r", newline="") as f:
        l1 = [float(i) for i in f.readlines()]

    lambdaA1 = []
    with open("ampl_inputs/lambda_alpha1.dat", "r", newline="") as f:
        rdr = csv.reader(f, delimiter=" ")
        for row in rdr:
            lambdaA1.append(float(row[0]))

    fig = go.Figure(go.Scatter(x=dtg, y=pN1,
        name="Chiller 1 Electric Power [kWe]"))
    fig.add_trace(go.Scatter(x=dtg, y=lambdaX1,
        name="Chiller 1 Charge Cost [kWe/kWth added]"))
    fig.add_trace(go.Scatter(x=dtg, y=lambdaA1,
        name="Chiller 1 Partial Storage Discharge Savings [kWe/kWth shed]"))
    fig.add_trace(go.Scatter(x=dtg, y=[pN1[i]/l1[i] for i in range(len(dtg))],
        name="Chiller 1 Full Storage Discharge Savings [kWe/kWth shed]"))
    fig.add_trace(go.Scatter(x=dtg, y=l1,
        name="Chiller 1 Thermal Load [kWth]"))

    fig.update_layout(title="Chiller 1 Parameter Comparison")
    fig.show()


    return


dtg, N = get_dtg()
total_power(dtg)
soc(dtg, N)
dispatch(dtg)
peak(dtg)
parameters(dtg)
