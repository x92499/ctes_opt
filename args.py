# args.py
# CTES Optimization Processor
# Populate parser for command line arguments
# Karl Heine, kheine@mines.edu, heinek@erau.edu
# July 2021

import argparse

def args():
    # Create parser
    parser = argparse.ArgumentParser(description="CTES Optimization Processor.")

    # Create arguments
    parser.add_argument('-i', '--input_path', type=str, action='append',
        help=('specify source directory for input building energy simulation ' \
            'files; may be used multiple times'))
    parser.add_argument('-o', '--overwrite', action='store_const', const=True,
        help='overwrite existing project')
    parser.add_argument('-p', '--project_name', type=str,
        default='ctes_project', help='specify name of project directory')
    parser.add_argument('-r', '--run', action='store_const', const=True,
        help='run project pre-optimization processor; use with -p')
    parser.add_argument('-s', '--setup', action='store_const', const=True,
        help='set up initial project structure; use with -i and -p')
    parser.add_argument('-u', '--utility', action='store_const', const=True,
        help='update utility rate only')

    return parser
