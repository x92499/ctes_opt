# aggregator.py
# CTES Optimization Processor
# Aggregate individual building results into community summary
# Karl Heine, kheine@mines.edu, heinek@erau.edu
# July 2021

def run(prep, log):
    # Get total timesteps
    steps = prep['program_manager']['timesteps'] * 8760
    # Set helper variables
    comm_elec_W = [0 for t in range(steps)]
    comm_cool_Wt = [0 for t in range(steps)]
    comm_elec_cool_W = [0 for t in range(steps)]
    comm_elec_non_cool_W = [0 for t in range(steps)]
    # Sum building profiles to generate community profile
    for b in prep['community']['building_names']:
        comm_elec_W = [i + j for i,j in zip(
            prep[b]['rate_electricity_W'], comm_elec_W)]
        comm_elec_cool_W = [i + j for i,j in zip(
            prep[b]['rate_elec_cooling_W'], comm_elec_cool_W)]
        comm_elec_non_cool_W = [i + j for i,j in zip(
            prep[b]['rate_elec_non_cooling_W'], comm_elec_non_cool_W)]
    prep['community']['rate_electricity_W'] = comm_elec_W
    prep['community']['rate_elec_cooling_W'] = comm_elec_cool_W
    prep['community']['rate_elec_non_cooling_W'] = comm_elec_non_cool_W

    return prep
