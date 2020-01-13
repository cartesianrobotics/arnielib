"""
Module handling tools for the robot, both mobile and floor-based
"""

import logging
from copy import deepcopy
import re

# Internal arnielib modules
import low_level_comm as llc
import param
import cartesian as cart    # TODO: Remove it when finishing refactoring.

SPEED_Z_MOVING_DOWN = 10000 # Robot can move down much faster than up.

default_slot = {
    "LT": [-1, -1], 
    "LB": [-1, -1], 
    "RT": [-1, -1], 
    "RB": [-1, -1], 
    "floor_z": -1
}

default_tool = {
    "slot": deepcopy(default_slot),
    "n_x": -1,
    "n_y": -1,
    "type": None, # mobile_probe, pipettor, etc.
    "position": [-1, -1, -1],
    "tip": [-1, -1, -1],
    "params": None
}


class tool(llc.serial_device):
    """
    Parent class, handling tools
    """
    
    def __init__(self, com_port_number=None, tool_name=None,
                 welcome_message=None):
        """
        Handles any general tool properties; that any tool will have.
        This class will rarely be used by itself, instead, it is
        provided as parent one for specialized tools.
        
        Inputs:
            robot
                Instance of Arnie cartesian robot. Needed because the tool will dictate movements.
            com_port_number
                Name of the com port. Example: COM4
            welcome_message
                At initialization, tool will send some welcome message.
                It must contain this unique string, so the tool is identified.
            z_init
                Safe height at which robot won't hit anything. Default is 0.
        """
        
        if tool_name is not None:
            self.tool_name = tool_name

        if welcome_message is not None:
            self.welcome_message = welcome_message
        
        # Trying to find proper port from the list of existing ports,
        # Using device name and welcome message
        if com_port_number is None:
            ports_list = llc.listSerialPorts()
            matched_ports_dicts = llc.matchPortsWithDevices(
                ports_list, {self.tool_name: self.welcome_message})
            try:
                com_port_number = matched_ports_dicts[self.tool_name]
            except:
                logging.error("Tool initialization: No serial port name provided.")
                return

        super().__init__(com_port_number, welcome_message=self.welcome_message)
        

    @classmethod
    def getToolFromSerialDev(cls, device, welcome_message=""):
        """
        Initializa tool instance from already existing serial_device instance
        """
        
        port_name = device.port_name
        device.close()
        
        # Defining variables for compatibility
        cls.x_dock = None
        cls.y_dock = None
        cls.z_dock = None
        cls.z_safe = None
        
        return cls(com_port_number=port_name, welcome_message=welcome_message)
        

    
class mobile_tool(tool):
    """
    Handles mobile tools (contrary to the tools with fixed position)
    """
    def __init__(self, robot, com_port_number=None, tool_name=None,
                 welcome_message=None):
        """
        Handles any general tool properties; that any tool will have.
        This class will rarely be used by itself, instead, it is
        provided as parent one for specialized tools.
        
        Inputs:
            robot
                Instance of Arnie cartesian robot. Needed because the tool will dictate movements.
            com_port_number
                Name of the com port. Example: COM4
            welcome_message
                At initialization, tool will send some welcome message.
                It must contain this unique string, so the tool is identified.
            z_init
                Safe height at which robot won't hit anything. Default is 0.
        """
        
        # Tool will get control of the robot to tell it where to move itself,
        # or what operation may be needed.
        self.robot = robot
        try:
            self.getDockingPointByToolName(tool_name=tool_name)
        except:
            pass
        
        # Setting safe Z value
        try:
            # Checking if it does not exist, but variable is there
            if self.z_safe is None:
                self.z_safe = 0
        except AttributeError:
            # If variable is not there, I'm just assinging zero
            # If necessary, it can be chagned later.
            self.z_safe = 0
        
        super().__init__(com_port_number=com_port_number, tool_name=tool_name,
                 welcome_message=welcome_message)

    @classmethod
    def getToolAtCoord(cls, robot, x, y, z, z_init=0, speed_xy=None, speed_z=None, welcome_message=""):
        """
        Get tool positioned at known absolute coordinates x, y, z.
        """
        
        device = robot.getToolAtCoord(x, y, z, z_init=z_init, speed_xy=speed_xy, speed_z=speed_z)
        
        cls.x_dock = x
        cls.y_dock = y
        cls.z_dock = z
        cls.z_safe = z_init
        
        cls.speed_xy = speed_xy
        cls.speed_z = speed_z
        cls.welcome_message = welcome_message
        
        return cls.getToolFromSerialDev(robot=robot, device=device, welcome_message="")


    @classmethod
    def getToolFromSerialDev(cls, robot, device, welcome_message=""):
        """
        Initializa tool instance from already existing serial_device instance
        """
        
        port_name = device.port_name
        device.close()
        
        # Defining variables for compatibility
        #cls.x_dock = None
        #cls.y_dock = None
        #cls.z_dock = None
        #cls.z_safe = None
        
        return cls(robot=robot, com_port_number=port_name, welcome_message=welcome_message)


    @classmethod
    def getTool(cls, robot, tool_name="", welcome_message=""):
        """
        Get tool using its name
        """
        [x, y, z] = param.getToolDockingPoint(tool_name)
        cls.tool_name = tool_name
        return cls.getToolAtCoord(robot=robot, x=x, y=y, z=z, welcome_message=welcome_message)


    def setDockingPoint(x, y, z, z_safe):
        self.x_dock = x
        self.y_dock = y
        self.z_dock = z
        self.z_safe = z_safe


    def getDockingPointByToolName(self, tool_name=None):
        if tool_name is None:
            tool_name = self.tool_name
        [self.x_dock, self.y_dock, self.z_dock] = param.getToolDockingPoint(tool_name)
        return [self.x_dock, self.y_dock, self.z_dock]


    def returnTool(self):
        """
        Returns tool to its place.
        
        Assumes that coordinates were already specified in one or another way
        """
        
        if self.x_dock is None or self.y_dock is None or self.z_dock is None:
            # Attempting to load docking points using tool name
            self.getDockingPointByToolName()
        if self.z_safe is None:
            # Just setting safe height to be at the top of the robot
            self.z_safe = 0
        
        self.returnToolToCoord(self.x_dock, self.y_dock, self.z_dock, self.z_safe)


    def returnToolToCoord(self, x, y, z, z_init, speed_xy=None, speed_z=None):
        """
        Returns tool positioned at known absolute coordinates x, y, z.
        Operation will perform regardless of what state the tool is, 
        where there is a connection with it or whether it is initilized.
        User is responsible for prepping the tool for return, if applicable.
        """
        try:
            # Attempting to close the serial connection with a tool before returning it.
            self.close()
        except:
            pass
        self.robot.returnToolToCoord(x, y, z, z_init, speed_xy, speed_z)
    
    

class pipettor(mobile_tool):
    # TODO: Factor this function out into serial_device.
    def write_wait(self, expression, confirm_message="Idle", eol=None):
        """
        Function will write an expression to the device and wait for the proper response.
        
        Use this function to make the devise perform a physical operation and
        make sure program continues after the operation is physically completed.
        
        Function will return an output message
        """
        self.write(expression, eol)
        
        full_message = ""
        while True:
            message = self.readAll()
            if message_level == "verbose":
                print(message)
            if message != "":
                full_message += message
                if re.search(pattern=confirm_message, string=full_message):
                    break
            self.write("?")

    def home(self):
        set_pipettor_speed(self, 400)
        self.write_wait("$H")
        self.readAll()
    
    def drop_tip(self, plunger_lower=-40, plunger_raise=-2):
        """
        Tells currently connected pipettor to drop a tip. No checking is performed.
        Both parameters mean units to move plunger in absolute values.
        Value "0" will trigger endstop; -40 is the lowest possible position.
        
        Function lowers the servo lever and then moves plunger down. Lowered servo lever
        will push on the tip dispencer part, thus discarding the tip.
        After that, plunger is moved up and servo lever is risen.
        
        Parameters:
            - plunger_lower: Coordinate to move plunger down to, after lowering the servo
            - plunger_raise: Coordinate to move plunger up, after discarding the tip.
                Do not set to 0, as this may cause problem when parking the servo.
        """
        self.home() # Home the pipettor
        self.write_wait("M3 S90")   # Making sure servo lever is in the upper position
        self.readAll()
        self.write_wait("M5")   # Lowering the servo lever
        self.readAll()
        self.write_wait("G0 X"+str(plunger_lower)) # Moving plunger down to discard tip
        self.readAll()
        self.write_wait("G0 X"+str(plunger_raise))  # Raising plunger up
        self.readAll()
        self.write_wait("M3 S90")   # Raising servo lever
        self.readAll()


class touch_probe():
    """
    Handles behavior of all touch probes, either mobile, or fixed position.
    """
    
    def isTouched(self):
        self.write('d')
        response = self.readAll()
        logging.info("Touch probe response: %s", response)
        return bool(int(re.split(pattern='/r/n', string=response)[0]))
    
    def isNotTouched(self):
        return not self.isTouched()    
    

class mobile_touch_probe(mobile_tool, touch_probe):

    #def __init__(self, robot, com_port_number=None, 
    #             tool_name='mobile_probe', welcome_message='mobile touch probe'):
    #    super().__init__(robot, com_port_number=com_port_number, 
    #             tool_name="mobile_probe",
    #             welcome_message="mobile touch probe")


    @classmethod
    def getTool(cls, robot):
        """
        Get touch probe from its saved position and initializes the object
        """
        cls.tool_name = "mobile_probe"
        cls.welcome_message="mobile touch probe"
        return super().getTool(robot, 
            tool_name=cls.tool_name, welcome_message=cls.welcome_message)
            
            
    def approachUntilTouch(self, axis, step, retract=False, speed_xy=None, speed_z=None):
        """
        Arnie will move along specified "axis" by "step"
            Inputs
                axis - string, "x", "y" or "z"
                step - distance to move at every step
                retract - if True, function will inverse its behavior; i.e. keep 
                    moving while touch probe is engaged, and stop when touch
                    probe gets disengaged
                speed_xy, speed_z - axis moving speed. Using robot defaults at cartesian.py
        """
        
        axis = axis.lower()
        
        # Getting speed defaults from the robot instance.
        if speed_xy is None:
            speed_xy = self.robot.speed_x
        if speed_z is None:
            speed_z = self.robot.speed_z
        
        dC = self.robot.axisToCoordinates(axis, step)
        
        # Determining condition at which movement will continue.
        if retract:
            # Function assumes touch probe is touching something
            # Goal is to move until probe stops touching
            movingConditionEvaluator = self.isTouched
        else:
            # Function assumes touch probe is not touching anything
            # Goal is to move until it starts touching
            movingConditionEvaluator = self.isNotTouched
        
        while movingConditionEvaluator():
            self.robot.move_delta(dx=dC[0], dy=dC[1], dz=dC[2], speed_xy=speed_xy, speed_z=speed_z)
            position = self.robot.getPosition()
        x, y, z = self.robot.getPosition()
        
        if axis == 'x':
            return x
        elif axis == 'y':
            return y
        elif axis== 'z':
            return z
        else:
            return


    def findWall(self, axis, direction, step_dict=None, step_back_length=3):
        """
        Find coordinate of the wall on given "axis".
        Will move on "axis" into "direction", until touch probe detects collision. Then it 
        retracts until probe stops detecting collision. Then it approaches again with finer steps,
        until collision detected. This cycle repeats several times according to step_dict
        
        After that, it retracts on "step_back_length".
        
        Parameters:
            axis
                axis at which to perform calibration; only allowed "X", "Y" or "Z".
            direction
                direction at which to move robot; 
                eiter +1 or -1. +1 moves further from homing point; -1 - towards homing point
            step_dict
                Dictionary containing instructions on how to perform approach and retraction
                (step sizes, speeds). 
                Dictionary contains keys, all numbered as 0, 1, 2, ...
                Each key points to a dictionary of the form:
                {'step_fwd': 12, 'speed_xy_fwd': 5000, 'speed_z_fwd':5000,
                    'step_back': 12, 'speed_xy_back': 5000, 'speed_z_back':5000}
                Overall dictionary looks like this:
                step_dict = {
                    0: {'step_fwd': 12, 'speed_xy_fwd': 5000, 'speed_z_fwd':5000,
                        'step_back': 12, 'speed_xy_back': 5000, 'speed_z_back':5000},
                    1: {'step_fwd': 3, 'speed_xy_fwd': 2000, 'speed_z_fwd':3000,
                        'step_back': 6, 'speed_xy_back': 5000, 'speed_z_back':2000},
                    ...
                }
            step_back_length
                distance to retract after finishing calibration; default is 5.
        
        Returns coordinate at which collision was detected during finest approach.
        """
        # Sanity checks --------------------------------------------------------------------------------------------------------------------
        # direction should be either 1 or -1
        if direction != 1 and direction != -1:
            logging.error("Mobile touch probe, findWall(): wrong direction provided.")
            logging.error("Possible values are 1 or -1; provided value: %s", direction)
            return
        
        # Checking whether axes specified properly
        axis = axis.upper()
        if axis != "X" and axis != "Y" and axis != "Z":
            logging.error("Mobile touch probe, findWall(): wrong axis provided.")
            logging.error("Possible values are X, Y or Z; provided value: %s", axis)
            print("ERROR: wrong axis specified. Only allowed X, Y or Z")
            print(axis)
            return
        #  --------------------------------------------------------------------------------------------
        
        # If settings dictionary is not provided, the following ones will be used.
        # TODO: make them loadable from settings file
        if step_dict is None:
            step_dict = {
                0: {'step_fwd': 12, 'speed_xy_fwd': 5000, 'speed_z_fwd':5000,
                    'step_back': 12, 'speed_xy_back': 5000, 'speed_z_back':5000},
                1: {'step_fwd': 3, 'speed_xy_fwd': 2000, 'speed_z_fwd':3000,
                    'step_back': 6, 'speed_xy_back': 5000, 'speed_z_back':2000},
                2: {'step_fwd': 0.75, 'speed_xy_fwd': 200, 'speed_z_fwd':1000,
                    'step_back': 1.5, 'speed_xy_back': 500, 'speed_z_back':1000},
                3: {'step_fwd': 0.2, 'speed_xy_fwd': 100, 'speed_z_fwd':1000,
                    'step_back': 0.4, 'speed_xy_back': 100, 'speed_z_back':1000},
                4: {'step_fwd': 0.05, 'speed_xy_fwd': 25, 'speed_z_fwd':1000,
                    'step_back': 0.1, 'speed_xy_back': 50, 'speed_z_back':1000},
            }
            
        # Iterating through dictionary keys in the right order; i.e. starting from smallest
        for key in range(0, len(step_dict)):
            current_step_dict = step_dict[key]
            
            # Going backwards until touch probe no longer touches anything
            self.approachUntilTouch(axis=axis, 
                step=(-direction * current_step_dict['step_back']), 
                retract=True,
                speed_xy=current_step_dict['speed_xy_back'], 
                speed_z=current_step_dict['speed_z_back'])
            
            # Going forward until hitting the wall
            coord = self.approachUntilTouch(axis=axis, 
                step=(direction * current_step_dict['step_fwd']), 
                speed_xy=current_step_dict['speed_xy_fwd'], 
                speed_z=current_step_dict['speed_z_fwd'])
                
        # Retracting after calibration is finished
        [dx, dy, dz] = self.robot.axisToCoordinates(axis=axis, value=(-direction * step_back_length))
        self.robot.move_delta(dx=dx, dy=dy, dz=dz)
        
        return coord
        
    
    def findCenterInner(self, axis, step_dict=None, step_back_length=3, opposite_side_dist=0, direction=1):
        axis = axis.lower()
        # Finding first wall
        front_wall = self.findWall(axis=axis, direction=direction, step_dict=step_dict)
        # Moving to the other wall
        if axis == 'x':
            self.robot.move_delta(dx=-direction*opposite_side_dist)
        elif axis == 'y':
            self.robot.move_delta(dy=-direction*opposite_side_dist)
        else:
            pass
        # Finding second wall
        rear_wall = self.findWall(axis=axis, direction=-direction, step_dict=step_dict)
        # Calculating center
        center = (front_wall + rear_wall) / 2.0
        return center
    
    
    def findCenterOuter(self, axis, raise_height, dist_through_obstruct,
                        step_dict=None, step_back_length=3, opposite_side_dist=0, direction=1):
        """
        Performs "Pi-type" calibtation: from one side of the wall, then go through the wall,
        then from the other side of the wall.
        
        Inputs:
            axis
                x or y; axis at which to perform calibration
            raise_height
                height at which to raise gantry, so the probe can go through the obstruction
            dist_through_obstruct
                distance to travel to get through the obstruction
            ...
        """
        # Find first wall
        front_wall = self.findWall(axis=axis, direction=direction, step_dict=step_dict)
        # Raise gantry
        self.robot.move_delta(dz=-raise_height)
        # Move through obstruction
        if axis == 'x':
            self.robot.move_delta(dx=direction*dist_through_obstruct)
        elif axis == 'y':
            self.robot.move_delta(dy=direction*dist_through_obstruct)
        else:
            pass
        # Lower gantry back
        self.robot.move_delta(dz=raise_height)
        # Find opposite side of the wall
        rear_wall = self.findWall(axis=axis, direction=-direction, step_dict=step_dict)
        # Calculateing center
        center = (front_wall + rear_wall) / 2.0
        return center
    
    
class mobile_gripper(mobile_tool):
    def operate_gripper(self, level):
        self.write(str(level))

    
class stationary_touch_probe(tool, touch_probe):

    def __init__(self, com_port_number=None, tool_name="stationary_probe",
                 welcome_message="stationary touch probe"):
        super().__init__(com_port_number=com_port_number, tool_name=tool_name,
            welcome_message=welcome_message)



device_type_descriptions = [
    {"class": cart.arnie, "message": "Marlin", "type": "", "mobile": False}, 
    {"class": stationary_touch_probe, "message": "stationary touch probe", "type": "stationary_probe", "mobile": False}, 
    {"class": mobile_touch_probe, "message": "mobile touch probe", "type": "mobile_probe", "mobile": True},
    {"class": pipettor, "message": "Servo", "type": "pipettor", "mobile": True},
    {"class": mobile_gripper, "message": "mobile circular gripper", "type": "mobile_gripper", "mobile": True},
    ]