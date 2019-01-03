import socket
from VALUES_ultrasound_comm_protocol import *
from VALUES_ultrasound_server_constants import *
import pyUlterius
from SUPPORT_ultra_image_streamer import UltraImageStreamer
from SUPPORT_ultrasound_parameter_controller import UltraParamController
from PIL import Image

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *


class UltrasoundServer(QtGui.QMainWindow):

    def __init__(self):
        super(UltrasoundServer, self).__init__()
        self.sonix_timeout = SONIX_TIMEOUT
        self.sonix_address = SONIX_ADDRESS
        self.sonix_fail_max_count = SONIX_FAIL_MAX_COUNT
        self.ultrasound_fail_count = 0

        self.image_streamer = None
        self.ultrasound = None
        self.param_controller = None
        self.client_communication_thread = None
        self.image_update_timer_thread = None
        self.image = None

        self.start_thread_communicate_with_client()

    def connect_to_ultrasonix(self):
        self.ultrasound = pyUlterius.ulterius()
        self.param_controller = UltraParamController(self.ultrasound)
        self.ultrasound.setTimeout(SONIX_TIMEOUT)
        # Check whether there is any previous connection
        if self.ultrasound.isConnected():
            if self.ultrasound.disconnect():
                print 'Successfully disconnected from Ultrasonix'
            else:
                print 'Error: Could not disconnect from Ultrasonix'

        # Connect to Sonix RP
        if not self.ultrasound.isConnected():
            if not self.ultrasound.connect(SONIX_ADDRESS):
                print 'Error: Could not connect to Ultrasonix'
            else:
                print 'Successfully connected to Ultrasonix'

    def initialize_image_acquisition(self):
        # Initialize ultrasound image acquisition thread
        self.image_streamer = UltraImageStreamer(self.ultrasound, IMAGING_MODE, SONIX_ADDRESS, SONIX_FAIL_MAX_COUNT)

        # create a new ultrasound acquisition thread
        self.image_streamer.start_image_acquisition()
        if self.ultrasound.isConnected():
            self.image_streamer.change_data_to_acquire(IMAGING_MODE)

    def start_thread_communicate_with_client(self):
        self.client_communication_thread = ClientCommThread()
        self.client_communication_thread.data.connect(self.callback_communicate_with_client)
        self.client_communication_thread.start(SERVER_IMAGE_PORT)

    def thread_start_image_acquisition(self):
        self.image_update_timer_thread = QtCore.QTimer()
        self.image_update_timer_thread.start(.1)
        self.connect(self.image_update_timer_thread, QtCore.SIGNAL('timeout()'), self.callback_image_update)

    def callback_communicate_with_client(self, data):
        if data == CONNECT_TO_ULTRASONIX:
            print "connect to ultrasonix"
            self.connect_to_ultrasonix()

        elif data == INITIALIZE_IMAGE_ACQUISITION:
            print "start image acquisition"
            self.initialize_image_acquisition()

        elif data == START_IMAGE_STREAMING:
            self.thread_start_image_acquisition()

        elif data == QUIT:
            print "QUIT signal received"
            self.image_update_timer_thread.stop()
            self.image_streamer.stop_image_acquisition()
            self.client_communication_thread.close_sockets()
            self.ultrasound.disconnect()

        elif data == PARAM_INC_DEPTH:
            self.param_controller.increase_depth()

        elif data == PARAM_DEC_DEPTH:
            self.param_controller.decrease_depth()

        elif data == PARAM_GET_DEPTH:
            val = self.param_controller.get_depth_value()
            self.client_communication_thread.send_requested_value(PARAM_GET_DEPTH, val)

        elif data == PARAM_INC_GAIN:
            self.param_controller.increase_gain()

        elif data == PARAM_DEC_GAIN:
            self.param_controller.decrease_gain()

        elif data == PARAM_GET_GAIN:
            val = self.param_controller.get_gain_value()
            self.client_communication_thread.send_requested_value(PARAM_GET_GAIN, val)

        elif data == PARAM_INC_FREQ:
            self.param_controller.increase_frequency()

        elif data == PARAM_DEC_FREQ:
            self.param_controller.decrease_frequency()

        elif data == PARAM_GET_FREQ:
            val = self.param_controller.get_frequency_value()
            self.client_communication_thread.send_requested_value(PARAM_GET_FREQ, val)

        elif data == PARAM_INC_FOCUS:
            self.param_controller.increase_focus()

        elif data == PARAM_DEC_FOCUS:
            self.param_controller.decrease_focus()

        elif data == PARAM_GET_FOCUS:
            val = self.param_controller.get_focus_value()
            self.client_communication_thread.send_requested_value(PARAM_GET_FOCUS, val)

        elif data == PARAM_FREEZE_TOGGLE:
            self.param_controller.toggle_freeze()

        else:
            print "unknown command: " + str(data)

    def callback_image_update(self):
            self.image = self.image_streamer.get_new_image_array()
            self.image = self.image.astype('float64')[:, :, 1]

            self.image = Image.fromarray(self.image)

            # self.image = self.image.convert("RGB")
            # self.image = self.image.resize((RESIZE_IMAGE_WIDTH, RESIZE_IMAGE_HEIGHT))

            self.image = self.image.convert("L")
            self.image = self.image.resize((1092, 758))

            self.image = self.image.tostring()

            self.client_communication_thread.send_data_to_client(self.image)

    def __del__(self):
        print "object terminated"
        return self


class ClientCommThread(QThread, QtGui.QGraphicsView):

    data = QtCore.pyqtSignal(object)

    def __init__(self):
        QtCore.QThread.__init__(self)

        self.stopFlag = False

        self.tcp_server_socket = None
        self.tcp_server_image_socket = None
        self.tcp_connection = None
        self.tcp_client_address = None

        self.tcp_connection_image = None
        self.tcp_client_address_image = None
        self.tcp_received_image_communication = None
        self.sent = None

        self.open_sockets()

    def run(self):
            while True:
                if self.stopFlag:
                    self.stopFlag = False
                    break
                else:
                    buf = self.tcp_connection.recv(COMM_DATA_SIZE)
                    if len(buf) > 0:
                        print "received: " + buf
                        if buf == CONNECT_TO_SERVER:
                            self.tcp_connection.send(ACK_CONNECT_TO_SERVER)

                        elif buf == CONNECT_TO_ULTRASONIX:
                            self.tcp_connection.send(ACK_CONNECT_TO_ULTRASONIX)
                            self.data.emit(CONNECT_TO_ULTRASONIX)

                        elif buf == INITIALIZE_IMAGE_ACQUISITION:
                            self.tcp_connection.send(ACK_INITIALIZE_IMAGE_ACQUISITION)
                            self.data.emit(INITIALIZE_IMAGE_ACQUISITION)

                        elif buf == START_IMAGE_STREAMING:
                            self.tcp_connection.send(ACK_START_IMAGE_STREAMING)

                            self.data.emit(START_IMAGE_STREAMING)

                        elif buf == QUIT:
                            self.tcp_connection.send(ACK_QUIT)
                            self.data.emit(QUIT)

                        else:
                            self.data.emit(buf)

    def send_requested_value(self, param, value):
        print "param: " + param + ", value: " + str(value)
        self.tcp_connection.send(str(value))

    def open_sockets(self):
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_socket.bind((SERVER_ADDRESS, SERVER_PARAM_PORT))
        print >> sys.stderr, 'starting up TCP connection on %s port %s' % (SERVER_ADDRESS, SERVER_PARAM_PORT)
        self.tcp_server_socket.listen(1)

        self.tcp_server_image_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_image_socket.bind((SERVER_ADDRESS, SERVER_IMAGE_PORT))
        print >> sys.stderr, 'starting up TCP connection on %s port %s' % (SERVER_ADDRESS, SERVER_IMAGE_PORT)
        self.tcp_server_image_socket.listen(1)

        self.tcp_connection, self.tcp_client_address = self.tcp_server_socket.accept()

    def send_data_to_client(self, data):
        self.tcp_connection_image, self.tcp_client_address_image = self.tcp_server_image_socket.accept()
        self.tcp_connection_image.sendall(data)

    def close_sockets(self):
        print "closing sockets"
        self.tcp_server_socket.close()
        self.tcp_server_image_socket.close()
        self.tcp_connection.close()
        print "sockets closed"

        self.stopFlag = True

    def __del__(self):
        print "deleting ClientCommThread"
        self.quit()
        self.wait()

if __name__ == "__main__":
    import sys

    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Ultrasound Server')

    main = UltrasoundServer()
    main.show()

    sys.exit(app.exec_())
