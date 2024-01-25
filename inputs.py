from datetime import datetime, timedelta
from dateutil import tz, parser
import glob
import re
import os
import json
import yaml
import pandas as pd



def load_settings():
    '''Load settings from YAML config files'''

    with open('config.yaml') as f:                           # Load settings from YAML files
       config_dict = yaml.load(f, Loader=yaml.FullLoader)
    with open('per_run_overrides.yaml') as f:                           # Load settings from YAML files
       override_dict = yaml.load(f, Loader=yaml.FullLoader)
    return config_dict['settings'], override_dict['defaults'], override_dict['runs']

def read_bcms(settings):
    """Read Inputs files, choosing between scaler_calc1 and IPM2C21A based on value, return dict keyed on datetime"""
    files = glob.glob(settings['bcm_dir']+"\*.csv")
    bcms = {}
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')
    print("Loading BCMs", datetime.now())

    if os.path.isfile('bcm.pkl'):         # if already in pickle, return that, otherwise read from file
        df = pd.read_pickle('bcm.pkl')
        df.sort_index()
    else:
        for file in files:
            with open(file, 'r') as f:
                for line in f:
                    if 'time' in line: continue
                    dt_string, stamp, pol, scaler, ipm = line.strip().split(',')
                    if '?' in scaler: continue
                    dt = datetime.fromtimestamp(float(stamp),eastern)   # datetime in local tz
                    utc_dt = dt.astimezone(utc)  #datetime in utc
                    if float(scaler) > 15:
                        bcms[utc_dt] = float(ipm)
                    else:
                        bcms[utc_dt] = float(scaler)
        df = pd.DataFrame.from_dict(bcms, orient='index')
        df.sort_index()
        df.to_pickle('bcm.pkl')
    return df


def read_runs(settings):
    """Read run file to determine bounds to analyze"""
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')
    runs = {}

    files = [settings['input_dir']+"/NH3_runs.txt", settings['input_dir']+"/ND3_runs.txt"]

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

def read_offline_cc(settings):
    """Read calibration period file to get CCs"""
    eastern = tz.gettz('US/Eastern')

    files = [settings['input_dir']+"/nh3_cc.txt", settings['input_dir']+"/nd3_cc.txt"]

    ccs = {}
    for file in files:
        with open(file, 'r') as f:
            for line in f:
                if "#" in line: continue
                date, run, area, on_cc, on_pol, cc, pol = line.split()
                ccs[run] = float(cc)
    return ccs

def get_events(settings):

    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')
    filename_regex = re.compile(
        '(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})__(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}).txt')
    #all_files = glob.glob(f"{settings['proton_data_dir']}/*.txt") \
    #            + glob.glob(f"{settings['deuteron_data_dir']}/*.txt")
    all_files = glob.glob(f"{settings['sample_data_dir']}/*.txt")
    events = {}
    print("Loading events", datetime.now())

    if os.path.isfile('event.pkl'):         # if already in pickle, return that, otherwise read from file
        df = pd.read_pickle('event.pkl')
        df.sort_index()
    else:
        print("Filling pickle")
        for eventfile in all_files:
            if 'base' in eventfile or 'current' in eventfile: continue
            print('Parsing file:', eventfile)
            with open(eventfile, 'r') as f:
                for line in f:
                    event = json.loads(line)
                    #for key in list(event.keys()):   # reducing data size by removing lists
                    #    if isinstance(event[key], list):
                    #        del event[key]
                    event['start_dt'] = parser.parse(event['start_time']).replace(tzinfo=utc)
                    event['stop_dt'] = parser.parse(event['stop_time']).replace(tzinfo=utc)
                    events[event['stop_dt']] = event
        print("Entering to dataframe")
        df = pd.DataFrame.from_dict(events, orient='index')
        print("Done filling")
        df.sort_index()
        df.to_pickle('event.pkl')
    return df

