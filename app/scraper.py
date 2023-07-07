from datetime import datetime, timedelta
from dateutil import tz, parser
import glob
import shelve
import re
import json
import yaml
import numpy as np

def main():
    """"""
    e_per_nc = int(6.241e9)  # electrons per nanocoloumb
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')

    settings = load_settings()
    print("Loading BCMs", datetime.now())
    bcms = read_bcms()   # keyed on datetime
    runs = read_runs()             # keyed on run  number, value is dict with 'start_time', 'stop_time', 'species'
    print("Loading events", datetime.now())
    events = get_events(settings)
    moller_runs = read_mollers()   # keyed on dt, value is pol
    scatter_runs = read_scattering() # keyed on run number, value is pol
    print("Finished loads", datetime.now())

    out = open('run_online.txt', 'w')

    for run in sorted(runs.keys()):   # get dose for this event
        print("Run", run, runs[run]['start_time'], runs[run]['stop_time'])
        selected = select_events(events, runs[run]['start_dt'], runs[run]['stop_dt'])
        if '20' in runs[run]['cell']:
            raster_area = np.pi*0.9*0.9  # assuming 18mm raster
        elif '15' in runs[run]['cell']:
            raster_area = np.pi*0.65*0.65  # assuming 13mm raster
        else:
            print('No cell match')
            raster_area = 1
        weighted_pol = 0
        weight = 0
        # Charge average pol per run
        for event in sorted(selected.keys()):
            sum_charge = 0
            event_start = datetime.fromtimestamp(float(selected[event]['start_stamp']),utc)
            event_stop = datetime.fromtimestamp(float(selected[event]['stop_stamp']),utc)
            include_bcms = []
            for dt in bcms.keys():  # find bcms to include
                if event_start < dt < event_stop:
                    include_bcms.append(dt)   #
            previous = 0
            for dt in sorted(include_bcms):  # do time weighted sum
                if previous == 0: previous = dt
                if dt - previous > timedelta(seconds=60): # too long since last bcm reading, assuming beam off in between
                    previous = dt
                    continue
                if bcms[dt]<1: continue # skip tiny readings
                sum_charge += bcms[dt]*(dt-previous).total_seconds()     # summing nanocoulombs by time
                print(bcms[dt],(dt-previous).total_seconds())

            selected[event]['dose'] = sum_charge*e_per_nc/raster_area
            print(event, selected[event]['dose'])
            weighted_pol += selected[event]['dose']*selected[event]['pol']
            weight += selected[event]['dose']
        charge_avg = weighted_pol/weight
        run_dose = weight
        out.write(f"{run}\t{runs[run]['stop_time']}\t{runs[run]['species']}\t{runs[run]['cell']}\t{charge_avg}\t{run_dose}")

    # go through scattering runs and get Pt using Pb, put in same file




def read_bcms():
    """Read Inputs files, choosing between scaler_calc1 and IPM2C21A based on value, return dict keyed on datetime"""
    files = glob.glob("O:\poltar\HallB\RGC\BCM\Mya\*.csv")
    bcms = {}
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')

    shelf = shelve.open('bcm_shelf')
    if 'bcms' in shelf:         # if already in shelf, return that, otherwise read from file
        bcms.update(shelf['bcms'])
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
        shelf['bcms'] = bcms
        shelf.close()
    return bcms


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

    read_regex = re.compile('(\d+\/\d+\/\d\d)\s(\d+)\s(\d\d:\d\d)\s(\d\d:\d\d)\s(\d\d)')
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
            if 'Runs' in line: continue
            runstr, pol, err = line.strip().split(';')
            runs = runstr.split(',')
            for run in runs:
                run_dict[run] = pol
    return run_dict


def get_events(settings):

    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')
    filename_regex = re.compile(
        '(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})__(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}).txt')
    all_files = glob.glob(f"{settings['proton_data_dir']}/*.txt") \
                + glob.glob(f"{settings['deuteron_data_dir']}/*.txt")
    events = {}

    shelf = shelve.open('event_shelf')
    if 'events' in shelf:         # if already in shelf, return that, otherwise read from file
        events.update(shelf['events'])
    else:
        print("Filling shelf")
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

        print("Done filling shelf")
        shelf['events'] = events
        shelf.close()
    return events

def select_events(events, begin, end):
    '''Return events from datetime range given'''
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')
    selected_events = []

    for event_dt in sorted(events.keys()):
        dt = events[event_dt]['stop_dt']
        if begin <  dt < end and 'pol' in events[event_dt]:
            selected_events[dt] = events[event_dt]  # full dictionary from datafile
    return selected_events

if __name__ == '__main__':
    main()