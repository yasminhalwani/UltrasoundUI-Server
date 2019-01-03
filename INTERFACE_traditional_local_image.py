import math
import time
import win32api
import win32gui

import numpy as np
import pyqtgraph as pg
from PIL import Image
from numpy import array
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import *

import SUPPORT_moosegesture
from SUPPORT_arduino_interface import ArduinoThread
from SUPPORT_gazepoint_tracker import GazeTrackerThread
from VALUES_main import *


class Traditional(QtGui.QMainWindow):
    def __init__(self, sonix_address, sonix_timeout, sonix_fail_max_count,
                 screen_width_input, screen_height_input):
        super(Traditional, self).__init__()

        # ---------------------------#
        #     VARIABLES              #
        # ---------------------------#
        # <editor-fold desc="state variables">
        # State variable
        self.interface = Interface.TRADITIONAL
        self.system_state = SystemState.FULLSCALE
        self.indicators_state = POGValidity.VALID
        self.indicators_state_prev = POGValidity.INVALID_LONG
        self.roi_state = ROIState.NONE
        self.padding_state = PaddingType.NONE
        # </editor-fold>

        # <editor-fold desc="window variables">
        self.screen_width = screen_width_input
        self.screen_height = screen_height_input
        # </editor-fold>

        # <editor-fold desc="image variables">
        self.image = None
        self.image_width = 0
        self.image_height = 0
        self.image_diagonal = 0
        # </editor-fold>

        # <editor-fold desc="counter variables">
        self.no_gaze_counter = 0
        # </editor-fold>

        # <editor-fold desc="mouse variables">
        self.mouse_pos_history = None
        self.mouse_pos_history_max_size = None
        self.current_trackball_x = 0
        self.current_trackball_y = 0
        self.prev_trackball_x = 0
        self.prev_trackball_y = 0
        # </editor-fold>

        # <editor-fold desc="gaze variables">
        self.POG = QtCore.QPoint(0, 0)
        self.converted_cursor_pos = QtCore.QPoint(0, 0)
        # </editor-fold>

        # <editor-fold desc="hardware interface variables">
        self.arduino = None
        self.pb_pressed = False
        self.pb_press_start_time = 0
        self.pb_press_elapsed_time = 0
        self.pb_held = False
        # </editor-fold>

        # # <editor-fold desc="gui variables">
        # GUI variables
        # -- docks
        self.dock_area = None
        self.image_dock = None
        self.indicators_dock = None
        self.context_dock = None
        self.extra_dock = None

        # -- image layout
        self.image_layout_widget = None
        self.image_view_box = None
        self.image_item = None
        self.roi = None
        self.min_roi_width = None
        self.min_roi_height = None
        self.last_roi_before_reset = None
        self.detail_view_roi = None

        # -- context image layout
        self.context_image_layout_widget = None
        self.context_image_view_box = None
        self.context_image_item = None
        self.context_roi = None

        # -- indicators graphics and layout
        self.indicators_widget = None
        self.indicators_view_box = None
        self.indicators_graph_item = None
        self.indicators_pen = None
        self.indicators_brush_valid = None
        self.indicators_brush_invalid_1 = None
        self.indicators_brush_invalid_2 = None
        self.indicators_brush_invalid_3 = None
        self.indicators_pos = None
        self.indicators_adj = None
        self.indicators_symbols = None

        # -- extra dock layout
        self.extra_widget = None
        self.extra_layout_view_box = None
        self.extra_label_item = None

        # -- pan areas
        self.upper_rect = None
        self.upper_right_rect = None
        self.upper_left_rect = None
        self.lower_rect = None
        self.lower_right_rect = None
        self.lower_left_rect = None
        self.left_rect = None
        self.right_rect = None

        # -- padding layout
        self.padding_view_box = None
        self.padding_image = None
        self.left_padding = None
        self.right_padding = None
        self.top_padding = None
        self.bottom_padding = None

        # </editor-fold>

        # <editor-fold desc="threads variables">
        # Threads
        # Image update
        self.image_update_timer_thread = None
        self.is_streaming_image = True  # TODO falsify this and enable it somewhere else

        # Gaze tracker
        self.gaze_tracker_thread = None

        # Cursor monitor thread
        self.trackball_thread = None

        # Arduino interface thread
        self.arduino_interface_thread = None
        self.is_arduino_connected = False
        # </editor-fold>

        # ---------------------------#
        #     METHOD CALLS           #
        # ---------------------------#
        self.load_central_image()
        self.setup_gui()
        self.connect_to_ultrasound_machine()
        self.thread_start_image_update()
        self.thread_start_cursor_monitor()
        self.thread_start_arduino_interface()
        self.reset_all_values()

    def reset_all_values(self):
        # TODO reset the rest of the values (ultrasound parameters, zoom, etc)
        pass

    # <editor-fold desc="gui functions">
    @staticmethod
    def load_image(file_name):
        # TODO stream image
        image = Image.open(file_name)
        image = array(image)
        image = image.astype('float64')
        image = np.rot90(image)
        image = np.rot90(image)
        image = np.rot90(image)

        return image

    def load_central_image(self):
        self.image = self.load_image("image_patterns.jpg")

        self.image_width = self.image.shape[0]
        self.image_height = self.image.shape[1]
        self.image_diagonal = math.sqrt((self.image_width ** 2 + self.image_height ** 2))

    def load_padding_image(self):
        self.padding_image = Image.open("dot.jpg")
        self.padding_image = array(self.padding_image)
        self.padding_image = self.padding_image.astype('float64')

    def get_image_center_wrt_scene(self):
        x = self.image_width / 2
        y = self.image_height / 2
        pos = QtCore.QPoint(x, y)
        pos = self.image_item.mapToScene(pos.x(), pos.y())
        return pos

    def get_roi_center_wrt_scene(self):
        size = self.roi.size()
        pos = self.roi.pos()
        center = QtCore.QPoint(pos.x() + size.x() / 2, pos.y() + size.y() / 2)
        x = center.x()
        y = center.y()
        pos = QtCore.QPoint(x, y)
        pos = self.roi.mapToScene(pos.x(), pos.y())
        return pos

    def get_image_center_wrt_view(self):
        x = self.image_width / 2
        y = self.image_height / 2
        pos = QtCore.QPoint(x, y)
        pos = self.image_view_box.mapFromItemToView(self.image_item, QtCore.QPoint(pos.x(), pos.y()))
        return pos

    def get_roi_center_wrt_view(self):
        size = self.roi.size()
        pos = self.roi.pos()
        center = QtCore.QPoint(pos.x() + size.x() / 2, pos.y() + size.y() / 2)
        x = center.x()
        y = center.y()
        pos = QtCore.QPoint(x, y)
        pos = self.image_view_box.mapFromItemToView(self.image_item, QtCore.QPoint(pos.x(), pos.y()))
        return pos

    def setup_gui(self):
        self.setWindowTitle('Zoom Interface')
        self.showFullScreen()
        win32api.ShowCursor(False)

        self.setup_docks_layout()
        self.setup_image_layout()
        self.setup_roi_layout()
        self.setup_detail_view_roi()
        self.setup_context_image_layout()
        self.setup_gaze_indicators()
        self.setup_extra_widget()
        self.setup_padding_base_layout()
        self.reset_roi()
        self.set_view_to_roi_and_pad()

        self.image_view_box.sigRangeChanged.connect(self.callback_image_view_box)
        self.mouse_pos_history = []
        self.mouse_pos_history_max_size = 5

    def setup_docks_layout(self):
        self.dock_area = DockArea()
        self.setCentralWidget(self.dock_area)

        # define docks
        self.image_dock = Dock("Ultrasound Image", size=(1092, 1000))
        self.indicators_dock = Dock("Eye Gaze Indicators", size=(728, 200))
        self.context_dock = Dock("Image Context", size=(364, 200))
        self.extra_dock = Dock("Extras", size=(364, 200))

        # hide docks' title bars
        self.image_dock.hideTitleBar()
        self.indicators_dock.hideTitleBar()
        self.context_dock.hideTitleBar()
        self.extra_dock.hideTitleBar()

        # add docks
        self.dock_area.addDock(self.image_dock, 'top')
        self.dock_area.addDock(self.indicators_dock, 'bottom', self.image_dock)
        self.dock_area.addDock(self.context_dock, 'right', self.indicators_dock)
        self.dock_area.addDock(self.extra_dock, 'left', self.indicators_dock)

    def setup_image_layout(self):
        self.image_layout_widget = pg.GraphicsLayoutWidget()
        self.image_view_box = self.image_layout_widget.addViewBox(row=1, col=1)
        self.image_item = pg.ImageItem()

        self.image_view_box.addItem(self.image_item)
        self.image_item.setImage(self.image)
        self.image_item.setRect(QtCore.QRectF(0.0, 0.0, self.image_width, self.image_height))
        self.image_view_box.setAspectLocked(True)

        self.image_dock.addWidget(self.image_layout_widget)
        self.image_view_box.setMouseMode(pg.ViewBox.PanMode)

        self.image_view_box.autoRange(padding=0)
        self.image_view_box.setMouseEnabled(False, False)

    def setup_roi_layout(self):
        self.min_roi_width = self.image_width / 6
        self.min_roi_height = self.image_height / 6

        self.roi = pg.RectROI([0, 0], [DEFAULT_ROI_SIDE_LENGTH, DEFAULT_ROI_SIDE_LENGTH], movable=False,
                              maxBounds=QtCore.QRectF(0, 0, self.image_width, self.image_height))
        self.image_view_box.addItem(self.roi)

        self.roi.setPen(pg.mkPen('r', width=1, style=QtCore.Qt.SolidLine))
        self.roi.removeHandle(0)
        self.roi.hide()

    def setup_detail_view_roi(self):
        self.detail_view_roi = pg.RectROI([0, 0], [self.image_width, self.image_height], movable=False,
                                          maxBounds=QtCore.QRectF(0, 0, self.image_width, self.image_height))
        self.detail_view_roi.setPen(pg.mkPen('r', width=2, style=QtCore.Qt.SolidLine))
        self.image_view_box.addItem(self.detail_view_roi)

    def setup_context_image_layout(self):
        self.context_image_layout_widget = pg.GraphicsLayoutWidget()
        self.context_image_view_box = self.context_image_layout_widget.addViewBox(row=1, col=1)
        self.context_image_item = pg.ImageItem()

        self.context_image_view_box.addItem(self.context_image_item)
        self.context_image_item.setImage(self.image)
        self.context_image_item.setRect(QtCore.QRectF(0.0, 0.0, self.image_width, self.image_height))
        self.context_image_view_box.setAspectLocked(True)
        self.context_image_view_box.setMouseEnabled(False, False)

        self.context_dock.addWidget(self.context_image_layout_widget)

        # -- manage ROI displayed over the context image
        self.context_roi = pg.RectROI([0, 0], [DEFAULT_ROI_SIDE_LENGTH, DEFAULT_ROI_SIDE_LENGTH], pen=(0, 5),
                                      maxBounds=QtCore.QRectF(0, 0, self.image_width, self.image_height))
        self.context_image_view_box.addItem(self.context_roi)

        if self.system_state == SystemState.FULLSCALE:
            # self.context_image_item.hide()
            pass

    def setup_gaze_indicators(self):
        # -- setup widgets and containers
        self.indicators_widget = pg.GraphicsLayoutWidget()
        self.indicators_view_box = self.indicators_widget.addViewBox(row=1, col=1)
        self.indicators_view_box.setAspectLocked()
        self.indicators_graph_item = pg.GraphItem()
        self.indicators_view_box.addItem(self.indicators_graph_item)
        self.indicators_view_box.setMouseEnabled(False, False)

        # -- manage graphics
        color = QtGui.QColor(QtCore.Qt.darkRed)
        self.indicators_pen = QtGui.QPen()
        self.indicators_brush_valid = QtGui.QBrush()
        self.indicators_brush_invalid_1 = QtGui.QBrush(color.darker(150))
        self.indicators_brush_invalid_2 = QtGui.QBrush(color.darker(100))
        self.indicators_brush_invalid_3 = QtGui.QBrush(color.darker(50))

        self.indicators_pos = np.array([[0, 0], [5, 0]])
        self.indicators_adj = np.array([[0, 1], [1, 0]])
        self.indicators_symbols = ['o', 'o']

        self.indicators_graph_item.setData(pos=self.indicators_pos,
                                           adj=self.indicators_adj,
                                           size=1,
                                           symbol=self.indicators_symbols,
                                           pxMode=False,
                                           symbolBrush=self.indicators_brush_invalid_1,
                                           symbolPen=self.indicators_pen)

        self.indicators_dock.addWidget(self.indicators_widget)
        self.indicators_graph_item.hide()

    def setup_extra_widget(self):
        self.extra_widget = pg.GraphicsLayoutWidget()
        self.extra_layout_view_box = self.extra_widget.addViewBox(row=1, col=1)
        self.extra_label_item = pg.LabelItem()
        self.extra_layout_view_box.addItem(self.extra_label_item)
        self.extra_label_item.setText(self.system_state, color='CCFF00', size='2pt', bold=True, italic=False)
        self.extra_layout_view_box.invertY()
        self.extra_layout_view_box.setMouseEnabled(False, False)

        self.extra_dock.addWidget(self.extra_widget)

    def setup_padding_base_layout(self):
        image = Image.open("black.jpg")
        image = array(image)
        image = image.astype('float64')

        self.padding_view_box = self.image_layout_widget.addViewBox(row=1, col=1)
        transparent_background = pg.ImageItem()

        self.padding_view_box.addItem(transparent_background)
        transparent_background.setImage(image, opacity=0.0)
        transparent_background.setRect(QtCore.QRectF(0.0, 0.0, self.image_width, self.image_height))
        self.padding_view_box.setAspectLocked(True)
        self.padding_view_box.setMouseEnabled(False, False)

        self.load_padding_image()
        self.padding_view_box.autoRange(padding=0)

    # </editor-fold>

    # <editor-fold desc="callback functions">

    def callback_arduino_update(self, info):

        event = None
        key = None
        if info == HwInterface.ZOOM_PRESS:
            key = QtCore.Qt.Key_W

        elif info == HwInterface.ZOOM_CW:
            key = QtCore.Qt.Key_A

        elif info == HwInterface.ZOOM_CCW:
            key = QtCore.Qt.Key_D

        elif info == HwInterface.CAPTURE_PRESS:
            key = QtCore.Qt.Key_O

        elif info == HwInterface.FREEZE_PRESS:
            key = QtCore.Qt.Key_P

        elif info == HwInterface.CALIBRATE_PRESS:
            key = QtCore.Qt.Key_G

        elif info == HwInterface.DEPTH_CW:
            key = QtCore.Qt.Key_Z

        elif info == HwInterface.DEPTH_CCW:
            key = QtCore.Qt.Key_X

        elif info == HwInterface.FOCUS_CW:
            key = QtCore.Qt.Key_C

        elif info == HwInterface.FOCUS_CCW:
            key = QtCore.Qt.Key_V

        elif info == HwInterface.FOCUS_PRESS:
            key = QtCore.Qt.Key_B

        elif info == HwInterface.PB_PRESS:
            if not self.pb_pressed:
                self.pb_pressed = True
                self.pb_press_start_time = time.time()
            else:
                self.pb_pressed = False
                if not self.pb_held:
                    key = QtCore.Qt.Key_S
                else:
                    self.pb_held = False

        if key is not None:
            event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, QtCore.Qt.KeyboardModifiers())

        if event is not None:
            self.keyPressEvent(event)

    def callback_image_update(self):
        arr = self.image_streamer.get_new_image_array()
        self.image = arr

        self.image = self.image.astype('float64')
        self.image = np.rot90(self.image)
        self.image = np.rot90(self.image)
        self.image = np.rot90(self.image)

        self.image_width = self.image.shape[0]
        self.image_height = self.image.shape[1]
        self.image_diagonal = math.sqrt((self.image_width ** 2 + self.image_height ** 2))

        try:
            self.image_item.setImage(self.image)
            self.context_image_item.setImage(self.image)
        except:
            pass
        if self.is_streaming_image:
            return True  # the update function must always return true
        else:
            return False

    def callback_update_POG(self, info):
        # receive data from gaze thread
        received_data = info.split(',')

        xpos = float(received_data[0]) * self.screen_width
        ypos = float(received_data[1]) * self.screen_height
        is_valid = float(received_data[2])
        if is_valid:
            self.POG = QtCore.QPoint(xpos, ypos)

        # update eye gaze validity indicators
        self.update_validity_indicators(is_valid)

    def callback_cursor_monitor(self):

        if self.system_state == SystemState.ZOOM_A or self.system_state == SystemState.ZOOM_B or \
                        self.system_state == SystemState.PRE_ZOOM_A or self.system_state == SystemState.PRE_ZOOM_B:

            flags, hcursor, (x, y) = win32gui.GetCursorInfo()

            self.current_trackball_x = x
            self.current_trackball_y = y

            if self.current_trackball_y != self.prev_trackball_y or self.current_trackball_x != self.prev_trackball_x:
                self.prev_trackball_y = self.current_trackball_y
                self.prev_trackball_x = self.current_trackball_x

                if x > self.screen_width - 50:
                    win32api.SetCursorPos((int(50), int(y)))
                    self.mouse_pos_history = []

                    direction = Direction.RIGHT
                    if self.system_state == SystemState.ZOOM_A or self.system_state == SystemState.ZOOM_B:
                        if self.system_state == SystemState.ZOOM_A:
                            self.translate_roi(direction, ROI_TRANSLATION_SCALE)
                        elif self.system_state == SystemState.ZOOM_B:
                            self.resize_roi(direction)
                        self.set_view_to_roi_and_pad()
                    elif self.system_state == SystemState.PRE_ZOOM_A:
                        self.translate_roi(direction, ROI_TRANSLATION_SCALE)
                    elif self.system_state == SystemState.PRE_ZOOM_B:
                        self.resize_roi(direction)
                elif x < 50:
                    win32api.SetCursorPos((int(self.screen_width - 50), int(y)))
                    self.mouse_pos_history = []

                    direction = Direction.LEFT
                    if self.system_state == SystemState.ZOOM_A or self.system_state == SystemState.ZOOM_B:
                        if self.system_state == SystemState.ZOOM_A:
                            self.translate_roi(direction, ROI_TRANSLATION_SCALE)
                        elif self.system_state == SystemState.ZOOM_B:
                            self.resize_roi(direction)
                        self.set_view_to_roi_and_pad()
                    elif self.system_state == SystemState.PRE_ZOOM_A:
                        self.translate_roi(direction, ROI_TRANSLATION_SCALE)
                    elif self.system_state == SystemState.PRE_ZOOM_B:
                        self.resize_roi(direction)

                if y > self.screen_height - 50:
                    win32api.SetCursorPos((int(x), int(50)))
                    self.mouse_pos_history = []

                    direction = Direction.DOWN
                    if self.system_state == SystemState.ZOOM_A or self.system_state == SystemState.ZOOM_B:
                        if self.system_state == SystemState.ZOOM_A:
                            self.translate_roi(direction, ROI_TRANSLATION_SCALE)
                        elif self.system_state == SystemState.ZOOM_B:
                            self.resize_roi(direction)
                        self.set_view_to_roi_and_pad()
                    elif self.system_state == SystemState.PRE_ZOOM_A:
                        self.translate_roi(direction, ROI_TRANSLATION_SCALE)
                    elif self.system_state == SystemState.PRE_ZOOM_B:
                        self.resize_roi(direction)

                elif y < 50:
                    win32api.SetCursorPos((int(x), int(self.screen_height - 50)))
                    self.mouse_pos_history = []

                    direction = Direction.UP
                    if self.system_state == SystemState.ZOOM_A or self.system_state == SystemState.ZOOM_B:
                        if self.system_state == SystemState.ZOOM_A:
                            self.translate_roi(direction, ROI_TRANSLATION_SCALE)
                        elif self.system_state == SystemState.ZOOM_B:
                            self.resize_roi(direction)
                        self.set_view_to_roi_and_pad()
                    elif self.system_state == SystemState.PRE_ZOOM_A:
                        self.translate_roi(direction, ROI_TRANSLATION_SCALE)
                    elif self.system_state == SystemState.PRE_ZOOM_B:
                        self.resize_roi(direction)

                self.mouse_pos_history.append((x, y))
                if len(self.mouse_pos_history) > self.mouse_pos_history_max_size:
                    self.mouse_pos_history.pop(0)

                strokes = SUPPORT_moosegesture.getGesture(self.mouse_pos_history)
                direction = SUPPORT_moosegesture.getGestureStr(strokes)

                if direction == 'R':
                    direction = Direction.RIGHT
                elif direction == 'L':
                    direction = Direction.LEFT
                elif direction == 'U':
                    direction = Direction.UP
                elif direction == 'D':
                    direction = Direction.DOWN
                elif direction == 'UL':
                    direction = Direction.UPPER_LEFT
                elif direction == 'UR':
                    direction = Direction.UPPER_RIGHT
                elif direction == 'DL':
                    direction = Direction.LOWER_LEFT
                elif direction == 'DR':
                    direction = Direction.LOWER_RIGHT

                if self.system_state == SystemState.ZOOM_A:
                    self.translate_roi(direction, ROI_TRANSLATION_SCALE)
                    self.set_view_to_roi_and_pad()
                elif self.system_state == SystemState.ZOOM_B:
                    self.resize_roi(direction)
                    self.set_view_to_roi_and_pad()
                elif self.system_state == SystemState.PRE_ZOOM_A:
                    self.translate_roi(direction, ROI_TRANSLATION_SCALE)
                elif self.system_state == SystemState.PRE_ZOOM_B:
                    self.resize_roi(direction)

    def callback_image_view_box(self):
        self.context_roi.setPos(self.roi.pos())
        self.context_roi.setSize(self.roi.size())

    # </editor-fold>

    # <editor-fold desc="threading functions">

    def thread_start_gaze_tracker(self):
        self.gaze_tracker_thread = GazeTrackerThread(FILTER_POG)
        self.gaze_tracker_thread.pog.connect(self.callback_update_POG)
        self.gaze_tracker_thread.start(10000)

    def thread_start_image_update(self):
        self.image_update_timer_thread = QtCore.QTimer()
        self.image_update_timer_thread.start(.1)
        self.connect(self.image_update_timer_thread, QtCore.SIGNAL('timeout()'), self.callback_image_update)
        self.is_streaming_image = True

    def thread_start_cursor_monitor(self):
        self.trackball_thread = QtCore.QTimer()
        self.trackball_thread.start(.1)
        self.connect(self.trackball_thread, QtCore.SIGNAL('timeout()'), self.callback_cursor_monitor)

    def thread_start_arduino_interface(self):
        self.arduino_interface_thread = ArduinoThread()
        self.arduino_interface_thread.data.connect(self.callback_arduino_update)
        self.arduino_interface_thread.start(10000)

    # </editor-fold>

    # <editor-fold desc="zoom functions">

    def go_to_pre_zoom(self):

        if self.last_roi_before_reset is not None:
            if self.system_state == SystemState.FULLSCALE:
                self.roi.setPos((self.last_roi_before_reset.x(), self.last_roi_before_reset.y()))
                self.roi.setSize((self.last_roi_before_reset.width(), self.last_roi_before_reset.height()))
                self.context_roi.setPos((self.last_roi_before_reset.x(), self.last_roi_before_reset.y()))
                self.context_roi.setSize((self.last_roi_before_reset.width(), self.last_roi_before_reset.height()))
        else:
            x = self.image_width / 2
            y = self.image_height / 2
            center_pos = QtCore.QPoint(int(x), int(y))
            center_pos = self.image_view_box.mapFromItemToView(self.image_item, center_pos)
            self.roi.setSize((self.image_width / 2, self.image_height / 2))  # default
            self.set_roi_position_in_the_center_of(center_pos.x(), center_pos.y())

        self.roi.show()
        self.context_roi.hide()

    def zoom_in(self):
        new_width = self.roi.size().x() * ZOOM_RATIO
        new_height = self.roi.size().y() * ZOOM_RATIO

        x_shift = (new_width - self.roi.size().x()) / 2
        y_shift = (new_height - self.roi.size().y()) / 2

        if new_width > self.min_roi_width and new_height > self.min_roi_height:
            self.roi.setSize((new_width, new_height))
            self.roi.setPos((self.roi.pos().x() - x_shift, self.roi.pos().y() - y_shift))
            self.set_view_to_roi_and_pad()
        else:
            print "max zoom reached"

    def zoom_in_to_roi(self):
        # this function is typically used to zoom into a pre-set roi (from pre-zoom)
        if self.roi.size().x() > self.min_roi_width and self.roi.size().y() > self.min_roi_height:
            self.set_view_to_roi_and_pad()

    def zoom_out(self):
        new_width = self.roi.size().x() * 1 / ZOOM_RATIO
        new_height = self.roi.size().y() * 1 / ZOOM_RATIO

        x_shift = (new_width - self.roi.size().x()) / 2
        y_shift = (new_height - self.roi.size().y()) / 2

        new_x = self.roi.pos().x() - x_shift
        new_y = self.roi.pos().y() - y_shift

        if new_x < 0:
            new_x = 0

        if new_y < 0:
            new_y = 0

        if new_x + new_width > self.image_width:
            new_x = self.image_width - new_width

        if new_y + new_height > self.image_height:
            new_y = self.image_height - new_height

        if new_width < self.image_width or new_height < self.image_height:
            self.roi.setSize((new_width, new_height))
            self.roi.setPos((new_x, new_y))
            self.set_view_to_roi_and_pad()
        else:
            self.reset_zoom()
            self.set_view_to_roi_and_pad()

    def reset_zoom(self):
        self.last_roi_before_reset = QtCore.QRect(self.roi.pos().x(), self.roi.pos().y(),
                                                  self.roi.size().x(), self.roi.size().y())

        self.reset_roi()
        self.image_view_box.autoRange(padding=0)

    # </editor-fold>

    # <editor-fold desc="padding functions">

    def set_view_to_roi_and_pad(self):

        # setting view to ROI
        rect = QtCore.QRectF(self.roi.pos().x(), self.roi.pos().y(), self.roi.size().x(), self.roi.size().y())
        self.image_view_box.setRange(rect, padding=0)
        self.padding_view_box.setRange(rect, padding=0)

        # adding the red border around the detail view
        self.detail_view_roi.setPos((rect.x(), rect.y()))
        self.detail_view_roi.setSize((rect.width(), rect.height()))

        # adding the padding if needed
        padding_type, view_range_width, view_range_height = self.check_for_padding_requirement()
        self.padding_state = padding_type

        if padding_type is not PaddingType.NONE and padding_type is not PaddingType.INVALID:
            self.add_padding(padding_type, view_range_width, view_range_height)

        # manage the visibility of the context view
        if self.roi.size().x() == self.image_width and self.roi.size().y() == self.image_height:
            self.detail_view_roi.hide()
            self.context_roi.hide()
        else:
            self.detail_view_roi.show()
            self.context_roi.show()

    def check_for_padding_requirement(self):
        view_range = self.image_view_box.viewRange()
        view_range_width = view_range[0][1] - view_range[0][0]
        view_range_height = view_range[1][1] - view_range[1][0]

        equal_heights = False
        equal_widths = False
        padding_type = PaddingType.NONE

        if int(self.roi.size().y()) == int(view_range_height):
            equal_heights = True
        if int(self.roi.size().x()) == int(view_range_width):
            equal_widths = True

        if equal_widths and not equal_heights:
            padding_type = PaddingType.UP_DOWN

        if equal_heights and not equal_widths:
            padding_type = PaddingType.LEFT_RIGHT

        if equal_heights and equal_widths:
            padding_type = PaddingType.NONE

        if not equal_heights and not equal_widths:
            padding_type = PaddingType.INVALID

        return padding_type, view_range_width, view_range_height

    def remove_existing_padding(self):
        if self.padding_state == PaddingType.LEFT_RIGHT:
            self.padding_view_box.removeItem(self.left_padding)
            self.padding_view_box.removeItem(self.right_padding)
        elif self.padding_state == PaddingType.UP_DOWN:
            self.padding_view_box.removeItem(self.top_padding)
            self.padding_view_box.removeItem(self.bottom_padding)

    def add_padding(self, padding_type, view_range_width, view_range_height):

        self.remove_existing_padding()

        # then add the new one
        padding_view_range = self.padding_view_box.viewRange()

        if padding_type == PaddingType.LEFT_RIGHT:
            padding_width = (view_range_width - self.roi.size().x()) / 2

            self.right_padding = pg.ImageItem()
            self.padding_view_box.addItem(self.right_padding)
            self.right_padding.setImage(self.padding_image)
            self.right_padding.setPos(self.roi.pos().x() + self.roi.size().x(), self.roi.pos().y())
            self.right_padding.scale(padding_width, view_range_height)
            self.right_padding.show()

            self.left_padding = pg.ImageItem()
            self.padding_view_box.addItem(self.left_padding)
            self.left_padding.setImage(self.padding_image)
            self.left_padding.setPos(padding_view_range[0][0], padding_view_range[1][0])
            self.left_padding.scale(padding_width, view_range_height)
            self.left_padding.show()

        elif padding_type == PaddingType.UP_DOWN:
            padding_height = (view_range_height - self.roi.size().y()) / 2

            self.top_padding = pg.ImageItem()
            self.padding_view_box.addItem(self.top_padding)
            self.top_padding.setImage(self.padding_image)
            self.top_padding.setPos(self.roi.pos().x(), self.roi.pos().y() + self.roi.size().y())
            self.top_padding.scale(view_range_width, padding_height)
            self.top_padding.show()

            self.bottom_padding = pg.ImageItem()
            self.padding_view_box.addItem(self.bottom_padding)
            self.bottom_padding.setImage(self.padding_image)
            self.bottom_padding.setPos(padding_view_range[0][0], padding_view_range[1][0])
            self.bottom_padding.scale(view_range_width, padding_height)
            self.bottom_padding.show()

        elif padding_type == PaddingType.NONE:
            print "no padding required"

        elif padding_type == PaddingType.INVALID:
            print "invalid padding"

    # </editor-fold>

    # <editor-fold desc="panning functions">
    def translate_image(self, direction):

        if direction == Direction.UP:
            self.image_view_box.translateBy((0.0, TRANSLATION_PX))

        elif direction == Direction.DOWN:
            self.image_view_box.translateBy((0.0, -TRANSLATION_PX))

        elif direction == Direction.LEFT:
            self.image_view_box.translateBy((-TRANSLATION_PX, 0.0))

        elif direction == Direction.RIGHT:
            self.image_view_box.translateBy((TRANSLATION_PX, 0.0))

        elif direction == Direction.UPPER_LEFT:
            self.image_view_box.translateBy((-TRANSLATION_PX, TRANSLATION_PX))

        elif direction == Direction.UPPER_RIGHT:
            self.image_view_box.translateBy((TRANSLATION_PX, TRANSLATION_PX))

        elif direction == Direction.LOWER_LEFT:
            self.image_view_box.translateBy((-TRANSLATION_PX, -TRANSLATION_PX))

        elif direction == Direction.LOWER_RIGHT:
            self.image_view_box.translateBy((TRANSLATION_PX, -TRANSLATION_PX))
    # </editor-fold>

    # <editor-fold desc="roi functions">

    def translate_roi(self, direction, scale):

        if self.system_state == SystemState.ZOOM_A:
            scale /= 2

        if direction != Direction.NONE:

            if direction == Direction.UP:
                if self.roi.pos().y() + self.roi.size().y() < self.image_height:
                    self.roi.setPos((self.roi.pos().x(), self.roi.pos().y() + TRANSLATION_PX * scale))
                else:
                    self.roi.setPos((self.roi.pos().x(), self.image_height - self.roi.size().y()))

            elif direction == Direction.DOWN:
                if self.roi.pos().y() > 0:
                    self.roi.setPos((self.roi.pos().x(), self.roi.pos().y() - TRANSLATION_PX * scale))
                else:
                    self.roi.setPos((self.roi.pos().x(), 0))

            elif direction == Direction.LEFT:
                if self.roi.pos().x() > 0:
                    self.roi.setPos((self.roi.pos().x() - TRANSLATION_PX * scale, self.roi.pos().y()))
                else:
                    self.roi.setPos((0, self.roi.pos().y()))

            elif direction == Direction.RIGHT:
                if self.roi.pos().x() + self.roi.size().x() < self.image_width:
                    self.roi.setPos((self.roi.pos().x() + TRANSLATION_PX * scale, self.roi.pos().y()))
                else:
                    self.roi.setPos((self.image_width - self.roi.size().x(), self.roi.pos().y()))

            elif direction == Direction.UPPER_LEFT:
                if self.roi.pos().y() + self.roi.size().y() < self.image_height:
                    if self.roi.pos().x() > 0:
                        self.roi.setPos((self.roi.pos().x() - TRANSLATION_PX * scale,
                                         self.roi.pos().y() + TRANSLATION_PX * scale))
                    else:
                        self.roi.setPos((0, self.roi.pos().y()))
                else:
                    self.roi.setPos((self.roi.pos().x(), self.image_height - self.roi.size().y()))

            elif direction == Direction.UPPER_RIGHT:
                if self.roi.pos().y() + self.roi.size().y() < self.image_height:
                    if self.roi.pos().x() + self.roi.size().x() < self.image_width:
                        self.roi.setPos((self.roi.pos().x() + TRANSLATION_PX * scale,
                                         self.roi.pos().y() + TRANSLATION_PX * scale))
                    else:
                        self.roi.setPos((self.image_width - self.roi.size().x(), self.roi.pos().y()))
                else:
                    self.roi.setPos((self.roi.pos().x(), self.image_height - self.roi.size().y()))

            elif direction == Direction.LOWER_LEFT:
                if self.roi.pos().y() > 0:
                    if self.roi.pos().y() + self.roi.size().y() < self.image_height:
                        self.roi.setPos((self.roi.pos().x() - TRANSLATION_PX * scale,
                                         self.roi.pos().y() - TRANSLATION_PX * scale))
                    else:
                        self.roi.setPos((0, self.roi.pos().y()))
                else:
                    self.roi.setPos((self.roi.pos().x(), 0))

            elif direction == Direction.LOWER_RIGHT:
                if self.roi.pos().y() > 0:
                    if self.roi.pos().x() + self.roi.size().x() < self.image_width:
                        self.roi.setPos((self.roi.pos().x() + TRANSLATION_PX * scale,
                                         self.roi.pos().y() - TRANSLATION_PX * scale))
                    else:
                        self.roi.setPos((self.image_width - self.roi.size().x(), self.roi.pos().y()))
                else:
                    self.roi.setPos((self.roi.pos().x(), 0))

            self.context_roi.setPos((self.roi.pos().x(), self.roi.pos().y()))
            self.context_roi.setSize((self.roi.size().x(), self.roi.size().y()))

    def resize_roi(self, direction):

        if direction != Direction.NONE:

            if direction == Direction.UP:
                new_height = self.roi.size().y() + RESIZE_PX
                new_y = self.roi.pos().y() - RESIZE_PX / 2
                if new_height <= self.image_height and new_y >= 0:
                    if self.roi.pos().y() + self.roi.size().y() < self.image_height:
                        self.roi.setSize((self.roi.size().x(), new_height))
                        self.roi.setPos((self.roi.pos().x(), new_y))

            elif direction == Direction.DOWN:
                new_height = self.roi.size().y() - RESIZE_PX
                new_y = self.roi.pos().y() + RESIZE_PX / 2
                if new_height >= self.min_roi_height:
                    if self.roi.pos().y() >= 0:
                        self.roi.setSize((self.roi.size().x(), new_height))
                        self.roi.setPos((self.roi.pos().x(), new_y))

            if direction == Direction.LEFT:
                new_width = self.roi.size().x() - RESIZE_PX * 2
                new_x = self.roi.pos().x() + (RESIZE_PX * 2) / 2
                if new_width >= self.min_roi_width:
                    if self.roi.pos().x() >= 0:
                        self.roi.setSize((new_width, self.roi.size().y()))
                        self.roi.setPos((new_x, self.roi.pos().y()))

            elif direction == Direction.RIGHT:
                new_width = self.roi.size().x() + RESIZE_PX * 2
                new_x = self.roi.pos().x() - (RESIZE_PX * 2) / 2
                if new_width <= self.image_width and new_x >= 0:
                    if self.roi.pos().x() + self.roi.size().x() < self.image_width:
                        self.roi.setSize((new_width, self.roi.size().y()))
                        self.roi.setPos((new_x, self.roi.pos().y()))

            self.context_roi.setPos((self.roi.pos().x(), self.roi.pos().y()))
            self.context_roi.setSize((self.roi.size().x(), self.roi.size().y()))

    def set_roi_position_in_the_center_of(self, x, y):
        size = self.roi.size()
        new_x = x - (size.x() / 2)
        new_y = y - (size.y() / 2)

        self.roi.setPos([new_x, new_y])
        self.context_roi.setPos((self.roi.pos().x(), self.roi.pos().y()))
        self.context_roi.setSize((self.roi.size().x(), self.roi.size().y()))

    def reset_roi(self):
        x = self.image_width / 2
        y = self.image_height / 2
        center_pos = QtCore.QPoint(int(x), int(y))
        center_pos = self.image_view_box.mapFromItemToView(self.image_item, center_pos)
        self.roi.setSize((self.image_width, self.image_height))
        self.set_roi_position_in_the_center_of(center_pos.x(), center_pos.y())

        self.context_roi.setPos((self.roi.pos().x(), self.roi.pos().y()))
        self.context_roi.setSize((self.roi.size().x(), self.roi.size().y()))

    # </editor-fold>

    # <editor-fold desc="feedback functions">
    def update_validity_indicators(self, is_valid):

        if not is_valid:
            self.no_gaze_counter += 1

            if 20 < self.no_gaze_counter <= 59:
                self.indicators_state = POGValidity.INVALID_SHORT

            elif 60 < self.no_gaze_counter <= 99:
                self.indicators_state = POGValidity.INVALID_INTERMEDIATE

            elif self.no_gaze_counter > 100:
                self.indicators_state = POGValidity.INVALID_LONG
        else:
            self.no_gaze_counter = 0
            self.indicators_state = POGValidity.VALID

        if self.indicators_state != self.indicators_state_prev:
            self.indicators_state_prev = self.indicators_state

            if self.indicators_state == POGValidity.VALID:
                self.indicators_graph_item.setData(pos=self.indicators_pos,
                                                   adj=self.indicators_adj,
                                                   size=1,
                                                   symbol=self.indicators_symbols,
                                                   pxMode=False,
                                                   symbolBrush=self.indicators_brush_valid,
                                                   symbolPen=self.indicators_pen)
                self.indicators_graph_item.hide()

            elif self.indicators_state == POGValidity.INVALID_SHORT:
                self.indicators_graph_item.setData(pos=self.indicators_pos,
                                                   adj=self.indicators_adj,
                                                   size=1,
                                                   symbol=self.indicators_symbols,
                                                   pxMode=False,
                                                   symbolBrush=self.indicators_brush_invalid_1,
                                                   symbolPen=self.indicators_pen)
                self.indicators_graph_item.show()

            elif self.indicators_state == POGValidity.INVALID_INTERMEDIATE:
                self.indicators_graph_item.setData(pos=self.indicators_pos,
                                                   adj=self.indicators_adj,
                                                   size=1,
                                                   symbol=self.indicators_symbols,
                                                   pxMode=False,
                                                   symbolBrush=self.indicators_brush_invalid_2,
                                                   symbolPen=self.indicators_pen)
                self.indicators_graph_item.show()

            elif self.indicators_state == POGValidity.INVALID_LONG:
                self.indicators_graph_item.setData(pos=self.indicators_pos,
                                                   adj=self.indicators_adj,
                                                   size=1,
                                                   symbol=self.indicators_symbols,
                                                   pxMode=False,
                                                   symbolBrush=self.indicators_brush_invalid_3,
                                                   symbolPen=self.indicators_pen)
                self.indicators_graph_item.show()
    # </editor-fold>

    # </editor-fold>

    def keyPressEvent(self, event):
        key = event.key()

        if key == QtCore.Qt.Key_J:
            if self.is_frozen:
                self.is_frozen = False
            else:
                self.is_frozen = True

        # temporary
        if not event.isAutoRepeat():
            if key == QtCore.Qt.Key_M:
                print "gaze thread started"
                self.thread_start_gaze_tracker()

        # TODO FREEZE
        if key == QtCore.Qt.Key_P:
            print "freeze"

        # TODO CAPTURE
        if key == QtCore.Qt.Key_O:
            print "capture"

        # TODO CALIBRATE
        if key == QtCore.Qt.Key_G:
            print "calibrate"

        if key == QtCore.Qt.Key_Z:
            print "increase depth"
            self.param_controller.increase_depth()

        if key == QtCore.Qt.Key_X:
            print "decrease depth"
            self.param_controller.decrease_depth()

        if key == QtCore.Qt.Key_C:
            print "increase focus depth"
            self.param_controller.increase_focus_depth()

        if key == QtCore.Qt.Key_V:
            print "decrease focus depth"
            self.param_controller.decrease_focus_depth()

        if self.system_state == SystemState.FULLSCALE:

            # ZOOM IN
            if key == QtCore.Qt.Key_A:
                print "zoom in"
                self.zoom_in()
                self.system_state = SystemState.ZOOM_A
                self.extra_label_item.setText(self.system_state)

            # GO TO PRE-ZOOM
            if key == QtCore.Qt.Key_W:
                print "go to pre-zoom"
                self.go_to_pre_zoom()
                self.system_state = SystemState.PRE_ZOOM_A
                self.extra_label_item.setText(self.system_state)

        elif self.system_state == SystemState.PRE_ZOOM_A or self.system_state == SystemState.PRE_ZOOM_B:

            # TOGGLE
            if key == QtCore.Qt.Key_S:
                print "toggle"
                if self.system_state == SystemState.PRE_ZOOM_A:
                    self.system_state = SystemState.PRE_ZOOM_B
                elif self.system_state == SystemState.PRE_ZOOM_B:
                    self.system_state = SystemState.PRE_ZOOM_A

                self.extra_label_item.setText(self.system_state)

            # CONFIRM ZOOM
            if key == QtCore.Qt.Key_W:
                print "confirm zoom"
                self.zoom_in_to_roi()
                self.system_state = SystemState.ZOOM_A
                self.extra_label_item.setText(self.system_state)
                self.roi.hide()
                self.context_roi.show()

        elif self.system_state == SystemState.ZOOM_A or self.system_state == SystemState.ZOOM_B:

            # TOGGLE
            if key == QtCore.Qt.Key_S:
                print "toggle"
                if self.system_state == SystemState.ZOOM_A:
                    self.system_state = SystemState.ZOOM_B
                elif self.system_state == SystemState.ZOOM_B:
                    self.system_state = SystemState.ZOOM_A
                self.extra_label_item.setText(self.system_state)

            # RESET ZOOM
            if key == QtCore.Qt.Key_W:
                print "reset zoom"
                self.reset_zoom()
                self.reset_roi()
                self.set_view_to_roi_and_pad()

                # TODO fix this the right way
                self.padding_view_box.removeItem(self.left_padding)
                self.padding_view_box.removeItem(self.right_padding)
                self.padding_view_box.removeItem(self.top_padding)
                self.padding_view_box.removeItem(self.bottom_padding)

                self.system_state = SystemState.FULLSCALE
                self.extra_label_item.setText(self.system_state)

            # ZOOM OUT
            if key == QtCore.Qt.Key_D:
                print "zoom out"
                self.zoom_out()
                if self.roi.size().x() == self.image_width and self.roi.size().y() == self.image_height:
                    self.system_state = SystemState.FULLSCALE
                    self.extra_label_item.setText(self.system_state)

            # ZOOM IN
            if key == QtCore.Qt.Key_A:
                print "zoom in"
                self.zoom_in()


if __name__ == "__main__":
    import sys

    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Traditional Magnification Interface')

    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()

    # TODO replace these values with global values
    main = Traditional('127.0.0.1', 250, 100, width, height)
    main.show()

    sys.exit(app.exec_())
