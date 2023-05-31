'''PyNMR, J.Maxwell 2020
'''
import datetime
import glob
import json
import re
import numpy as np
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, \
    QTableView, QAbstractItemView, QAbstractScrollArea, QStackedWidget, QDoubleSpinBox, QDateTimeEdit, QPushButton
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator, QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from dateutil.parser import parse


class HistTab(QWidget):
    '''Creates history tab. '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.__dict__.update(parent.__dict__)

        self.parent = parent

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')


        self.base_pen = pg.mkPen(color=(180, 0, 0), width=2)
        self.base2_pen = pg.mkPen(color=(0, 0, 180), width=2)
        self.base3_pen = pg.mkPen(color=(0, 180, 0), width=2)
        self.sub_pen = pg.mkPen(color=(220, 0, 0), width=2)
        self.sub2_pen = pg.mkPen(color=(0, 0, 150), width=2)
        self.sub3_pen = pg.mkPen(color=(0, 180, 0), width=2)

        self.main = QHBoxLayout()  # main layout
        self.setLayout(self.main)

        # Left Side
        self.left = QVBoxLayout()
        self.main.addLayout(self.left)

        # Datetime box box
        self.date_box = QGroupBox('Datetime Range Selection')
        self.date_box.setLayout(QHBoxLayout())
        self.start_label = QLabel("Start:")
        self.start_label.setAlignment(Qt.AlignCenter)
        self.date_box.layout().addWidget(self.start_label)
        self.left.addWidget(self.date_box)
        self.start_dedit = QDateTimeEdit(calendarPopup=True)
        self.end_dedit = QDateTimeEdit(calendarPopup=True)
        self.start_dedit.setDateTime(datetime.datetime.strptime('Mar 31 2023  12:00AM', '%b %d %Y %I:%M%p'))
        self.end_dedit.setDateTime(datetime.datetime.strptime('Apr 1 2023  12:00AM', '%b %d %Y %I:%M%p'))
        #self.start_dedit.dateTimeChanged.connect(self.range_changed)
        self.date_box.layout().addWidget(self.start_dedit)
        self.end_label = QLabel("End:")
        self.end_label.setAlignment(Qt.AlignCenter)
        self.date_box.layout().addWidget(self.end_label)
        #self.end_dedit.dateTimeChanged.connect(self.range_changed)
        self.date_box.layout().addWidget(self.end_dedit)
        self.range_but = QPushButton('Open Range')
        self.range_but.clicked.connect(self.range_changed)
        self.date_box.layout().addWidget(self.range_but)

        # Selection list
        self.event_model = QStandardItemModel()
        self.event_model.setHorizontalHeaderLabels(
            ['Timestamp', 'Date', 'Time', 'Polarization', 'Sweeps', 'Channel', 'Label'])

        self.event_table = QTableView()
        self.event_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.event_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.event_table.resizeColumnsToContents()
        self.event_table.setModel(self.event_model)
        self.event_table.clicked.connect(self.select_event)
        self.left.addWidget(self.event_table)

        # Right Side
        self.right = QVBoxLayout()
        self.main.addLayout(self.right)

        self.time_axis = pg.DateAxisItem(orientation='bottom')
        self.strip_wid = pg.PlotWidget(title='Range Polarization History', axisItems={'bottom': self.time_axis})
        self.strip_wid.showGrid(True, True)
        self.strip_wid.addLegend(offset=(0.5, 0))
        self.strip_plot = self.strip_wid.plot([], [], pen=self.base2_pen, name='Polarization')
        self.right.addWidget(self.strip_wid)

        self.sig_wid = pg.PlotWidget(title='Selected Signal')
        self.sig_wid.showGrid(True, True)
        self.raw_plot = self.sig_wid.plot([], [], pen=self.sub_pen, name='Raw')
        self.sub_plot = self.sig_wid.plot([], [], pen=self.sub2_pen, name='Base Subtracted')
        self.fin_plot = self.sig_wid.plot([], [], pen=self.sub3_pen, name='Fit Subtracted')
        self.sig_wid.addLegend(offset=(0.5, 0))
        self.right.addWidget(self.sig_wid)


    def range_changed(self):
        '''Update time range of events used. Looks through data directory to pull in required events
        '''
        self.start = self.start_dedit.dateTime().toPyDateTime()
        self.end = self.end_dedit.dateTime().toPyDateTime()
        self.all_files = glob.glob(f"{self.parent.settings['proton_data_dir']}/*.txt") \
                         + glob.glob(f"{self.parent.settings['deuteron_data_dir']}/*.txt")
        self.current_time = datetime.datetime.strptime('Jan 1 2000  12:00AM', '%b %d %Y %I:%M%p')
        self.included = []
        for file in self.all_files:
            self.filename_regex = re.compile('(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})__(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}).txt')
            if 'current' in file or 'baseline' in file:
                continue
            else:
                m = self.filename_regex.search(file)
                if not m: continue   # skip if we don't match the regex
                start = m.groups()[0]
                stop = m.groups()[1]
                start_dt = datetime.datetime.strptime(start, "%Y-%m-%d_%H-%M-%S")
                stop_dt = datetime.datetime.strptime(stop, "%Y-%m-%d_%H-%M-%S")
                if self.start < start_dt < self.end or self.start < stop_dt < self.end:
                    self.included.append(file)
        self.all = {}
        for eventfile in self.included:
            print('Parsing file:', eventfile)
            with open(eventfile, 'r') as f:
                for line in f:
                    event = json.loads(line)
                    s = event['stop_time']
                    line_stoptime = datetime.datetime.strptime(s[:26], '%Y-%m-%d %H:%M:%S.%f')
                    utcstamp = str(event['stop_stamp'])
                    if self.start < line_stoptime < self.end and 'pol' in event:
                        self.all[utcstamp] = event    # full dictionary from datafile

        self.event_model.removeRows(0, self.event_model.rowCount())
        for i, stamp in enumerate(self.all.keys()):
            try:
                dt = parse(self.all[stamp]['stop_time'])
                time = dt.strftime("%H:%M:%S")
                date = dt.strftime("%m/%d/%y")
                self.event_model.setItem(i,0,QStandardItem(str(self.all[stamp]['stop_stamp'])))
                self.event_model.setItem(i,1,QStandardItem(date))
                self.event_model.setItem(i,2,QStandardItem(time))
                self.event_model.setItem(i,3,QStandardItem(f"{self.all[stamp]['pol']:.4f}"))
                self.event_model.setItem(i,4,QStandardItem(str(self.all[stamp]['sweeps'])))
                self.event_model.setItem(i,5,QStandardItem(str(self.all[stamp]['channel']['name'])))
                self.event_model.setItem(i,6,QStandardItem(str(self.all[stamp]['label'])))
            except KeyError:
                pass
        try:
            graph_data = np.column_stack((list([float(k) for k in sorted(self.all.keys())]),[float(self.all[k]['pol']) for k in sorted(self.all.keys())]))
            self.strip_plot.setData(graph_data)
        except KeyError:
            pass


    def select_event(self, item):
        self.update_event_plot(item)

    def update_event_plot(self, item):
        '''Update event plot.
        '''
        stamp = self.event_model.data(self.event_model.index(item.row(), 0))
        freq_list = np.array(self.all[stamp]['freq_list'])
        phase = np.array(self.all[stamp]['phase'])
        sub = np.array(self.all[stamp]['basesub'])
        fin = np.array(self.all[stamp]['fitsub'])
        self.raw_plot.setData(freq_list,phase-phase.max())
        self.sub_plot.setData(freq_list,sub-sub.max())
        self.fin_plot.setData(freq_list,fin)

