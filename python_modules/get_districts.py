## Get Districts Preprocessor for CTES Optimization Workflow
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Initiated: May 13, 2021
# Completed:
# Revised:

## Description:
# This script parses the districts.csv file to determine which buildings to
# include in the optimization and to determine their plant loop assignments.

import csv
import os
import sys

def run(input_path, log):
    # check for and parse districts.csv
    buildings = {}
    plant_loops = {}
    disctrict_count = 0
    try:
        with open(os.path.join(input_path, "districts.csv"), "r",
            newline="") as f:
            rdr = csv.reader(f, dialect="excel")
            for row in rdr:
                b = row[0].strip()
                l = row[1].strip()
                buildings[b] = {}
                buildings[b]["plant_loop"] = l
                if l not in plant_loops and l != "" and l != "None":
                    plant_loops[l] = {}
                    disctrict_count += 1
                elif l not in plant_loops:
                    plant_loops[b] = {}
    except:
        log.error("Failed to properly parse 'districts.csv'. May be missing " \
            "or improperly formatted.")
        log.info("Program terminated early!")
        sys.exit("See log file.")

    # check for district_sim folder
    if disctrict_count > 0:
        try:
            os.path.isdir(os.path.join(input_path, "district_sim"))
        except:
            log.warning("Chilled water district loops are expected, but the " \
                "folder does not exist. Creating the directory. Plant loop " \
                "simulations will be required to fully process this scenario.")
            os.mkdir(os.path.join(input_path, "district_sim"))

    return buildings, plant_loops
