## Get command line user arguments

# -buildings_processor (-b): perform building file (.eso) preprocessing
# -curve_processor (-c): perform community preprocessing
# -plant_loops_processor (-p): perform district plant loop preprocessing
# -input_path= (-i): set path to scenario folder
# -segments= (-s): set number of segments for chiller curve linearization (default: 3)
# -ts_opt= (-t): set number of timesteps per hour for optimization (default: 1)

import os
import sys

def run(opts, args, log):
    # set defaults
    buildings_processor = False
    curve_processor = False
    plant_loops_processor = False
    reset = False
    input_path = os.path.join(os.getcwd())
    segments = 3
    ts_opt = 1
    # execute program
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print("Help! Needs to be populated w/useful info")
            sys.exit("See log file")
        elif opt in ("-b", "--buildings_processor"):
            print("Performing building pre-processing step")
            log.info("Performing building pre-processing step")
            buildings_processor = True
        elif opt in ("-c", "--curve_processor"):
            print("Performming performance curve pre-processing step")
            log.info("Performming performance curve pre-processing step")
            curve_processor = True
        elif opt in ("-p", "--plant_loops_processor"):
            print("Performming district plant loops pre-processing step")
            log.info("Performming district plant loops pre-processing step")
            plant_loops_processor = True
        elif opt in ("-r", "--reset"):
            reset = True
        elif opt in ("-i", "--input_path"):
            if arg[1] == ":":
                input_path = arg
            else:
                input_path = os.path.join(os.getcwd(), arg)
        elif opt in ("-s", "--segments"):
            segments = int(arg)
        elif opt in ("-t", "--ts_opt"):
            ts_opt = int(arg)

    # Validate the specified input directory
    if not os.path.isdir(input_path):
        log.error("Specified input directory '{}' does not exist".format(
            input_path))
        log.info("Program terminated early!")
        sys.exit("See log file.")

    # Log argument values
    log.info("buildings_processor = {}".format(buildings_processor))
    log.info("curve_processor = {}".format(curve_processor))
    log.info("plant_loops_processor = {}".format(plant_loops_processor))
    log.info("reset = {}".format(reset))
    log.info("input_path = {}".format(input_path))
    log.info("segments = {}".format(segments))
    log.info("ts_opt = {}".format(ts_opt))

    return [buildings_processor, curve_processor, plant_loops_processor,
        reset, input_path, segments, ts_opt]
