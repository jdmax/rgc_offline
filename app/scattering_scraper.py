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
    e_per_nc = int(6.241e9)  # electrons per nanocoloumb
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')

    moller_runs = read_mollers()   # keyed on dt, value is pol
    scatter_runs = read_scattering() # keyed on run number, value is pol
    print(scatter_runs)
    runs = read_runs()
    print("Finished loads", datetime.now())

    out = open('scattering_prelim.txt', 'w')
    out.write(f"#time run\tpbpt\tpb\tpt\n")

    for run in sorted(scatter_runs.keys()):
        previous = 0
        pb = 0
        pbpt = float(scatter_runs[run])
        for moller_dt in moller_runs.keys():
            if moller_dt > runs[run]['stop_time']:
                pb = float(moller_runs[previous])/100
                break
            else:
                previous = moller_dt
        pt = pbpt / pb if pb != 0 else 0

        out.write(f"{runs[run]['stop_time']}\t{run}\t{pbpt}\t{pb}\t{pt}\n")



def load_settings():
    '''Load settings from YAML config file'''

    with open('../config.yaml') as f:                           # Load settings from YAML files
       config_dict = yaml.load(f, Loader=yaml.FullLoader)
    return config_dict['settings']


def read_runs():
    """Read run file to determine bounds to analyze"""
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')
    runs = {}

    files = ["../inputs/NH3_runs.txt", "../inputs/ND3_runs.txt"]

    read_regex = re.compile('(\d+\/\d+\/\d+)\s(\d+)\s(\d+:\d+)\s(\d+:\d+)\s(\d\d)')
    for file in files:
        with open(file, 'r') as f:
            matches = read_regex.findall(f.read())
            for match in matches:
                entry = {}
                date, run, start, stop, cell = match
                entry['cell'] = cell
                entry['start_time'] = parser.parse(date+" "+start).replace(tzinfo=eastern)
                if start.split(":")[0] > stop.split(":")[0]:     # handle runs that end on next day
                    dt = parser.parse(date+" "+stop).replace(tzinfo=eastern)
                    entry['stop_time'] = dt + timedelta(days=1)
                else:
                    entry['stop_time'] = parser.parse(date+" "+stop).replace(tzinfo=eastern)
                entry['species'] = 'p' if 'H' in file else 'd'
                runs[run] = entry
    return runs

def read_mollers():
    """Read moller files"""
    files = glob.glob("../inputs/PB*")
    runs = {} # keyed on date, value is polarization
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')

    moller_regex = re.compile('Moller Run #(\d+)\n.+Polarization\s\(\%\)([\s-]\d+.\d+).+\n+baltzell\s-\s(\d{4}-\d{2}-\d{2} \d{2}:\d{2})')

    for file in files:
        with open(file, 'r') as f:
            matches = moller_regex.findall(f.read())
            for match in matches:
                run, pol, dt = match
                datetime = parser.parse(dt).replace(tzinfo=eastern)
                runs[datetime] = pol
    return runs


def read_scattering():
    """Read scattering example file"""
    file = "../inputs/scattering_run.txt"
    run_dict = {} # keyed on run, value is polarization

    with open(file, 'r') as f:
        for line in f:
            if '#' in line: continue
            if 'Runs' in line: continue
            runstr, pol, err = line.strip().split(';')
            runs = runstr.split(',')
            for run in runs:
                run_dict[run] = pol
                print(run, pol)
    print(run_dict)
    return run_dict



if __name__ == '__main__':
    main()