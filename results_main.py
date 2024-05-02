from PyQt5 import QtCore
from PyQt5 import QtWidgets
import sys
import getopt

from app.gui_results import MainWindow

def main():
    '''Main executable calls main gui
    '''
    app = QtWidgets.QApplication([])
    # app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True) #enable highdpi scaling
    app.setApplicationName("Run Group C Offline Polarization")
    gui = MainWindow()
    gui.show()
    app.exec_()

if __name__ == '__main__':
    main()
