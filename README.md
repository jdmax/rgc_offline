# RGC Offline Target Polarization

## Instructions for Users

To run the offline analysis software, you will need access to the experimental data. By default, the software points to the JLab `O:\` drive to access this data. If you do not have access to that drive, you can copy the data locally and specify the new location in the `config.yaml` file.

You will need all data from the `/group/poltar/HallB/RGC/` directories:
- `data-p` (proton data)
- `data-d` (deuteron data)
- `BCM/Mya` (beam current monitor and related metadata)

Additional metadata can be found in the `inputs/` directory within the code repository.

---

## Overview of Scripts

### `inputs.py`
Processes experimental metadata for analysis. This script runs automatically when executing `offline_main.py`. It reads the BCM exports, run ranges, and event files, producing the `bcm.pkl` and `event.pkl` files required for further analysis.

### `main.py`
Provides the main GUI to inspect and calibrate events. For each calibration period, a calibration constant (CC) is generated—from either Thermal Equilibrium (TE) data (for proton targets) or golden events (for deuteron targets). While performing calibrations, be sure to document the analysis settings used (e.g., fit wing positions or integration ranges) for reproducibility.

### `per_run_overrides.yaml`
Defines analysis configurations per run range. This file is created manually after calibration is complete and should be placed in the main directory. It includes:

- An `options` section with default analysis settings applied to all runs.
- A `runs` section, dividing the experiment into run ranges. Each range (named by its starting run number) can override defaults for signal analysis.  

Settings can include:
- `wings`: Fit boundaries (values from 0 to 1) used in the polynomial fit.
- `sum_range`: Integration limits for computing signal area.
- `cc`: Calibration constant used to convert area to polarization.

### `offline_main.py`
Performs the full offline signal analysis. It:
1. Loads the generated metadata (`bcm.pkl`, `event.pkl`).
2. Iterates over all experimental runs.
3. For each run, selects corresponding NMR events and performs signal analysis using methods in `analysis.py`.
4. Saves results in the `results/` directory as:
   - `results_meta.pkl` (summary metadata for all runs)
   - `results[run number].pkl` (full results for each run)

### `results_main.py`
A visualization tool for reviewing analysis outcomes. You can:
- Select a date range to plot results.
- Inspect individual events to assess the quality of the analysis.

---

## Summary of Workflow

1. Set the paths to all necessary data in `config.yaml`.
2. Use `main.py` to calibrate events and define settings in `per_run_overrides.yaml`.
3. Run `offline_main.py` to analyze all events using your calibration settings.
4. Run `results_main.py` to visualize the results.


---


## Procedures for Extracting Calibration Constants

Extracting calibration constants differs between proton (NH₃) and deuteron (ND₃) targets. Proton calibration requires dedicated TE (Thermal Equilibrium) data, whereas deuteron does not. The procedures for each are outlined below. This assumes that both `config.yaml` and `per_run_overrides.yaml` are configured properly.


### Procedure for Proton (NH₃)

1. Run the script main.py.

2. In the **History tab**, identify the dedicated TE measurements that occurred before or after the polarization period. During TE, the polarization value should be nearly steady (below 0.5%) with minor fluctuations. Ideally, select one TE measurement before and one after polarization to minimize uncertainty in the calibration constant (CC).
![historytab](https://github.com/user-attachments/assets/ed0b782e-ca5b-407a-92b2-2616a3f203ed)

3. Go to the **Calibration tab** and use the **Area vs Time** panel to select a time range where polarization is steady.
![calibrationtab](https://github.com/user-attachments/assets/f677598b-586c-4e89-9e24-983c54426fc9)


4. In the **Select for TE** panel (middle green graph), select a vertical range that results in a nearly horizontal fitted line. Aim for 15–20 data points in the left-hand table.

5. For each of the selected data points:

   a. Click the data point to load the corresponding signal in the bottom panel. If the signal is not clearly visible, zoom in on the Y-axis using your mouse scroll wheel. If no signal is visible even after zooming (Y scale ~10⁻⁶), double-click to remove that point from the table.

   b. Go to the **Analysis tab** and adjust the fit boundaries to highlight the wings touching the signal. Record the fit boundaries.
   ![analysistab](https://github.com/user-attachments/assets/3488cf1b-375f-49de-b192-999c7194ac58)


   c. Use the Integrate within Range option to include the signal region. Record the **Area** from the Results panel and the **Temperature** from the Calibration tab.

   d. Repeat steps (a)–(c) for all selected data points.

6. Use all collected **Area** and **Temperature** values to compute (TE Calculator spreadsheet):

   * Average Temperature

   * Average Area

   * Average TE Polarization

   * Average Calibration Constant (CC)

   * Statistical uncertainties for each value

### Procedure for Deuteron (ND₃)

1. Since no dedicated TE data is available, use the **History tab** to identify regions of interest—look for “golden events” after a swap or anneal, particularly after achieving maximum polarization and entering a steady phase.
 ![ND3_HistoryTab](https://github.com/user-attachments/assets/b647f107-ac58-440d-8442-ef235afc4a19)

2. In the **Calibration tab**, use the **Area vs Time** panel to select a steady polarization region.
![ND3_CalibrationTab](https://github.com/user-attachments/assets/59855994-ffc7-44bb-875f-60ca93cc3312)

3. In the **Select for TE** panel, define a range that produces a nearly horizontal fit line. Ensure it includes about 15–20 data points in the left-hand table.

4. For each selected data point:

   a. Click the point to display its signal in the lower panel. Zoom in if necessary. If no clear deuteron signal (pake-doublet) appears at a Y scale ~10⁻⁵, double-click the point to remove it.

   b. Go to the **Analysis tab** and set the fit boundaries to highlight the wings touching the signal. Record the boundaries.
    ![ND3_AnalysisTab-1](https://github.com/user-attachments/assets/409f1ac1-8d52-4b1d-8301-6f0719338ca8)


   c. Use Integrate within Range to select the signal region. Record the **Area** and **Temperature**.

   d. In the **Analysis tab**, select "Deuteron Peak Fit" from the dropdown in the **Results** panel. This will fit the deuteron signal and display key parameters including CC, Area, and Polarization. Record these.
   ![ND3_AnalysisTab-2](https://github.com/user-attachments/assets/8ea8dfa7-ebf2-4dc9-b4b0-a1b76346f860)


   e. Repeat steps (a)–(d) for all data points.

6. Copy all these collected values into a spreadsheet for further analysis.

