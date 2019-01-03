# <editor-fold desc="states and options classes">


class SystemState:
    def __init__(self):
        pass

    FULLSCALE = "FullScale"
    PRE_ZOOM_A = "Pre Zoom A"
    PRE_ZOOM_B = "Pre Zoom B"
    ZOOM_A = "Zoom A"
    ZOOM_B = "Zoom B"


class Interface:
    def __init__(self):
        pass

    TRADITIONAL = 1
    GAZE_BASED = 2
    DUAL = 3


class ImageState:
    def __init__(self):
        pass

    ORIGINAL = 1
    ZOOMED = 2


class EyeTrackerState:
    def __init__(self):
        pass

    DISCONNECTED = 1
    PENDING = 2
    UNDETECTED = 3
    DETECTED = 4


class Direction:
    def __init__(self):
        pass

    NONE = 0
    UP = 1
    DOWN = 2
    RIGHT = 3
    LEFT = 4
    UPPER_LEFT = 5
    UPPER_RIGHT = 6
    LOWER_LEFT = 7
    LOWER_RIGHT = 8



class POGValidity:
    def __init__(self):
        pass

    VALID = 1
    INVALID_SHORT = 2
    INVALID_INTERMEDIATE = 3
    INVALID_LONG = 4


class ROIState:
    def __init__(self):
        pass

    NONE = 1
    VISIBLE = 2
    INVISIBLE = 3
    RESIZING = 4
    MOVING = 5
    HELD = 6


class PaddingType:
    def __init__(self):
        pass

    NONE = 1
    LEFT_RIGHT = 2
    UP_DOWN = 3
    INVALID = 4


class HwInterface:
    def __init__(self):
        pass

    ZOOM_CW = "ZOOM_CLOCKWISE"
    ZOOM_CCW = "ZOOM_COUNTER"
    ZOOM_PRESS = "ZOOM_PRESS"

    DEPTH_CW = "DEPTH_CLOCKWISE"
    DEPTH_CCW = "DEPTH_COUNTER"

    FOCUS_CW = "FOCUS_CLOCKWISE"
    FOCUS_CCW = "FOCUS_COUNTER"
    FOCUS_PRESS = "FOCUS_PRESS"

    PB_PRESS = "PB_PRESS"
    FREEZE_PRESS = "FREEZE_PRESS"
    CAPTURE_PRESS = "CAPTURE_PRESS"

    CALIBRATE_PRESS = "CALIBRATE_PRESS"


class UltrasoundCommunicationType:
    def __init__(self):
        pass

    LOCAL = 1
    REMOTE = 2

# </editor-fold>


# <editor-fold desc="constants">
TRANSLATION_PX = 5
RESIZE_PX = 5
ZOOM_RATIO = 0.9
DEFAULT_ROI_SIDE_LENGTH = 200
MIN_ROI_SIDE_LENGTH = 50
MAX_ROI_SIDE_LENGTH = 500
ACTIVE_SPOTS_SIZE_RATIO = 0.2
ACTIVE_BUTTON_SIDE_LENGTH = 40
ARDUINO_INTERFACE = 'COM8'
FILTER_POG = False
ROI_TRANSLATION_SCALE = 3

TCP_COMMANDS_PORT = 8089
TCP_IMAGE_STREAMING_PORT = 10000
SERIALIZED_IMAGE_SIZE = 5024000

RECEIVED_IMAGE_WIDTH = 800
RECEIVED_IMAGE_HEIGHT = 600

ULTRASOUND_COMMUNICATION_TYPE = UltrasoundCommunicationType.REMOTE
ULTRASONIX_ADDRESS = "192.168.0.1"
SONIX_TIMEOUT = 250
SONIX_FAIL_MAX_COUNT = 100
# </editor-fold>


# <editor-fold desc="global variables">
class GlobalVariables:
    def __init__(self):
        pass

# </editor-fold>
