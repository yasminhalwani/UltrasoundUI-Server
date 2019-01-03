from INTERFACE_traditional import Traditional
from pyqtgraph.Qt import QtCore, QtGui
from VALUES_main import *
import pyqtgraph as pg
import win32gui
import time


class Dual(Traditional):
    def __init__(self, sonix_address, sonix_timeout, sonix_fail_max_count,
                 screen_width_input, screen_height_input):
        # TODO replace these values with global values
        super(Dual, self).__init__('127.0.0.1', 250, 100, screen_width_input, screen_height_input)

        self.filter_pog = FILTER_POG

        self.pb_held_monitor_timer_thread = None

        self.thread_start_pb_held_monitor()

    def thread_start_pb_held_monitor(self):
        self.pb_held_monitor_timer_thread = QtCore.QTimer()
        self.pb_held_monitor_timer_thread.start(.1)
        self.connect(self.pb_held_monitor_timer_thread, QtCore.SIGNAL('timeout()'), self.callback_pb_held_monitor)

    def callback_pb_held_monitor(self):
        self.pb_press_elapsed_time = time.time() - self.pb_press_start_time

        if self.pb_pressed:
            if self.pb_press_elapsed_time > 0.5:
                self.pb_held = True
        else:
            self.pb_press_start_time = 0

        if self.pb_held:
            if self.system_state == SystemState.ZOOM_A or self.system_state == SystemState.ZOOM_B:
                self.gaze_tracker_thread.set_use_filtering(False)
                self.auto_pan()

            elif self.system_state == SystemState.PRE_ZOOM_A or self.system_state == SystemState.PRE_ZOOM_B:
                self.gaze_tracker_thread.set_use_filtering(True)
                self.set_roi_in_center_of_pog()

    def set_roi_in_center_of_pog(self):
        pos = self.image_view_box.mapSceneToView(self.POG)

        x = pos.x()
        y = pos.y()

        pos_check = self.image_view_box.mapFromViewToItem(self.image_item, pos)

        if pos_check.x() - self.roi.size().x() / 2 < 0:
            x = self.roi.size().x() / 2

        if pos_check.x() + self.roi.size().x() / 2 > self.image_width:
            x = self.image_width - self.roi.size().x() / 2

        if pos_check.y() + self.roi.size().y() / 2 > self.image_height:
            y = self.image_height - self.roi.size().y() / 2

        if pos_check.y() - self.roi.size().y() / 2 < 0:
            y = self.roi.size().y() / 2

        self.set_roi_position_in_the_center_of(x, y)

    def define_pan_areas(self):
        image_rect = self.image_layout_widget.contentsRect()

        #  TODO check this logic
        # x = image_rect.x()
        # y = image_rect.y()
        # region_width = image_rect.width()
        # region_height = image_rect.height()
        #
        # padding_type = PaddingType.NONE
        # padding_width = 0
        # padding_height = 0
        # padding_type, padding_width, padding_height = self.check_for_padding_requirement()
        #
        # if padding_type == PaddingType.LEFT_RIGHT:
        #     x += padding_width
        #     region_width -= padding_width*2
        #
        # elif padding_type == PaddingType.UP_DOWN:
        #     y += padding_height
        #     region_height -= padding_height*2
        #
        # image_rect = QtCore.QRect(x, y, region_width, region_height)

        x1 = image_rect.x()
        x2 = image_rect.x() + image_rect.width() * 0.25
        x3 = image_rect.x() + image_rect.width() * 0.75
        y1 = image_rect.y()
        y2 = image_rect.y() + image_rect.height() * 0.25
        y3 = image_rect.y() + image_rect.height() * 0.75
        w25 = image_rect.width() * 0.25
        w50 = image_rect.width() * 0.50
        h25 = image_rect.height() * 0.25
        h50 = image_rect.height() * 0.50

        self.upper_left_rect = QtCore.QRect(x1, y1, w25, h25)
        self.upper_rect = QtCore.QRect(x2, y1, w50, h25)
        self.upper_right_rect = QtCore.QRect(x3, y1, w25, h25)
        self.left_rect = QtCore.QRect(x1, y2, w25, h50)
        self.lower_left_rect = QtCore.QRect(x1, y3, w25, h25)
        self.lower_rect = QtCore.QRect(x2, y3, w50, h25)
        self.lower_right_rect = QtCore.QRect(x3, y3, w25, h25)
        self.right_rect = QtCore.QRect(x3, y2, w25, h50)

    def locate_panning_direction(self, pos):
        pos = self.image_view_box.mapFromScene(pos.x(), pos.y())
        pos = QtCore.QPoint(pos.x(), pos.y())

        if self.upper_left_rect.contains(pos):
            return Direction.UPPER_LEFT

        elif self.upper_rect.contains(pos):
            return Direction.UP

        elif self.upper_right_rect.contains(pos):
            return Direction.UPPER_RIGHT

        elif self.left_rect.contains(pos):
            return Direction.LEFT

        elif self.right_rect.contains(pos):
            return Direction.RIGHT

        elif self.lower_left_rect.contains(pos):
            return Direction.LEFT

        elif self.lower_rect.contains(pos):
            return Direction.DOWN

        elif self.lower_right_rect.contains(pos):
            return Direction.LOWER_RIGHT

    def auto_pan(self):
        self.define_pan_areas()
        pos = self.POG
        direction = self.locate_panning_direction(QtCore.QPoint(pos.x(), pos.y()))
        self.translate_roi(direction, ROI_TRANSLATION_SCALE)
        self.set_view_to_roi_and_pad()

    def calculate_focus_rectangles(self):

        # get depth value
        depth_val = None
        int_val = pyUlterius.IntByRef()
        if self.ultrasound.getParamValue('b-depth', int_val.access_ref()):
            depth_val = float(int_val.get()) / 10.0
            print depth_val
        else:
            print "Unable to retrieve depth value. Cannot calculate focus areas."
            return

        self.num_focus_areas = int(5 + (2 * abs((2-depth_val) * 2)))

        area_height = self.image_height/self.num_focus_areas

        self.focus_rect = []
        self.focus_roi = []

        for num in range(1, self.num_focus_areas):
            rect = QtCore.QRect(0, 0 + (area_height*(num-1)), self.image_width, area_height)
            self.focus_rect.append(rect)

            roi = pg.RectROI([rect.x(), rect.y()], [rect.width(), rect.height()], movable=False,
                              maxBounds=QtCore.QRectF(0, 0, self.image_width, self.image_height))

            self.focus_roi.append(roi)
            self.image_view_box.addItem(roi)

        for item in self.focus_roi:
            item.hide()

        print self.focus_rect

    def find_which_focus_rectangle_gazepoint_falls_in(self):

        gazepoint = QtCore.QPoint(self.POG.x(), self.POG.y())
        num_of_focus_rectangles = len(self.focus_rect)

        for index in range(1, num_of_focus_rectangles):
            if (self.focus_rect[index].contains(gazepoint)):
                # print str(index)
                self.gazepoint_intersect_focus_rect_number = index
                break

    def keyPressEvent(self, event):
        key = event.key()

        if key == QtCore.Qt.Key_J:
            self.calculate_focus_rectangles()

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

        if self.system_state == SystemState.FULLSCALE:

            # ZOOM IN
            if key == QtCore.Qt.Key_A:
                print "zoom in"
                self.set_roi_in_center_of_pog()  # TODO do this step only if gaze data is being streamed, otherwise, set roi to center
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
                self.set_roi_in_center_of_pog()  # TODO do this step only if gaze data is being streamed, otherwise, set roi to center
                self.zoom_in()


if __name__ == "__main__":
    import sys

    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Dual Magnification Interface')

    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()

    main = Dual('127.0.0.1', 250, 100, width, height)
    main.show()

    sys.exit(app.exec_())
