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

    settings = load_settings()
    bcms = read_bcms()   # dataframe index on datetime
    runs = read_runs()             # keyed on run  number, value is dict with 'start_time', 'stop_time', 'species'
    ccs = read_offline_cc()             # keyed on run  number, value cc float

    events = get_events(settings)  # dataframe index on datetime
    #moller_runs = read_mollers()   # keyed on dt, value is pol
    #scatter_runs = read_scattering() # keyed on run number, value is pol
    print("Finished loads", datetime.now())

    out = open('run_online.txt', 'w')
    out.write(f"#run\tstart_time\tstop_time\tspecies\tcell\tcharge_avg_online\tcharge_avg_offline\trun_dose(Pe/cm2)\n")

    for run in sorted(runs.keys()):   # get dose for this event
        #if '16243' not in run: continue
        print("Run", run, runs[run]['start_time'], runs[run]['stop_time'])
        try:
            selected = events.loc[str(runs[run]['start_time']):str(runs[run]['stop_time'])]
        except ValueError:
            print('ValueError:', str(runs[run]['start_time']), str(runs[run]['stop_time']))
        #print(selected)
        if '20' in runs[run]['cell']:
            raster_area = np.pi*0.9*0.9  # assuming 18mm raster
        elif '15' in runs[run]['cell']:
            raster_area = np.pi*0.7*0.7  # assuming 14mm raster
        else:
            print('No cell match')
            raster_area = 1
        weighted_on_pol = 0
        weighted_off_pol = 0
        weight = 0

        # Charge average pol per run
        for index, row in selected.iterrows():  # loop through selected events
            sum_charge = 0
            begin = row['start_dt']
            end = row['stop_dt']
            include_bcms = bcms.loc[str(begin):str(end)]
            previous = 0
            for dt, bcm_row in include_bcms.iterrows():  # do time weighted sum
                if previous == 0: previous = dt
                if dt - previous > timedelta(seconds=60): # too long since last bcm reading, assuming beam off in between
                    previous = dt
                    continue
                if bcm_row[0]<1: continue # skip tiny readings
                sum_charge += bcm_row[0]*(dt-previous).total_seconds()     # summing nanocoulombs by time
                #if bcm_row[0] > 5:
                #    print("bcm",bcm_row[0],(dt-previous).total_seconds())
                previous = dt

            row['dose'] = sum_charge*e_per_nc/raster_area
            #print("event dose:",index, row['dose']/1E12)
            weighted_on_pol += row['dose']*row['pol']
            try:
                weighted_off_pol += row['dose']*row['area']*ccs[run]
            except Exception as e:
                print("Error in weighted offline sum")
                weighted_off_pol = 0
            weight += row['dose']
        charge_avg_on = weighted_on_pol/weight if weight>0 else 0
        charge_avg_off = weighted_off_pol/weight if weight>0 else 0
        run_dose = weight
        print("run dose:", run, run_dose / 1E12)
        out.write(f"{run}\t{runs[run]['start_time']}\t{runs[run]['stop_time']}\t{runs[run]['species']}\t{runs[run]['cell']}\t{charge_avg_on:.4f}\t{charge_avg_off:.4f}\t{run_dose/1E15}\n")

    # go through scattering runs and get Pt using Pb, put in same file


def read_bcms():
    """Read Inputs files, choosing between scaler_calc1 and IPM2C21A based on value, return dict keyed on datetime"""
    files = glob.glob("O:\poltar\HallB\RGC\BCM\Mya\*.csv")
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

def read_offline_cc():
    """Read calibration period file to get CCs"""
    eastern = tz.gettz('US/Eastern')

    files = ["../inputs/nh3_cc.txt", "../inputs/nd3_cc.txt"]

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
    all_files = glob.glob(f"{settings['proton_data_dir']}/*.txt") \
                + glob.glob(f"{settings['deuteron_data_dir']}/*.txt")
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
                    for key in list(event.keys()):
                        if isinstance(event[key], list):
                            del event[key]
                    event['start_dt'] = parser.parse(event['start_time']).replace(tzinfo=utc)
                    event['stop_dt'] = parser.parse(event['stop_time']).replace(tzinfo=utc)
                    events[event['stop_dt']] = event
        df = pd.DataFrame.from_dict(events, orient='index')
        print("Done filling ")
        df.sort_index()
        df.to_pickle('event_old.pkl')
    return df


if __name__ == '__main__':
    main()