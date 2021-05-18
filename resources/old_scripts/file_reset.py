## reset.py
# This module resets previously generated output files

import os

def run(in_path, out_path, log):
    if os.path.isfile(os.path.join(in_path, "bldgs.p")):
        os.remove(os.path.join(in_path, "bldgs.p"))

    if os.path.isfile(os.path.join(in_path, "community.p")):
        os.remove(os.path.join(in_path, "community.p"))

    for file in os.listdir(in_path):
        if file.endswith(".csv"):
            os.remove(os.path.join(in_path, file))

    for file in os.listdir(out_path):
        os.remove(os.path.join(out_path, file))

    for file in os.listdir(os.path.join(out_path, "../results")):
        os.remove(os.path.join(out_path, "../results", file))

    log.info("Reset flag was specified. Files located in the folders {}, " \
        "{}, and {} were deleted. This includes previously generated " \
        "'bldgs.p' and 'community.p' dictionary files".format(
            in_path, out_path, os.path.join(out_path, "../results")))
