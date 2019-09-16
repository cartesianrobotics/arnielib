"""
TODO:
1. Make commands interruptable.
2. Make a function for specifying tools. 
3. Save tools in a file. 
4. Make a function for swapping tools. 

"""

import serial
import time
import math
import re

import sys
import glob

robots = []

def serial_ports():
    """ Lists serial port names

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
	
class serial_device():
    """
    Parent class, handling basic communication with a device, 
    be it an Arnie robot, or a tool or something else
    """
    
    def __init__(self, port_name, baudrate=115200, timeout=0.1, eol="\r"):
        
        """
        Initializes a devise to communicate through the serial port
        (which is now most likely a USB emulation of a serial port)
        
        Inputs:
            port_name 
                The name of the port through which a robot or a tool is going to communicate.
            baudrate
                Speed of communication. For USB 115200 is good. Lower if communication becomes bad.
            timeout
                How long to wait (in seconds) for a device to respond before returning an error
                0.1 seconds is default.
            eol
                character to pass at the end of a line when sending something to the device.
                Default is '\r'
        """
        
        self.eol=eol

        self.openSerialPort(port_name, baudrate, timeout)
    
    
    def openSerialPort(self, port_name="", baudrate=115200, timeout=0.1):
        """
        Opens serial port
        """
        # Trying to use specifically provided port_name
        # Otherwise using whatever internal number instance may already have.
        if port_name != "":
            com_port = port_name
        else:
            com_port = self.port_name
        # Make sure port is closed
        self.close()
        # Opening robot instance
        self.port = serial.Serial(com_port, baudrate, timeout=timeout)
        # Cleaning input buffer from hello message
        self.port.flushInput()

        
    def close(self):
        """
        Will try to close Arnie port if it is open
        """
        if self in robots:
            robots.remove(self)
        
        try:
            self.port.close()
        except:
            pass
        
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
        
        # Writing to robot
        self.port.write(expr_enc)
        
        
    def read(self, number_of_bytes=1):
        """
        Same functionality as Serial.read()
        """
        return self.port.read(number_of_bytes).decode("utf-8")
    
    
    def readAll(self, timeout=0.1):
        """
        Function will wait until everything that the devise send is read
        """
        # Give time for device to respond
        time.sleep(timeout)
        # Wait forever for device to return something
        message=self.read()
        #message=''
        # Continue reading until device output buffer is empty
        while self.port.inWaiting():
            message += self.read()
        return message

    
    def waitUntilFinished(self, confirm_message='ok\n'):
        """
        Function will wait until confirm_message appears in the output buffer
        """
        full_message = ''
        while True:
            message_received = self.read()
            full_message += message_received
            if re.search(pattern=confirm_message, string=full_message):
                break
        return full_message
    
    
    def writeAndWait(self, expression, eol=None, confirm_message='ok\n'):
        """
        Function will write an expression to the device and wait for the proper response.
        
        Use this function to make the devise perform a physical operation and
        make sure program continues after the operation is physically completed.
        
        Function will return an output message
        """
        
        self.write(expression, eol)
        return self.waitUntilFinished(confirm_message)
		
class arnie(serial_device):
    
    def __init__(self, port_name, baudrate=115200, timeout=0.1, speed_x=20000, speed_y=20000, speed_z=15000):
        super().__init__(port_name, baudrate, timeout, eol="\r")
        
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.speed_z = speed_z		
        
    def home(self, axis='XYZ'):
        """
        Home one of the axis, X, Y or Z.
        Axis 
            axis to home
                x - home X axis
                y - home Y axis
                z - home Z axis
        """
        axis = axis.upper()
        if axis != 'X' and axis != 'Y' and axis != 'Z' and axis != 'XYZ':
            print ('Wrong axis specified. Please specify x, y or z. You specified: '+axis)
        elif axis == 'XYZ':
            self.writeAndWait('G28 Z')
            self.writeAndWait('G28 Y')
            self.writeAndWait('G28 X')
        else:
            self.writeAndWait('G28 '+axis)
    
    
    def _decideSpeed(self, axis, speed):
        if speed is None:
            if axis=='X':
                speed = self.speed_x
            elif axis=='Y':
                speed = self.speed_y
            else:
                speed = self.speed_z
        return speed
    
    
    def moveAxis(self, axis, coordinate, speed=None):
        
        axis=axis.upper()
        coordinate = str(coordinate)
        coord_cmd = axis + coordinate
        speed = self._decideSpeed(axis, speed)
        speed_cmd = 'F' + str(speed)
        full_cmd = 'G0 ' + coord_cmd + ' ' + speed_cmd
        
        try:
            self.writeAndWait(full_cmd)
        except:
            pass
        
        
    def moveXY(self, x, y, speed=None):
        speed = self._decideSpeed('X', speed)
        full_cmd = 'G0 X' + str(x) + ' Y' + str(y) + ' F' + str(speed)
        try:
            self.writeAndWait(full_cmd)
        except:
            pass
    
    
    def moveZ(self, z, speed=None):
        self.moveAxis('Z', z, speed)
    
    
    def move(self, x=None, y=None, z=None, z_first=True, speed_xy=None, speed_z=None):
        """
        Move robot to an absolute coordinates.
        
        Spefify z_first = True if you want Z to move first; otherwise x an y will move first.
        """
        speed_xy = self._decideSpeed('X', speed_xy)
        speed_z = self._decideSpeed('Z', speed_z)
        
        # Each of the functions attempting to move an axis to the coordinate. 
        # If something goes wrong, like coordinate not specified, command is ignored
        # and the next one is attempted.
        if z_first:
            if z is not None:
                self.moveZ(z, speed_z)
            if x is not None and y is not None:
                self.moveXY(x, y, speed_xy)
            elif x is not None and y is None:
                self.moveAxis('X', x, speed_xy)
            elif y is not None and x is None:
                self.moveAxis('Y', y, speed_xy)
        else:
            if x is not None and y is not None:
                self.moveXY(x, y, speed_xy)
            elif x is not None and y is None:
                self.moveAxis('X', x, speed_xy)
            elif y is not None and x is None:
                self.moveAxis('Y', y, speed_xy)
            if z is not None:
                self.moveZ(z, speed_z)
    
    def moveDelta(self, dx=None, dy=None, dz=None, z_first=True, speed_xy=None, speed_z=None):
        """
        Moves the robot arbitrarily to the current position
        """
        # Getting current absolute position
        x, y, z = self.getPosition()
        
        # Assigning zero movement to coordinates which are not provided
        if dx is None:
            dx = 0
        if dy is None:
            dy = 0
        if dz is None:
            dz = 0
            
        # Calculating new absolute position for Arnie
        new_x = x + dx
        new_y = y + dy
        new_z = z + dz
        
        # Moving Arnie
        self.move(new_x, new_y, new_z, z_first=z_first, speed_xy=speed_xy, speed_z=speed_z)
    
    def openTool(self):
        """Docker opens to accept a tool"""
        self.write('M280 P1 S10')
        time.sleep(1.5)
        
    def closeTool(self):
        """Docker closes, fixing a tool in place"""
        self.write('M280 P1 S80')
        time.sleep(1.5)
    
    def getPosition(self):
        msg = self.writeAndWait("M114")
        msg_list = re.split(pattern=' ', string=msg)
        x_str = msg_list[0]
        y_str = msg_list[1]
        z_str = msg_list[2]
        #print (x_str, y_str, z_str)
        x = float(re.split(pattern="\:", string=x_str)[1])
        y = float(re.split(pattern="\:", string=y_str)[1])
        z = float(re.split(pattern="\:", string=z_str)[1])
        return x, y, z
    
        
    def approachToolPosition(self, x, y, z, speed_xy=None, speed_z=None):
        """
        Moves robot to specified coordinates, where the tool is expected to be.
        Alternatively, moves robot WITH a tool to its empty slot
        Coordinates for both operations should be the same.
        Thif function will not engage docker, as one need to make sure the tool is at the right position
        """
        
        self.move(x, y, z, z_first=False, speed_xy=speed_xy, speed_z=speed_z)
    
    def approachToolAtSlot(self, tool_at_slot, speed_xy=None, speed_z=None):
        """
        Moves robot towards the tool, which object is passed in "tool_at_slot". 
        Same as "approachToolPosition", but using the object of tool_at_slot class
        """
        x, y, z = tool_at_slot.getCenterCoordinates()
        self.move(x, y, z, z_first=False, speed_xy=speed_xy, speed_z=speed_z)
    
    
    def getTool(self, tool, speed_xy=None, speed_z=None):
        """
        Engages with a tool, using tool instance for guidance
        """
        # Make sure docker is open
        self.openTool()
        x, y, z = tool.getToolCoordinates()
        self.approachToolPosition(x, y, z)
        
        # Attempting to initialize the tool
        attempt_successful = self.softInitToolAttempt(tool, total_attempts=2)
        if not attempt_successful:
            attempt_successful = self.hardInitToolAttempt(tool, total_attempts=3)
        if attempt_successful:
            # Locking tool
            self.closeTool()
            # Moving back up
            self.move(z=0, speed_z=speed_z)
        else:
            self.openTool()
            print("Failed to pickup tool. Program stopped.")
            
    
    def returnTool(self, tool=None, position_tuple=None, speed_xy=None, speed_z=None):
        """
        Returns tool back on its place.
        The place is provided either with tool instance, or simply as position_tuple (x, y, z)
        """
        if tool is not None:
            x, y, z = tool.getToolCoordinates()
        elif position_tuple is not None:
            x = position_tuple[0]
            y = position_tuple[1]
            z = position_tuple[2]
        else:
            print ("Must provide coordinates")
        
        self.home()
        try:
            self.move(x, y, z, z_first=False, speed_xy=speed_xy, speed_z=speed_z)
            self.openTool()
            self.home()
        except:
            pass
        

    def softInitToolAttempt(self, tool, total_attempts=4, wait_time=2, current_attempt=0):
        # Attempt to initialize tool several times without robot movement
        # Waiting before attempt, so electronics has time to connect
        time.sleep(wait_time)
        try:
            tool.openSerialPort()
            attempt_successful=1
        except:
            print("Tool initialization failed, attempting again")
            if total_attempts > current_attempt:
                attempt_successful=0
                current_attempt += 1
                attempt_successful = self.softInitToolAttempt(
                    tool=tool,
                    total_attempts=total_attempts, 
                    wait_time=wait_time, 
                    current_attempt=current_attempt)
            else:
                attempt_successful = 0
                print('Tool initialization failed after '+str(current_attempt)+' attempts')
        return attempt_successful
    
    
    def hardInitToolAttempt(self, tool, total_attempts=3, current_attempt=0):
        # Attempt to re-connect to the tool. 
        # To be used after failed initialization
        self.openTool()
        # Moving Arnie up and down for an attempt to physically reconnect
        self.moveDelta(dz=-300)
        self.moveDelta(dz=300)
        
        attempt_successful = self.softInitToolAttempt(tool, total_attempts=1)
        if not attempt_successful and total_attempts > current_attempt:
            current_attempt += 1
            attempt_successful = 0
            attempt_successful = self.hardInitToolAttempt(
                tool=tool, total_attempts=total_attempts, current_attempt=current_attempt)
        elif not attempt_successful and total_attempts <= current_attempt:
            print("Repeated tool pickup failed after "+str(current_attempt)+" attempts")
            attempt_successful = 0
        return attempt_successful
		
class slot():
    """
    Handles a slot on a robot base
    """
    
    def __init__(self, x, y, z):
        """
        Initializes with center position of a slot (x, y, z)
        """
        
        self.provideCenterCoordinates(x, y, z)

        
    def provideCenterCoordinates(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        
    def getCenterCoordinates(self):
        return self.x, self.y, self.z
		
class tool_slot(slot):
    """
    Handles a slot for a tool
    """
    
    def __init__(self, x, y, z):
        super().__init__(x=x, y=x, z=z)
        
    def defineResponseMessage(self, msg):
        self.msg = msg
    
    def getResponseMessage(self):
        return self.msg
		
class tool(serial_device):
    
    def __init__ (self, position_tuple, port_name, eol="\r\n"):
        
        """
        To initialize, provide position_tuple in the form (x, y, z). 
        Those are coordinates at which the tool can be found on a base
        
        To establish connection with a tool, call openSerialPort()
        
        To send a command, use write()
        
        To read all buffer, use readAll()
        """
        
        # Tool coordinates
        self.x = position_tuple[0]
        self.y = position_tuple[1]
        self.z = position_tuple[2]
        # End of line
        self.eol = eol
        self.port_name = port_name
    
    
    def getToolCoordinates(self):
        """
        Returns coordinates at which the tool should be picked up
        """
        return self.x, self.y, self.z  
		
class touch_probe(tool):
    def __init__(self, position_tuple, port_name):
        super().__init__(position_tuple, port_name, eol="")
    
    def isTouched(self):
        self.write('d')
        response = self.readAll()
        return bool(int(re.split(pattern='/r/n', string=response)[0]))
		
GenCenter = lambda xmin, xmax: xmin + (xmax - xmin)/2.0
GenCenterXYZ = lambda xmin, xmax, ymin, ymax, zmin, zmax: (
    GenCenter(xmin, xmax), 
    GenCenter(ymin, ymax),
    GenCenter(zmin, zmax),
)

def AxisToCoordinates(axis, value, nonetype=False):
    """
    Accepts "axis" input as "x", "y", "z" and numerical value.
    Returns tuple (x, y, z), where two of the values are 0, other is "value"
    For example:
        AxisToCoordinates('y', 5)
    returns
        (0, 5, 0)
    """
    axis = axis.lower()
    if nonetype:
        t = [None, None, None]
    else:
        t = [0, 0, 0]
        
    if axis=='x':
        t[0] = value
    elif axis=='y':
        t[1] = value
    elif axis=='z':
        t[2] = value
    else:
        print("Wrong axis provided: ", axis)
        print("Provide axis x, y or z")
    return t
	
def ApproachUntilTouch(arnie, touch_probe, axis, step):
    """
    Arnie will move along specified "axis" by "step"
    Provide:
        arnie - instance of Arnie object
        touch_probe - instance of touch_probe object
        axis - string, "x", "y" or "z"
        step - distance to move at every step
    """
    
    delta_coord = AxisToCoordinates(axis, step)
    x, y, z = arnie.getPosition()
    
    if delta_coord != [0, 0, 0] and delta_coord != [None, None, None]:
        while True:
            if touch_probe.isTouched():
                x, y, z = arnie.getPosition()
                # Move backwards by a tiny step to disengage after sensor got engaged
                arnie.moveDelta(dx=-delta_coord[0], dy=-delta_coord[1], dz=-delta_coord[2], speed_xy=1000)
                break
            # ApproachUntilTouchoach forward by a tiny step
            arnie.moveDelta(dx=delta_coord[0], dy=delta_coord[1], dz=delta_coord[2], speed_xy=1000)
    else:
        print ("Interrupted because wrong axis was provided.")
        
    return x, y, z
	
def findCenter(arnie, touch_probe, axis, x, y, z, axis_lift=None, lift_val=None, second_end=None, step=5.0, fine_coef=5.0):
    """
    """
    
    # Moving to initial position
    arnie.move(x=x, y=y, z=z, z_first=False)
    
    # Starting 3 approaches
    ApproachUntilTouch(arnie, touch_probe, axis, step)
    time.sleep(1)
    ApproachUntilTouch(arnie, touch_probe, axis, step/fine_coef)
    time.sleep(1)
    val_min = ApproachUntilTouch(arnie, touch_probe, axis, step/(fine_coef*fine_coef))
    
    val_center = val_min
    
    if axis_lift is not None and lift_val is not None and second_end is not None:
        # Lifting up and moving to the second position
        # To measure from the other side
        lift_coord = AxisToCoordinates(axis_lift, lift_val)
        second_end_coord = AxisToCoordinates(axis, second_end, nonetype=True)
        arnie.moveDelta(dx=lift_coord[0], dy=lift_coord[1], dz=lift_coord[2])
        arnie.move(x=second_end_coord[0], y=second_end_coord[1], z=second_end_coord[2], z_first=False)
        arnie.moveDelta(dx=-lift_coord[0], dy=-lift_coord[1], dz=-lift_coord[2])
        
        ApproachUntilTouch(arnie, touch_probe, axis, -step)
        time.sleep(1)
        ApproachUntilTouch(arnie, touch_probe, axis, -step/fine_coef)
        time.sleep(1)
        val_max = ApproachUntilTouch(arnie, touch_probe, axis, -step/(fine_coef*fine_coef))
        
        val_center = GenCenterXYZ(val_min[0], val_max[0], val_min[1], val_max[1], val_min[2], val_max[2])
    
    return val_center
	
def findXY(arnie, touch_probe, x1, y1, z, z_lift, x2, y2):
    xmin, xmax = findCenter(arnie, touch_probe, 'x', x1, y1, z, axis_lift='z', lift_val=z_lift, second_end=x2)
    ymin, ymax = findCenter(arnie, touch_probe, 'y', x1, y1, z, axis_lift='z', lift_val=z_lift, second_end=y2)
    return xmin, xmax, ymin, ymax
	
def findZ(arnie, touch_probe, x, y, z):
    return findCenter(arnie, touch_probe, 'z', x, y, z)[0]

def connect():
	ports = serial_ports()
	
	if len(ports) == 0:
		print("ERROR: Couldn't find any ports.")
		return
		
	if len(ports) > 1:
		print("ERROR: More than one port detected. Please remove all tools manually.")
		return
	
	# TODO: What if we see a port, but it's not a robot?
	
	robot = arnie(ports[0])
	robots.append(robot)
	robot.home()
	return robot
