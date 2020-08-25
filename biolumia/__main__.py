from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import sys

from biolumia.mainwindow import MainWindow


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = MainWindow()

    w.show()

    app.exec_()
