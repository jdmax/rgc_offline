from datetime import datetime, timedelta
from dateutil import tz, parser
import numpy as np
import pandas as pd


import inputs
import analysis

def main():
    """Main analysis loop"""

    sum_events = 0
    sum_sweeps = 0
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
    out.write(f"#run\tstart_time\tstop_time\tspecies\tcell\tcharge_avg_online\tcharge_avg_offline_cc\tcharge_avg_offline_ice\tcharge_avg_offline\tcharge_avg_offline_err\trun_dose(Pe/cm2)\tcc_on\tcc_off\tcc_off_err\tpol_on\tpol_off\tpol_off_err\tpol_off_m2\tpol_off_m2_err\n")
    #out.write(f"#run\tstart_time\tstop_time\tspecies\tcell\tcharge_avg_online\tcharge_avg_offline_cc\tcharge_avg_offline\trun_dose(Pe/cm2)\n")
 #  out.write(f"#run\tstart_time\tstop_time\tspecies\tcell\tcharge_avg_online\tcharge_avg_offline_cc\tcharge_avg_offline\trun_dose(Pe/cm2)\tcc_on\tcc_off\tcc_off_err\tpol_on\tpol_off\tpol_off_err\n")

    current_eventfile = ''
    results_meta = {}
    for run in sorted(chosen_runs.keys()):   # loop on runs, get dose for this run
        # Use the following two lines to check any individual run
        # if run != '16768':
        #     continue
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
        weighted_off_ice_pol = 0
        weight = 0

        on_pol_array = []
        off_pol_array = []
        off_pol_err_sqrd_array = []

        # full pol. uncertainty with uncorrelated error from each event
        weighted_off_pol_method2 = 0
        weighted_inverse_sigma2  = 0
        off_charge_avgd_pol_sum = 0

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
            try:
                include_bcms = bcms.loc[str(begin):str(end)]
            except KeyError:
                print("BCM key error at", begin, end)
                continue
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
            on_pol = row['pol']
            on_pol_array.append(on_pol)


            #print(on_pol)
            on_cc = row['pol']/row['area']
            weighted_on_pol += row['dose']*row['pol']
            try:  # try to set the cc from the overrides file
                # cc = ccs[run] # This was first run offline cc
                cc = overrides[runs[run]['override']]['cc']
            except KeyError:
                print('No CC entry for run', run)
                continue

            ## added on 03/24/2025 ##
            # Extract cc_err from overrides 
            try:
                cc_err = overrides[runs[run]['override']]['cc_err']
            except KeyError:
                print('No CC error entry for run', run)
                cc_err = 0  # Default to zero if not found
            try:
                weighted_off_cc_pol += row['dose']*row['area']*cc
            except Exception as e:
                print("Error in weighted offline cc sum", e)
                weighted_off_cc_pol = 0

            freq_list = np.array(event_df.loc[index]['freq_list'])
            phase = np.array(event_df.loc[index]['phase'])
            basesweep = np.array(event_df.loc[index]['basesweep'])
            off_cc = cc

            # Determine options for analysis
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
                if 'ice-correction' in overrides[runs[run]['override']]:
                    cc_ice = cc * overrides[runs[run]['override']]['ice-correction']
                else:
                    cc_ice = cc * options['defaults-'+type]['ice-correction']
            poly = analysis.poly3  # default is third order


            # Do actual signal analysis on event
            result = analysis.area_signal_analysis(freq_list, phase, basesweep, wings, poly, sum_range)
            ## added on 03/24/2025 ##
            #print(result['area'])
            # Compute standard deviation of area for error propagation
            sigma_area = np.std(result['area'])
            # Compute the uncertainty on pol
            # sigma_pol = np.sqrt((sigma_area * cc) ** 2 + (cc_err * result['area']) ** 2)
            sigma_pol_sqrd = (sigma_area * cc) ** 2 + (cc_err * result['area']) ** 2
            off_pol_err_sqrd_array.append(sigma_pol_sqrd)
            # print("**** Sigma of offline avg pol***")
            # print(sigma_pol)
            # print("************************")
            #############################
            pol = result['area']*cc
            pol_ice = result['area']*cc_ice
            off_pol_array.append(pol)


            sum_sweeps += row['sweeps']
            sum_events += 1
            
            print(row['area'],result['area'],event_df.loc[index]['cc'],cc)
            weighted_off_pol += row['dose']*pol
            weighted_off_ice_pol += row['dose']*pol_ice
            weight += row['dose']
            result['offline_cc'] = cc
            result['offline_cc_ice'] = cc_ice

            weighted_off_pol_method2 += pol/sigma_pol_sqrd
            weighted_inverse_sigma2 += 1/sigma_pol_sqrd
            off_charge_avgd_pol_sum +=  row['dose']* row['dose']*sigma_pol_sqrd

            #except Exception as e:
            #    print("Error in weighted full offline sum", e)
            #    weighted_off_pol = 0
            print("Finished event", index, datetime.now())
            results[row['stop_dt']] = event_df.loc[index].to_dict()
            results[row['stop_dt']]['result'] = result
            results_meta[index] = row
            results_meta[index]['run_number'] = run
            results_meta[index]['online_pol'] = row['pol']
            results_meta[index]['offline_pol'] = pol
            results_meta[index]['offline_pol_ice'] = pol_ice
            results_meta[index]['offline_cc'] = cc
        charge_avg_on = weighted_on_pol/weight if weight>0 else 0
        charge_avg_off_cc = weighted_off_cc_pol/weight if weight>0 else 0
        charge_avg_off_ice = weighted_off_ice_pol/weight if weight>0 else 0
        charge_avg_off = weighted_off_pol/weight if weight>0 else 0
        charge_avg_off_err = np.sqrt(off_charge_avgd_pol_sum)/weight if weight>0 else 0

        run_dose = weight
        on_pol_array = np.array(on_pol_array)
        off_pol_array = np.array(off_pol_array)
        off_pol_err_sqrd_array = np.array(off_pol_err_sqrd_array)

        # avg_on_pol = np.mean(on_pol_array)
        # avg_off_pol = np.mean(off_pol_array)
        # avg_off_pol_err = np.sqrt(np.sum(off_pol_err_sqrd_array)) / len(off_pol_err_sqrd_array)
        # avg_off_pol_err = np.sqrt(np.sum(off_pol_err_sqrd_array)) / len(off_pol_err_sqrd_array)

        # This is to avoid zero (or 10^-4 or 10^-5) scale values when taking the mean.
        # If you don't want to do that, comment the following lines 206-213 with 222, then uncomment 199-202 with 223
        threshold = 1e-3
        filtered_on_pol = on_pol_array[abs(on_pol_array) >= threshold]
        filtered_off_pol = off_pol_array[abs(off_pol_array) >= threshold]
        filtered_off_pol_err_sqrd_array = off_pol_err_sqrd_array[abs(off_pol_err_sqrd_array) >= threshold]
        avg_on_pol = np.mean(filtered_on_pol) if filtered_on_pol.size > 0 else np.nan
        avg_off_pol = np.mean(filtered_off_pol) if filtered_off_pol.size > 0 else np.nan
        avg_off_pol_std = np.std(filtered_off_pol) if filtered_off_pol.size > 0 else np.nan
        avg_off_pol_err = np.sqrt(np.sum(filtered_off_pol_err_sqrd_array)) / len(filtered_off_pol_err_sqrd_array)


        off_pol_method2 = weighted_off_pol_method2/weighted_inverse_sigma2 if weighted_inverse_sigma2>0 else 0
        off_pol_method2_err = 1/np.sqrt(weighted_inverse_sigma2)

        # Some print statements for testing
        # print(len(on_pol_array))
        # print(on_pol_array)
        # print(len(off_pol_array))
        # print(off_pol_array)
        # print(off_pol_err_sqrd_array)
        print("Finished run", datetime.now(), "run dose:", run, run_dose / 1E12)
        out.write(f"{run}\t{runs[run]['start_time']}\t{runs[run]['stop_time']}\t{runs[run]['species']}\t{runs[run]['cell']}\t{charge_avg_on:.4f}\t{charge_avg_off_cc:.4f}\t{charge_avg_off_ice:.6f}\t{charge_avg_off:.4f}\t{charge_avg_off_err:.6f}\t{run_dose/1E15}\t{on_cc:.4f}\t{off_cc:.4f}\t{cc_err:.4f}\t{avg_on_pol:.4f}\t{avg_off_pol:.4f}\t{avg_off_pol_std:.6f}\t{off_pol_method2:.4f}\t{off_pol_method2_err:.6f}\n")
  #     out.write(f"{run}\t{runs[run]['start_time']}\t{runs[run]['stop_time']}\t{runs[run]['species']}\t{runs[run]['cell']}\t{charge_avg_on:.4f}\t{charge_avg_off_cc:.4f}\t{charge_avg_off:.4f}\t{run_dose/1E15}\t{on_cc:.4f}\t{off_cc:.4f}\t{cc_err:.4f}\t{avg_on_pol:.4f}\t{avg_off_pol:.4f}\t{avg_off_pol_std:.6f}\n")
        # out.write(f"{run}\t{runs[run]['start_time']}\t{runs[run]['stop_time']}\t{runs[run]['species']}\t{runs[run]['cell']}\t{charge_avg_on:.4f}\t{charge_avg_off_cc:.4f}\t{charge_avg_off:.4f}\t{run_dose/1E15}\t{on_cc:.4f}\t{off_cc:.4f}\t{cc_err:.4f}\t{avg_on_pol:.4f}\t{avg_off_pol:.4f}\t{avg_off_pol_err:.6f}\n")


        # # Write run results to dataframe and pickle
        df = pd.DataFrame.from_dict(results, orient='index')
        df.sort_index()
        df.to_pickle('results/results'+run+'.pkl')
        print('Wrote results for run', run, 'to pickle')

    df = pd.DataFrame.from_dict(results_meta, orient='index')
    df.sort_index()
    df.to_pickle('results/result_meta.pkl')
    print("total events, sweeps:", sum_events, sum_sweeps)

if __name__ == '__main__':
    main()
