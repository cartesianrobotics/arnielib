"""
Sub-library of ArnieLib, handling basic cartesian robot
properties and operations

Part of ArnieLib.

Sergii Pochekailov
"""

import re
import time
import logging

# Local parts of ArnieLib imports
import low_level_comm as llc
import param    # Handles calibration data

# Constants
# ===============================

# Arnie's welcome message
WELCOME_MESSAGE = "Marlin"

# Axis moving speed
SPEED_X = 8000
SPEED_Y = 8000
SPEED_Z = 5000
SPEED_Z_MOVING_DOWN = 15000 # Robot can move down much faster than up.

# Homing command
# Example: G28 - homes all axis (careful, better first home Z axis, then others)
# G28 Z - Homes only Z axis
HOMING_CMD = 'G28'

# Operations with a tool
OPEN_TOOL_G_CODE = "M280 P1 S10"
OPEN_TOOL_DELAY = 3 # seconds
CLOSE_TOOL_G_CODE = "M280 P1 S80"
CLOSE_TOOL_DELAY = 3 # seconds

# Moving G-code command: G0 X<value> Y<value> Z<value> F<value>


def axis_index(axis):
    result = axis.upper()
    axes = ["X", "Y", "Z"]
    if result not in axes:
        print("ERROR: wrond axis provided: " + axis)
        return -1
    else:
        result = axes.index(result)
        return result


class arnie(llc.serial_device):
    """
    Class handling cartesian robot's basic operations and data
    """

    def __init__(self, com_port_number, 
                 speed_x=SPEED_X, speed_y=SPEED_Y, speed_z=SPEED_Z,
                 welcome_message=WELCOME_MESSAGE):
        logging.info("Cartesian robot Arnie: start initialization.")
        super().__init__(com_port_number, welcome_message=welcome_message)
        self.firstActions(speed_x=speed_x, speed_y=speed_y, speed_z=speed_z, home=False)
        logging.info("Cartesian robot Arnie initializsed successfully.")

    
    def firstActions(self, speed_x=SPEED_X, speed_y=SPEED_Y, speed_z=SPEED_Z, home=False):
        """
        Call this function when initializing the device, or
        promoting serial_device class.
        
        Inputs:
            speed_x, speed_y, speed_z
                Speed of the corresponding axis
            home
                Whether to perform homing at initialization; true or false
        """
        self.promote(SPEED_X, SPEED_Y, SPEED_Z)
        if home:
            logging.info("Homing at initialization started.")
            self.home('Z')
            self.home('Y')
            self.home('X')
            logging.info("Homing at initialization finished.")

    
    def promote(self, speed_x=SPEED_X, speed_y=SPEED_Y, speed_z=SPEED_Z):
        self.calibrated = False
        self.speed = [speed_x, speed_y, speed_z]
        self.tools = []
        self.tool_devices = []
        
    def home(self, axes='ZXY'):
        """
        Home one of the axes, X, Y or Z.
        Axis 
            axis to home
                x - home X axis
                y - home Y axis
                z - home Z axis
        """
        for axis in axes:
            axis = axis.upper()
            if axis != 'X' and axis != 'Y' and axis != 'Z' and axis != 'XYZ':
                logging.warning("Homing attempted with axis value %s.", axis)
                logging.warning("However, this value is not currently supported.")
                logging.warning("Homing cancelled.")
            else:
                logging.info("Homing axis %s started", axis)
                self.writeAndWait(HOMING_CMD + ' ' +axis)
    

    def moveAxis(self, axis, destination, speed=None):
        """
        Moves specified axis to a new position with absolute coordinate.
        
        Inputs:
            axis
                Axis along which to perform movement. "X", "Y" or "Z".
                
            destination
                New absolute coordinate, in mm from homing point
                
            speed
                Speed at which to perform movement. If not specified, 
                library default is used.
        """
        
        axis=axis.upper()
        if speed == None:
            speed = self.speed[axis_index(axis)]
        speed_cmd = 'F' + str(speed)
        full_cmd = 'G0 ' + axis + str(destination) + ' ' + speed_cmd
        
        try:
            logging.info("moveAxis: Moving carriage to the new position along the axis %s", axis)
            logging.info("moveAxis: %s=%s with speed %s", axis, destination, speed)
            logging.info("moveAxis: G-code command generated: %s", full_cmd)
            
            self.writeAndWait(full_cmd)
        except:
            logging.warning("moveAxis: Attempted to move carriage to the new position along the axis %s", axis)
            logging.warning("moveAxis: %s=%s with speed %s", axis, destination, speed)
            logging.warning("moveAxis: G-code command generated: %s", full_cmd)
            logging.warning("moveAxis: However, something went wrong, command aborted.")

        
    def moveXY(self, x, y, speed=None):
        """
        Moves axes X and Y simultaneously. 
        Generates G-code for moving of the type: G0 X<value> Y<value> F<value>
        Passes G-code to 
        low_level_comm.writeAndWait() function (will wait for operation to complete)
        
        Inputs:
            x, y
                Final coordinate values in mm
            speed
                Moving speed for X an Y axes. Both will be moving with the same speed.
                Speed is measured in arbitrary units.
        """
        if speed == None:
            speed = self.speed[axis_index("X")]
        full_cmd = 'G0 X' + str(x) + ' Y' + str(y) + ' F' + str(speed)
        try:
            logging.info("moveXY: Moving carriage to the new position with coordinates:")
            logging.info("moveXY: X=%s, Y=%s with speed %s", x, y, speed)
            logging.info("moveXY: G-code command generated: %s", full_cmd)
            
            self.writeAndWait(full_cmd)
        except:
            logging.warning("moveXY: Attempted to move carriage to the new position with coordinates:")
            logging.warning("moveXY: X=%s, Y=%s with speed %s", x, y, speed)
            logging.warning("moveXY: G-code command generated: %s", full_cmd)
            logging.warning("moveXY: However, something went wrong, command aborted.")
    
    
    def move(self, x=None, y=None, z=None, z_first=True, speed_xy=None, speed_z=None):
        """
        Move robot to a new position with given absolute coordinates.
        
            Inputs
                x, y, z
                    final coordinates to which to move the robot;
                    values in mm from homing position.
                    You can provide any of x, y or z, or all of them.
                    If both x and y provided, robot will move them simultaneously.
                z_first
                    if True and z value provided, will move Z coordinate first, 
                    then X and Y. Otherwise, will start from X and Y and then Z.
                    Default is True.
                speed_xy
                    Speed at which to move X and Y coordinates.
                    If not provided, library default values from arnie.speed will be used.
                speed_z
                    Speed at which to move Z coordinate.
                    If not provided, library default values from arnie.speed will be used.
        """
        
        if speed_xy == None:
            speed_xy = self.speed[axis_index("X")]
        if speed_z == None:
            speed_z = self.speed[axis_index("Z")]
        
        logging.info("move: Moving carriage to the new position with coordinates:")
        logging.info("move: X=%s, Y=%s, Z=%s with X and Y speed %s, Z speed %s", 
                     x, y, z, speed_xy, speed_z)
        
        
        # Each of the functions attempting to move an axis to the coordinate. 
        # If something goes wrong, like coordinate not specified, command is ignored
        # and the next one is attempted.
        if z_first:
            logging.info("move: Z coordinate will move first.")
            if z is not None:
                self.moveAxis('Z', z, speed_z)
            # If both X and Y should be moved, I need to call moveXY(), one which would move
            # those axes simultaneously
            if x is not None and y is not None:
                self.moveXY(x=x, y=y, speed=speed_xy)
            elif x is not None:
                self.moveAxis('X', x, speed_xy)
            elif y is not None:
                self.moveAxis('Y', y, speed_xy)
        else:
            logging.info("move: X and Y coordinates will move first.")
            # If both X and Y should be moved, I need to call moveXY(), one which would move
            # those axes simultaneously
            if x is not None and y is not None:
                self.moveXY(x=x, y=y, speed=speed_xy)
            elif x is not None:
                self.moveAxis('X', x, speed_xy)
            elif y is not None:
                self.moveAxis('Y', y, speed_xy)
            if z is not None:
                self.moveAxis('Z', z, speed_z)

    
    def move_delta(self, dx=None, dy=None, dz=None, z_first=True, speed_xy=None, speed_z=None):
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
        open_tool_G_code = OPEN_TOOL_G_CODE
        sleep_time = OPEN_TOOL_DELAY
        
        logging.info("Arnie openTool: Opening tool docker to accept a new tool.")
        logging.info("Arnie openTool: G-code sent: %s, delay %s seconds.", open_tool_G_code, sleep_time)
        
        self.write(open_tool_G_code)
        time.sleep(sleep_time)
        
    def closeTool(self):
        """Docker closes, fixing a tool in place"""
        close_tool_G_code = CLOSE_TOOL_G_CODE
        sleep_time = CLOSE_TOOL_DELAY
        
        logging.info("Arnie closeTool: Closing tool docker, possibly with a new tool.")
        logging.info("Arnie closeTool: G-code sent: %s, delay %s seconds.", close_tool_G_code, sleep_time)
        self.getPosition() # This is done so the actual position is recorded in the log file.
        
        self.write(close_tool_G_code)
        time.sleep(sleep_time)
    
    def getPosition(self):
        """
        Requests current position from cartesian robot firmware.
        Request is done by sending G-code M114.
        
        Returns:
            x, y, z
                Current coordinates of the cartesian robot relative to homing position, in mm.
        """
        self.writeAndWait("M114")
        msg = self.recent_message
        msg_list = re.split(pattern=' ', string=msg)
        x_str = msg_list[0]
        y_str = msg_list[1]
        z_str = msg_list[2]
        #print (x_str, y_str, z_str)
        x = float(re.split(pattern="\:", string=x_str)[1])
        y = float(re.split(pattern="\:", string=y_str)[1])
        z = float(re.split(pattern="\:", string=z_str)[1])
        logging.info("Current cartesian robot coordinates are x=%s, y=%s, z=%s", x, y, z)
        return x, y, z
    
        
    def approachToolPosition(self, x, y, z, speed_xy=None, speed_z=None):
        """
        Moves robot to specified coordinates, where the tool is expected to be.
        Alternatively, moves robot WITH a tool to its empty slot
        Coordinates for both operations should be the same.
        Thif function will not engage docker, as one need to make sure the tool is at the right position
        """
        
        logging.info("Approaching tool position at coordinates x=%s, y=%s, z=%s", x, y, z)
        self.move(x, y, z, z_first=False, speed_xy=speed_xy, speed_z=speed_z)
    
    def approachToolAtSlot(self, tool_at_slot, speed_xy=None, speed_z=None):
        """
        Moves robot towards the tool, which object is passed in "tool_at_slot". 
        Same as "approachToolPosition", but using the object of tool_at_slot class
        """
        x, y, z = tool_at_slot.getCenterCoordinates()
        self.approachToolPosition(x=x, y=y, z=z, speed_xy=speed_xy, speed_z=speed_z)
    
    
    def getToolAtCoord(self, x, y, z, z_init=0, speed_xy=None, speed_z=None):
        """
        Get tool positioned at known absolute coordinates x, y, z.
        """
        
        # Producing a list of present serial ports BEFORE engaging a new tool
        initial_ports_list = llc.listSerialPorts()
        
        # Moving to the save height, so nothing is kicked by a robot
        self.move(z=z_init, speed_z=None)
        # Opening docker
        self.openTool()
        # Moving to the tool coordinate
        self.move(x=x, y=y, z=z, z_first=False, speed_xy=speed_xy, speed_z=SPEED_Z_MOVING_DOWN)
        # Closing docker (hopefully gripping the tool)
        self.closeTool()
        
        # Obtaining updated list of serial devices. Now a new device should be present there.
        updated_ports_list = llc.listSerialPorts()
        # Obtaining newly appeared port
        new_port = list(set(updated_ports_list) - set(initial_ports_list))[0]
        
        # Connecting to the device
        device = llc.serial_device(new_port)
        
        self.move(z=z_init)
        
        return device
        
    
    def getTool(self, x_n=None, y_n=None, 
        tool_name=None, tool_data=None, data_path=None, 
        z_init=0, z_dest_delta=0, speed_xy=None, speed_z=None):
        """
        Get tool positioned at specified (x_n, y_n) slot
        """
        
        if data_path is None:
            data_path = param.DEFAULT_TOOL_CALIBR_FILE
        
        if tool_data is None:
            tool_data = param.loadData('tools.json')
            
        if tool_name is not None:
            [x, y, z] = param.getToolDockingPoint(toolname=tool_name, data=tool_data, tool_file=data_path)
        elif (x_n is not None) and (y_n is not None):
            [x, y, z] = param.getToolDockingPoint(slot=[x_n, y_n], data=tool_data, tool_file=data_path)
            
        device = self.getToolAtCoord(
            x=x, y=y, z=z+z_dest_delta, z_init=z_init, speed_xy=speed_xy, speed_z=speed_z)
        self.current_tool = device  # Object of robot class now stores current tool
        
        return self.current_tool


    def returnToolToCoord(self, x, y, z, z_init, speed_xy=None, speed_z=None):
        """
        Returns tool positioned at known absolute coordinates x, y, z.
        Operation will perform regardless of what state the tool is, 
        where there is a connection with it or whether it is initilized.
        User is responsible for prepping the tool for return, if applicable.
        """
        
        # Moving robot to the safe height, where it will not accidentally touch anything.
        self.move(z=z_init)
        # Moving to the tool release position
        self.move(x=x, y=y, z=z, z_first=False, speed_xy=speed_xy, speed_z=SPEED_Z_MOVING_DOWN)
        # Opening tool
        self.openTool()
        # Moving back to the safe position
        self.move(z=z_init)
        
    
    def returnTool(self, x_n=None, y_n=None, z_dest_delta=0, z_init=0,
        tool_name=None, tool_data=None, data_path=None,
        device=None, speed_xy=None, speed_z=None):
        """
        Returns a tool, trying to find where to return from different sources
        """
        
        # trying to get coordinates from the device object
        # The object may not contain coordinates though
        coordinates_obtained = False
        if device is None:
            try:
                [x, y, z] = self.current_tool['position']
                coordinates_obtained = True
            except:
                pass
        else
            # Trying to get coordinates from the object provided as an argument
            try:
                [x, y, z] = device['position']
                coordinates_obtained = True
            except:
                pass
        
        # If unable to get coordinates from the object itself, 
        # trying to find them by the device name using calibration
        # data stored on drive
        if (not coordinates_obtained) and (tool_name is not None):
            try:
                [x, y, z] = param.getToolDockingPoint(tool_name)
                coordinates_obtained = True
            except:
                pass
        # Trying to get by the slot given it is provided
        elif (not coordinates_obtained) and (x_n is not None) and (y_n is not None):
            try:
                [x, y, z] = param.getToolDockingPoint(tool_name)
                coordinates_obtained = True
            except:
                pass
        
        if coordinates_obtained:
            self.returnToolToCoord(x=x, y=y, z=z, z_init=z_init, speed_xy=speed_xy, speed_z=speed_z)
            self.current_tool = None    # Removing info about current tool from robot object
                # As the tool is no longer engaged with the robot.
        else:
            logging.error("Cartesian returnTool(): Unable to find coordinates where to place the tool.")
            logging.error("Cartesian returnTool(): Use returnToolToCoord() instead. ")
        

    # TODO: This function is never used. Clean it? 
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
    
    # TODO: This function is never used. Clean it? 
    def hardInitToolAttempt(self, tool, total_attempts=3, current_attempt=0):
        # Attempt to re-connect to the tool. 
        # To be used after failed initialization
        self.openTool()
        # Moving Arnie up and down for an attempt to physically reconnect
        self.move_delta(dz=-300)
        self.move_delta(dz=300)
        
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