'''PyNMR, J.Maxwell 2020
'''
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, \
    QSizePolicy, QComboBox, QPushButton, QProgressBar, QStackedWidget, QDoubleSpinBox
import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal, Qt

from gui_anal_stack import *

class AnalTab(QWidget):
    '''Creates analysis tab. '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.__dict__.update(parent.__dict__)

        self.parent = parent

        self.base_pen = pg.mkPen(color=(180, 0, 0), width=1.5)
        self.base2_pen = pg.mkPen(color=(0, 0, 150), width=1.5)
        self.base3_pen = pg.mkPen(color=(0, 180, 0), width=1.5)
        self.sub_pen = pg.mkPen(color=(180, 0, 0), width=1.5)
        self.sub2_pen = pg.mkPen(color=(0, 0, 150), width=1.5)
        self.sub3_pen = pg.mkPen(color=(0, 180, 0), width=1.5)
        self.res_pen = pg.mkPen(color=(180, 0, 0), width=1.5)
        self.res2_pen = pg.mkPen(color=(0, 0, 150), width=1.5)
        self.res3_pen = pg.mkPen(color=(0, 180, 0), width=1.5)

        self.base_chosen = None
        self.sub_chosen = None
        self.res_chosen = None

        self.main = QHBoxLayout()  # main layout
        self.setLayout(self.main)

        # Left Side
        self.left = QVBoxLayout()
        self.main.addLayout(self.left)

        # Baseline options box
        self.base_box = QGroupBox('Baseline Options')
        self.base_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.base_box)
        self.base_combo = QComboBox()
        self.base_box.layout().addWidget(self.base_combo)
        self.base_stack = QStackedWidget()
        self.base_box.layout().addWidget(self.base_stack)

        # Subtraction Box
        self.sub_box = QGroupBox('Fit Options')
        self.sub_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.sub_box)
        self.sub_combo = QComboBox()
        self.sub_box.layout().addWidget(self.sub_combo)
        self.sub_stack = QStackedWidget()
        self.sub_box.layout().addWidget(self.sub_stack)

        # Results Box
        self.res_box = QGroupBox('Results')
        self.res_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.res_box)
        self.res_combo = QComboBox()
        self.res_box.layout().addWidget(self.res_combo)
        self.res_stack = QStackedWidget()
        self.res_box.layout().addWidget(self.res_stack)

        # Right Side
        self.right = QVBoxLayout()
        self.main.addLayout(self.right)

        self.base_wid = pg.PlotWidget(title='Baseline Subtraction')
        self.base_wid.showGrid(True, True)
        self.base_wid.addLegend(offset=(0.5, 0))
        self.raw_plot = self.base_wid.plot([], [], pen=self.base_pen, name='Raw Signal')
        self.base_plot = self.base_wid.plot([], [], pen=self.base2_pen, name='Baseline')
        self.basesub_plot = self.base_wid.plot([], [], pen=self.base3_pen, name='Subtracted')
        self.base_region1 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 180, 0, 0))
        self.base_region1.setMovable(False)
        self.base_region1.setRegion([self.parent.event.scan.freq_list.min(), self.parent.event.scan.freq_list.min()])
        self.base_wid.addItem(self.base_region1)
        self.base_region2 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 180, 0, 0))
        self.base_region2.setMovable(False)
        self.base_region2.setRegion([self.parent.event.scan.freq_list.max(), self.parent.event.scan.freq_list.max()])
        self.base_wid.addItem(self.base_region2)
        self.right.addWidget(self.base_wid)

        self.sub_wid = pg.PlotWidget(title='Fit Subtraction')
        self.sub_wid.showGrid(True, True)
        self.sub_wid.addLegend(offset=(0.5, 0))
        self.sub_plot = self.sub_wid.plot([], [], pen=self.sub_pen, name='Baseline Subtracted')
        self.fit_plot = self.sub_wid.plot([], [], pen=self.sub2_pen, name='Fit')
        self.fitsub_plot = self.sub_wid.plot([], [], pen=self.sub3_pen, name='Subtracted')
        self.sub_region1 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 0, 180, 0))
        self.sub_region1.setMovable(False)
        self.sub_region1.setRegion([self.parent.event.scan.freq_list.min(), self.parent.event.scan.freq_list.min()])
        self.sub_wid.addItem(self.sub_region1)
        self.sub_region2 = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 0, 180, 0))
        self.sub_region2.setMovable(False)
        self.sub_region2.setRegion([self.parent.event.scan.freq_list.max(), self.parent.event.scan.freq_list.max()])
        self.sub_wid.addItem(self.sub_region2)
        self.right.addWidget(self.sub_wid)

        self.res_wid = pg.PlotWidget(title='Results')
        self.res_wid.showGrid(True, True)
        self.res_wid.addLegend(offset=(0.5, 0))
        self.unc_plot = self.res_wid.plot([], [], pen=self.res_pen, name='Fit Subtracted')
        self.res_plot = self.res_wid.plot([], [], pen=self.sub3_pen, name='Result')
        self.res_region = pg.LinearRegionItem(pen=pg.mkPen(0, 180, 0, 0), brush=pg.mkBrush(0, 180, 0, 0))
        self.res_region.setMovable(False)
        self.res_region.setRegion([self.parent.event.scan.freq_list.max(), self.parent.event.scan.freq_list.max()])
        self.res_wid.addItem(self.res_region)
        self.right.addWidget(self.res_wid)

        # Set up list of options for each step, putting instances into stack
        self.base_opts = []
        self.base_opts.append(StandardBase(self))
        self.base_opts.append(PolyFitBase(self))
        # self.base_opts.append(CircuitBase(self))   Not ready for prime time
        self.base_opts.append(NoBase(self))
        for o in self.base_opts:
            self.base_combo.addItem(o.name)
            self.base_stack.addWidget(o)
        self.sub_opts = []
        self.sub_opts.append(PolyFitSub(self))
        self.sub_opts.append(NoFitSub(self))
        for o in self.sub_opts:
            self.sub_combo.addItem(o.name)
            self.sub_stack.addWidget(o)
        self.res_opts = []
        self.res_opts.append(SumAllRes(self))
        self.res_opts.append(SumRangeRes(self))
        self.res_opts.append(PeakHeightRes(self))
        self.res_opts.append(FitPeakRes(self))
        self.res_opts.append(FitPeakRes2(self))
        self.res_opts.append(FitDeuteron(self))
        for o in self.res_opts:
            self.res_combo.addItem(o.name)
            self.res_stack.addWidget(o)

        # Setup default methods
        self.base_combo.currentIndexChanged.connect(self.change_base)
        self.base_combo.setCurrentIndex(self.event.config.settings['analysis']['base_def'])
        self.change_base(self.event.config.settings['analysis']['base_def'])
        self.sub_combo.currentIndexChanged.connect(self.change_sub)
        self.sub_combo.setCurrentIndex(self.event.config.settings['analysis']['sub_def'])
        self.change_sub(self.event.config.settings['analysis']['sub_def'])
        self.res_combo.currentIndexChanged.connect(self.change_res)
        self.res_combo.setCurrentIndex(self.event.config.settings['analysis']['res_def'])
        self.change_res(self.event.config.settings['analysis']['res_def'])

    def change_base(self, i):
        '''Set base_chosen to correct baseline class instance
        '''
        self.base_chosen = self.base_opts[i].result
        self.base_opts[i].switch_here()
        self.base_stack.setCurrentIndex(i)
        self.run_analysis()

    def change_sub(self, i):
        '''Set sub_chosen to desired subtraction class instance
        '''
        self.sub_chosen = self.sub_opts[i].result
        self.sub_opts[i].switch_here()
        self.sub_stack.setCurrentIndex(i)
        self.run_analysis()

    def change_res(self, i):
        '''Set res_chosen to desired subtraction class instance
        '''
        self.res_chosen = self.res_opts[i].result
        self.res_opts[i].switch_here()
        self.res_stack.setCurrentIndex(i)
        self.run_analysis()

    def run_analysis(self):
        '''Run event signal analysis and call for new plots if base and sub methods are chosen'''

        self.event = self.parent.gui_history.selected_event
        self.freq_list = np.array(self.event['freq_list'])
        self.phase = np.array(self.event['phase'])
        self.basesub = np.array(self.event['basesub'])
        self.fitsub = np.array(self.event['fitsub'])
        self.basesweep = np.array(self.event['basesweep'])
        self.fitcurve = np.array(self.event['fitcurve'])
        self.rescurve = np.array(self.event['rescurve'])

        if self.base_chosen and self.sub_chosen and self.res_chosen:
            self.signal_analysis(self.base_chosen, self.sub_chosen, self.res_chosen)
            self.update_event_plots()

    def update_event_plots(self):
        '''Update analysis tab plots. Right now doing a DC subtraction on unsubtracted signals.
        '''
        self.event = self.parent.previous_event
        self.raw_plot.setData(self.freq_list, self.phase - self.phase.max())
        self.base_plot.setData(self.freq_list, self.basesweep - self.basesweep.max())
        self.basesub_plot.setData(self.freq_list, self.basesub - self.basesub.max())

        # print(self.parent.event.basesub, self.parent.event.poly_curve, self.parent.event.polysub)
        self.sub_plot.setData(self.freq_list, self.basesub - self.basesub.max())
        self.fit_plot.setData(self.freq_list, self.fitcurve - self.basesub.max())
        self.fitsub_plot.setData(self.freq_list, self.fitsub)

        self.unc_plot.setData(self.freq_list, self.fitsub)
        self.res_plot.setData(self.freq_list, self.rescurve)

    def signal_analysis(self, base_method, sub_method, res_method):
        '''Perform analysis on signal
        '''

        if np.any(self.phase):  # do the thing
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

        self.finished.emit()


