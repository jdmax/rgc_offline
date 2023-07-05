from datetime import datetime, timedelta
from dateutil import tz, parser
import glob
import shelve
import re
import json
import yaml

def main():
    """"""
    #print("Start: ", datetime.now())
    #bcms = read_bcms()
    #print("Stop: ", datetime.now())
    settings = load_settings()

    runs = read_runs()             # keyed on run  number, value is dict with 'start_time', 'stop_time', 'species'
    moller_runs = read_mollers()   # keyed on dt, value is pol
    scatter_runs = read_scattering() # keyed on run number, value is pol

    selected = select_events(settings, '02/07/2023 10:00', '02/07/2023 10:30')   # give in eastern

    print(len(selected))



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

    read_regex = re.compile('(\d\d\/\d\d\/\d\d)\s(\d+)\s(\d\d:\d\d)\s(\d\d:\d\d)')
    for file in files:
        with open(file, 'r') as f:
            matches = read_regex.findall(f.read())
            for match in matches:
                entry = {}
                date, run, start, stop = match
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

    begin = parser.parse(begin).replace(tzinfo=eastern)
    end = parser.parse(end).replace(tzinfo=eastern)
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