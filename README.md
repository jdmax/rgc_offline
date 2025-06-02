# Instructions for Users

To run the offline analysis software, you will need access to the experimental data. By default, the software points to the JLab O:\ drive to access the data. If you don't have access to that drive, copy the data locally and specify the location in the config.yaml file. You will need all the data from the `/group/poltar/HallB/RGC/` directories: `data-p`, `data-d`, and `BCM/Mya`. Other metadata can be found in the `inputs` directory within the code.

## An Introduction to the scripts

### inputs.py
This file processes experimental metadata to prepare it for use in the analysis code. The functions in this file run when you execute `offline_main.py`. It reads the BCM exports, run ranges, and event files, creating the `bcm.pkl` and `event.pkl` metadata files that are necessary for subsequent steps.

### main.py
This is the main GUI for walking through events to perform calibrations. For each calibration period, a calibration constant (CC) must be produced from either TEs (in the case of proton data) or golden events (in the case of deuteron data). While these calibrations are running, thorough notes should be taken documenting the analysis settings used to create each calibration for that period, such as any changes to the fit wings or sum range from the defaults necessary to produce a clean fit.

### per_run_overrides.yaml
Once the organizational and calibration steps are finished, the end result should be a hand-created `per_run_overrides.yaml` file in the main directory. This file sets options for the signal analysis, first establishing general defaults to apply to every event under the "options" heading. The next section, "runs", breaks down the entire experiment into sets of runs with common calibration settings. For each set of runs, it outlines the differences needed for analysis from the defaults. Each range is named after the starting run of the experiment and contains an "end" entry that specifies the last run in that range. 

Typically, a range might have a different set of "wings" (the two areas outside the polarization signal on the q-curve used in the polynomial fit, given from 0 to 1). Ranges might also specify a different `sum_range`, which causes the final integration to occur only in a smaller central section to ignore noise away from the polarization signal. Most importantly, each range needs a "cc" (calibration constant) to convert the area calculated in the code to a polarization value.

### offline_main.py
This is the core of the offline analysis, which takes the metadata for events and calibrations and uses it to analyze each event. It first loads the metadata pickles, then walks through each experimental run. For each run, it selects the NMR events that occurred in that time frame. For each event in the timeframe, it performs signal analysis and loads data from the necessary event file if it isn't already open. The signal analysis uses methods from the `analysis.py` file for each event. Once the signal analysis is complete, results are saved to two files in the `results` directory: a quick-to-read metadata file for all runs called `results_meta.pkl`, and full results pickles for each run named `results[run number].pkl`.

### results_main.py
Finally, results can be visualized by running `results_main.py`. From here, you can select a date range to plot and select individual events to see how the analysis performed.


## Summary of steps in general

1. Ensure the location of all necessary files is set in `config.yaml`.
2. Set all calibration data for each run range in `per_run_overrides.yaml`, using `main.py` to navigate through and perform analysis on the calibration events.
3. Run `offline_main.py` to perform the full analysis using the calibrations you set.
4. Run `results_main.py` to visualize the results.


## Procedures for Extracting Calibration Constants

Extracting calibration constants differs between proton (NH₃) and deuteron (ND₃) targets. Proton calibration requires dedicated TE (Thermal Equilibrium) data, whereas deuteron does not. The procedures for each are outlined below.
This assuming that both 'config.yaml' and `per_run_overrides.yaml` are configured properly.


### Procedure for Proton (NH₃)

1. Run the script main.py.

2. In the History tab, identify the dedicated TE measurements that occurred before or after the polarization period. During TE, the polarization value should be nearly steady (below 0.5%) with minor fluctuations. Ideally, select one TE measurement before and one after polarization to minimize uncertainty in the calibration constant (CC).

3. Go to the Calibration tab and use the Area vs Time panel to select a time range where polarization is steady.

4. In the Select for TE panel (middle green graph), select a vertical range that results in a nearly horizontal fitted line. Aim for 15–20 data points in the left-hand table.

5. For each of the selected data points:

   a. Click the data point to load the corresponding signal in the bottom panel. If the signal is not clearly visible, zoom in on the Y-axis using your mouse scroll wheel. If no signal is visible even after zooming (Y scale ~10⁻⁶), double-click to remove that point from the table.

   b. Go to the Analysis tab and adjust the fit boundaries to highlight the wings touching the signal. Record the fit boundaries.

   c. Use the Integrate within Range option to include the signal region. Record the "Area" from the Results panel and the "Temperature" from the Calibration tab.

   d. Repeat steps (a)–(c) for all selected data points.

6. Enter all collected "Area" and "Temperature" values into the TE Calculator spreadsheet to compute:

   * Average Temperature

   * Average Area

   * Average TE Polarization

   * Average Calibration Constant (CC)

   * Statistical uncertainties for each value

### Procedure for Deuteron (ND₃)

1. Since no dedicated TE data is available, use the History tab to identify regions of interest—look for “golden events” after a swap or anneal, particularly after achieving maximum polarization and entering a steady phase.

2. In the Calibration tab, use the Area vs Time panel to select a steady polarization region.

3. In the Select for TE panel, define a range that produces a nearly horizontal fit line. Ensure it includes about 15–20 data points in the left-hand table.

4. For each selected data point:

   a. Click the point to display its signal in the lower panel. Zoom in if necessary. If no clear deuteron signal (pake-doublet) appears at a Y scale ~10⁻⁵, double-click the point to remove it.

   b. Go to the Analysis tab and set the fit boundaries to highlight the wings touching the signal. Record the boundaries.

   c. Use Integrate within Range to select the signal region. Record the "Area" and "Temperature."

   d. In the Analysis tab, select Deuteron Peak Fit from the dropdown in the Results panel. This will fit the deuteron signal and display key parameters including CC, Area, and Polarization. Record these.

   e. Repeat steps (a)–(d) for all data points.

5. Copy all collected values into a spreadsheet for further analysis.

