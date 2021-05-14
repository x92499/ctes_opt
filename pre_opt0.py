## Cool Thermal Storage Pre-Processor
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Initialized: February 2021
# Completed: March 2021
# Revision: Ongoing as of March 2021
# Written in support of an ice storage optimization workflow

## Description:
# This script is the supervisory script which manages all the pre-optimization
# subroutines required to execute the optimization program via AMPL.
#
# The script will look for EnergyPlus simulation output files (.eso), a weather
# data file (.epw), and a specific set of descriptive files which summarize key
# performance characteristics of the buildings and equipment to be optimized.
# Users may specify the path to the folder containing the required files, or the
# scipt will look for the 'simulation_outputs' folder in the current directory
# by default.
#
# To obtain the necessary files, certain OpenStudio measure(s) may be required.
# THIS PARAGRAPH WILL BE UPDATED WITH DETAILS ONCE THOSE MEASURE(S) ARE FINISHED

## Organization:
# 1. Import modules and set up logger
# 2. Parse command line arguments and other inputs
# 3. Check for proper files
# 4. Read in weather data
# 5. Read in chiller and plant loop information
# 6. Process chiller performance curves to generate chiller parameters
# 7. Process ice tank performance curves to generate ice tank parameters
# 8. Verify parameter output files were successfully(?) written by each module
# 9. Update and close logger

## Modules
import csv
import datetime
import esoreader
import getopt
import logging as log
import os
import pickle as pkl
import sys
import time

## Custom Modules
import get_args
import check_files
import file_reset
import get_wx
import get_bldg_data
import calc_chiller_params
import get_ctes_params
import create_erate
import get_base_costs
import parameter_writer

## Setup Logger
log.basicConfig(filename='log_pre_opt.log',
                filemode='w',
                format="%(levelname)s: %(message)s",
                level=log.DEBUG)
log.info("Logging initialized")
log.info("File: 'pre_opt.py'. Start time: {}".format(time.ctime()))
start_time = time.time()

## Main Program
# Parse command line arguments
mods = [log, os, sys]
argv = sys.argv[1:]
try:
    opts, args = getopt.getopt(argv,"bcfhri:o:s:t:",
                 ["bldgs_only", "chillers_only", "figs", "help", "reset", "in_path=","out_path=", "segs=","ts_opt="])
except:
    log.error("Unrecognized argument; see help: -h or --help")
    log.info("Program terminated early!")
    sys.exit("Error. See log file")

chillers_only, bldgs_only, figs, in_path, out_path, reset, segs, ts_opt = list(get_args.run(opts, args, log))

# Check folder contents for proper files
bldgs, chillers, wx = check_files.run(in_path, out_path, log)

# Reset previous outputs if flagged
if reset:
    file_reset.run(in_path, out_path, log)
    sys.exit("Files reset.")

# Get weather data from .epw file
Twb, Tdb = get_wx.run(in_path, wx, ts_opt, log)

## Set chiller operating season - NEED TO CONVERT TO USER ARGUMENT AT CL
cooling_season = [datetime.date(2006,3,15) - datetime.date(2005,12,31),
    datetime.date(2006,11,1) - datetime.date(2005,12,31)]
season = [i.days * 24 * ts_opt for i in cooling_season]
print("Season:", season)

# Execute if chillers_only is NOT specified
if not chillers_only:
    # Get data from .eso and chiller .dat files
    bldgs, community = get_bldg_data.run(in_path, bldgs, chillers, ts_opt, log)

    # Dump bldgs and community dictionaries into file
    pkl.dump(bldgs, open(os.path.join(in_path, "bldgs.p"), "wb"))
    pkl.dump(community, open(os.path.join(in_path, "community.p"), "wb"))
    log.info("'bldg.p' and 'community.p' files saved to {}".format(in_path))

    # Write mass flow and cooling load .csv's for each district
    for d in community["district_loops"]:
        with open(os.path.join(in_path, "{}_load.csv".format(d)), "w", newline="") as f:
            wtr = csv.writer(f, dialect="excel")
            for t in range(len(community["district_loops"][d]["load"])):
                if t >= season[0] and t < season[1]:
                    wtr.writerow([-community["district_loops"][d]["load"][t]])
                else:
                    wtr.writerow([0])
        log.info("District thermal load profiles saved to {}".format(in_path))

        with open(os.path.join(in_path, "{}_flow.csv".format(d)), "w", newline="") as f:
            wtr = csv.writer(f, dialect="excel")
            max_flow = max(community["district_loops"][d]["m_dot"])
            print(max_flow)
            for t in range(len(community["district_loops"][d]["m_dot"])):
                if t >= season[0] and t < season[1]:
                    wtr.writerow([community["district_loops"][d]["m_dot"][t] /
                        max_flow])
                else:
                    wtr.writerow([0])
        log.info("District cooling fluid mass flow rates saved to {}".format(in_path))

    # Execute if buildings_only IS specified
    if bldgs_only:
        log.info("Preprocessor terminated at the completion of the " \
        "'get_bldg_data.py' script")
        log.info("Total pre-process run time: {}s".format(
            round(time.time() - start_time), 2))
        sys.exit("Buildings only pre-process success!")

# Execute if chillers_only IS specified
else:
    try:
        bldgs = pkl.load(open(os.path.join(in_path, "bldgs.p"), "rb"))
        community = pkl.load(open(os.path.join(in_path, "community.p"), "rb"))
    except:
        log.error("Failed to load previously processed data; required " \
            "with the -c flag specified.")
        log.info("Program terminated early!")
        sys.exit("Error. See log file")

    # Check for .eso's to match chiller plants
    for d in community["district_loops"]:
        if os.path.isfile(os.path.join(in_path, "{}.eso".format(d))):
            # This code section loads the eso and gets the total elec. use profile
            dd, data = esoreader.read(os.path.join(
                in_path, "{}.eso".format(d)))
            log.info("Complete".format(i))

            # Load total electric load profile into community dictionary
            
        else:
            log.error("District cooling plant '{}' was specified, but no " \
                "simulation results were provided. Please simulate using the " \
                "a district cooling workflow.".format(
                    d))
            log.info("Program terminated early!")
            sys.exit("See log file.")



sys.exit()

##### BREAK WORKSPACE ABOVE ########

# Calculate chiller performance parameters
bldgs = calc_chiller_params.chillers(bldgs, segs, Tdb, Twb, log)
community = calc_chiller_params.district(community, segs, Tdb, Twb, season, log)

# Calculate CTES parameters
ctes = get_ctes_params.run(community, bldgs, ts_opt, log)

# Create electricity rate -> Need boolean and code if using other resource (URDB or Emmissions?)
erates = create_erate.run(ts_opt, log)

# Calculate baseline costs
erates, community = get_base_costs.run(community, erates, ts_opt, log)

## Write data to AMPL-readable files
parameter_writer.community(out_path, ts_opt, community, ctes, erates, segs, log)
parameter_writer.chillers(out_path, community, bldgs, log)
parameter_writer.ctes(out_path, ctes, log)

# Make figures(Lower priority - )

## Close logger
log.info("Preprocessor successfully finished. End time: {}".format(
    time.ctime()))
log.info("Total pre-process run time: {}s".format(
    round(time.time() - start_time), 2))
print("Success!")
