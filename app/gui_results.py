import pytz
import yaml
from PyQt5.QtWidgets import QMainWindow, QErrorMessage, QTabWidget, QLabel, QWidget, QDialog, QDialogButtonBox, \
    QVBoxLayout
import pyqtgraph as pg
import datetime
import glob
import json
import os
import re
import pytz
import numpy as np
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, \
    QTableView, QAbstractItemView, QAbstractScrollArea, QStackedWidget, QDoubleSpinBox, QDateTimeEdit, QPushButton
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator, QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt
import pandas as pd

import inputs

class MainWindow(QMainWindow):
    '''
    '''

    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_settings()


        self.tz = pytz.timezone('US/Eastern')

        self.left = 100
        self.top = 100
        self.title = 'Run Group C Results Browser'
        self.width = 1500
        self.height = 1200
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.tab_widget = QTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        # Make tabs
        self.hist_tab = HistTab(self)
        self.tab_widget.addTab(self.hist_tab, "History")

    def load_settings(self):
        '''Load settings from YAML config file'''

        with open('config.yaml') as f:                           # Load settings from YAML files
           self.config_dict = yaml.load(f, Loader=yaml.FullLoader)
        self.settings = self.config_dict['settings']
        print(f"Loaded settings from config.yaml.")

    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div



class HistTab(QWidget):
    """Creates history tab. """

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.__dict__.update(parent.__dict__)

        self.parent = parent

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.eventfile = ''


        self.base_pen = pg.mkPen(color=(180, 0, 0), width=2)
        self.base2_pen = pg.mkPen(color=(0, 0, 180), width=2)
        self.base3_pen = pg.mkPen(color=(0, 180, 0), width=2)
        self.sub_pen = pg.mkPen(color=(220, 0, 0), width=2)
        self.sub2_pen = pg.mkPen(color=(0, 0, 150), width=2)
        self.sub3_pen = pg.mkPen(color=(0, 180, 0), width=2)
        self.sub4_pen = pg.mkPen(color=(180, 180, 0), width=2)

        self.filename_regex = re.compile(
            '(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})__(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}).txt')

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
            ['Date', 'Time', 'Online Pol','Offline Pol', 'Sweeps', 'Channel', 'Label'])

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
        self.strip_plot = self.strip_wid.plot([], [], pen=self.base2_pen, name='Online Polarization')
        self.strip_off_plot = self.strip_wid.plot([], [], pen=self.base_pen, name='Offline Polarization')
        self.right.addWidget(self.strip_wid)

        self.sig_wid = pg.PlotWidget(title='Selected Signal Offline Analysis')
        self.sig_wid.showGrid(True, True)
        self.sig_wid.addLegend(offset=(0.5, 0))
        self.raw_plot = self.sig_wid.plot([], [], pen=self.sub_pen, name='Raw')
        self.sub_plot = self.sig_wid.plot([], [], pen=self.sub2_pen, name='Base Subtracted')
        self.poly_plot = self.sig_wid.plot([], [], pen=self.sub4_pen, name='Polynomial Fit')
        self.fin_plot = self.sig_wid.plot([], [], pen=self.sub3_pen, name='Fit Subtracted')
        self.right.addWidget(self.sig_wid)


        self.date_box = QGroupBox('Selected Point Metadata')
        self.date_box.setLayout(QVBoxLayout())
        self.right.addWidget(self.date_box)
        self.meta_label = QLabel("Metadata will appear here when an event is selected.")
        self.date_box.layout().addWidget(self.meta_label)

        if os.path.isfile('results/result_meta.pkl'):  # if already in pickle, return that, otherwise read from file
            self.events = pd.read_pickle('results/result_meta.pkl')  # self.events is meta data dict
            self.events.sort_index()
        else:
            print("No results to read")


    def range_changed(self):
        '''Update time range of events used. Looks through data directory to pull in required events
        '''
        self.start = self.start_dedit.dateTime().toPyDateTime()
        self.end = self.end_dedit.dateTime().toPyDateTime()
        self.current_time = datetime.datetime.strptime('Jan 1 2000  12:00AM', '%b %d %Y %I:%M%p')
        self.included = self.events.loc[str(self.start):str(self.end)]   # events within datetime range
        self.event_model.removeRows(0, self.event_model.rowCount())
        self.row_to_dt = []
        for i, tup in enumerate(self.included.iterrows()):
            index, row = tup
            self.row_to_dt.append(index)
            try:
                #dt = parse(self.all[stamp]['stop_time'])
                dt = index
                time = dt.strftime("%H:%M:%S")
                date = dt.strftime("%m/%d/%y")
                self.event_model.setItem(i,0,QStandardItem(date))
                self.event_model.setItem(i,1,QStandardItem(time))
                self.event_model.setItem(i,2,QStandardItem(f"{row['online_pol']*100:.4f}"))
                self.event_model.setItem(i,3,QStandardItem(f"{row['offline_pol']*100:.4f}"))
                self.event_model.setItem(i,4,QStandardItem(str(row['sweeps'])))
                self.event_model.setItem(i,5,QStandardItem(str(row['channel'])))
                self.event_model.setItem(i,6,QStandardItem(str(row['label'])))
            except KeyError:
                pass
        try:
            graph_data = np.column_stack((list([k.timestamp() for k,row in self.included.iterrows()]),
                                          [float(row['online_pol']) for k,row in self.included.iterrows()]))
            graph_data2 = np.column_stack((list([k.timestamp() for k, row in self.included.iterrows()]),
                                          [float(row['offline_pol']) for k, row in self.included.iterrows()]))

            self.strip_plot.setData(graph_data)
            self.strip_off_plot.setData(graph_data2)
        except KeyError:
            print("Key error")
            pass

        #self.parent.te_tab.update_events(self.all)


    def select_event(self, item):
        "Item in list clicked"
        self.update_event_plot(item)

    def update_event_plot(self, item):
        '''Update event plot.
        '''
        dt = self.row_to_dt[int(self.event_table.currentIndex().row())]
        print(self.row_to_dt)
        print(dt)
        meta = self.included.loc[dt]

        if not meta['run_number'] in self.eventfile:  # if already in pickle, return that, otherwise read from file
            df = pd.read_pickle(f'results/results{meta["run_number"]}.pkl')
            df.sort_index()

        event = df.loc[dt]

        freq_list = np.array(event['freq_list'])
        phase = np.array(event['phase'])
        sub = np.array(event['result']['basesub'])
        poly = np.array(event['result']['polyfit'])
        fin = np.array(event['result']['fitsub'])
        self.raw_plot.setData(freq_list,phase-phase.max())
        self.sub_plot.setData(freq_list,sub-sub.max())
        self.poly_plot.setData(freq_list,poly-poly.max())
        self.fin_plot.setData(freq_list,fin)

        #text = "Local time: " + self.all[stamp]['stop_time'].replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%m/%d/%Y, %H:%M:%S")
        #text += f"\t{self.all[stamp]['diode_vout']}"
        #self.meta_label.setText(text)
