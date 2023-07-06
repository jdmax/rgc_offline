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
    bcms = read_bcms()   # keyed on datetime
    runs = read_runs()             # keyed on run  number, value is dict with 'start_time', 'stop_time', 'species'
    moller_runs = read_mollers()   # keyed on dt, value is pol
    scatter_runs = read_scattering() # keyed on run number, value is pol


    for run in sorted(runs.keys()):   # get dose for this event
        events = select_events(settings, runs[run]['start_time'], runs[run]['stop_time'])
        if '20' in runs[run]['cell']:
            raster_area = np.pi*9*9  # assuming 18mm raster
        elif '15' in runs[run]['cell']:
            raster_area = np.pi*6.5*6.5  # assuming 13mm raster
        else:
            print('No cell match')
            raster_area = 1
        weighted_pol = 0
        weight = 0
        # Charge average pol per run
        for event in sorted(events):
            sum_charge = 0
            event_start = datetime.fromtimestamp(float(event['start_stamp']),utc)
            event_stop = datetime.fromtimestamp(float(event['stop_stamp']),utc)
            include_bcms = []
            for dt in bcms.keys():  # find bcms to include
                if event_start < dt < event_stop:
                    include_bcms.append(dt)   #
            previous = 0
            for dt in sorted(include_bcms):  # do time weighted sum
                if previous = 0: previous = dt
                if dt-previous > 60: # too long since last bcm reading, assuming beam off in between
                    previous = dt
                    continue
                sum_charge += bcms[dt]*(dt-previous)     # summming nanocoulombs by time
            event['dose'] = sum_charge*e_per_nc/raster_area



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
                entry['start_time'] = parser.parse(date+" "+start)
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

def select_events(settings, begin, end):
    '''Return events from datetime range given'''
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')

    #begin = parser.parse(begin).replace(tzinfo=eastern)
    #end = parser.parse(end).replace(tzinfo=eastern)
    filename_regex = re.compile(
        '(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})__(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}).txt')
    all_files = glob.glob(f"{settings['proton_data_dir']}/*.txt") \
                     + glob.glob(f"{settings['deuteron_data_dir']}/*.txt")
    included = []

    for file in sorted(all_files):
        if 'current' in file or 'baseline' in file:
            continue
        else:
            m = filename_regex.search(file)
            if not m: continue  # skip if we don't match the regex
            start = m.groups()[0]
            stop = m.groups()[1]
            start_dt = datetime.strptime(start, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=utc)
            stop_dt = datetime.strptime(stop, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=utc)
            if start_dt < end < stop_dt or start_dt< begin < stop_dt:
                included.append(file)
    events = {}
    for eventfile in included:
        print('Parsing file:', eventfile)
        with open(eventfile, 'r') as f:
            for line in f:
                event = json.loads(line)
                s = event['stop_time']
                line_stoptime = datetime.strptime(s[:26], '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=utc)
                # utcstamp = str(event['stop_stamp'])
                #utcstamp = parser.parse(event['stop_stamp']).replace(tzinfo=utc)
                if begin < line_stoptime < end and 'pol' in event:
                    events[line_stoptime] = event  # full dictionary from datafile
                    events[line_stoptime]['stop_time'] = line_stoptime  # full dictionary from datafile
    return events

if __name__ == '__main__':
    main()