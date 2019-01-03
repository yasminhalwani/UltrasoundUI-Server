__author__ = 'Yasmin'
# Developed by Yasmin Halwani for MASc Thesis Project [2015 - 2016]
# Robotics and Control Laboratory | Electrical and Computer Engineering 
# University of British Columbia

# PYTHON SCRIPT DESCRIPTION #
"""
    This script is responsible for acquiring the ultrasound image based on the required imaging mode

    This script runs with ultrasound_controller.py
"""


# IMPORTS #
# -- Standard library
import Queue
import threading
import numpy as np

# -- Third party
from PIL import Image
import pyUlterius

# GLOBAL VARIABLES #
DEBUG = False


# CLASSES #
class UltraImageStreamer(object):
    """Streams the image from the ultrasound machine

        Attributes:
        size: a tuple containing the width and height of the window

        ultrasound: an instance of pyUlterius, which serves as a high-level python wrapper of Ulterius SDK

        imaging_mode: the imaging mode to be displayed

        sonix_address: the IP address of the ultrasound machine to be connected to

        sonix_fail_max_count: maximum number of allowed dropped frames

        frame: an instance of FrameData - which describes basic properties of a frame

        is_callback_allowed: a flag to indicate whether or not to execute the image thread callback method

        us_fail_count: a counter of dropped image frames

        image_thread: the image thread - a daemon thread that shuts down as soon as the parent thread exits

        img_queue: the image queue

        raw_queue: the raw queue obtained, before conversion to an image

    """
    # TODO check that all local attributes are described in the comment above


    def __init__(self, ultrasound, initial_imaging_mode, sonix_address, sonix_fail_max_count):
        """Inits UltraImageStreamer with an instance of pyUlterius, the initial imaging mode,
        the ultrasound machine IP address, and the maximum number of allowed dropped frames."""

        self.ultrasound = ultrasound
        self.imaging_mode = initial_imaging_mode
        self.sonix_address = sonix_address
        self.sonix_fail_max_count = sonix_fail_max_count


        if self.imaging_mode == 'b-mode':
            self.imaging_mode = pyUlterius.udtBPost
        elif self.imaging_mode == 'color-mode':
            self.imaging_mode = pyUlterius.udtColorCombined
        else:
            self.imaging_mode = pyUlterius.udtBPost

        self.frame = FrameData(None, 0, 0, False, 0)
        self.is_callback_allowed = False
        self.us_fail_count = 0

        self.image_thread = None

        self.img_queue = Queue.Queue(4)
        self.raw_queue = Queue.Queue(4)

        self.is_running = True
        self.is_image_stream_initialized = False
        self.image_data = None
        self.data_desc = pyUlterius.uDataDesc()

        self.set_data_to_acquire(self.imaging_mode)
        # self.change_data_to_acquire(self.imaging_mode)


    def start_image_acquisition(self):

        # print "UltraImageStream: start_image_acquisition()"

        if not self.is_image_stream_initialized:
            self.initialize_acquisition()

        if self.is_image_stream_initialized and self.image_thread is None:
            self.enable_callback()
            self.is_running = True
            self.empty_queue(self.raw_queue)
            self.image_thread = threading.Thread(target=self.get_image, args=(self.raw_queue, self.img_queue,))
            self.image_thread.daemon = True
            self.image_thread.start()

    def initialize_acquisition(self):

        # print "UltraImageStream: initialize_acquisition()"

        # Initialize image data acquisition
        if self.is_connected():
            self.initialize_callback(self.raw_queue)

            if not self.set_data_to_acquire(self.imaging_mode):
                print 'Error: set_data_to_acquire failed'
            else:
                self.is_image_stream_initialized = True

            if not self.retrieve_parameters(self.imaging_mode):
                print 'Error: retrieve_parameters failed'

    def get_image(self, raw_queue, img_queue):
        while self.is_running:
            pFrame = None

            try:
                pFrame = raw_queue.get(block=False, timeout=0)
            except Queue.Empty:
                continue

            while raw_queue.empty() == False:
                raw_queue.get()

            if pFrame is not None:
                if pFrame.datatype == pyUlterius.udtBPost:
                    # print "retreiving b mode images"
                    self.image_data = self.get_image_data(pFrame.data, pFrame.sz)
                    # print 'Data size:',len(image_data)

                    if self.image_data is not None:
                        img = Image.frombuffer("L", (self.data_desc.w, self.data_desc.h),
                                               self.image_data, "raw", "L", 0, 1)
                        img = img.convert("RGBX")
                        # img = img.resize((self.size[0], self.size[1]), Image.NEAREST)

                        try:

                            img_queue.put_nowait(img)
                        except Queue.Full:
                            img_queue.get_nowait()
                    else:
                        print 'Error acquiring BPost image data'

    def empty_queue(self, queue):

        # print "UltraImageStream: empty_queue()"

        while not queue.empty():
            try:
                queue.get(False)
            except Queue.Empty:
                continue
            queue.task_done()

    def change_data_to_acquire(self, mode):

        # print "UltraImageStream: change_data_to_acquire()"

        # if mode == PARAM_B_MODE:
        #     data_mode = pyUlterius.udtBPost
        # elif mode == PARAM_COLOR_MODE:
        #     data_mode = pyUlterius.udtColorCombined
        # else:
        #     data_mode = pyUlterius.udtBPost
        # TODO: might return this commented part

        if self.is_connected():
            if not self.set_data_to_acquire(mode):
                print 'Error: set_data_to_acquire failed'
                # if not self.retrieve_parameters(new_uData_type):
                #    print 'Error: retrieve_parameters failed'

                # if self.is_connected():
                #     self.set_data_to_acquire(pyUlterius.udtColorCombined)

    def enable_callback(self):
        # print "UltraImageStream: enable_callback()"
        self.is_callback_allowed = True

    def get_image_data(self, data, size):
        # print "UltraImageStream: get_image_data()"
        """
        Helper function to convert an image data type from PyCapsule to bytearray
        """
        temp = None
        try:
            temp = self.ultrasound.getImageData(data, size)
        except TypeError as e:
            print 'Error', e
        else:
            if temp is None:
                print 'Result is None'

        return temp

    def initialize_callback(self, raw_queue):
        # print "UltraImageStream: initialize_callback()"

        """
        Initialize callbacks for new frames and parameter monitoring
        """
        self.raw_queue = raw_queue
        self.is_callback_allowed = True

        self.ultrasound.set_pyCallback(self._callback)
        # self.ultrasound.set_pyParamCallback(self._paramCallback)
        print 'Ultrasound callback initialization completed'

    def is_connected(self): #TODO: remove this
        # print "UltraImageStream: is_connected()"
        return self.ultrasound.isConnected()

    def retrieve_parameters(self, mode):
        # print "UltraImageStream: retrieve_parameters()"
        success = False

        if mode == pyUlterius.udtRF:
            success = self.ultrasound.getDataDescriptor(pyUlterius.udtRF, self.data_desc)

        elif mode == pyUlterius.udtBPre:
            success = self.ultrasound.getDataDescriptor(pyUlterius.udtBPre, self.data_desc)

        elif mode == pyUlterius.udtBPost:
            success = self.ultrasound.getDataDescriptor(pyUlterius.udtBPost, self.data_desc)

        elif mode == pyUlterius.udtBPost32:
            success = self.ultrasound.getDataDescriptor(pyUlterius.udtBPost32, self.data_desc)

        elif mode == pyUlterius.udtColorCombined:
            success = self.ultrasound.getDataDescriptor(pyUlterius.udtColorCombined, self.data_desc)

        elif mode == pyUlterius.udtColorVelocityVariance:
            success = self.ultrasound.getDataDescriptor(pyUlterius.udtColorVelocityVariance, self.data_desc)

        elif mode == pyUlterius.udtPWSpectrum:
            success = self.ultrasound.getDataDescriptor(pyUlterius.udtPWSpectrum, self.data_desc)

        return success

    def set_data_to_acquire(self, data):
        # print "UltraImageStream: set_data_to_acquire()"

        # if data == PARAM_B_MODE:
        #     datatype = pyUlterius.udtBPost
        # elif data == PARAM_COLOR_MODE:
        #     datatype = pyUlterius.udtColorCombined
        # else:
        #     datatype = pyUlterius.udtBPost
        # TODO might return this commented part

        return self.ultrasound.setDataToAcquire(pyUlterius.udtBPost)

    def set_silent_callback(self):
        # print "UltraImageStream: set_silent_callback()"
        self.is_callback_allowed = False

    def _callback(self, data, datatype, sz, cine, frnum):
        # print "UltraImageStream: _callback()"
        """
        Callback used when new frames arrive or when the server has disconnected
        """
        if self.is_callback_allowed:
            # GUI needs ultrasound image to be displayed
            if data and sz:
                self.frame.data = data  # PyCapsule of a void*
                self.frame.datatype = datatype
                self.frame.sz = sz
                self.frame.cine = cine
                self.frame.frnum = frnum

                if self.raw_queue is not None:
                    try:
                        self.raw_queue.put_nowait(self.frame)
                    except Queue.Full:
                        self.raw_queue.get_nowait()
                else:
                    print 'Error: Queue for sending raw data has not been initialized'

                return True
            else:
                return False
        else:
            # GUI does not need the ultrasound image
            return False

    def _paramCallback(self, paramID, ptX, ptY):
        # print "UltraImageStream: _paramCallback()"
        """
        Callback used to monitor status of some parameters on the server side
        """
        # paramID is a PyCapsule of a void*
        print 'paramCallback invoked'
        return True

    def stop_image_acquisition(self):
        # print "UltraImageStream: stop_image_acquisition()"

        self.set_silent_callback()
        self.is_running = False
        if self.image_thread is not None:
            while self.image_thread.isAlive():
                pass
            try:
                self.image_thread.join(timeout=0.02)
            except RuntimeError:
                print 'Failed in joining image conversion thread'
            else:
                print 'Ultrasound image conversion thread joined successfully'
                self.image_thread = None

    def get_new_image_array(self):
        self.is_image_received = False

        while not self.is_image_received:
            try:
                q_img = self.img_queue.get_nowait()
                self.us_fail_count = 0
                # print "image received"
                self.is_image_received = True
            except Queue.Empty:
                # print "queue empty"
                q_img = None
                # Count how many consecutive frames have dropped
                if self.us_fail_count >= self.sonix_fail_max_count:
                    print 'No ultrasound image received'
                    self.us_fail_count = 0


        # Throw away unused frames
        while self.img_queue.empty() == False:
            self.img_queue.get_nowait()
        # while self.queue.empty() == False:
        #     self.queue.get_nowait()

        arr = np.array(q_img)

        return arr


class FrameData(object):
    def __init__(self, data, datatype, sz, cine, frnum):
        print "FrameData: __init__()"
        self.data = data  # PyCapsule of a void*
        self.datatype = datatype
        self.sz = sz
        self.cine = cine
        self.frnum = frnum
