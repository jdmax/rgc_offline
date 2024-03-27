from datetime import datetime, timedelta
from dateutil import tz, parser
import glob
import shelve
import re
import os
import json
import yaml
import numpy as np
import pandas as pd

def main():
    """"""

    outp = open('run_dose_p.txt', 'w')
    outd = open('run_dose_d.txt', 'w')
    outp.write(f"#run\tcell\tpol\tdose\sum_dose\n")
    outd.write(f"#run\tcell\tpol\tdose\sum_dose\n")

    runs = read_runs()

    p_dose = 0
    d_dose = 0

    for run in sorted(runs.keys()):
        if 'p' in runs[run]['species']:
            p_dose += float(runs[run]['dose'])
            outp.write(f"{run}\t{runs[run]['cell']}\t{runs[run]['off_pol']}\t{runs[run]['dose']}\t{p_dose}\n")
        if 'd' in runs[run]['species']:
            d_dose += float(runs[run]['dose'])
            outd.write(f"{run}\t{runs[run]['cell']}\t{runs[run]['off_pol']}\t{runs[run]['dose']}\t{d_dose}\n")

def read_runs():
    """Read scattering example file"""
    file = "run_online.txt"
    run_dict = {}  # keyed on run, value is polarization

    with open(file, 'r') as f:
        for line in f:
            if '#' in line: continue
            run, start, stop, species, cell, on_pol, off_pol, dose = line.strip().split('\t')
            run_dict[run] = {}
            run_dict[run]['start'] = start
            run_dict[run]['stop'] = stop
            run_dict[run]['species'] = species
            run_dict[run]['cell'] = cell
            run_dict[run]['on_pol'] = on_pol
            run_dict[run]['off_pol'] = off_pol
            run_dict[run]['dose'] = dose
    return run_dict



if __name__ == '__main__':
    main()