## post.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Initiated: May 18, 2021
# Completed:
# Revised:

## The purpose of this script is to postprocess the results of an optimization
# run.

## Imports
import csv
import getopt
import logging as log
import os
import pickle as pkl
import plotly.graph_objects as go
import plotly.subplots as sp
import sys
import time

## Custom Modules
sys.path.append("python_modules")
import get_args
import xfer

#-------------------------------------------------------------------------------
## Main Program
#-------------------------------------------------------------------------------
## Setup Logger
log.basicConfig(filename='post.log',
                filemode='w',
                format="%(levelname)s: %(message)s",
                level=log.DEBUG)
log.info("Logging initialized")
log.info("File: 'post.py'. Start time: {}".format(time.ctime()))
start_time = time.time()
#-------------------------------------------------------------------------------
## Get user arguments from command line
log.info("\n **Getting user arguments from the command line**")
argv = sys.argv[1:]
try:
    opts, args = getopt.getopt(argv, "hfsxi:", [
        "help"
        "show_figures",
        "save_project",
        "input_path"])
except:
    log.error("Unrecognized argument; see help: -h or --help")
    log.info("Program terminated early!")
    sys.exit("Error. See log file")

[input_path, save, show_figs, transfer] = list(get_args.post(opts, args, log))
#-------------------------------------------------------------------------------
## Transfer optimization files from remote server if required
if transfer:
    log.info("\n **Transferring files from remote**")
    xfer.receive(input_path)
#-------------------------------------------------------------------------------
## Load data from pre.py for analysis and plotting
try:
    community = pkl.load(open(os.path.join(input_path, "workspace",
        "community_final.p"), "rb"))
    plant_loops = pkl.load(open(os.path.join(input_path, "workspace",
        "plant_loops_final.p"), "rb"))
    buildings = pkl.load(open(os.path.join(input_path, "workspace",
        "buildings_final.p"), "rb"))
    erates = pkl.load(open(os.path.join(input_path, "workspace",
        "erates_final.p"), "rb"))
    log.info("Loaded data from community_final.p, plant_loops_final.p, " \
        "buildings_final.p, and erates_final.p written by pre.py")
    ts_opt = int(len(community["dtg"]) / 8760)
    log.info("The detected optimization timestep is: {}".format(ts_opt))
except:
    log.error("Unable to load data written by the preprocessor")
    log.info("Program terminated early!")
    sys.exit("See log file.")
#-------------------------------------------------------------------------------
## Load results data in the .out files into a data dictionary
log.info("Populating the 'optimized' dictionary")
results_path = os.path.join(input_path, "results")
figs_path = os.path.join(results_path, "figures")
optimized = {}
optimized["electricity_rate"] = []
optimized["peak_demand"] = []
# Total energy use
with open(os.path.join(results_path, "P.out"), "r") as f:
    for line in f:
        optimized["electricity_rate"].append(float(line))
# Peak demand
with open(os.path.join(results_path, "P_hat.out"), "r") as f:
    for line in f:
        optimized["peak_demand"].append(float(line))
# Plant loop timeseries data
keys = ["alpha", "PX", "PYfull", "PYpart", "Q", "X", "Yfull", "Ypart", "load"]
for k in keys:
    optimized[k] = []
    with open(os.path.join(results_path, "{}.out".format(k)), "r") as f:
        rdr = csv.reader(f, delimiter=" ")
        for row in rdr:
            optimized[k].append([float(i) for i in row])
#-------------------------------------------------------------------------------
## Get cooling load after seasonal schedule applied
chiller_loads = [[] for i in range(len(optimized["PX"][0]))]
chiller_power = [[] for i in range(len(optimized["PX"][0]))]
community["evap_cooling_rate"] = [0 for i in range(len(optimized["PX"]))]
idx = 0
for p in plant_loops:
    for c in plant_loops[p]:
        if c in ["district_cooling_load", "district_mass_flow", "total_power"]:
            continue
        for t in range(len(community["dtg"])):
            chiller_loads[idx].append(plant_loops[p][c]["evap_cooling_rate"][t])
            chiller_power[idx].append(plant_loops[p][c]["electricity_rate"][t])
            community["evap_cooling_rate"][t] += chiller_loads[idx][-1]
        idx += 1
#-------------------------------------------------------------------------------
## Populate high-level summary data
cool_elec = [0 for t in range(len(community["dtg"]))]
for t in range(len(community["dtg"])):
    cool_elec[t] += community["cooling_electricity_rate"][t]
    cool_elec[t] += sum(optimized["PX"][t])
    cool_elec[t] += -sum(optimized["PYfull"][t])
    cool_elec[t] += -sum(optimized["PYpart"][t])
optimized["cooling_electricity_rate"] = cool_elec
optimized["cooling_thermal_rate"] = [sum(v) for v in optimized["load"]]
with open(os.path.join(results_path, "soln.out"), "r", newline="") as f:
    val = f.readline().split("= ")[-1]
    optimized["total_bill"] = float(val)
    f.readlines(2)
    tank_count = []
    for i in range(len(optimized["PX"][0])):
        val = f.readline().split(" ")[-1]
        tank_count.append(int(val))
    f.readlines(3)
    val = f.readline().split("= ")[-1]
    optimized["energy_bill"] = float(val)
    val = f.readline().split("= ")[-1]
    optimized["demand_bill"] = float(val)
    val = f.readline().split("= ")[-1]
    optimized["storage_bill"] = float(val)
#-------------------------------------------------------------------------------
## Create optimized.csv
with open(os.path.join(results_path, "optimized.csv"), "w", newline="") as f:
    wtr = csv.writer(f, delimiter=",")
    wtr.writerow(["Total Electricity [MWh]",
        "Total Cooling Electricity [MWh]",
        "Total Non-Cooling Electricity [MWh]",
        "Total Cooling Thermal Energy [MWh_th]"])
    wtr.writerow([round(sum(optimized["electricity_rate"]) / 1e3 / ts_opt, 3),
        round(sum(optimized["cooling_electricity_rate"]) / 1e6 / ts_opt, 3),
        round(sum(community["non_cooling_electricity_rate"]) / 1e6 / ts_opt, 3),
        round(sum(optimized["cooling_thermal_rate"]) / 1e3 / ts_opt, 3)])
    wtr.writerow(["Total Electricity bill [$]",
        "Total Demand Charges [$]",
        "Total Energy Charges [$]"])
    wtr.writerow([round(optimized["total_bill"], 2),
        round(optimized["demand_bill"], 2),
        round(optimized["energy_bill"], 2)])
    wtr.writerow(["Peak Demand by Period [kW]"])
    wtr.writerow([round(i, 2) for i in optimized["peak_demand"]])
    wtr.writerow(["Demand Charge by Period"])
    wtr.writerow([round(i * j, 2) for i,j in zip(
        optimized["peak_demand"], erates["demand_cost"])])
#-------------------------------------------------------------------------------
## Create Figures - Show if flagged
#-------------------------------------------------------------------------------
## Electric Load Profiles for Community
fig = go.Figure(go.Scatter(
    x=community["dtg"], y=[i / 1000 for i in community["electricity_rate"]],
    name="Baseline", line=dict(dash="dash", color="black")))
fig.add_trace(go.Scatter(
    x=community["dtg"], y=optimized["electricity_rate"],
    name="Optimal", line=dict(color="#ABD1F3")))
fig.update_layout(title="Community Electricity Demand by Timestep",
    yaxis=dict(title="kWe", gridcolor="whitesmoke",
        rangemode="tozero", zeroline=True, zerolinecolor="lightslategray"),
    paper_bgcolor="white", plot_bgcolor="white")
fig.update_xaxes(zeroline=True, zerolinecolor="black")
fig.write_html(os.path.join(figs_path, "Electric Profile.html"),
    auto_open=show_figs)
#-------------------------------------------------------------------------------
## Themral Load Profiles for Community
fig = go.Figure(go.Scatter(
    x=community["dtg"], y=[i / 1000 for i in community["evap_cooling_rate"]],
    name="Baseline", line=dict(dash="dash", color="black")))
fig.add_trace(go.Scatter(
    x=community["dtg"], y=optimized["cooling_thermal_rate"],
    name="Optimal", line=dict(color="#ABD1F3")))
fig.update_layout(title="Community Thermal Cooling Load by Timestep",
    yaxis=dict(title="kWt", gridcolor="whitesmoke",
        rangemode="tozero", zeroline=True, zerolinecolor="lightslategray"),
    paper_bgcolor="white", plot_bgcolor="white")
fig.update_xaxes(zeroline=True, zerolinecolor="black")
fig.write_html(os.path.join(figs_path, "Cooling Load Profile.html"),
    auto_open=show_figs)
#-------------------------------------------------------------------------------
## Load duration curves
fig = sp.make_subplots(rows=2, cols=1, shared_xaxes=True,
    subplot_titles=("Total Electricity", "Coincident Cooling Electricity"))
ld, cld = zip(*sorted(zip(community["electricity_rate"],
    community["cooling_electricity_rate"]), reverse=True))
ldo, cldo = zip(*sorted(zip(optimized["electricity_rate"],
    optimized["cooling_electricity_rate"]), reverse=True))
fig.add_trace(go.Scatter(y=[i / 1000 for i in ld],
    name="Baseline", line=dict(dash="dash", color="black")),
    row=1, col=1)
fig.add_trace(go.Scatter(y=ldo,
    name="Optimal", line=dict(color="#ABD1F3")),
    row=1, col=1)
fig.add_trace(go.Scatter(y=[i / 1000 for i in cld],
    name="Baseline Cooling", line=dict(dash="dash", color="black")),
    row=2, col=1)
fig.add_trace(go.Scatter(y=[i / 1000 for i in cldo],
    name="Optimal Cooling", line=dict(color="#ABD1F3")),
    row=2, col=1)
fig.update_layout(title="Electricity Load Duration Curves",
    yaxis=dict(title="MWe"), yaxis2=dict(title="MWe"),
    paper_bgcolor="white", plot_bgcolor="white")
fig.update_yaxes(gridcolor="whitesmoke", rangemode="tozero", zeroline=True,
    zerolinecolor="lightslategray")
fig.update_xaxes(rangemode="tozero", zeroline=True,
    zerolinecolor="lightslategray")
fig.write_html(os.path.join(figs_path, "Load Duration Curve.html"),
    auto_open=show_figs)
