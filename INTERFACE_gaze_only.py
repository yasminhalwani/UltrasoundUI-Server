from INTERFACE_dual import Dual
from pyqtgraph.Qt import QtCore, QtGui
from VALUES_main import *
import win32gui
import time

class GazeOnly(Dual):
    def __init__(self, sonix_address, sonix_timeout, sonix_fail_max_count,
                 screen_width_input, screen_height_input):
        # TODO replace these values with global values
        super(GazeOnly, self).__init__('127.0.0.1', 250, 100, screen_width_input, screen_height_input)

    def keyPressEvent(self, event):
        key = event.key()

        if key == QtCore.Qt.Key_J:
            pass

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
                self.system_state = SystemState.ZOOM_B
                self.extra_label_item.setText(self.system_state)

            # GO TO PRE-ZOOM
            if key == QtCore.Qt.Key_W:
                print "go to pre-zoom"
                self.go_to_pre_zoom()
                self.system_state = SystemState.PRE_ZOOM_B
                self.extra_label_item.setText(self.system_state)

        elif self.system_state == SystemState.PRE_ZOOM_B:

            # CONFIRM ZOOM
            if key == QtCore.Qt.Key_W:
                print "confirm zoom"
                self.zoom_in_to_roi()
                self.system_state = SystemState.ZOOM_B
                self.extra_label_item.setText(self.system_state)
                self.roi.hide()

        elif self.system_state == SystemState.ZOOM_B:

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
                if key == QtCore.Qt.Key_A:
                    print "zoom in"
                    # self.set_roi_in_center_of_pog()  # TODO do this step only if gaze data is being streamed, otherwise, set roi to center
                    # pos = self.image_view_box.mapSceneToView(self.POG)
                    # self.set_roi_position_in_the_center_of(pos.x(), pos.y())
                    # self.zoom_in()

                    self.set_roi_in_center_of_pog()  # TODO do this step only if gaze data is being streamed, otherwise, set roi to center
                    self.zoom_in()


if __name__ == "__main__":
    import sys

    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Gaze-Only Magnification Interface')

    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()

    main = GazeOnly('127.0.0.1', 250, 100, width, height)
    main.show()

    sys.exit(app.exec_())