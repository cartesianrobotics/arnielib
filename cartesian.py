"""
Sub-library of ArnieLib, handling basic cartesian robot
properties and operations

Part of ArnieLib.

Sergii Pochekailov
"""

import logging

# Local parts of ArnieLib imports
import low_level_comm as llc

# Constants
# ===============================

# Arnie's welcome message
WELCOME_MESSAGE = "Marlin"

# Axis moving speed
SPEED_X = 8000
SPEED_Y = 8000
SPEED_Z = 5000

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
        
        self.move(x, y, z, z_first=False, speed_xy=speed_xy, speed_z=speed_z)
    
    def approachToolAtSlot(self, tool_at_slot, speed_xy=None, speed_z=None):
        """
        Moves robot towards the tool, which object is passed in "tool_at_slot". 
        Same as "approachToolPosition", but using the object of tool_at_slot class
        """
        x, y, z = tool_at_slot.getCenterCoordinates()
        self.move(x, y, z, z_first=False, speed_xy=speed_xy, speed_z=speed_z)
    
    
    def get_tool(self, x_n, y_n, z_init=1, z_dest_delta=0):
        """
        Engages with a tool, using tool instance for guidance
        """
        if self.current_tool != None:
            self.return_tool()
        
        tool_to_get = None
        for saved_tool in self.tools:
            if x_n == saved_tool["n_x"] and y_n == saved_tool["n_y"]:
                tool_to_get = deepcopy(saved_tool)
                break
        
        if tool_to_get == None:
            print("ERROR: slot (" + str(x_n) + ", " + str(y_n) + ") doesn't contain any tool.")
            return 
        
        dest = tool_to_get["position"]
        
        self.openTool()
        self.move(z=z_init)
        #self.home("Z")
        self.move(x=dest[0], y=dest[1])
        self.move(z=dest[2] + z_dest_delta) # z_dest_delta corrects for the error in instrument height estimation
        self.closeTool()
        self.current_tool = saved_tool
        #self.home("Z")
        self.move(z=z_init)
        
        # TODO: handle the case when the port is physically not connected
        while True:
            ports = llc.listSerialPorts()
            if len(ports) > 0:
                break
        
        for port in ports:
            self.current_tool_device = connect_tool(port, self)
        
        # TODO: Uncomment the following or write some other check for a device that couldn't connect. 
        
        #self.current_tool_device = 
        
        # Attempting to initialize the tool
        #attempt_success    ful = self.softInitToolAttempt(tool, total_attempts=2)
        #if not attempt_successful:
        #   attempt_successful = self.hardInitToolAttempt(tool, total_attempts=3)
        #if attempt_successful:
            # Locking tool
        #   self.closeTool()
            # Moving back up
        #   self.move(z=0, speed_z=speed_z)
        #else:
        #   self.openTool()
        #   print("Failed to pickup tool. Program stopped.")
            
    
    def return_tool(self, z_init=1):
        """
        Returns tool back to its place.
        The place is provided either with tool instance, or simply as position_tuple (x, y, z)
        """
        if self.current_tool == None:
            print("ERROR: Trying to return tool, but no tool is connected.")
        
        if self.current_tool["type"] == "pipettor":
            self.current_tool_device.home()
            time.sleep(5)

        if self.current_tool["type"] == "mobile_gripper":
            self.current_tool_device.write("1")
            time.sleep(2)
        
        dest = self.current_tool["position"]
        self.move(z=z_init)
        #self.home("Z")
        self.move(x=dest[0], y=dest[1])
        self.move(z=dest[2])
        self.openTool()
#       time.sleep(5)   # Short delay after placing an instrument into the holder, to prevent premature Z lifting
        self.move(z=z_init)
        self.home("Z")
        self.current_tool = None
        self.current_tool_device = None

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