## simulation_manager.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Initiated: May 17, 2021
# Completed: ** POSTPONED FOR FUTURE DEVELOPMENT **

#### INCOMPLETE DUE TO LOWER PRIORITY EFFORT

## The purpose of this script is to execute buiding energy simulations via
# OpenStudio in order to process the .eso output files for use in the
# CTES optimization workflow.

import getopt
import logging as log
import os
import sys
import time

# Custom Modules
sys.path.append("python_modules")
import get_args

#-------------------------------------------------------------------------------
## Setup Logger
log.basicConfig(filename='sim_mgr.log',
                filemode='w',
                format="%(levelname)s: %(message)s",
                level=log.DEBUG)
log.info("Logging initialized")
log.info("File: 'simulation_manager.py'. Start time: {}".format(time.ctime()))
start_time = time.time()
#-------------------------------------------------------------------------------
## Get user arguments from command line
argv = sys.argv[1:]
try:
    opts, args = getopt.getopt(argv, "hi:", [
        "help",
        "input_path="])
except:
    log.error("Unrecognized argument; see help: -h or --help")
    log.info("Program terminated early!")
    sys.exit("Error. See log file")

input_path = get_args.sim_mgr(opts, args, log)
#-------------------------------------------------------------------------------
## Verify args
print(input_path)
#-------------------------------------------------------------------------------
## Find osm seed files
seed_path = os.path.join(input_path, "seeds")
seeds = []
for f in os.listdir(seed_path):
    if f.endswith(".osm"):
        seeds.append(f)
#-------------------------------------------------------------------------------
## Find available weather files
wx_path = os.path.join(input_path, "weather")
wx = []
for f in os.listdir(wx_path):
    if f.endswith(".epw"):
        wx.append(f)
#-------------------------------------------------------------------------------
## Create osw workflow files
measure_path = os.path.join(os.getcwd(),"measures").replace("\\","/")
file_path = os.path.join(input_path, "seeds", seeds[0]).replace("\\","/")
weather_path = os.path.join(wx_path, wx[0]).replace("\\","/")
osw = []
osw.append('''{0}
    "seed_file":"{1}",
    "weather_file":"{2}",
    "measure_paths":["{3}"],
    "steps":[
        {0}
            "measure_dir_name":"expose_chillers"
        {5}
    ]
{5}'''.format("{", file_path, weather_path, measure_path, seed_path, "}"))

# Write .osw file
with open(os.path.join(input_path, "workspace", "test.osw"), "w", newline="") as f:
    for line in osw:
        f.write(line)
#-------------------------------------------------------------------------------
## Try to run the osw file
os.system("openstudio run -w {}".format(
    os.path.join(input_path,"workspace","test.osw")))
print("It came back!")


# osw.append('''{0}
#     "seed_file":"{1}",
#     "weather_file":"{2}",
#     "measure_paths":["{3}"],
#     "file_path":"{4}"
#     "run_directory":null,
#     "steps":[
#         {0}
#             "measure_dir_name":"expose_chillers"
#         {5}
#     ]
# {5}'''.format("{",seeds[0], wx[0], measure_path, seed_path, "}"))
