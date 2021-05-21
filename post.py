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
except:
    log.error("Unable to load data written by the preprocessor")
    log.info("Program terminated early!")
    sys.exit("See log file.")
#-------------------------------------------------------------------------------
## Load results data in the .out files into a data dictionary\
log.info("Populating the 'optimized' dictionary")
results_path = os.path.join(input_path, "results")
file_path = os.path.join(results_path, "figures")
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
# Plant loop data
PX = []
# Electricity used for charging
with open(os.path.join(results_path, "PX.out"), "r") as f:
    rdr = csv.reader(f, delimiter=" ")
    for row in rdr:
        vals.append([float(i) for i in row])
idx = 0
for p in plant_loops:
    optimized[p] = {}
    optimized[p]["charging_electricity_rate"] = [v[idx] for v in vals]
    idx += 1
