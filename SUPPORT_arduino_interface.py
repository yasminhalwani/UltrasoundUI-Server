from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *
import serial
from VALUES_main import ARDUINO_INTERFACE
from VALUES_main import HwInterface

class ArduinoThread(QThread, QtGui.QGraphicsView):

    data = QtCore.pyqtSignal(object)
    connected = False

    def __init__(self):
        QtCore.QThread.__init__(self)

        try:
            self.arduino = serial.Serial(ARDUINO_INTERFACE, 9600)
            self.connected = True
        except:
            self.connected = False

        self._loop = True

    def run(self):
        if self.connected:
            while self._loop:
                try:
                    string = self.arduino.readline()

                    if HwInterface.ZOOM_CW in string:
                        self.data.emit(HwInterface.ZOOM_CW)
                    elif HwInterface.ZOOM_CCW in string:
                        self.data.emit(HwInterface.ZOOM_CCW)
                    elif HwInterface.ZOOM_PRESS in string:
                        self.data.emit(HwInterface.ZOOM_PRESS)
                    elif HwInterface.PB_PRESS in string:
                        self.data.emit(HwInterface.PB_PRESS)
                    elif HwInterface.CAPTURE_PRESS in string:
                        self.data.emit(HwInterface.CAPTURE_PRESS)
                    elif HwInterface.FREEZE_PRESS in string:
                        self.data.emit(HwInterface.FREEZE_PRESS)
                    elif HwInterface.FOCUS_CW in string:
                        self.data.emit(HwInterface.FOCUS_CW)
                    elif HwInterface.FOCUS_CCW in string:
                        self.data.emit(HwInterface.FOCUS_CCW)
                    elif HwInterface.FOCUS_PRESS in string:
                        self.data.emit(HwInterface.FOCUS_PRESS)
                    elif HwInterface.DEPTH_CW in string:
                        self.data.emit(HwInterface.DEPTH_CW)
                    elif HwInterface.DEPTH_CCW in string:
                        self.data.emit(HwInterface.DEPTH_CCW)
                    elif HwInterface.CALIBRATE_PRESS in string:
                        self.data.emit(HwInterface.CALIBRATE_PRESS)

                except:
                    pass
        else:
            pass

    def exit_thread(self):
        # TODO close thread properly
        pass
