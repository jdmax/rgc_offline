'''PyNMR, J.Maxwell 2020
'''
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QRegExpValidator
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import random
import os.path
import datetime
from dateutil.parser import parse
import json
import pytz
from scipy import optimize
import numpy as np


class Event():
    '''Data and method object for single event point. Takes config instance on init.

    Arguments:
        config: Config class instance

    Attributes:
        config: Config object for the event
        scan: Scan object for the event
        start_time: Datetime object for time event started accumulating measurements
        start_stamp: Timestamp int for starting datetime
        stop_time: Datetime object for time event stopped accumulating measurements
        stop_stamp: Timestamp int for stop datetime
        baseline: Baseline phase sweep list selected from baseline tab
        basesweep: Baseline used, varies based on chosen method from analysis tab
        basesub: Baseline subtracted phase sweep list for event
        polysub: Polyfit subtracted basesub list
        wings: Portion of sweep to use for fit, 4 long list giving position of left start, left stop, right start and right stop positions as a decimal from 0 to 1
        cc: Calibration constant float
        area: Area under polyfit curve float
        pol: Measured polarization for event, CC*Area, float
        base_time: Datetime object for stop of baseline event
        base_stamp: Timestamp int of baseline event
        base_file: Filename string where baseline event can be found
        uwave_freq: Microwave frequency (GHz) as read from GPIB
        uwave_power: Microwave power (W) as read from serial
        elapsed: Number of seconds taken to finish sweeps
        label: type of event from combobox
    '''

    def __init__(self, line):
        lists = ['freq_list','phase','basesub','fitsub','basesweep','fitcurve','rescurve','diode','baseline']
        json_dict = json.loads(line)
        self.stop_stamp = json_dict['stop_stamp']  # time stamp float
        for key, value in json_dict:
            if key in lists:
                self.__dict__[key] = np.array(value)
            elif:
                self.__dict__[key] = value
    def close_event(self, base_method, sub_method, res_method):
        '''Closes event, calls for signal analysis, adds epics reads to event

        Args:
            epics_reads: Return of read_all of EPICS class, Dict
            base_method: method to produce baseline subtracted signal given event instance, return baseline and subtracted
            sub_method: method to produce fit subtracted signal and area given event instance, return fit, subtracted, sum

        Todo:
            * Send data to EPICS, history
        '''
        # self.stop_time =  datetime.datetime.now(tz=pytz.timezone('US/Eastern'))
        self.stop_time = datetime.datetime.now(tz=datetime.timezone.utc)
        self.stop_stamp = self.stop_time.timestamp()
        self.elapsed = (self.stop_time - self.start_time).seconds
        # print(self.stop_time, self.stop_stamp, self.elapsed)

        self.signal_analysis(base_method, sub_method, res_method)

    def signal_analysis(self, base_method, sub_method, res_method):
        '''Perform analysis on signal
        '''

        if np.any(self.scan.phase):  # do the thing
            try:
                self.anal_thread = AnalThread(self, base_method, sub_method, res_method)
                self.anal_thread.finished.connect(self.parent.end_finished)
                self.anal_thread.start()
            except Exception as e:
                print('Exception starting run thread: ' + str(e))
                # self.basesweep, self.basesub  = base_method(self)
            # self.fitcurve, self.fitsub = sub_method(self)
            # self.rescurve, self.area, self.pol = res_method(self)
        else:  # unless the phase signal is zeroes, then set all to zeroes
            self.basesweep = np.zeros(len(self.basesweep))
            self.basesub = np.zeros(len(self.basesweep))
            self.fitcurve = np.zeros(len(self.basesweep))
            self.fitsub = np.zeros(len(self.basesweep))
            self.rescurve = np.zeros(len(self.basesweep))
            self.pol, self.area = 0, 0

    def poly(self, p, x):
        '''Third order polynomial for fitting

        Args:
            p: List of polynomial coefficients
            x: Sample point
        '''
        return p[0] + p[1] * x + p[2] * np.power(x, 2) + p[3] * np.power(x, 3)  # + p[4]*np.power(x,4)

    def fit_wings(self, wings, sweep):
        '''Fit to wings with scipy

        Args:
            wings: Wings, 4 element list of portions of sweep to use, attribute from Config
            sweep: List of samples to fit

        Returns:
            pf: Tuple of final fit coefficient list

        '''
        bounds = [x * len(sweep) for x in wings]
        data = [(x, y) for x, y in enumerate(sweep) if (bounds[0] < x < bounds[1] or bounds[2] < x < bounds[3])]
        X = np.array([x for x, y in data])
        Y = np.array([y for x, y in data])

        errfunc = lambda p, x, y: self.poly(p, x) - y
        pi = [0.01, 0.8, 0.01, 0.001, 0.00001]  # initial guess
        pf, success = optimize.leastsq(errfunc, pi[:], args=(X, Y))  # perform fit
        return pf

    def set_uwave(self, freq, power):
        '''Set microwave power and frequency'''
        self.uwave_freq = freq
        self.uwave_power = power

    def sum_beam_current(self, current):
        '''Sum in time-weighted beam current to make average over event'''

        time = (datetime.datetime.now(tz=datetime.timezone.utc) - self.beam_current_update_time).total_seconds()
        self.beam_current_sum = self.beam_current_sum + current * time
        self.beam_time_sum = self.beam_time_sum + time
        self.beam_current_update_time = datetime.datetime.now(tz=datetime.timezone.utc)


class AnalThread(QThread):
    '''Thread class for analysis. Calls for epics reads and writes once done.
    Args:
        config: Config object of settings
    '''
    reply = pyqtSignal(tuple)  # reply signal
    finished = pyqtSignal()  # finished signal

    def __init__(self, parent, base_method, sub_method, res_method):
        QThread.__init__(self)
        self.parent = parent  # event object
        self.base_method = base_method
        self.sub_method = sub_method
        self.res_method = res_method

    def __del__(self):
        self.wait()

    def run(self):
        '''Main analysis loop.
        '''
        self.parent.basesweep, self.parent.basesub = self.base_method(self.parent)
        self.parent.fitcurve, self.parent.fitsub = self.sub_method(self.parent)
        self.parent.rescurve, self.parent.area, self.parent.pol = self.res_method(self.parent)
        # print("Analysis done, waiting on epics.")

        self.parent.parent.epics_update(self.parent)

        self.finished.emit()


