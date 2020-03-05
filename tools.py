"""
Module handling tools for the robot, both mobile and floor-based
"""

import logging
from copy import deepcopy
import re
import cartesian as cart    # TODO: Remove it when finishing refactoring.
import json
import configparser

# Internal arnielib modules
import low_level_comm as llc
import param
import racks

SPEED_Z_MOVING_DOWN = 8000 # Robot can move down much faster than up.

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

# TODO: move all variables into tool_data dictionary; 
# To make it simpler to save/load.
class tool(llc.serial_device):
    """
    Parent class, handling tools
    """
    
    def __init__(self, robot, com_port_number=None, 
                 tool_name=None, tool_type=None, rack_name=None, rack_type=None,
                 welcome_message=None, tool_data=None):
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
        
        self.tool_data = tool_data
        
        
        # Tool will get control of the robot to tell it where to move itself,
        # or what operation may be needed.
        self.robot = robot

        # Attempting to read data from HD
        if self.tool_data is None:
            self.tool_data = self.openFileWithToolParameters(tool_name+'.json')

        # Populating dictionary with current rack properties
        if self.tool_data is None:
            self.tool_data = {}
        
        # Initialize rack
        rack_type, rack_name, tool_type, tool_name = self._populateNames(rack_type, rack_name, tool_type, tool_name)
        self.rack = racks.rack(rack_name=rack_name, rack_type=rack_type)
        
        # Reading settings data for the tool
        # Using provided or saved tool type, load rack properties from config file
        # Tool has 2 sets of settings: for the rack and for the tool itself.
        # Rack settings contain all information relating storage place of that tool,
        # such as tool rack geometry and pickup instructions.
        # Tool only has information which relates to the tool itself, 
        # such as tool geometry.
        config = configparser.ConfigParser()
        config_path = 'configs/' + tool_type + '.ini'
        config.read(config_path)
        
        # How much longer the tool is compared to the mobile touch probe.
        # This setting to be used only for calibration purposes, 
        # after which obtained Z coordinate will be used for the other operations.
        self.delta_length_for_calibration = float(config['calibration']['delta_length_for_calibration'])
        
        if tool_name is not None:
            self.tool_name = tool_name
            self.tool_data['name'] = tool_name
            

        if welcome_message is not None:
            self.welcome_message = welcome_message
            self.tool_data['welcome_message'] = welcome_message
            
        
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

        
    def _populateNames(self, rack_type=None, rack_name=None, tool_type=None, tool_name=None):
        """
        Initializes rack
        """
        
        if (tool_name is None) and (tool_type is not None):
            tool_name = tool_type
        
        if (tool_type is None) and (tool_name is not None):
            tool_type = tool_name
        
        if rack_type is None:
            rack_type = tool_type + '_rack'
        
        if rack_name is None:
            rack_name = rack_type

        return rack_type, rack_name, tool_type, tool_name


    @classmethod
    def getToolFromSerialDev(cls, device, welcome_message="", 
            tool_name=None, tool_type=None, rack_name=None, rack_type=None):
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


    def openFileWithToolParameters(self, path):
        try:
            filehandler = open(path, 'r')
            result = json.loads(filehandler.read())
            filehandler.close()
        except FileNotFoundError:
            return None
            
        
        return result
        
    def save(self):
        tool_name = self.tool_data['name']
        f = open(tool_name+'.json', 'w')
        f.write(json.dumps(self.tool_data))
        f.close()


    
class mobile_tool(tool):
    """
    Handles mobile tools (contrary to the tools with fixed position)
    """
    def __init__(self, robot, com_port_number=None, 
                 tool_name=None, tool_type=None, rack_name=None, rack_type=None,
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
        
        #try:
        #    self.getDockingPointByToolName(tool_name=tool_name)
        #except:
        #    pass
        
        # TODO: Create process of checking all available tools for highest height, from that,
        # calculate z_safe.
        # z_safe is the height at which robot won't knock anything off even when using longest
        # tool.
        
        # Setting safe Z value
        try:
            # Checking if it does not exist, but variable is there
            if self.z_safe is None:
                self.z_safe = 0
        except AttributeError:
            # If variable is not there, I'm just assinging zero
            # If necessary, it can be chagned later.
            self.z_safe = 0
        
        super().__init__(robot=robot, com_port_number=com_port_number, 
                 tool_name=tool_name, tool_type=tool_type, rack_name=rack_name, rack_type=rack_type,
                 welcome_message=welcome_message)

    @classmethod
    def getToolAtCoord(cls, 
            robot, x, y, z, z_init=0, speed_xy=None, speed_z=None, 
            tool_name=None, tool_type=None, rack_name=None, rack_type=None,
            welcome_message=None):
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
        
        return cls.getToolFromSerialDev(
                    robot=robot, device=device, 
                    tool_name=tool_name, tool_type=tool_type, rack_name=rack_name, rack_type=rack_type,
                    welcome_message=welcome_message)


    @classmethod
    def getToolFromSerialDev(cls, robot, device, 
            tool_name=None, tool_type=None, rack_name=None, rack_type=None,
            welcome_message=None):
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
        
        return cls(robot=robot, com_port_number=port_name,
                   tool_name=tool_name, tool_type=tool_type, rack_name=rack_name, rack_type=rack_type,
                   welcome_message=welcome_message)


    @classmethod
    def getTool(cls, robot,
            tool_name=None, tool_type=None, rack_name=None, rack_type=None,
            welcome_message=""):
        """
        Get tool using its name
        """
               
        if (tool_type is None) and (tool_name is not None):
            tool_type = tool_name
        if (tool_type is not None) and (tool_name is None):
            tool_name = tool_type
        if rack_type is None:
            rack_type = tool_type + '_rack'
        if rack_name is None:
            rack_name = rack_type

        cls.rack = racks.rack(rack_name=rack_name, rack_type=rack_type)
        [x, y, z] = cls.rack.getCalibratedRackCenter()
        z_height = cls.rack.z_height
        z_working_height = cls.rack.z_working_height
        # After exchanging slot height for calibrated rack point
        #z_pickup = z - z_height - z_working_height
        z_pickup = z - z_working_height
        cls.tool_name = tool_name
        return cls.getToolAtCoord(robot=robot, 
                x=x, y=y, z=z_pickup, 
                tool_name=tool_name, tool_type=tool_type, rack_name=rack_name, rack_type=rack_type,
                welcome_message=welcome_message)


# Following two functions stores and returns coordinates of #stalagmyte.
# After #stalagmyte calibration, the resulting coordinates are stored in the 
# tool object. 
# In case of a #mobile_touch_probe, they are then passed to the 
# object of corresponding rack or immobile tool during calibration,
# then both rack coordinates and stalagmyte coordinates are dumped into rack data.
# In case of any other device, such as a pipettor, they are also passed to the
# rack object, however not stored but used to adjust position of the tool relative to the rack.
    def setStalagmyteCoord(self, x, y, z):
        """
        With this function, #mobile_tool (touch probe, pipettor, etc.) object 
        receives coordinates of interaction with 
        a #stalagmyte, or an #immobile_touch_probe
        
        Inputs:
            x, y, z
                Center of immobile touch probe
        """
        self.immob_probe_x = x
        self.immob_probe_y = y
        self.immob_probe_z = z

    def getStalagmyteCoord(self):
        """
        Returns #stalagmyte (or #immobile_touch_probe) coordinates, that are 
        saved in the object after calibration
        """
        return self.immob_probe_x, self.immob_probe_y, self.immob_probe_z

# TODO: remove this completely?
# Should be in rack class
# See rack.updateCenter()
    def setDockingPoint(x, y, z, z_safe):
        self.x_dock = x
        self.y_dock = y
        self.z_dock = z
        self.z_safe = z_safe


    def getDockingPointByToolName(self, tool_name=None):
        if tool_name is None:
            tool_name = self.tool_data['name']
        x, y, z = self.rack.calcWorkingPosition(0, 0)
        #print (self.rack.z_working_height)
        #[self.x_dock, self.y_dock, self.z_dock] = param.getToolDockingPoint(tool_name)
        return [x, y, z]


    def returnTool(self):
        """
        Returns tool to its place.
        
        Assumes that coordinates were already specified in one or another way
        """
        
        
        #if self.x_dock is None or self.y_dock is None or self.z_dock is None:
        #    # Attempting to load docking points using tool name
        #    self.getDockingPointByToolName()
        #if self.z_safe is None:
        #    # Just setting safe height to be at the top of the robot
        #    self.z_safe = 0
        #print (self.rack.rack_data)
        #x, y, z = self.getDockingPointByToolName()
        
        [x, y, z] = self.rack.getCalibratedRackCenter()
        z_height = self.rack.z_height
        z_working_height = self.rack.z_working_height
        z_return = z - z_working_height
        # TODO: designe for z_safe
        self.returnToolToCoord(x, y, z_return, z_init=0, speed_xy=None, speed_z=None)


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
        self.robot.returnToolToCoord(x, y, z, z_init=z_init, speed_xy=speed_xy, speed_z=speed_z)
    
    

class pipettor(mobile_tool):

    def __init__ (self, robot, tool_name, rack_name=None, rack_type=None, tool_type=None, com_port_number=None, 
            welcome_message=None):
        super().__init__(robot=robot, com_port_number=com_port_number,
            tool_name=tool_name, welcome_message='Servo', rack_type='pipette_rack', rack_name=tool_name+'_rack')
            
        # Homing pipettor
        if self.tool_name == 'p20':
            self.home(pipettor_speed=400)
        else:
            self.home(pipettor_speed=1000)        
            
    @classmethod
    def getTool(cls, robot, tool_name):
        """
        Get touch probe from its saved position and initializes the object
        """
        #cls.tool_name = tool_name
        cls.welcome_message="Servo"
        return super().getTool(robot, 
            tool_name=tool_name, welcome_message="Servo", rack_type='pipette_rack', rack_name=tool_name+'_rack')        
    
    # TODO: Factor this function out into serial_device.
    def sendCmdToPipette(self, expression, confirm_message="Idle", eol=None):
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
#            if message_level == "verbose":
#                print(message)
            if message != "":
                full_message += message
                if re.search(pattern=confirm_message, string=full_message):
                    break
            self.write("?")

    def home(self, pipettor_speed=400):
        self.setPipettorSpeed(pipettor_speed)
        self.sendCmdToPipette("$H")
        self.switchModeToNormal()


    def pickUpTip(self, rack, column, row, fine_approach_dz=10, raise_z=0, raise_dz_with_tip=100, fine_approach_speed=500):
        # Obtaining coordinate of the tip position
        x, y, z = rack.calcWorkingPosition(column, row, self)
        # Moving up
        self.robot.move(z=raise_z)
        # Moving above tip
        self.robot.move(x=x, y=y)
        # Coarse approach
        fine_approach_z = z - fine_approach_dz
        self.robot.move(z=fine_approach_z)
        # Fine approach
        self.robot.move(z=z, speed_z=fine_approach_speed)
        # Raise with a tip
        raise_with_tip_z = z - raise_dz_with_tip
        self.robot.move(z=raise_with_tip_z)

    
    def dropTip(self, plunger_lower=-40, plunger_raise=-2):
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
        self.movePlunger(plunger_raise) # Moving plunger up
        # Making sure servo lever is in the upper position
        self.switchModeToNormal()
        self.switchModeToDropTip()   # Lowering the servo lever
        self.movePlunger(plunger_lower)
        self.movePlunger(plunger_raise)
        self.switchModeToNormal()   # Raising servo lever

    
    def setPipettorSpeed(self, speed):
        """
        Sets pipettor speed
        """
        self.sendCmdToPipette("$110="+str(speed), confirm_message="")
        
    
    def switchModeToNormal(self):
        self.sendCmdToPipette("M3 S90")
        
    def switchModeToDropTip(self):
        self.sendCmdToPipette("M5")
        
    def movePlunger(self, level):
        self.sendCmdToPipette("G0 X"+str(level))


# Some functions may involve both mobile and immobile touch probes simultaneously;
# and so, have to be moved out of the classes.
# Example is calibration of stalagmite against stalaktite; during which
# both are checked for whether they touch anything.

def approachUntilTouch(robot, touch_function, axis, step, speed_xy=None, speed_z=None):
    """
    Arnie will move along specified "axis" by "step"
        Inputs
            robot
                Arnie instance
            touch_function
                Function used to evaluate whether probe is touching anything. 
                Example:
                    p = mobile_touch_probe.getTool(robot)
                    touch_function = p.isNotTouched
                    approachUntilTouch(robot, touch_function, 'x', 5)
            axis
                string, "x", "y" or "z"
            step
                distance to move at every step
            speed_xy, speed_z
                axis moving speed. Using robot defaults at cartesian.py
    """
    
    # Getting speed defaults from the robot instance.
    if speed_xy is None:
        speed_xy = robot.speed_x
    if speed_z is None:
        speed_z = robot.speed_z
    
    dC = robot.axisToCoordinates(axis, step)
    
    while touch_function():
        robot.move_delta(dx=dC[0], dy=dC[1], dz=dC[2], speed_xy=speed_xy, speed_z=speed_z)
    
    return robot.getAxisPosition(axis)


def findWall(probe, axis, direction, second_probe=None, step_dict=None, step_back_length=3):
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
    # Sanity checks --------------------------------------------------------------------------------------------------------
    # direction should be either 1 or -1
    if direction != 1 and direction != -1:
        logging.error("Mobile touch probe, findWall(): wrong direction provided.")
        logging.error("Possible values are 1 or -1; provided value: %s", direction)
        return
    #  --------------------------------------------------------------------------------------------
    
    # If settings dictionary is not provided, the following ones will be used.
    # TODO: make them loadable from settings file
    if step_dict is None:
        step_dict = probe.step_dict
        
    # Iterating through dictionary keys in the right order; i.e. starting from smallest
    for key in range(0, len(step_dict)):
        current_step_dict = step_dict[key]
        
        if second_probe is not None:
            def retract_touch_function():
                return (probe.isTouched() or second_probe.isTouched())
            def forward_touch_function():
                return (probe.isNotTouched() and second_probe.isNotTouched())
        else:
            retract_touch_function = probe.isTouched
            forward_touch_function = probe.isNotTouched
        
        # Going backwards until touch probe no longer touches anything
        approachUntilTouch(robot=probe.robot, touch_function=retract_touch_function,
            axis=axis,
            step=(-direction * current_step_dict['step_back']),
            speed_xy=current_step_dict['speed_xy_back'], 
            speed_z=current_step_dict['speed_z_back'])
        
        # Going forward until hitting the wall
        coord = approachUntilTouch(robot=probe.robot, touch_function=forward_touch_function,
            axis=axis, 
            step=(direction * current_step_dict['step_fwd']), 
            speed_xy=current_step_dict['speed_xy_fwd'], 
            speed_z=current_step_dict['speed_z_fwd'])
            
    # Retracting after calibration is finished
    [dx, dy, dz] = probe.robot.axisToCoordinates(axis=axis, value=(-direction * step_back_length))
    probe.robot.move_delta(dx=dx, dy=dy, dz=dz)
    
    return coord


def findWallManyPoints(probe, axis, direction, touch_coord_list, 
        second_probe=None, step_dict=None, step_back_length=3):
    """
    Probe wall against many points.
    
    Returns
        List of measured collision coordinates against a given axis
    """
    robot = probe.robot
    points_list = []
    for coord in touch_coord_list:
        if axis == 'x':
            robot.moveAxis(axis='y', destination=coord)
        else:
            robot.moveAxis(axis='x', destination=coord)
        wall_coord = findWall(probe=probe, axis=axis, direction=direction,
                                   second_probe=second_probe,
                                   step_dict=step_dict,
                                   step_back_length=step_back_length)
        points_list.append(wall_coord)
    return points_list
    
    
def findCenterOuterTwoProbes(probe1, probe2, axis, raise_height=None, dist_through_obstruct=None,
                        step_dict=None, step_back_length=3, opposite_side_dist=0, direction=1):
    # TODO: Remove raise_height and dist_through_obstruct completely, 
    # for now only left them for possible back compatibility
    # Assuming probe1 is a mobile probe; and probe2 is a stationary probe
    # TODO: Add routine to automatically find which probe is which.
    x_cal, y_cal, z_cal, opposite_x, orthogonal_y, raise_z = probe2.rack.getSimpleCalibrationPoints()
    if axis == 'x':
        dist_through_obstruct = opposite_x
    elif axis == 'y':
        dist_through_obstruct = orthogonal_y * 2
    # Find first wall
    front_wall = findWall(probe=probe1, 
                     axis=axis, 
                     direction=direction, 
                     step_dict=step_dict, 
                     second_probe=probe2)
    # Raise gantry
    probe1.robot.move_delta(dz=-raise_z)
    # Move through obstruction
    probe1.robot.moveAxisDelta(axis=axis, value=direction*dist_through_obstruct)
    # Lower gantry back
    probe1.robot.moveAxisDelta(axis='z', value=raise_z)
    # Find opposite side of the wall
    rear_wall = findWall(probe=probe1, 
                     axis=axis, 
                     direction=-direction, 
                     step_dict=step_dict,
                     second_probe=probe2)
    # Calculateing center
    center = (front_wall + rear_wall) / 2.0
    return center


class touch_probe():
    """
    Handles behavior of all touch probes, either mobile, or fixed position.
    """
    
#    step_dict = {
#                0: {'step_fwd': 12, 'speed_xy_fwd': 5000, 'speed_z_fwd':5000,
#                    'step_back': 12, 'speed_xy_back': 5000, 'speed_z_back':5000},
#                1: {'step_fwd': 3, 'speed_xy_fwd': 2000, 'speed_z_fwd':3000,
#                    'step_back': 6, 'speed_xy_back': 5000, 'speed_z_back':2000},
#                2: {'step_fwd': 0.75, 'speed_xy_fwd': 200, 'speed_z_fwd':1000,
#                    'step_back': 1.5, 'speed_xy_back': 500, 'speed_z_back':1000},
#                3: {'step_fwd': 0.2, 'speed_xy_fwd': 100, 'speed_z_fwd':1000,
#                    'step_back': 0.4, 'speed_xy_back': 100, 'speed_z_back':1000},
#                4: {'step_fwd': 0.05, 'speed_xy_fwd': 25, 'speed_z_fwd':1000,
#                    'step_back': 0.1, 'speed_xy_back': 50, 'speed_z_back':1000},
#            }

    step_dict = {
                0: {'step_fwd': 3, 'speed_xy_fwd': 1000, 'speed_z_fwd':2000,
                    'step_back': 3, 'speed_xy_back': 1000, 'speed_z_back':2000},
                1: {'step_fwd': 0.2, 'speed_xy_fwd': 200, 'speed_z_fwd':1000,
                    'step_back': 1, 'speed_xy_back': 500, 'speed_z_back':1000},
                2: {'step_fwd': 0.05, 'speed_xy_fwd': 25, 'speed_z_fwd':500,
                    'step_back': 0.2, 'speed_xy_back': 50, 'speed_z_back':500},
            }

    
    def isTouched(self):
        self.write('d')
        response = self.readAll()
        logging.info("Touch probe response: %s", response)
        return bool(int(re.split(pattern='/r/n', string=response)[0]))
    
    def isNotTouched(self):
        return not self.isTouched()    
    

    def approachUntilTouch(self, axis, step, retract=False, speed_xy=None, speed_z=None):
        # Determining condition at which movement will continue.
        if retract:
            # Function assumes touch probe is touching something
            # Goal is to move until probe stops touching
            touch_function = self.isTouched
        else:
            # Function assumes touch probe is not touching anything
            # Goal is to move until it starts touching
            touch_function = self.isNotTouched
        
        return approachUntilTouch(self.robot, touch_function, axis, step, speed_xy=None, speed_z=None)


    def findWall(self, axis, direction, step_dict=None, step_back_length=3):
        if step_dict is None:
            step_dict = touch_probe.step_dict
        return findWall(self, axis, direction, 
                   step_dict=step_dict, 
                   step_back_length=step_back_length)
        
    
    def findCenterInner(self, axis, step_dict=None, step_back_length=3, opposite_side_dist=0, direction=1):
        # Finding first wall
        front_wall = self.findWall(axis=axis, direction=direction, step_dict=step_dict)
        # Moving to the other wall
        self.robot.moveAxisDelta(axis=axis, value=-direction*opposite_side_dist)
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
        self.robot.moveAxisDelta(axis=axis, value=direction*dist_through_obstruct)
        # Lower gantry back
        self.robot.moveAxisDelta(axis='z', value=raise_height)
        # Find opposite side of the wall
        rear_wall = self.findWall(axis=axis, direction=-direction, step_dict=step_dict)
        # Calculateing center
        center = (front_wall + rear_wall) / 2.0
        return center



class mobile_touch_probe(mobile_tool, touch_probe):

    def __init__(self, robot, com_port_number=None, 
                 tool_name='mobile_touch_probe', tool_type=None, rack_name=None, rack_type=None, 
                 welcome_message='mobile touch probe'):
        self.step_dict = touch_probe.step_dict
        super().__init__(robot, com_port_number=com_port_number, 
                 tool_name=tool_name,
                 welcome_message=welcome_message)


    @classmethod
    def getTool(cls, robot):
        """
        Get touch probe from its saved position and initializes the object
        """
        cls.tool_name = "mobile_touch_probe"
        cls.welcome_message="mobile touch probe"
        return super().getTool(robot, 
            tool_name="mobile_touch_probe", welcome_message="mobile touch probe")
            
            
class stationary_touch_probe(tool, touch_probe):
    """
    Handles stationary touch probes
    """
    def __init__(self, robot, com_port_number=None, 
                 tool_name='stationary_probe', welcome_message='stationary touch probe'):
        self.step_dict = touch_probe.step_dict
        super().__init__(robot=robot, com_port_number=com_port_number, 
                 tool_name=tool_name,
                 welcome_message=welcome_message)


    
    
class mobile_gripper(mobile_tool):
    def operate_gripper(self, level):
        self.write(str(level))




device_type_descriptions = [
    {"class": cart.arnie, "message": "Marlin", "type": "", "mobile": False}, 
    {"class": stationary_touch_probe, "message": "stationary touch probe", "type": "stationary_probe", "mobile": False}, 
    {"class": mobile_touch_probe, "message": "mobile touch probe", "type": "mobile_probe", "mobile": True},
    {"class": pipettor, "message": "Servo", "type": "pipettor", "mobile": True},
    {"class": mobile_gripper, "message": "mobile circular gripper", "type": "mobile_gripper", "mobile": True},
    ]