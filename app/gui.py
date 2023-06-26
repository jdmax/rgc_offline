import pytz
import yaml
from PyQt5.QtWidgets import QMainWindow, QErrorMessage, QTabWidget, QLabel, QWidget, QDialog, QDialogButtonBox, \
    QVBoxLayout

#from app.event import Config, Scan, RunningScan, Event, Baseline, HistPoint, History
from app.gui_history import HistTab
from app.gui_te import TETab


class MainWindow(QMainWindow):
    '''
    '''

    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_settings()


        self.tz = pytz.timezone('US/Eastern')

        self.left = 100
        self.top = 100
        self.title = 'Run Group C Offline Polarization'
        self.width = 1500
        self.height = 1200
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.tab_widget = QTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        # Make tabs
        self.hist_tab = HistTab(self)
        self.tab_widget.addTab(self.hist_tab, "History")
        self.te_tab = TETab(self)
        self.tab_widget.addTab(self.te_tab, "Calibration")


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