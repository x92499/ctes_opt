## Cool Thermal Storage Optimization Pre-Processor
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Re-consctruted from pre_opt.py to facilitate program reorganization
# Initiated: May 13, 2021
# Completed:
# Revised:

## Description:
# This script is the supervisory script which manages all the pre-optimization
# subroutines required to execute the optimization program via AMPL.
# THIS PARAGRAPH WILL BE UPDATED WITH DETAILS ONCE THOSE MEASURE(S) ARE FINISHED

## Organization:
# Get User Arguments
# Get District Assignments
# Get Building Energy Use Data


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
import get_districts
import get_wx
import get_sim_data
import process_curves
#-------------------------------------------------------------------------------
## Main Program
#-------------------------------------------------------------------------------
## Setup Logger
log.basicConfig(filename='pre.log',
                filemode='w',
                format="%(levelname)s: %(message)s",
                level=log.DEBUG)
log.info("Logging initialized")
log.info("File: 'pre.py'. Start time: {}".format(time.ctime()))
start_time = time.time()
#-------------------------------------------------------------------------------
## Get user arguments from command line
log.info("\n **Getting user arguments from the command line**")
argv = sys.argv[1:]
try:
    opts, args = getopt.getopt(argv, "hbcpri:s:t:", [
        "help"
        "buildings_processor",
        "curve_processor",
        "plant_loops_processor",
        "reset",
        "input_path=",
        "segments=",
        "ts_opt="])
except:
    log.error("Unrecognized argument; see help: -h or --help")
    log.info("Program terminated early!")
    sys.exit("Error. See log file")

[buildings_processor, curve_processor, plant_loops_processor, reset,
    input_path, segments, ts_opt] = list(get_args.run(opts, args, log))
#-------------------------------------------------------------------------------
## Execute reset if specified
if reset:
    log.warning("\n **Performing data reset. Program will terminate**")

    # delete the workspace folder
    for file in os.listdir(os.path.join(input_path, "workspace")):
        os.remove(os.path.join(input_path, "workspace", file))

    log.info("Emptied the contents of the workspace folder.")
    log.warning("Terminated after file reset")
    sys.exit("Deleted contents of workspace folder.")

#-------------------------------------------------------------------------------
## Get district assignments for building files
log.info("\n **Parsing the districts assignments file**")
buildings, plant_loops = get_districts.run(input_path, log)

log.info(buildings)
log.info(plant_loops)
#-------------------------------------------------------------------------------
## Get weather file
log.info("\n **Getting the weather file**")
wx = []
for file in os.listdir(os.path.join(input_path, "building_sim")):
    if file.endswith(".epw"):
        wx.append(os.path.join(input_path, "building_sim", file))
# Check for one and only one .epw file
if len(wx) > 1:
    log.error("More than one weather file dectected in the 'building_sim' " \
        "folder.")
    log.info("Program terminated early!")
    sys.exit("See log file.")
elif len(wx) == 0:
    log.error("No weather file was specified. Place an .epw file in the " \
        "'building_sim' folder")
    log.info("Program terminated early!")
    sys.exit("See log file.")
else:
    Twb, Tdb = get_wx.run(wx[0], ts_opt, log)
    log.info("Weather file: {}".format(wx[0]))
#-------------------------------------------------------------------------------
## Get building data from .eso files
# This action will be executed unless specifically excluded by the -c or -p
# flags.
if not curve_processor and not plant_loops_processor:
    log.info("\n **Performing the building file pre-processor**")

    buildings, plant_loops = get_sim_data.bldgs(
        input_path, buildings, plant_loops, ts_opt, log)

    # Write dictionaries to file
    try:
        os.path.isdir(os.path.join(input_path, "workspace"))
    except:
        os.mkdir(os.path.join(input_path, "workspace"))

    # Pickle dump
    pkl.dump(buildings, open(os.path.join(
        input_path, "workspace", "buildings.p"), "wb"))
    pkl.dump(plant_loops, open(os.path.join(
        input_path, "workspace", "plant_loops.p"), "wb"))
    log.info("buildings.p and plant_loops.p saved to workspace folder")

    # Perform -b only tasks
    if buildings_processor:
        # Write load and flow data
        for p in plant_loops:
            if p not in buildings:
                with open(os.path.join(input_path, "workspace",
                    "{}_load.csv".format(p)), "w", newline="") as f:
                    wtr = csv.writer(f, dialect="excel")
                    for v in plant_loops[p]["district_cooling_load"]:
                        wtr.writerow([v])
                with open(os.path.join(input_path, "workspace",
                    "{}_flow.csv".format(p)), "w", newline="") as f:
                    wtr = csv.writer(f, dialect="excel")
                    for v in plant_loops[p]["district_mass_flow"]:
                        wtr.writerow([v])
                max_flow = round(max(plant_loops[p]["district_mass_flow"]), 3)
                log.info("The peak mass flow rate for this plant is {} " \
                    "[kg/s] or ~{} [m3/s]".format(
                        max_flow, max_flow / 1000))
        # Terminate early
        log.warning("Terminated at completion of buildings processor")
        sys.exit("Terminated at completion of buildings processor")
#-------------------------------------------------------------------------------
## Process plant loops to get chiller performance curve data
# This action will be executed unless specifically excluded by the -c flag.
# If -b is present, the program will terminate prior to this step.
if not curve_processor:
    log.info("\n **Performing the plant loop pre-processor**")

    # Load buildings.p and plant_loops.p if the -p flag is provided
    if plant_loops_processor:
        try:
            buildings = pkl.load(open(os.path.join(input_path, "workspace",
                "buildings.p"), "rb"))
            plant_loops = pkl.load(open(os.path.join(input_path, "workspace",
                "plant_loops.p"), "rb"))
        except:
            log.error("Failed to load required data. Run without '-p' flag " \
                "or with '-b' flag first.")
            log.info("Program terminated early!")
            sys.exit("See log file")

    plant_loops = get_sim_data.plants(input_path, buildings, plant_loops,
        ts_opt, log)

    # Pickle dump
    pkl.dump(plant_loops, open(os.path.join(
        input_path, "workspace", "plant_loops.p"), "wb"))
    log.info("plant_loops.p saved to workspace folder")

    # Perform -p only tasks
    if plant_loops_processor:
        # Terminate early
        log.warning("Terminated at completion of plant loops processor")
        sys.exit("Terminated at completion of plant loops processor")
#-------------------------------------------------------------------------------
## Process performance curves
# This action will be executed unless program has terminated earlier. If all
# the building and plant loop data is previously processed, the -c flag allows
# the program to pick up from here and not require parsing the .eso files
log.info("\n **Performing the performance curve pre-processor**")
if curve_processor:
    try:
        buildings = pkl.load(open(os.path.join(input_path, "workspace",
            "buildings.p"), "rb"))
        plant_loops = pkl.load(open(os.path.join(input_path, "workspace",
            "plant_loops.p"), "rb"))
        log.info("Loading data from 'buildings.p' and 'plant_loops.p'")
    except:
        log.error("Failed to load required data. Run without '-p' flag " \
            "or with '-b' flag first.")
        log.info("Program terminated early!")
        sys.exit("See log file")

plant_loops = process_curves.run(buildings, plant_loops, input_path,
    segments, Twb, Tdb, log)





# check buildings
# print("\n Buildings Check")
# for k, v in buildings.items():
#     for i, j in v.items():
#         print(k,":", i, len(j))


for p in plant_loops:
    print("Plant Loop: ", p)
    print("Keys:", plant_loops[p].keys())
    for c in plant_loops[p]:
        try:
            print("Chiller Keys:", plant_loops[p][c].keys())
        except:
            pass


print("Finished!")
# os.system("cp pre.log {}".format(
#     os.path.join(input_path, "pre-{}.log".format(time.time()))))
