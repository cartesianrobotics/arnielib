import serial
import time
import re
import logging
import sys


"""
Low level communication library with a device connected through serial port.

Part of ArnieLib.

Sergii Pochekailov
"""

# Those are parameters for serial connection. 
# Used when opening serial port.
BAUDRATE = 115200
TIMEOUT = 0.1   # seconds
END_OF_LINE = "\r"

# This is the time to wait for the welcome message to be send by a newly initialized device.
WELCOME_MESSAGE_DELAY = 2   # seconds

# This is the default time to wait for any message to be send by a device.
# No effect when using readBufferUntilMatch(), or writeAndWait().
READALL_DELAY = 0.1 # secodns


class serial_device():
    """
    Parent class, handling basic communication with a device, 
    be it an Arnie robot, or a tool or anything else
    """
    
    def __init__(self, port_name, welcome_message="", welcome_message_delay=WELCOME_MESSAGE_DELAY, baudrate=BAUDRATE, timeout=TIMEOUT, eol=END_OF_LINE):
        
        """
        Initializes a devise to communicate through the serial port
        (which is now most likely a USB emulation of a serial port)
        
        Inputs:
            port_name 
                The name of the port through which a robot or a tool is going to communicate.
            welcome_message
                Each device upon initialization is likely to send some first message, usually
                containing name of the device connected. This message is called "welcome message".
                This variable is used to confirm that the actual device connected is what we think is connected.
                Currently unused.
            welcome_message_delay
                Time in seconds to wait for the device to send a welcome message.
                Default is 1 second.
                If time is too short, the welcome message may not fully appear, causing 
                the program to return an error during initialization.
            baudrate
                Speed of communication. For USB 115200 is good. Lower if communication becomes bad.
            timeout
                How long to wait (in seconds) for a device to respond before returning an error
                0.1 seconds is default.
            eol
                character to pass at the end of a line when sending something to the device.
                Default is '\r'
        """
        
        self.port_name = port_name
        logging.info("Port %s: Initialization of a device started.", self.port_name)
        logging.info("Port %s: Expected welcome message:  %s", self.port_name, welcome_message)
        self.eol=eol # Keeps End Of Line that the device expects to receive
        self.recent_message = "" # This variable contains the latest stuff received from the device
        
        # This is the stub of the dictionary containing device properties
        self.description = {"class": serial_device, 
            "message": welcome_message, 
            "type": "", 
            "mobile": False,
        }

        self.baudrate = baudrate
        self.timeout = timeout

        self.openSerialPort(port_name, baudrate, timeout)
        
        # Reading welcome message from the device connected
        logging.info("Port %s: Welcome message received:", self.port_name)
        self.actual_welcome_message = self.readAll(delay=welcome_message_delay)
        # Cleaning input buffer from some extra messages
        self.port.flushInput()

    
    def openSerialPort(self, port_name="", baudrate=BAUDRATE, timeout=TIMEOUT):
        """
        Opens serial port
        """
        # Trying to use specifically provided port_name
        # Otherwise using whatever internal number instance may already have.
        if port_name != "":
            com_port = port_name
            self.port_name = port_name
        else:
            com_port = self.port_name
        # Make sure port is closed
        self.close()
        # Opening robot instance
        self.port = serial.Serial(com_port, baudrate, timeout=timeout)
        logging.info("Port %s: Opened.", self.port_name)
        logging.info("Port %s: baudrate=%s.", self.port_name, baudrate)
        logging.info("Port %s: timeout=%s.", self.port_name, timeout)
        
        
    def close(self):
        """
        Will try to close Arnie port if it is open
        """
        try:
            self.port.close()
            logging.info("Port %s: Closed successfully", self.port_name)
        except:
            logging.info("Port %s: Attempted to close, unsuccessfully", self.port_name)

    
    def findDeviceInList(self, names_list):
        """
        Compares provided names_list with the welcome message, returns 
        list index for the right name.
            Inputs:
                names_list
                    Contains list of welcome messages, or fractions of them, to be
                    compared to the actual welcome message received from the device.
                    One of the name should match fully or partially the welcome message
                    of currently connected device
                    
            Returns:
                right_index
                    Index of a welcome message in names_list, that was matched to
                    the actual welcome message obtained from the device.
                    If nothing was matched, returns None.
        """
        right_index = None
        for name in names_list:
            if self.isWelcomeMessageMatches(name):
                right_index = names_list.index(name)
        return right_index
    
    
    def isWelcomeMessageMatches(self, expected_welcome_message):
        """
        Compares welcome message returned from the device,
        with the expected_welcome_message provided by a user.
        
        Returns True if match found.
        """
        matched = False
        if re.search(pattern=expected_welcome_message, string=self.actual_welcome_message):
            matched = True
            logging.info("Port %s: Successfully matched pattern", self.port_name)
            logging.info(expected_welcome_message)
            logging.info("To the welcome message: ")
            logging.info(self.actual_welcome_message)
        
        return matched
    
    def write(self, expression, eol=None):
        """
        Sending an expression to a device. Expression is in str format.
        Proper end of line will be sent. If eol specified here, it will be sent
        Otherwise the one specified during initialization will be sent.
        """
        # Cleaning input buffer (so the buffer will contain only response of a device 
        # to the command send within this function)
        self.port.flushInput()
        # Strip all EOL characters for consistency
        expression = expression.strip()
        if eol:
            eol_to_send = eol
        else:
            eol_to_send = self.eol
        # Add end of line
        expression = expression + eol_to_send
        # Encode to binary
        expr_enc = expression.encode()
        
        logging.info("Port %s: Sending message: ", self.port_name)
        logging.info(expression)
        # Writing to the device (robot or a tool)
        self.port.write(expr_enc)
        
        
    # TODO: Inline this function so that people don't circumvent logging by using this function. 
    def _read(self, number_of_bytes=1):
        """
        Same functionality as Serial.read()
        """
        return self.port.read(number_of_bytes).decode("utf-8")
    
    def readAll(self, delay=READALL_DELAY):
        """
        Function will wait until everything that the device send is read
        """
        # Give time for device to respond
        time.sleep(delay)
        # Wait forever for device to return something
        message=self._read()
        # Continue reading until device output buffer is empty
        while self.port.inWaiting():
            message += self._read()
        
        logging.info("Port %s: Function readAll(): Received message: ", self.port_name)
        logging.info(message)
        return message
    
    def readBufferUntilMatch(self, pattern):
        """
        This function will monitor serial port buffer, until the "pattern" occurs.
        
        Inputs:
            - pattern - any string; put something that is expected to return from serial port
            
        Returns:
            Everything which was read from the buffer before the pattern occurred, including the pattern.
        """
        
        full_message = ""
        while True:
            message = self.port.readline().decode("utf-8")
            full_message += message
            if re.search(pattern=pattern, string=full_message):
                self.recent_message = full_message
                break
        logging.info("Port %s: Function readBufferUntilMatch(): Received message: ", self.port_name)
        logging.info(full_message)
        logging.info("It was successfully matched with pattern %s", pattern)
        return full_message

    # TODO: Rename this into "write", and rename "write"into "write_ignore_response".
    def writeAndWait(self, expression, eol=None, confirm_message='ok\n'):
        """
        Function will write an expression to the device and wait for the proper response.
        
        Use this function to make the devise perform a physical operation and
        make sure program continues after the operation is physically completed.
        
        Function will return an output message
        """
        self.write(expression, eol)
        self.recent_message = self.readBufferUntilMatch(pattern=confirm_message)
        return self.recent_message



def listSerialPorts():
    """ 
    Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result
    
    
def matchPortsWithDevices(ports_list, device_matchline_dict):
    """
    Matches port number with a device name for that port.
    
    Inputs:
        ports_list
            List of the serial ports present in the system
            Example: ['COM3', 'COM4', ...]
        device_matchline_dict
            Dictionary matching device name with the pattern that occurrs in its welcome message
            Example: {'Arnie': 'Marlin', 'Pipettor_1000': 'Servo', ...}
    
    Returns:
        device_port_dict
            Dictionary matching device name with the com port name
            Example: {'Arnie': 'COM4', 'Pipettor_1000': 'COM3', ...}
    """
    
    patterns_list = list(device_matchline_dict.values())
    device_port_dict = {}
    
    for port in ports_list:
        s = serial_device(port)
        # Finds index of a proper pattern, then calls that pattern out of pattern_list
        # When serial_device is something that is not in patterns_list, 
        # s.findDeviceInList will return None. Current device is ignored, and 
        # function continues to the next device.
        try:    
            correct_pattern = patterns_list[s.findDeviceInList(patterns_list)]
        except:
            logging.error("matchPortsWithDevices(): could not execute finiding device in list.")
            logging.error("matchPortsWithDevices(): Provided patterns_list: %s", patterns_list)
            logging.error(s.findDeviceInList(patterns_list))
            # Assigning blank value, so later correct_pattern won't pass check on expected value.
            correct_pattern = ""
            #return
        for key, value in device_matchline_dict.items():
            if correct_pattern == value:
                device_port_dict[key] = port
        # Closing port after matching.
        s.close()
                
    return device_port_dict