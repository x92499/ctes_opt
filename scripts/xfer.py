## xfer.py
# Karl Heine, Colorado School of Mines, kheine@mines.edu
# Created: May 17, 2021
# Revised:

## The purpose of this program is to handle file transfer to the remote server
# at Colorado School of Mines to use the optimization solvers there

import os

def send(input_path):

    os.system("cp solver_files/* {}/ampl_files".format(input_path))
    os.system("scp {}/ampl_files/* kheine@track:CTES/{}".format(
        input_path, "xfer"))

    return

def receive(input_path):

    os.system("scp -r kheine@track:CTES/xfer/*.out {}/results".format(
        input_path))

    return
