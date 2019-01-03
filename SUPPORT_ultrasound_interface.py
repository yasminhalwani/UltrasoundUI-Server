from VALUES_main import *
from VALUES_ultrasound_comm_protocol import *
import socket
import numpy as np
from PIL import Image
import math

import pyUlterius
from SUPPORT_ultra_image_streamer import UltraImageStreamer
from SUPPORT_ultrasound_parameter_controller import UltraParamController


class UltrasoundInterface:
    def __init__(self, target_image_size):

        self.image = None
        self.image_width = None
        self.image_height = None
        self.image_diagonal = None

        if ULTRASOUND_COMMUNICATION_TYPE == UltrasoundCommunicationType.REMOTE:
            self.sonix_address = ULTRASONIX_ADDRESS
            self.tcp_commands_port = TCP_COMMANDS_PORT
            self.tcp_image_stream_port = TCP_IMAGE_STREAMING_PORT

            self.client_tcp_commands_socket = None
            self.client_tcp_images_socket = None
            self.tcp_commands_socket_last_received_data = None

            self.are_tcp_connections_established = False

            self.image_update_timer = 0
            self.previous_ultrasound_image = None
            self.received_image_data = None

            self.setup_tcp_connection()

        elif ULTRASOUND_COMMUNICATION_TYPE == UltrasoundCommunicationType.LOCAL:
            self.sonix_timeout = SONIX_TIMEOUT
            self.sonix_address = ULTRASONIX_ADDRESS
            self.sonix_fail_max_count = SONIX_FAIL_MAX_COUNT
            self.image_streamer = None
            self.ultrasound = None
            self.ultrasound_fail_count = 0
            self.param_controller = None
            self.size = target_image_size

            self.connect_to_ultrasound_machine()

    def connect_to_ultrasound_machine(self):
        self.ultrasound = pyUlterius.ulterius()
        self.param_controller = UltraParamController(self.ultrasound)
        self.ultrasound.setTimeout(self.sonix_timeout)
        # Check whether there is any previous connection
        if self.ultrasound.isConnected():
            if self.ultrasound.disconnect():
                print 'Successfully disconnected from Ultrasonix'
            else:
                print 'Error: Could not disconnect from Ultrasonix'

        # Connect to Sonix RP
        if not self.ultrasound.isConnected():
            if not self.ultrasound.connect(self.sonix_address):
                print 'Error: Could not connect to Ultrasonix'
            else:
                print 'Successfully connected to Ultrasonix'

        # Initialize ultrasound image acquisition thread
        self.image_streamer = UltraImageStreamer(self.size, self.ultrasound, 'b-mode', self.sonix_address,
                                                 self.sonix_fail_max_count)

        # create a new ultrasound acquisition thread
        self.image_streamer.start_image_acquisition()
        if self.ultrasound.isConnected():
            self.image_streamer.change_data_to_acquire('b-mode')

    def setup_tcp_connection(self):
        self.client_tcp_commands_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_tcp_commands_socket.connect((self.sonix_address, self.tcp_commands_port))

        self.client_tcp_commands_socket.send(CONNECT_TO_SERVER)
        self.tcp_commands_socket_last_received_data = self.client_tcp_commands_socket.recv(64)

        if self.tcp_commands_socket_last_received_data == ACK_CONNECT_TO_SERVER:
            self.client_tcp_commands_socket.send(CONNECT_TO_ULTRASONIX)
            self.tcp_commands_socket_last_received_data = self.client_tcp_commands_socket.recv(64)
            print "received: " + self.tcp_commands_socket_last_received_data

            if self.tcp_commands_socket_last_received_data == ACK_CONNECT_TO_ULTRASONIX:
                self.client_tcp_commands_socket.send(INITIALIZE_IMAGE_ACQUISITION)
                self.tcp_commands_socket_last_received_data = self.client_tcp_commands_socket.recv(64)
                print "received: " + self.tcp_commands_socket_last_received_data

                if self.tcp_commands_socket_last_received_data == ACK_INITIALIZE_IMAGE_ACQUISITION:
                    self.client_tcp_commands_socket.send(START_IMAGE_STREAMING)
                    self.tcp_commands_socket_last_received_data = self.client_tcp_commands_socket.recv(64)
                    print "received: " + self.tcp_commands_socket_last_received_data

                    if self.tcp_commands_socket_last_received_data == ACK_START_IMAGE_STREAMING:
                        self.client_tcp_images_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.client_tcp_images_socket.connect((self.sonix_address, self.tcp_image_stream_port))
                        self.client_tcp_images_socket.send(START_IMAGE_STREAMING)
                        self.are_tcp_connections_established = True

    def load_image(self):

        if ULTRASOUND_COMMUNICATION_TYPE == UltrasoundCommunicationType.REMOTE:
            return self.load_remote_image()

        elif ULTRASOUND_COMMUNICATION_TYPE == UltrasoundCommunicationType.LOCAL:
            return self.load_local_image()

    def load_local_image(self):
        arr = self.image_streamer.get_new_image_array()
        self.image = arr

        self.image = self.image.astype('float64')
        self.image = np.rot90(self.image)
        self.image = np.rot90(self.image)
        self.image = np.rot90(self.image)

        self.image_width = self.image.shape[0]
        self.image_height = self.image.shape[1]
        self.image_diagonal = math.sqrt((self.image_width ** 2 + self.image_height ** 2))

        return self.image, self.image_width, self.image_height, self.image_diagonal

    def load_remote_image(self):

        if self.are_tcp_connections_established:

            # We use a timer to limit how many images we request from the server each second:
            if self.image_update_timer < 1:

                try:
                    # Create a socket connection for connecting to the server:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((self.sonix_address, TCP_IMAGE_STREAMING_PORT))

                    # Receive data from the server:
                    self.received_image_data = client_socket.recv(SERIALIZED_IMAGE_SIZE)

                    # Set the timer back to 30:
                    self.image_update_timer = 1
                except:
                    print "could not connect to server"
                    self.are_tcp_connections_established = False

            else:

                # Count down the timer:
                self.image_update_timer -= 1

            # We store the previous received image in case the client fails to
            # receive all of the data for the new image:
            self.previous_ultrasound_image = self.image

            # We use a try clause to the program will not abort if there is an error:
            try:

                # We turn the data we received into a 120x90 PIL image:
                self.image = Image.fromstring("RGB", (RECEIVED_IMAGE_WIDTH, RECEIVED_IMAGE_HEIGHT),
                                              self.received_image_data)

                # We resize the image to 640x480:
                self.image = self.image.resize((RECEIVED_IMAGE_WIDTH, RECEIVED_IMAGE_HEIGHT))

            except:
                # If we failed to receive a new image we display the last image we received:
                self.image = self.previous_ultrasound_image
        try:
            self.image = np.array(self.image)
            self.image = self.image.astype('float64')
            self.image = np.rot90(self.image)
            self.image = np.rot90(self.image)
            self.image = np.rot90(self.image)

            self.image_width = self.image.shape[0]
            self.image_height = self.image.shape[1]
            self.image_diagonal = math.sqrt((self.image_width ** 2 + self.image_height ** 2))

        except:
            pass

        return self.image, self.image_width, self.image_height, self.image_diagonal
