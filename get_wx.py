## get_wx.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# March 2, 2021
#
## The purpose of this module is to capture ambient wetbulb and drybulb weather
# data from a specified .epw file. Hourly values are interpolated by the
# to the specified optimization timestep.
#
# Inputs: input path, weather file in .epw format, optimization timestep, logger
# Outputs: Twb and Tdb arrays for the full year at specified timestep

import os
import sys
import csv

def run(wx, ts, log):
    # log progress
    log.info("**Obtaining temperatures from weather file**")

    # execute program
    Tdb = []
    Twb = []
    with open(wx, 'r', newline="") as f:
        rdr = csv.reader(f, delimiter=",")
        [next(rdr) for i in range(8)]
        for row in rdr:
            if len(Tdb) == 0:
                for i in range(ts):
                    Tdb.append(float(row[7]))
                    Twb.append(float(row[6]))
            else:
                wb, db = [float(v) for v in row[6:8]]
                for i in range(ts):
                    Tdb.append(Tdb[-1] + ((i+1)/ts * (db-Tdb[-1])))
                    Twb.append(Twb[-1] + ((i+1)/ts * (wb-Twb[-1])))

    # Log info and check data lengths
    if ts > 1:
        log.info("The hourly weather data was linearly interpolated " \
                 "according to the optimization timestep.")
    if len(Tdb) != len(Twb):
        log.error("The wetbulb and drybulb temperature arrays are not of " \
                  "equal length.")
        log.info("Program terminated early!")
        sys.exit("Failed in 'get_wx' module.")
    log.info("The following data was extracted from the weather file:")
    log.info(" * {} wetbulb temperatures".format(len(Twb)))
    log.info(" * {} drybulb temperatures".format(len(Tdb)))

    return Tdb, Twb
