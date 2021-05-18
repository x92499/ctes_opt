## check_files.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# March 2, 2021

# The purpose of this module is the check the contents of the input directory
# to ensure that the following files exist:
# * One or more building energy simulation results files (.eso)
# * One weather file (.epw)
# * One or more chiller_index files (.dat)
# * One or more chiller data files (.dat)

import csv
import os
import sys

## Check files in the input directory
def run(in_path, out_path, log):
    # start logging
    log.info("**Checking for required files**")
    # Required: .eso, .epw, chiller_index.dat, chillerX.dat
    building_files = []
    chiller_files = []
    chiller_index_files = []
    weather_file = []
    other_files = []
    # check for input directory
    try:
        os.listdir(in_path)
    except:
        log.error("Input file directory does not exist")
        log.info("Program terminated early!")
        sys.exit("Error. See log file")
    # get files
    for file in os.listdir(in_path):
        if file.endswith(".eso"):
            building_files.append(file)
        elif file.endswith("chiller_index.dat"):
            chiller_index_files.append(file)
        elif file.endswith(".epw"):
            weather_file.append(file)
        else:
            other_files.append(file)
    # register number of building files
    log.info("{} building file(s) will be processed".format(
                len(building_files)))
    # check for 1 and only 1 weather file
    if len(weather_file) > 1:
        log.error("Too many weather files are in the directory; only \
                      one is allowed.")
        log.info("Program terminated early!")
    elif len(weather_file) == 0:
        log.error("Missing weather file.")
        log.info("Program terminated early!")
    else:
        wx = weather_file[0]
        log.info("The weather file '{}' will be used".format(wx))
    # check chiller files
    for f in chiller_index_files:
        chiller_count = len(open(os.path.join(in_path, f)).readlines())
        bldg = f.split("_")[0]
        chiller_file_count = 0
        for f2 in other_files:
            if f2.startswith(bldg):
                chiller_file_count += 1
                chiller_files.append(f2)
        if chiller_count == chiller_file_count:
            log.info("{} chiller data files for building '{}' " \
                     "will be processed".format(chiller_count, bldg))
        else:
            log.error("{} chiller data files are expected, only {} " \
                      "found.".format(chiller_count, chiller_file_count))
            log.info("Failed to find all the chiller files for building " \
                     "'{}'".format(bldg))
            log.info("Program terminated early!")
            sys.exit("Error. See log file")
    if len(chiller_index_files) == 0:
        log.warning("No chiller_index files were found")
    # clean up "other_files"
    for f in chiller_files:
        other_files.remove(f)

    # check for a district loop assignment file
    if "districts.dat" in other_files:
        log.info("A district loop assignment file was found")
        other_files.remove("districts.dat")

        # check to see if it is populated
        dist_check = open(os.path.join(in_path, "districts.dat"), "r")
        if len(dist_check.readlines()) == 0:
            log.warning("The 'district.dat' file is empty. " \
                "Any district cooling loads in the building simulation " \
                "files will be ignored unless assigned to a plant loop.")
    else:
        log.warning("No district loop assignment file was found. " \
            "Any district cooling loads in the building simulation " \
            "files will be ignored unless assigned to a plant loop in a " \
            "'districts.dat' file.")

    # Report extra/unused files
    if len(other_files) > 0:
        log.warning("{} extra files were found in the input directory; " \
                        "they will not be used by the preprocessor".format(
                        len(other_files)))
        log.info("The unused files are:")
        for f in other_files:
            log.info("  * {}".format(f))
    # setup output directory
    if not os.path.isdir(out_path):
        os.mkdir(out_path)
        log.info("Specified output directory did not exist; '{}' " \
                 "has been created".format(out_path))

    return building_files, chiller_files, wx
