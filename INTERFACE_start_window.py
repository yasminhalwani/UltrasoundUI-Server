import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import *

from VALUES_main import ZoomMethod, MoveMethod, ResizeMethod, GlobalVariables
from zoom_base import ZoomBase

class OptionsMenu(QtGui.QMainWindow):
    def __init__(self, screen_width_input, screen_height_input):
        super(OptionsMenu, self).__init__()

        self.resize(1000, 500)
        self.setWindowTitle('Multimodal Eye Gaze-supported Zoom Interface')

        area = DockArea()
        self.setCentralWidget(area)
        d1 = Dock("Select", size=(1, 1))
        d1.hideTitleBar()
        area.addDock(d1, 'left')

        layout = pg.LayoutWidget()

        # ----------------------- ZOOM -------------------

        label = QtGui.QLabel("Select a zoom method:")
        layout.addWidget(label, row=0, col=0)

        zoom_method_group = QtGui.QButtonGroup(layout)

        method_simz_button = QtGui.QRadioButton("SimZ")
        zoom_method_group.addButton(method_simz_button)

        method_resz_button = QtGui.QRadioButton("ResZ")
        zoom_method_group.addButton(method_resz_button)

        method_comz_button = QtGui.QRadioButton("ComZ")
        zoom_method_group.addButton(method_comz_button)

        layout.addWidget(method_simz_button, row=1, col=0)
        layout.addWidget(method_resz_button, row=1, col=1)
        layout.addWidget(method_comz_button, row=1, col=2)

        method_simz_button.toggled.connect(self.simz)
        method_resz_button.toggled.connect(self.resz)
        method_comz_button.toggled.connect(self.comz)

        # ----------------------- SEPARATOR 1 ------------

        separator1 = QtGui.QLabel("##########################################")
        layout.addWidget(separator1, row=2, col=2)

        # ----------------------- MOVE -------------------

        label = QtGui.QLabel("Select a ROI move method:")
        layout.addWidget(label, row=3, col=2)

        move_method_group = QtGui.QButtonGroup(layout)

        self.move_pog_latched_button = QtGui.QRadioButton("POG-Latched")
        move_method_group.addButton(self.move_pog_latched_button)

        self.move_active_spots_v_button = QtGui.QRadioButton("Visual Active Spots")
        move_method_group.addButton(self.move_active_spots_v_button)

        self.move_active_spots_no_v_button = QtGui.QRadioButton("Non-visual Active Spots")
        move_method_group.addButton(self.move_active_spots_no_v_button)

        self.move_gradual_active_spots_button = QtGui.QRadioButton("Non-visual Gradual Active Spots")
        move_method_group.addButton(self.move_gradual_active_spots_button)

        layout.addWidget(self.move_pog_latched_button, row=3, col=3)
        layout.addWidget(self.move_active_spots_v_button, row=4, col=3)
        layout.addWidget(self.move_active_spots_no_v_button, row=5, col=3)
        layout.addWidget(self.move_gradual_active_spots_button, row=6, col=3)

        self.move_pog_latched_button.toggled.connect(self.move_pog)
        self.move_active_spots_v_button.toggled.connect(self.move_active_spots_v)
        self.move_active_spots_no_v_button.toggled.connect(self.move_active_spots_no_v)
        self.move_gradual_active_spots_button.toggled.connect(self.move_gradual_spots)

        # ----------------------- SEPARATOR 2 ------------

        separator2 = QtGui.QLabel("##########################################")
        layout.addWidget(separator2, row=7, col=2)

        # ----------------------- RESIZE -----------------

        label = QtGui.QLabel("Select a ROI resize method:")
        layout.addWidget(label, row=8, col=2)

        resize_method_group = QtGui.QButtonGroup(layout)

        self.resize_trackball_button = QtGui.QRadioButton("Trackball")
        resize_method_group.addButton(self.resize_trackball_button)

        self.resize_active_spots_v_button = QtGui.QRadioButton("Visual Active Spots")
        resize_method_group.addButton(self.resize_active_spots_v_button)

        self.resize_active_spots_no_v_button = QtGui.QRadioButton("Non-visual Active Spots")
        resize_method_group.addButton(self.resize_active_spots_no_v_button)

        self.resize_active_buttons_button = QtGui.QRadioButton("Active Buttons")
        resize_method_group.addButton(self.resize_active_buttons_button)

        layout.addWidget(self.resize_trackball_button, row=8, col=3)
        layout.addWidget(self.resize_active_spots_v_button, row=9, col=3)
        layout.addWidget(self.resize_active_spots_no_v_button, row=10, col=3)
        layout.addWidget(self.resize_active_buttons_button, row=11, col=3)

        self.resize_trackball_button.toggled.connect(self.resize_trackball)
        self.resize_active_spots_v_button.toggled.connect(self.resize_active_spots_v)
        self.resize_active_spots_no_v_button.toggled.connect(self.resize_active_spots_no_v)
        self.resize_active_buttons_button.toggled.connect(self.resize_active_buttons)

        # ----------------------- CONFIRM ----------------

        confirm_button = QtGui.QPushButton("Confirm")
        layout.addWidget(confirm_button, row=12, col=0)
        confirm_button.pressed.connect(self.confirm)

        self.set_comz_buttons_enabled(False)
        method_simz_button.setChecked(True)

        d1.addWidget(layout)

    def simz(self):
        self.set_comz_buttons_enabled(False)
        GlobalVariables.zoom_method = ZoomMethod.SIMZ

    def resz(self):
        self.set_comz_buttons_enabled(False)
        GlobalVariables.zoom_method = ZoomMethod.RESZ

    def comz(self):
        self.set_comz_buttons_enabled(True)
        GlobalVariables.zoom_method = ZoomMethod.COMZ

    def move_pog(self):
        GlobalVariables.move_method = MoveMethod.POG_LATCHED

    def move_active_spots_v(self):
        GlobalVariables.move_method = MoveMethod.ACTIVE_SPOTS_V

    def move_active_spots_no_v(self):
        GlobalVariables.move_method = MoveMethod.ACTIVE_SPOTS_NO_V

    def move_gradual_spots(self):
        GlobalVariables.move_method = MoveMethod.GRADUAL_ACTIVE_SPOTS

    def resize_trackball(self):
        GlobalVariables.resize_method = ResizeMethod.TRACKBALL

    def resize_active_spots_v(self):
        GlobalVariables.resize_method = ResizeMethod.ACTIVE_SPOTS_V

    def resize_active_spots_no_v(self):
        GlobalVariables.resize_method = ResizeMethod.ACTIVE_SPOTS_NO_V

    def resize_active_buttons(self):
        GlobalVariables.resize_method = ResizeMethod.ACTIVE_BUTTONS

    def set_comz_buttons_enabled(self, status):
        self.move_pog_latched_button.setEnabled(status)
        self.move_active_spots_v_button.setEnabled(status)
        self.move_active_spots_no_v_button.setEnabled(status)
        self.move_gradual_active_spots_button.setEnabled(status)

        self.resize_trackball_button.setEnabled(status)
        self.resize_active_spots_v_button.setEnabled(status)
        self.resize_active_spots_no_v_button.setEnabled(status)
        self.resize_active_buttons_button.setEnabled(status)

    def confirm(self):
        main = ZoomBase(width, height)
        main.exec_()

if __name__ == '__main__':
    import sys

    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Multimodal Eye Gaze-supported Zoom Options')

    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()

    options_menu_window = OptionsMenu(width, height)
    options_menu_window.show()

    sys.exit(app.exec_())
