import inputs
from datetime import datetime, timedelta
from dateutil import tz, parser
import numpy as np

def main():
    """Main analysis loop"""


    e_per_nc = int(6.241e9)  # electrons per nanocoloumb
    eastern = tz.gettz('US/Eastern')
    utc = tz.gettz('UTC')

    settings = inputs.load_settings()
    bcms = inputs.read_bcms()   # dataframe index on datetime
    runs = inputs.read_runs()             # keyed on run  number, value is dict with 'start_time', 'stop_time', 'species'
    ccs = inputs.read_offline_cc()             # keyed on run  number, value cc float

    events = inputs.get_events(settings)  # dataframe index on datetime
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


if __name__ == '__main__':
    main()
