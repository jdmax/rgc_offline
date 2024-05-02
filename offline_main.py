from datetime import datetime, timedelta
from dateutil import tz, parser
import numpy as np
import pandas as pd


import inputs
import analysis

def main():
    """Main analysis loop"""


    e_per_nc = int(6.241e9)  # electrons per nanocoloumb
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')

    settings, options, overrides = inputs.load_settings()
    bcms = inputs.read_bcms(settings)   # dataframe index on datetime
    bcms = bcms.sort_index()
    runs = inputs.read_runs(settings)         # keyed on run  number, value is dict with 'start_time', 'stop_time', 'species'
    ccs = inputs.read_offline_cc(settings)             # keyed on run  number, value cc float

    # choose which runs to analyze based on per_run_overrides ranges
    chosen_runs = {}
    #print(runs.keys())
    for start in overrides.keys():
        for number in range(start, overrides[start]['end']+1):
            if str(number) in runs:
                chosen_runs[str(number)] = runs[str(number)]
                runs[str(number)]['override'] = start
    events = inputs.get_events(settings)  # dataframe index on datetime  - only metadata in the pickle!
    events = events.sort_index()
    #moller_runs = read_mollers()   # keyed on dt, value is pol
    #scatter_runs = read_scattering() # keyed on run number, value is pol
    print("Finished loads", datetime.now())

    out = open('run_offline.txt', 'w')
    out.write(f"#run\tstart_time\tstop_time\tspecies\tcell\tcharge_avg_online\tcharge_avg_offline_cc\tcharge_avg_offline\trun_dose(Pe/cm2)\n")

    current_eventfile = ''
    results_meta = {}
    for run in sorted(chosen_runs.keys()):   # loop on runs, get dose for this run
        #if '16243' not in run: continue
        results = {}
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
        weighted_off_cc_pol = 0  # online with offline calibration
        weighted_off_pol = 0
        weight = 0

        # Charge average pol per run
        for index, row in selected.iterrows():  # loop through selected events, run analysis for each event
            # row is event metadata dict for that event, index is stop_dt
            #print(row)
            sum_charge = 0

            # load eventfile to dataframe if needed
            if not row['eventfile'] in current_eventfile:
                event_df = inputs.eventfile_to_df(row['eventfile'])  # dataframe indexed on stop datetime
                current_eventfile = row['eventfile']

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
                cc = ccs[run]
            except KeyError:
                print('No CC entry for run', run)
                continue
            try:
                weighted_off_cc_pol += row['dose']*row['area']*cc
            except Exception as e:
                print("Error in weighted offline cc sum", e)
                weighted_off_pol = 0

            freq_list = np.array(event_df.loc[index]['freq_list'])
            phase = np.array(event_df.loc[index]['phase'])
            basesweep = np.array(event_df.loc[index]['basesweep'])

            try:
                wings = event_df.loc[index]['settings']['analysis']['wings']
                sum_range = event_df.loc[index]['settings']['analysis']['sum_range']
                #print(wings)
            except KeyError:
                print("KeyError on ",row['stop_dt'])
                continue
            type = runs[run]['species']
            if not options['online_defaults']:
                if 'wings' in overrides[runs[run]['override']]:
                    wings = overrides[runs[run]['override']]['wings']
                else:
                    wings = options['defaults-'+type]['wings']
                if 'sum_range' in overrides[runs[run]['override']]:
                    sum_range = overrides[runs[run]['override']]['sum_range']
                else:
                    sum_range = options['defaults-'+type]['sum_range']
                if 'cc' in overrides[runs[run]['override']]:
                    cc = overrides[runs[run]['override']]['cc']
                else:
                    cc = options['defaults-'+type]['cc']
            poly = analysis.poly3  # default is third order

            #try:
            result = analysis.area_signal_analysis(freq_list, phase, basesweep, wings, poly, sum_range)
            pol = result['area']*cc
            weighted_off_pol += row['dose']*pol
            result['offline_cc'] = cc
            #except Exception as e:
            #    print("Error in weighted full offline sum", e)
            #    weighted_off_pol = 0
            weight += row['dose']
            print("Finished event", index, datetime.now())
            results[row['stop_dt']] = event_df.loc[index].to_dict()
            results[row['stop_dt']]['result'] = result
            results_meta[index] = row
            results_meta[index]['run_number'] = run
            results_meta[index]['online_pol'] = row['pol']
            results_meta[index]['offline_pol'] = pol
            results_meta[index]['offline_cc'] = cc
        charge_avg_on = weighted_on_pol/weight if weight>0 else 0
        charge_avg_off_cc = weighted_off_cc_pol/weight if weight>0 else 0
        charge_avg_off = weighted_off_pol/weight if weight>0 else 0
        run_dose = weight
        print("Finished run", datetime.now(), "run dose:", run, run_dose / 1E12)
        out.write(f"{run}\t{runs[run]['start_time']}\t{runs[run]['stop_time']}\t{runs[run]['species']}\t{runs[run]['cell']}\t{charge_avg_on:.4f}\t{charge_avg_off_cc:.4f}\t{charge_avg_off:.4f}\t{run_dose/1E15}\n")


        # Write run results to dataframe and pickle
        df = pd.DataFrame.from_dict(results, orient='index')
        df.sort_index()
        df.to_pickle('results/results'+run+'.pkl')
        print('Wrote results for run', run, 'to pickle')

    df = pd.DataFrame.from_dict(results_meta, orient='index')
    df.sort_index()
    df.to_pickle('results/result_meta.pkl')

if __name__ == '__main__':
    main()
