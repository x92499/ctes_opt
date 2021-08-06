# Code tester

# Import modules
import argparse
import json
import logging as log
import os
import sys
import time

# Custom modules
sys.path.append("ctes_resources/scripts")
import aggregator
import args
import create_erate
import data_writer
import buildings
import project_setup
import storage

#-------------------------------------------------------------------------------
print('Started...')

#-------------------------------------------------------------------------------
# Parse command line arguments
parser = args.args()
parser.parse_args()

# Convert to usable arguments
args=vars(parser.parse_args())

#-------------------------------------------------------------------------------
# Peform setup actions if necessary
if args['setup']:
    print('Executing project setup')
    project_setup.run(args)
    print('Setup complete.')
    print("Note: You must open the 'ctes_district' file to specify " \
        "appropriate ctes type ('rtu', 'chiller', '<district>')")
    sys.exit()
#-------------------------------------------------------------------------------
# Run preprocessor(s)
if args['run']:
    print('Checking if project setup is complete')
    log = project_setup.check(args['project_name'])
    print('Executing optimization pre-processing scripts')
    preprocess = buildings.run(args['project_name'], log)
    if len(preprocess['community']['district_plant_names']) > 0:
        print("District loop(s) detected. ")
    else:
        print("No district loops assigned, proceeding with CTES processing")
        log.info("Processing CTES models for chillers and RTUs")
        preprocess = storage.run(args['project_name'], preprocess, log)
    preprocess = aggregator.run(preprocess, log)
    preprocess['utility_rate'] = create_erate.run(
        preprocess['program_manager']['timesteps'], log)

#-------------------------------------------------------------------------------
# Run with new utility rate only
if args['utility']:
    print('Checking if project setup is complete')
    log = project_setup.check(args['project_name'])
    print('Generating new utility rate profile')
    # Get preprocess.json
    with open(os.path.join(args['project_name'], 'project_workspace',
        'preprocess.json'), 'r') as f:
        preprocess = json.load(f)
    f.close()
    preprocess['utility_rate'] = create_erate.run(
        preprocess['program_manager']['timesteps'], log)
#-------------------------------------------------------------------------------
# Data Summary
print("Writing files")
data_writer.data_structure(preprocess, os.path.join(args['project_name'],
    'project_workspace', 'preprocessor_data_structure.txt'), log)
data_writer.write_json(preprocess,os.path.join(args['project_name'],
    'project_workspace'), "preprocess.json", log)
data_writer.ampl(preprocess, log)
#-------------------------------------------------------------------------------
# Terminate Logger
log.info("Logging terminated at {}".format(time.ctime()))
