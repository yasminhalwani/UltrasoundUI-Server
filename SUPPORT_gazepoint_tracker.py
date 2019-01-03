__author__ = 'Yasmin'
# Developed by Yasmin Halwani for MASc Thesis Project [2015 - 2016]
# Robotics and Control Laboratory | Electrical and Computer Engineering
# University of British Columbia

# PYTHON SCRIPT DESCRIPTION #
"""
    This script handles the communication with the GazePoint GP3 Eye Tracker based on the XML communication protocols
    set by GazePoint (for more details, please refer to the documentation provided by Gazepoint http://www.gazept.com/)

    The script is divided into 3 classes:
        GazeTracker: the main class that facilitates the communication. Currently, it only handles continuously
            receiving and parsing the point of gaze. It can be extended furhter to handle more functionalities based
            on the offered functions by the gaze tracker.
            This class uses the other the classes (GazeDataThread and GazeTrackerClient).

        GazeDataThread: handles the separate thread created for the data transmission with the gaze tracker

        GazeTrackerClient: handles the basic functions for a socket client such as connecting, sending a message,
            receving a message


    This script runs on its own (for unit testing purposes) or as integrated with an application
"""


# IMPORTS #
# -- Standard library
import select
import socket
import sys
import threading
from xml.dom import minidom
# -- Third party
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *
import numpy as np
from scipy.signal import butter, lfilter
import math
import pylab as plt

# -- Local
# import qt_prototype
# if __name__ == '__main__':
#     __package__ = 'qt_prototype'
#     from global_variables import *

import Queue

import VALUES_gazept_strings

# GLOBAL VARIABLES #
DEBUG = False
IS_STANDALONE = False

GAZEPT_PORT = 4242
TIMEOUT_INITIAL = 0.5
TIMEOUT_ERROR = 0.1
REPLY_MESSAGE_LENGTH = 40

SCREEN_WIDTH = 1680  # TODO make this automatic
SCREEN_HEIGHT = 1050  # TODO make this automatic


PLOT = False




# CLASSES #
class GazeTrackerGUI(QtGui.QGraphicsView):

    def __init__(self):
        super(GazeTrackerGUI, self).__init__()

        self.setScene(QtGui.QGraphicsScene())
        pDesktop = QtGui.QDesktopWidget()
        RectScreen0 = pDesktop.screenGeometry (0)

        self.width = SCREEN_WIDTH
        self.height = SCREEN_HEIGHT
        if self.width == 0 and self.height == 0:
            self.width = RectScreen0.width()
            self.height = RectScreen0.height()
        self.setFixedSize(self.width, self.height)
        self.setVerticalScrollBarPolicy (QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setStyleSheet("background:transparent;")
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.showFullScreen()

        self.resize_count = 100
        self.max_update_count = 0
        self.scale_value = 10
        self.size_max = 350
        self.size_min = 50
        self.size_default = 200
        self.update_count = 0
        self.xpos = 0
        self.ypos = 0
        self.locked_xpos = 0
        self.locked_ypos = 0
        self.rect = QRect(0,0,0,0)
        self.is_size_being_updated = False
        self.alpha_counter = 0

        x = 0
        y = 0
        self.w = self.size_default
        self.h = self.size_default
        self.last_valid_x = 0.0
        self.last_valid_y = 0.0

        self.window_color = QtGui.QColor(QtCore.Qt.green)
        self.window_color.setAlpha(0)
        # self.window_color.setAlpha(255)

        self.window_pen = QtGui.QPen()
        self.window_pen.setColor(self.window_color)

        brush = QtGui.QBrush(QtGui.QColor(QtCore.Qt.green).darker(150))

        self.moving_rect = self.scene().addRect(x, y, self.w, self.h)
        self.moving_rect.setPen(self.window_pen)
        self.moving_rect.setFlag(QtGui.QGraphicsItem.ItemIsMovable)

        self.moving_circle = self.scene().addRect(x, y, 10,10, self.window_pen, brush)
        self.moving_circle.setFlag(QtGui.QGraphicsItem.ItemIsMovable)


    def update_location(self, info):

        if self.resize_count >= 100:
            received_data = info.split(',')

            self.xpos = float(received_data[0]) * self.width
            self.ypos = float(received_data[1]) * self.height
            self.is_averaged = float(received_data[2])
            self.is_valid = float(received_data[3])

            if self.is_averaged:

                if self.is_size_being_updated is False:
                    if self.alpha_counter < 250:
                        self.alpha_counter = self.alpha_counter + 5

                else:
                    self.alpha_counter = 255

                self.window_color.setAlpha(self.alpha_counter)
                self.window_pen.setColor(self.window_color)
                self.moving_rect.setPen(self.window_pen)

                self.moving_rect.setPos(self.xpos - self.rect.width()/2, self.ypos - self.rect.height()/2)
                self.moving_circle.setPos(self.xpos, self.ypos)

            else:
                self.alpha_counter = 0

        if self.is_size_being_updated is True:
            self.resize_count = 0
        else:
            self.resize_count = self.resize_count + 1


    def update_mouse(self, info):

        self.rect = self.moving_rect.rect()
        self.is_size_being_updated = False

        try:
            updown = info[2]
            leftright = info[1]

            if self.is_size_being_updated is False:
                self.locked_xpos = self.xpos
                self.locked_ypos = self.ypos

            # increase width as the trackball scrolls to the right
            if (leftright <=5) and (self.rect.width() <= self.size_max):
                self.rect.setWidth(self.rect.width() + self.scale_value)
                self.moving_rect.setRect(self.rect)
                self.is_size_being_updated = True

            # decrease width as the trackball scrolls to the left
            if (leftright >=250) and (self.rect.width() > self.size_min):
                self.rect.setWidth(self.rect.width() - self.scale_value)
                self.moving_rect.setRect(self.rect)
                self.is_size_being_updated = True

            # increase height as the trackball scrolls to the bottom
            if (updown <=5) and (self.rect.height() < self.size_max):
                self.rect.setHeight(self.rect.height() + self.scale_value)
                self.moving_rect.setRect(self.rect)
                self.is_size_being_updated = True

            # decrease height as the trackball scrolls to the top
            if (updown >=250) and (self.rect.height() > self.size_min):
                self.rect.setHeight(self.rect.height() - self.scale_value)
                self.moving_rect.setRect(self.rect)
                self.is_size_being_updated = True

            # self.moving_rect.setPos(self.locked_xpos - self.rect.width()/2, self.locked_ypos - self.rect.height()/2)

        except: pass


    def keyPressEvent(self, event):
        key = event.key()

        if key == QtCore.Qt.Key_A:
            self.threads = []
            self.gazetrackerthread = GazeTrackerThread()
            # self.mousethread = MouseThread()
            self.gazetrackerthread.pog.connect(self.update_location)
            # self.mousethread.mouse_data.connect(self.update_mouse)
            self.threads.append(self.gazetrackerthread)
            # self.threads.append(self.mousethread)
            self.gazetrackerthread.start()
            # self.mousethread.start()

class GazeTrackerThread(QThread, QtGui.QGraphicsView):

    pog = QtCore.pyqtSignal(object)


    def __init__(self, use_extra_filtering):
        QtCore.QThread.__init__(self)
        self._loop = True
        self.tracker = GazeTracker("127.0.0.1", use_extra_filtering)

    def run(self):
        while self._loop:
            try:
                data_string = self.tracker.get_x_y_point()

                self.pog.emit(data_string)
            except:
                pass

    def exit_thread(self):
        self.tracker.exit_thread()
        self.stop_streaming()

    def stop_streaming(self):
        """ stops the stream of data by invalidating the is_running flag
        """
        self._loop = False

    def set_use_filtering(self, use_extra_filtering):
        self.tracker.use_extra_filtering = use_extra_filtering

class GazeTracker():
    """ Designed to handle the communication with the GazePoint gaze tracker based on socket communication with the
    specified XML message formats

    This class mainly handles receiving a continuous of the user's point of gaze. It can be further extended to perform
     other functions within the defined available functionalities by GazePoint.

    Attributes:
        gazept_tracker: an instance of GazeTrackerClient that facilitates basic socket communication methods

        data_queue: a queue of strings representing the raw data obtained in the data stream

        x_y_queue: a queue of strings representing the x and y data extracted from the raw data queue

        data_stream: the data stream used in the socket communication to transfer data back and forth

        tracker_thread_started: a boolean indicating whether the transmission is active in the gaze tracker thread

        message: a string that holds the message to be sent to the gaze tracker (based on the XML communication strings
            format in VALUES_gazept_strings.py)

        reply: a strings that holds the current reply obtained from the gaze tracker (also based on the XML
            communication strings format in VALUES_gazept_strings.py)

        parsed_reply: a string that handles parsing the raw XML reply obtained from the gaze tracker

        gazept_address: the IP address of the machine running the gaze tracker server application

    """

    def __init__(self, gazept_address, use_extra_filtering):
        """Inits GazeTracker with the IP address of the machine that is connected to the gaze tracker."""

        self.use_extra_filtering = use_extra_filtering
        self.gazept_socket = GazeTrackerClient()
        self.data_queue = Queue.Queue(4)
        self.x_y_queue = Queue.Queue(4)
        self.gaze_data_thread = None
        self.tracker_thread_started = False
        self.gazept_address = gazept_address

        self.connect_to_tracker()
        self.message = VALUES_gazept_strings.SET_ENABLE_SEND_POG_FIX

        self.parsed_reply = ''
        self.reply = ''

        # low-pass filter requirements
        self.order = 6
        self.fs = 30.0
        self.cutoff = 0.01

        self.b , self.a = self.butter_lowpass(self.cutoff, self.fs, self.order)

        # moving average filter requirements

        self.history_size  = 100
        self.d_history_size = 10
        self.xpos_history = Queue.Queue(self.history_size)
        self.ypos_history = Queue.Queue(self.history_size)
        self.d_history = Queue.Queue(self.d_history_size)

        for x in range(0,self.history_size):
            self.xpos_history.put_nowait(0)
            self.ypos_history.put_nowait(0)

        for x in range(0,self.d_history_size):
            self.d_history.put_nowait(0)


        self.moving_average_d_threshold = 0.004
        self.moving_average_counter = 0

        self.just_started = False

        if PLOT:
            self.data_plot = [1] * 100
            self.t = np.linspace(0,2,100)

            plt.ion()
            axes = plt.gca()
            axes.set_ylim([0,0.009])
            self.graph = plt.plot(self.t, self.data_plot)[0]
            plt.draw()

    def filter_data_wtih_customized_moving_average(self, data):

        x = 0
        y = 0
        is_averaged = 0

        data_string = data.split(',')

        validity = float(data_string[2])

        x_list = []
        for elem in list(self.xpos_history.queue):
            x_list.append(elem)

        y_list = []
        for elem in list(self.ypos_history.queue):
            y_list.append(elem)

        old_x = x_list[self.history_size-2]
        new_x = x_list[self.history_size-1]

        old_y = y_list[self.history_size-2]
        new_y = y_list[self.history_size-2]

        if x_list[0:10] == [0] * 10 and y_list[0:10] == [0] *10:
            self.just_started = True
        else:
            self.just_started = False

        if self.just_started is False:
            d = math.sqrt((old_x - new_x)**2 + (old_y - new_y)**2)
            self.d_history.get_nowait()
            self.d_history.put_nowait(d)

            d_list = []
            for elem in list(self.d_history.queue):
                d_list.append(elem)

            d_average = sum(d_list) / self.d_history_size

            if PLOT:
                self.data_plot.pop(0)
                self.data_plot.append(d)
                self.graph.set_ydata(self.data_plot)
                plt.draw()

            if d_average < self.moving_average_d_threshold:

                if self.moving_average_counter < self.history_size:
                    self.moving_average_counter = self.moving_average_counter + 1
                else:
                    self.moving_average_counter = self.history_size

                # reversing the list of points so that it will only average the recent ones
                x_list_reveresed = x_list
                x_list_reveresed.reverse()
                y_list_reveresed = y_list
                y_list_reveresed.reverse()
                x_average = sum(x_list_reveresed[0:self.moving_average_counter]) / self.moving_average_counter
                y_average = sum(y_list_reveresed[0:self.moving_average_counter]) / self.moving_average_counter

                x = x_average
                y = y_average
                is_averaged = 1

            else:
                self.moving_average_counter = 0
                x = new_x
                y = new_y
                is_averaged = 0

        return str(x) + "," + str(y) + "," + str(validity) + "," + str(is_averaged)


    def butter_lowpass(self, cutoff, fs, order = 5):
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype="low", analog=False)
        return b, a

    def butter_lowpass_filter(self, data, cutoff, fs, order = 5):
        b, a = self.butter_lowpass(cutoff, fs, order = order)
        y = lfilter(b, a, data)
        return y

    def apply_low_pass_filter(self, data):
        y = self.butter_lowpass_filter(data, self.cutoff, self.fs, self.order)
        return y

    def filter_data_with_lowpass_filter(self):

        x_list = []
        for elem in list(self.xpos_history.queue):
            x_list.append(elem)

        y_list = []
        for elem in list(self.ypos_history.queue):
            y_list.append(elem)

        xpos = self.apply_low_pass_filter(x_list)
        ypos = self.apply_low_pass_filter(y_list)

        xpos_pt = sum(xpos)/self.xpos_history.qsize()
        ypos_pt = sum(ypos)/self.xpos_history.qsize()

        filtered_data = str(xpos_pt) +\
                        "," + str(ypos_pt) \
                        + "," + str(1)



        return filtered_data

    def get_x_y_point(self):
        """Returns the current point of gaze

        Returns the current x and y from the queue in the form of {'x': x_value, 'y': y_value}
        the values returned are percentages of the area where the user is looking
        in terms of the display's width and height
        """
        self.update_points()
        return self.x_y_queue.get_nowait()

    def connect_to_tracker(self):
        """Connects to the gaze tracker

        Uses the method provided by GazeTrackerClient to safely connect to the gaze tracker
        """
        if DEBUG:
            print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeTracker - connect_to_tracker"

        try:
            self.gazept_socket.connect(self.gazept_address, GAZEPT_PORT)
            self.gazept_socket.sock.settimeout(TIMEOUT_INITIAL)
            if DEBUG:
                print "Socket for Gazepoint Opened"

        except socket.error as socketerror:
            print("Error Connecting to Gazepoint Socket", socketerror)
        else:
            self.gazept_socket.set_timeout(TIMEOUT_ERROR)

    def update_points(self):
        """Updates the point of gaze obtained by the gaze tracker

        This method handles sending and receiving the necessary XML-based messages to update the obtained point of gaze
        """
        # if DEBUG:
        #     print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeTracker - update_points"

        # if the data thread is active, receive data
        if self.tracker_thread_started:
            if not self.data_queue.empty():
                x_y_local = self.get_raw_xml_data(self.data_queue.get_nowait())
                if x_y_local!= "":  # some messages are empty, filter those
                    x_y_local = self.parse_xml_data(x_y_local)
                    x_y_local = self.parse_validate_updatehistory(x_y_local)

                    if self.use_extra_filtering:
                        x_y_local = self.filter_data_wtih_customized_moving_average(x_y_local)

                    try:
                        self.x_y_queue.put_nowait(x_y_local)
                    except Queue.Full:  # if the queue is full, push some data out of it
                        self.x_y_queue.get_nowait()

        # otherwise, determine the required message to send to the gaze tracker
        else:
            if self.gazept_socket.is_socket_client_opened and self.message != '':
                self.gazept_socket.send_message(self.message)  # sends the first message to start data transmission
                try:
                    read = [self.gazept_socket.sock]
                    while read:
                        read, write, error = select.select([self.gazept_socket.sock], [], [], 0.0)
                        self.reply = self.gazept_socket.receive_message(len(self.message))

                    if self.reply == VALUES_gazept_strings.ACK_ENABLE_SEND_POG_FIX:
                        self.message = VALUES_gazept_strings.SET_ENABLE_SEND_DATA
                    elif self.reply == VALUES_gazept_strings.ACK_ENABLE_SEND_DATA:
                        if DEBUG:
                            print 'Data transmission enabled'
                        self.message = ''
                        self.gaze_data_thread = GazeDataThread(self.gazept_socket, self.data_queue)
                        self.gaze_data_thread.set_message_length(REPLY_MESSAGE_LENGTH)
                        self.gaze_data_thread.daemon = True
                        self.gaze_data_thread.start()
                        self.tracker_thread_started = True

                except socket.timeout:
                    pass
                    # print 'Timeout'

    def parse_validate_updatehistory(self, data_string):

        ######################################
        # PARSE AND VALIDATE
        ######################################

        # data_string: a string of one POG information, including x, y, time, fixation, duration, ID, validity
        data_string = data_string.split(',')

        xpos = float(data_string[0])
        ypos = float(data_string[1])
        starting_time = float(data_string[2])
        fixation_duration = float(data_string[3])
        ID = int(data_string[4])
        is_valid = int(data_string[5])

        # print "[" + str(xpos) + "," + str(ypos) + "], starting time = " + str(starting_time) + \
        #       ", fixation duration = " + str(fixation_duration) + \
        #     ", ID = " + str(ID) + ", validity = " + str(is_valid)

        if is_valid == 1 and (xpos>=0.0 and ypos>=0.0):
            self.last_valid_x = xpos
            self.last_valid_y = ypos

        else:
            xpos = self.last_valid_x
            ypos = self.last_valid_y

        parsed_data = str(xpos) + "," + str(ypos) + "," + str(is_valid)

        ##################################################
        # UPDATE HISTORY WITH PARSED AND VALIDATED DATA
        ##################################################

        try:
            # update the window
            self.xpos_history.get_nowait()
            self.xpos_history.put_nowait(xpos)

            self.ypos_history.get_nowait()
            self.ypos_history.put_nowait(ypos)
        except:
            pass

        return parsed_data

    def parse_xml_data(self, raw_xml):

        xmldoc = minidom.parseString(raw_xml)
        itemlist = xmldoc.getElementsByTagName('REC')

        data = itemlist[0].attributes['FPOGX'].value + "," + itemlist[0].attributes['FPOGY'].value + \
                              "," + itemlist[0].attributes['FPOGS'].value + \
                              "," + itemlist[0].attributes['FPOGD'].value + \
                              "," + itemlist[0].attributes['FPOGID'].value + \
                              "," + itemlist[0].attributes['FPOGV'].value

        return data

    def get_raw_xml_data(self, input_string):

        # if DEBUG:
        #     print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeTracker - get_x_y_from_raw_string"

        reply_string = input_string
        if reply_string.find("<") and reply_string.find(">") >= 0:

            reply_string_1 = reply_string.split(">")[0]
            reply_string_2 = reply_string.split(">")[1]
            self.parsed_reply = self.parsed_reply + reply_string_1

            output = self.parsed_reply + ">"
            self.parsed_reply = reply_string_2

        elif reply_string.find("<") >= 0:
            self.parsed_reply = reply_string
            output = ""
        elif reply_string.find(">") >= 0:
            self.parsed_reply = self.parsed_reply + reply_string
            output = self.parsed_reply + ">"
        else:
            self.parsed_reply = self.parsed_reply + reply_string
            output = ""

        return output

    def exit_thread(self):
        try:
            self.gaze_data_thread.stop_streaming()
            self.gazept_socket.disconnect()
        except:
            pass

class GazeDataThread(threading.Thread):
    """ Handles the gaze tracker's data thread

    This class defines the run() method that runs continuously within the thread performing the rquired messages
    transmission

    Attributes:
        socket: the client socket of the established communication

        queue: the data queue shared between this thread and the parent_dir thread

        is_running: a boolean indicating whether or not to perform the functionality needed in the run() method

        message_length: the length of the message to be transmitted in the stream

        reply: a strings that holds the parsed_reply obtained from the gaze tracker
    """

    def __init__(self, gazetracker_socket, queue):
        """Inits GazeDataThread with the communication gazetracker_socket and data queue"""
        threading.Thread.__init__(self)
        self.socket = gazetracker_socket
        self.queue = queue
        self._loop = True
        self.message_length = 0
        self.reply = ''
        self.setName("GazeDataThread")

    def run(self):
        """ The main thread run() method. Automatically called once the thread is started by the parent_dir thread.
        """
        if DEBUG:
            print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeDataThread - run"

        while self._loop:
            try:
                read = [self.socket.sock]
                while read:
                    read, write, error = select.select([self.socket.sock], [], [], 0.0)
                    self.reply = self.socket.receive_message(self.message_length)
                    self.queue.put_nowait(self.reply)

            except socket.timeout:
                pass
                # print 'Timeout'
            except Queue.Full:
                self.queue.get_nowait()

    def set_message_length(self, length):
        """ Sets the lenght of the message to be transmitted in the data stream
        """
        if DEBUG:
            print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeDataThread - set_message_length"

        self.message_length = length

    def stop_streaming(self):
        """ stops the stream of data by invalidating the is_running flag
        """
        if DEBUG:
            print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeDataThread - stop_streaming"
        self._loop = False

class GazeTrackerClient(object):
    """Client communication with the gaze tracker

    This class facilitates socket communication with the gaze tracker by acting as a client to receive information form
    the gaze tracker (the server)

    Attributes:
        sock: the communication socket at the client's side
        is_socket_client_opened: a boolean that indicates whether the client is connected or disconnected

    """

    def __init__(self, sock=None):
        """Inits GazeTrackerClient with a socket."""
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

        self.is_socket_client_opened = False

    def connect(self, host, port):
        """Connects to the gaze tracker

        Attributes:
            host: IP address of the host (the gaze tracker in this case)
            port: the port number
        """
        if DEBUG:
            print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeTrackerClient - connect"

        self.sock.connect((host, port))
        self.is_socket_client_opened = True

    def disconnect(self):
        if DEBUG:
            print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeTrackerClient - disconnect"

        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

    def set_timeout(self, timeout):
        """Sets the timeout for the established socket communication session

        Attributes:
            timeout: a float number indicating the timeout for this session
        """
        if DEBUG:
            print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeTrackerClient - set_timeout"

        self.sock.settimeout(timeout)

    def send_message(self, content):
        """ Sends the message passed in the parameter of this method to the gaze tracker

        Attributes:
            conetnt: a string representing the conetent of the message to be sent through the established session
        """
        if DEBUG:
            print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeTrackerClient - send_message"

        totalsent = 0
        while totalsent < len(content):
            sent = self.sock.send(content[totalsent:])
            if sent == 0:
                raise RunTimeError("socket connection broken")
            totalsent = totalsent + sent

    def receive_message(self, message_length):
        """ Receives a message from the gaze tracker based on the required length

        Attributes:
            message_length: an integer indicating the length of the message to be read by the client

        Returns:
            message: the message received in a string form

        """
        # if DEBUG:
        #     print "FUNCTION: SUPPORT_gazepoint_tracker.py - GazeTrackerClient - receive_message"

        chunks = []
        bytes_received = 0
        while bytes_received < message_length:
            chunk = self.sock.recv(min(message_length - bytes_received, 2048))

            if chunk == '':
                raise RuntimeError("socket connection broken")

            chunks.append(chunk)
            bytes_received += len(chunk)

        message = ''.join(chunks)
        return message


# MAIN #
if __name__ == "__main__":
    IS_STANDALONE = True

    app = QtGui.QApplication(sys.argv)
    trackerGUI = GazeTrackerGUI()
    trackerGUI.show()
    app.exec_()
