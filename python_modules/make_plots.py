## make_plots.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Initiated: May 18, 2021
# Completed:
# Revised:

## The purpose of this script is to create figures for both pre.py and post.py

import datetime as dtg
import os
import pickle as pkl
from plotly import graph_objects as go
from plotly.subplots import make_subplots as sp
import sys

# Plots of pre-processed data
def pre(community, plant_loops, buildings, erates, input_path, log):
    # Check for results/figures subfolder
    if not os.path.isdir(os.path.join(input_path, "results", "figures")):
        os.mkdir(os.path.join(input_path, "results", "figures"))
    fig_path = os.path.join(input_path, "results", "figures")
    work_path = os.path.join(input_path, "workspace")

    # Baseline costs
    x_axis = ["Total Cost [$]", "Demand Charges [$]", "Energy Charges [$]"]
    bars = [round(erates["baseline_total"], 2),
        round(sum(erates["baseline_demand"]), 2),
        round(erates["baseline_energy"], 2)]
    fig = go.Figure(go.Bar(x=x_axis, y=bars, name="Baseline"))
    pkl.dump(fig, open(os.path.join(work_path, "fig_cost.p"), "wb"))
    # test = pkl.load(open(os.path.join(work_path, "fig_cost.p"), "rb"))
    # test.add_trace(go.Bar(x=x_axis, y=bars, name="Testing"))
    # test.show()

    # Plant loop cooling and electricity rates


    # Total energy use


    return

def post():


    return
