import pytz
from PyQt5.QtWidgets import QMainWindow, QErrorMessage, QTabWidget, QLabel, QWidget, QDialog, QDialogButtonBox, \
    QVBoxLayout
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator
from PyQt5.QtCore import QThread, pyqtSignal, Qt

from app.classes import Config, Scan, RunningScan, Event, Baseline, HistPoint, History
from app.gui_run_tab import RunTab


class MainWindow(QMainWindow):
    '''

    '''

    def __init__(self, config_file, parent=None):
        super().__init__(parent)


        self.tz = pytz.timezone('US/Eastern')

        self.left = 100
        self.top = 100
        self.title = 'JLab Polarization Display'
        self.width = 1200
        self.height = 800
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.tab_widget = QTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        # Make tabs
        self.run_tab = RunTab(self)
        self.tab_widget.addTab(self.run_tab, "Run")

