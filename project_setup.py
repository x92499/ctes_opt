# setup.py
# CTES Optimization Processor
# Setup project files
# Karl Heine, kheine@mines.edu, heinek@erau.edu
# July 2021

import csv
import json
import logging as log
import os
import shutil
import sys
import time

def run(args):
    # Check for existance of input directories
    input_paths = []
    cwd = os.getcwd()
    if args['input_path'] != None:
        for p in args['input_path']:
            if os.path.isabs(p):
                input_paths.append(p)
            elif os.path.isdir(p):
                input_paths.append(os.path.join(cwd, p))
            else:
                print("File path '{}' not found; searching local folder".format(
                    p))
                input_paths.append(cwd)
    else:
        print("No input path specified; searching local folder only")
        input_paths.append(cwd)

    # Create new project folders
    folders = [
        'ampl_files',
        'building_simulations',
        'district_plant_simulations',
        'optimization_results',
        'project_workspace',
        'seed_models',
        'weather_files']
    if not os.path.isdir(args['project_name']):
        os.mkdir(args['project_name'])
    elif args['overwrite']:
        shutil.rmtree(args['project_name'])
        os.mkdir(args['project_name'])
    else:
        sys.exit('Error: project already exists with that name. Use -o to ' \
            'overwrite existing project.')

    for f in folders:
        os.mkdir(os.path.join(args['project_name'], f))

    # Set up logger (after project_workspace folder is created)
    log.basicConfig(
        filename=os.path.join(args['project_name'], 'project_workspace',
            'ctes_processor.log'),
        filemode='w',
        format="%(levelname)s: %(message)s",
        level=log.DEBUG)
    log.info('Logging initialized')
    log.info("File: 'project_setup.py'. Start time: {}".format(time.ctime()))
    log.info("Arguments: {}".format(args))
    print('Logger initialized: see project_workspace folder for .log file')

    # Scrub input file paths for .osm, .eso, .epw, and chiller.dat files
    chillers = []
    esos = []
    osms = []
    wx = []
    for p in input_paths:
        for file in os.listdir(p):
            filename = file
            if file.endswith('.eso'):
                if file == 'eplusout.eso':
                    filename = input("WARNING: File is named 'eplusout.eso'. " \
                        "Please specify a new file name for use in this " \
                        "project: ")
                elif file in esos:
                    filename = input("WARNING: Filename {} already exists'. " \
                        "Please specify a new file name for use in this " \
                        "project: ".format(file))
                esos.append(filename)
                shutil.copy(os.path.join(p,file),
                    os.path.join(args['project_name'],'building_simulations',
                        filename))
                log.info("{} added to project".format(filename))
            elif file.endswith('.osm'):
                if file in osms:
                    filename = input("WARNING: Filename {} already exists'. " \
                        "Please specify a new file name for use in this " \
                        "project: ".format(file))
                osms.append(filename)
                shutil.copy(os.path.join(p,file),
                    os.path.join(args['project_name'],'seed_models', filename))
                log.info("{} added to project".format(filename))
            elif file.endswith('.epw'):
                wx.append(file)
                shutil.copy(os.path.join(p,file),
                    os.path.join(args['project_name'],'weather_files', file))
                log.info("{} added to project".format(filename))
            elif 'chiller' in file and file.endswith('.dat'):
                if file in chillers:
                    filename = input("WARNING: Filename {} already exists'. " \
                        "Please specify a new file name for use in this " \
                        "project: ".format(file))
                chillers.append(filename)
                shutil.copy(os.path.join(p,file),
                    os.path.join(args['project_name'],'building_simulations',
                        filename))
                log.info("{} added to project".format(filename))

    # Report summary of files transferred into project
    log.info("Expected project contents: {} .eso files, {} .osm files, {} " \
        ".epw files, and {} chillerX.dat files".format(
            len(esos), len(osms), len(wx), len(chillers)))

    # Create .csv to define district chiller loops
    with open(os.path.join(args['project_name'], 'ctes_district.csv'),
        'w', newline="") as f:
        wtr = csv.writer(f, dialect='excel')
        wtr.writerow(['id', 'building', 'ctes_type (rtu, chiller, district)'])
        idx = 0
        for v in esos:
            wtr.writerow([idx, v.strip('.eso'), "SET BEFORE RUNNING!"])
            idx += 1
    f.close()

    # Create program_manager.json with defaults
    pm = {
        'project_name': args['project_name'],
        'timesteps': 4,
        'segments': 3,
        'utss': 'ib40',
        'ctes': '1170c'
    }
    with open(os.path.join(args['project_name'], 'program_manager.json'),
        'w') as f:
        json.dump(pm, f, indent=2)
    f.close()

    log.info("Program_manager.json created with default values: {}".format(pm))
    log.info("Setup processes complete. Edit the ctes_district.csv file to " \
        "designate building for 'rtu', 'chiller', or '<district>' " \
        "as appropriate.")
    log.info("End time for setup: {}".format(time.ctime()))

    return

def check(project):
    # Check for project directory
    if not os.path.isdir(project):
        sys.exit("Project '{}' does not exist; " \
        "perform setup with -s first".format(project))

    # Check for districts.csv
    if not os.path.isfile(os.path.join(project, 'ctes_district.csv')):
        sys.exit("ctes_district.csv file is missing; " \
            "re-create file manually or by re-performing setup with -s")

    # The above checks imply that the setup process was executed. Now create
    # the logger and pass back to the main program.

    # Re-set up logger
    log.basicConfig(
        filename=os.path.join(project, 'project_workspace',
            'ctes_processor.log'),
        filemode='a',
        format="%(levelname)s: %(message)s",
        level=log.DEBUG)
    log.info('Logging re-initialized')
    log.info("Start time for pre-processing run: {}".format(time.ctime()))
    print('Logger initialized: see project_workspace folder for .log file')
    log.info('Initial setup check: passed')

    return log
