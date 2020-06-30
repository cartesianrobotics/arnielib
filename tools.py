"""
Module handling tools for the robot, both mobile and floor-based
"""

import logging
from copy import deepcopy
import re
import cartesian as cart    # TODO: Remove it when finishing refactoring.
import json
import configparser
import time

# Internal arnielib modules
import low_level_comm as llc
import param
import racks

SPEED_Z_MOVING_DOWN = 4000 # Robot can move down much faster than up.

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
        self.config = configparser.ConfigParser()
        config_path = 'configs/' + tool_type + '.ini'
        self.config.read(config_path)
        
        # How much longer the tool is compared to the mobile touch probe.
        # This setting to be used only for calibration purposes, 
        # after which obtained Z coordinate will be used for the other operations.
        self.delta_length_for_calibration = float(self.config['calibration']['delta_length_for_calibration'])
        
        # The following values are used when calibrating the tool against immobile touch probe
        # They are loaded from the tool config file.
        # As of 3/25/2020, they are only used in calibration.calibrateToolCustomPoints
        
        # All data are stored in this dictionary:
        self.immobile_probe_calibration_points = {}
        
        # TODO: consider moving those settings to the mobile_gripper child class
        # as some tools will not be using those settings.
        try:
            self.immobile_probe_calibration_points['x_Xfrontal'] = float(
                    self.config['calibration']['x_position_for_X_axis_calibration_frontal'])
            self.immobile_probe_calibration_points['x_Xrear'] = float(
                    self.config['calibration']['x_position_for_X_axis_calibration_rear'])
            self.immobile_probe_calibration_points['y_X'] = float(
                    self.config['calibration']['y_position_for_X_axis_calibration'])
            self.immobile_probe_calibration_points['z_X'] = float(
                    self.config['calibration']['z_position_for_X_axis_calibration'])
            self.immobile_probe_calibration_points['x_Y'] = float(
                    self.config['calibration']['x_position_for_Y_axis_calibration'])
            self.immobile_probe_calibration_points['y_Yfrontal'] = float(
                    self.config['calibration']['y_position_for_Y_axis_calibration_frontal'])
            self.immobile_probe_calibration_points['y_Yrear'] = float(
                    self.config['calibration']['y_position_for_Y_axis_calibration_rear'])
            self.immobile_probe_calibration_points['z_Y'] = float(
                    self.config['calibration']['z_position_for_Y_axis_calibration'])
            self.immobile_probe_calibration_points['raise_z'] = float(
                    self.config['calibration']['raise_z_to_move_over_the_probe'])
            self.immobile_probe_calibration_points['dx_Z'] = float(
                    self.config['calibration']['delta_x_position_for_Z_axis_calibration'])
            self.immobile_probe_calibration_points['dy_Z'] = float(
                    self.config['calibration']['delta_y_position_for_Z_axis_calibration'])
        except:
            pass
        try:
            self.step_back_length = float(self.config['calibration']['step_back_length'])
        except:
            self.step_back_length = 3
        

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


    def getHowMuchLongerIsTheToolRelativeToTouchProbe(self):
        return self.delta_length_for_calibration


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
    
    
    def _protectiveZMove(self, z_current, z_safe, movement_allowed):
        if z_current > z_safe and movement_allowed:
            self.robot.move(z=z_safe)
        return self.robot.getAxisPosition(axis='z')


    def getToSample(self, sample, z_above_the_top=10, move_z=True):
        """
        Will move robot towards the sample
        Inputs:
            sample
                Instance of the sample object. Must be placed into a rack 
                by running sample.place(rack, column, row)
            z_above_the_top
                Tells function how much to lift Z above sample highest point.
                Useful to prevent collisions, but won't check for other samples
                that may be higher. 
            move_z
                If False, will not perform height check, and will not move Z axis at all.
                
        """
        # Current Z position
        z = self.robot.getAxisPosition(axis='z')
        # Z coordinate of the top of the sample
        z_sample_top = sample.getSampleTopZ(self)
        # Safe Z coordinate to approach.
        z_safe = z_sample_top - z_above_the_top
        # If the end of the tool is lower than safe Z coordinate, raise Z gantry
        # Higher z value, lower the gantry is.
        self._protectiveZMove(z, z_safe, move_z)
        # Moving to the sample position
        x, y = sample.getSampleCenterXY(self)
        self.robot.move(x=x, y=y)

    def getToPosition(self, rack, column, row, z_above_the_top=10):
        """
        Moves robot towards specified position. X an Y only; Z may be rizen, but not lowered.
        """
        # Current Z position
        z = self.robot.getAxisPosition(axis='z')
        
        x, y, z_working = rack.calcWorkingPosition(well_col=column, well_row=row, tool=self)
        z_safe = z_working - z_above_the_top
        self._protectiveZMove(z, z_safe, True)
        self.robot.move(x=x, y=y)
        
    def getToRackCenter(self, rack, z_above_the_top=10):
        """
        Moves the robot towards the center of the specified rack, only X and Y; 
        Z may be rizen if determined as too low; but not lowered.
        """
        # Current Z position
        z = self.robot.getAxisPosition(axis='z')
        
        # Finding coordinates of the center of the rack, using all the calibrations
        x, y, z_working = rack.calcRackCenterFullCalibration(tool=self)
        
        z_safe = z_working - z_above_the_top
        self._protectiveZMove(z, z_safe, True)
        self.robot.move(x=x, y=y)
        
    
class pipettor(mobile_tool):

    def __init__ (self, robot, tool_name, 
                  rack_name=None, rack_type=None, 
                  tool_type=None, com_port_number=None, 
                  welcome_message=None):
        super().__init__(robot=robot, com_port_number=com_port_number,
                         tool_name=tool_name, welcome_message='Servo', 
                         rack_type='pipette_rack', rack_name=tool_name+'_rack')
        
        # Loading parameters specific to pipettors from config file
        self.tip_added_z_length = float(self.config['geometry']['tip_added_length'])
        # Maximum volume to pipette
        self.max_allowed_vol = float(self.config['pipetting']['max_volume'])
        # Plunger slack compensation volume
        # After uptaking a liquid, the pipette will release this volume of the liquid to the same tube
        try:
            self.plunger_slack_compensation_volume = float(self.config['pipetting']['plunger_slack_compensation_volume'])
        except:
            self.plunger_slack_compensation_volume = 0
        
        # Switch indicating whether tip is attached or not.
        self.tip_attached = False
        
        # Homing pipettor
        if self.tool_name == 'p20':
            self.home(pipettor_speed=300)
        else:
            self.home(pipettor_speed=750)        
            
        
        
            
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
        self.sendCmdToPipette("$X")
        self.movePlunger(-10)
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
        self.tip_attached = True
        # Raise with a tip
        raise_with_tip_z = z - raise_dz_with_tip
        self.robot.move(z=raise_with_tip_z)


    def dropOffTipToPosition(self, rack, column, row, raise_z=0, dropoff_dz=10):
        # Obtaining coordinate of the tip position
        x, y, z = rack.calcWorkingPosition(column, row, self)
        # Moving up
        self.robot.move(z=raise_z)
        # Moving above dropoff position
        self.robot.move(x=x, y=y)
        # Lowering Z to dropoff height
        z_dropoff = z - dropoff_dz
        self.robot.move(z=z_dropoff)
        # Dropping off tip
        self.dropTip()
        
    def dropTipToWaste(self, waste_rack, raise_z=0):
        self.dropOffTipToPosition(rack=waste_rack, column=0, row=0, raise_z=raise_z)

    
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
        self.tip_attached = False
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


    def movePlungerToVol(self, volume):
        """
        Moves plunger according to the desired volume position.
        """
        # Calculating plunger position from desired volume
        # k - slope, b - intercept
        k = self.tool_data['volume_to_position_slope']
        b = self.tool_data['volume_to_position_intercept']
        position = volume * k + b
        # Minus is because movement scale is currently from 0 (close to home) to -40
        # farthest from home. The model calibration was done using positive values
        # TODO: add minus to the calibration raw data; remove this minus.
        self.movePlunger(position)

    def setPlungerToVolConstants(self, slope, intercept):
        """
        Specifies constants for function to recalculate volume to plunger position
        """
        self.tool_data['volume_to_position_slope'] = slope
        self.tool_data['volume_to_position_intercept'] = intercept
        # Saving slope and intercept parameters
        self.save()

    
    def uptakeLiquid(self, sample, volume, uptake_delay=0, immerse_volume=None, tip_ignore=False,
                     move_z_before_and_after_uptake=True, bottom_gap=10, retract_z_speed=100):
        """
        Uptakes specified volume of liquid from the sample.
        Inputs:
            sample
                object of class sample. This function will try to read all necessary settings
                from that object
            volume
                Volume that you want to uptake. All volume values are in microliters.
            uptake_delay
                At the end of uptake, robot will wait specified number of seconds.
                This is useful when the liquid is viscous, and needs time to get into a tip
                Default is 0.
            immerse_volume
                Robot will immerse the tip to the specified volume mark. 
                If not specified, the robot will immerse the tip just below the current 
                liquid level in the sample; obtained from sample current volume and 
                height vs. volume dependence of the sample.
            tip_ignore
                Normally, function checks on whether the tip is attached to the pipettor, 
                and will only proceed if attached. If this parameter is specified as True,
                this check will be omitted.
            move_z_before_and_after_uptake
                If False, will not move z axis when approaching to the sample,
                and will not retract it when done pipetting.
        """
        # Checking whether the pipettor has a tip.
        # Will stop function if tip is not attached 
        if (not self.tip_attached) and (not tip_ignore):
            print("ERROR: pipette tip was not attached.")
            return
        # Moving robot towards the sample
        self.getToSample(sample=sample, move_z=move_z_before_and_after_uptake)
        
        
        # Moving plunger down
        self.movePlungerToVol(volume)
        
        # Checking whether custom immerse depth is provided; if not, 
        # immerse depth will be calculated from volume that will be left in the sample
        # after finishing pipetting.
        # TODO: add also percent and relative depth
        if immerse_volume is None:
            curr_sample_vol = sample.getVolume()
            resulting_volume = curr_sample_vol - volume
            # You must immerse tool deeper than just resulting volume,
            # to prevent uptaking bubbles.
            # Robot will calculate extra immerse from the maximum sample volume
            max_vol = sample.getMaxVolume()
            immerse_vol_fraction = max_vol * 0.1
            immerse_volume = resulting_volume - immerse_vol_fraction
            # It may be that the sample has just enough liquid to pipette.
            # In this case robot is lowering itself right to the bottom.
            if immerse_volume < 0:
                immerse_volume = 0
        
        # Pipetting procedure will differ on whether the tip is fully immersed into the tube
        if immerse_volume == 0:
            # Tip should be fully immersed,
            # the bottom of the tube will block liquid from uptaking.
            # Solution is lower not fully to the bottom; uptake most of the liquid, then
            # lower all the way down, and slowly retract, so remaining liquid has time to be 
            # uptaken
            z_immerse = sample.sampleVolToZ(volume=immerse_volume+bottom_gap, tool=self)
            self.robot.move(z=z_immerse)
            self.movePlungerToVol(bottom_gap)
            time.sleep(uptake_delay)
            z_immerse = sample.sampleVolToZ(volume=immerse_volume, tool=self)
            self.robot.move(z=z_immerse)
            self.movePlungerToVol(0)
            time.sleep(uptake_delay)
            z_immerse = sample.sampleVolToZ(volume=immerse_volume+bottom_gap, tool=self)
            self.robot.move(z=z_immerse, speed_z=retract_z_speed)
        else:
            # Now (finally) uptaking the liquid
            z_immerse = sample.sampleVolToZ(volume=immerse_volume, tool=self)
            self.robot.move(z=z_immerse)
            self.movePlungerToVol(0)
            time.sleep(uptake_delay)
        
        # Updating sample volume
        old_sample_vol = sample.getVolume()
        new_sample_vol = old_sample_vol - volume
        sample.setVolume(new_sample_vol)


    def _sideTubeUptake(self, extra_vol, uptake_delay, uptake_vol, axis, distance, dz):
        extra_vol = extra_vol - uptake_vol
        self.robot.moveAxisDelta(axis=axis, value=distance)
        self.robot.moveAxisDelta(axis='z', value=dz)
        self.movePlungerToVol(extra_vol)
        time.sleep(uptake_delay)
        self.robot.moveAxisDelta(axis='z', value=-dz)
        time.sleep(uptake_delay)
        self.robot.moveAxisDelta(axis=axis, value=-distance)
        return extra_vol

    
    def uptakeAll(self, sample, tip_ignore=False, volume=None, extra_vol_frac=0.2, 
                  immerse_levels_list=[10, 0], side_uptake_radius=2,  uptake_delay=0):
        """
        This function tries to uptake all the liquid that the tube may have, drying it up completely.
        Inputs:
            sample
                Object of a sample class. Used to obtain volume and movement parameters
            tip_ignore
                When True, do not perform the check on whether the tip is present. Default False.
            volume
                Expected volume in the sample. When provided, this value will be used
                to calculate uptaking scenario, instead of the value stored in sample object
            extra_vol_frac
                Tool will try to uptake move volume than there is in the tube, to make sure it is dry.
                This parameter specifies what fraction of the total maximum sample volume 
                will be used. Example: if tube max volume is 2 mL, currently tube contains 500 uL,
                and extra_vol_frac = 0.1, than the tool will try to uptake 700 uL.
            immerse_levels_list
                List of volumes at which to perform uptake. Robot will move to the first value,
                and uptake "volume" amount. Then it will move to the next value and uptake little 
                bit more, and so on. Total uptaken volume is volume + max_vol * extra_vol_frac
            side_uptake_radius
                Robot will attempt to uptake liquid at the center and little to the sides,
                to get possible droplets at the side of the tube. This value shows distance from
                the center at which to uptake.
            uptake_delay
                Will wait that number of seconds after moving plunger up. Use when liquid is 
                viscous.
        """
        
        if (not self.tip_attached) and (not tip_ignore):
            print("ERROR: pipette tip was not attached.")
            return
        
        # Moving robot towards the sample
        self.getToSample(sample=sample)
    
        # Figuring out volume
        if volume is None:
            volume = sample.getVolume()
        
        tool_max_vol = self.max_allowed_vol
        extra_vol = tool_max_vol * extra_vol_frac
        # Moving plunger down
        self.movePlungerToVol(volume+extra_vol)
        # Immersing into the tube
        z = sample.sampleVolToZ(volume=immerse_levels_list[0], tool=self)
        self.robot.move(z=z)
        # Uptaking most of the liquid volume (until extra volume mark)
        self.movePlungerToVol(extra_vol)
        time.sleep(uptake_delay)
        # Now going through the rest of the immersing levels
        vol_uptake_per_cycle = extra_vol / (len(immerse_levels_list[1:]) * 1.0)
        vol_uptake_per_suck = vol_uptake_per_cycle / 5.0
        for level in immerse_levels_list[1:]:
            z_low = sample.sampleVolToZ(volume=level, tool=self)
            z_high = sample.sampleVolToZ(volume=immerse_levels_list[0], tool=self)
            dz = z_low - z_high
            # Sucking at the center
            extra_vol = self._sideTubeUptake(extra_vol, uptake_delay/5.0, 
                                       vol_uptake_per_suck, 'x', 0, dz)
            # Sucking at the north
            extra_vol = self._sideTubeUptake(extra_vol, uptake_delay/5.0, 
                                       vol_uptake_per_suck, 'y', -side_uptake_radius, dz)
            # Sucking at the south
            extra_vol = self._sideTubeUptake(extra_vol, uptake_delay/5.0, 
                                       vol_uptake_per_suck, 'y', side_uptake_radius, dz)
            # Sucking at the west
            extra_vol = self._sideTubeUptake(extra_vol, uptake_delay/5.0, 
                                       vol_uptake_per_suck, 'x', -side_uptake_radius, dz)
            # Sucking at the east
            extra_vol = self._sideTubeUptake(extra_vol, uptake_delay/5.0, 
                                       vol_uptake_per_suck, 'x', side_uptake_radius, dz)
        sample.setVolume(0)
        
        
    
    def dispenseLiquid(self, sample, volume, 
                       dx=0, dy=0, release_delay=0, immerse_volume=None, plunger_retract=True,
                       blow_extra=False):
        """
        Dispenses liquid from pipettor tip into specified sample
        """
        # Moving robot towards the sample
        self.getToSample(sample=sample)
        # If shift is needed, here it goes:
        self.robot.moveAxisDelta(axis='x', value=dx)
        self.robot.moveAxisDelta(axis='y', value=dy)
        # What is maximum volume can fit in this sample?
        max_vol = sample.getMaxVolume()
        # Lowering tip into the tube
        # But first checking if the depth to immerse is specified
        # TODO: add also heigth to immerse, and % of tube height
        if immerse_volume is None:
            immerse_vol_fraction = max_vol * 0.1
            # Currently tip will be immersed to 10% of the volume
            # TODO: make it so user can specify percent themselves.
            immerse_volume = max_vol - immerse_vol_fraction
        # Actually lowering tip
        z_immerse = sample.sampleVolToZ(volume=immerse_volume, tool=self)
        self.robot.move(z=z_immerse)
        # Actually dispensing the liquid
        self.movePlungerToVol(volume)
        # Updating volume amount in the tube
        old_sample_vol = sample.getVolume()
        new_sample_vol = old_sample_vol + volume
        sample.setVolume(new_sample_vol)
        # Not lifting the tip, in case you need to touch the wall or liquid,
        # or pipette up and down.
        # If requested, returning plunger back to 0.
        # Some cases may require not retracting plunger, such as serial_device
        # filling of many tubes with one liquid
        if blow_extra:
            self.movePlunger(-40)
        if plunger_retract:
            # Now lifting the tip, if plunger retraction was chosen
            z_retract = sample.sampleVolToZ(volume=max_vol + max_vol * 0.2, tool=self)
            self.robot.move(z=z_retract)
            self.movePlungerToVol(0)
    
    
    def touchWall(self, sample, volume=None, movement=None):
        """
        Touches wall of the sample
        Used after finishing pipetting, to remove remaining drop from the tip.
        """
        # It is better to touch wall as low as possible into the sample.
        # First, figure out how much sample is filled, and get sample height
        # above the liquid
        if volume is None:
            volume = sample.getVolume() + sample.getVolume() * 0.2
        if volume > sample.getMaxVolume():
            volume = sample.getMaxVolume()
        # Calculating absolute Z value for given sample, at volume with given tool
        z = sample.sampleVolToZ(volume=volume, tool=self)
        # Moving to the level at which wall will be touched
        self.robot.move(z=z)
        # Calculating touch wall coordinates
        x, y, z = self.robot.getPosition()
        if movement is None:
            movement = sample.inner_diameter / 2.0
        y_touch = y + movement
        # Moving to touch wall
        self.robot.move(y=y_touch)
        # Moving back
        self.robot.move(y=y)
                

    def uptakeLiquidGradually(self, sample, volume, dv, immerse_vol_frac=0.1, uptake_delay=0):
        """
        Uptake given amount of liquid not all at once, but little by little, 
        gradually immersing pipette into the sample.
        Sometimes, if you fully immerse a tip into the liquid, it will 
        spill out of the tube. This function prevents that to happen, by 
        gradually immersing the tip into the liquid and uptaking liquid little by little, 
        until desired volume is obtained.
        """
        # This is the volume that remains to pipette
        remaining_vol = volume
        max_vol = sample.getMaxVolume()
        immerse_dv = max_vol * immerse_vol_frac
        while remaining_vol > 0:
            # Checking if this is the first pipetting
            if remaining_vol == volume:
                #Approaching the sample
                self.getToSample(sample=sample)
                self.movePlungerToVol(volume)
            curr_sample_vol = sample.getVolume()
            # Pipetting
            if remaining_vol >= dv:
                curr_sample_vol = curr_sample_vol - dv
                remaining_vol = remaining_vol - dv
            else:
                # Executes when volume that remains to pipette is smaller than 
                # volume iteration. This is the final stage of pipetting
                curr_sample_vol = curr_sample_vol - remaining_vol
                remaining_vol = 0
            
            immerse_volume = curr_sample_vol - immerse_dv
            # It may be that the sample has just enough liquid to pipette.
            # In this case robot is lowering itself right to the bottom.
            if immerse_volume < 0:
                immerse_volume = 0
            # Calculating absolute immerse height
            z_immerse = sample.sampleVolToZ(volume=immerse_volume, tool=self)
            # Moving sample to the immerse height
            self.robot.move(z=z_immerse)
            # Now (finally) uptaking the liquid
            self.movePlungerToVol(remaining_vol)
            time.sleep(uptake_delay)
            sample.setVolume(curr_sample_vol)

        
    def pipetteUpAndDown(self, sample, uptake_volume, repeats, gradual_vol=0, immerse_to_vol=None, 
                         uptake_delay=0, release_delay=0):
        """
        Pipette sample up and down. Used to mix a sample
        """
        if gradual_vol > 0:
            # Use gradual pipetting up and down
            for i in range(repeats):
                self.uptakeLiquidGradually(sample=sample, volume=uptake_volume, dv=gradual_vol,
                                           uptake_delay=uptake_delay)
                self.dispenseLiquid(sample=sample, volume=uptake_volume, 
                                    release_delay=release_delay, plunger_retract=False)
        else:
            # Using normal pipetting
            for i in range(repeats):
                self.uptakeLiquid(sample=sample, volume=uptake_volume, uptake_delay=uptake_delay)
                self.dispenseLiquid(sample=sample, volume=uptake_volume, 
                                    release_delay=release_delay, plunger_retract=False)
        # Moving up and releasing remaining liquid
        max_vol = sample.getMaxVolume()
        z = sample.sampleVolToZ(volume=max_vol+max_vol*0.2, tool=self)
        self.robot.move(z=z)
        # Moving plunger down as much as possible
        self.movePlunger(-40)
        self.touchWall(sample=sample)
        # Z up
        self.robot.move(z=z)
        # Plunger back to 0
        self.movePlungerToVol(0)
        
    
    def moveLiquid(self, sample_origin, sample_destination, volume, raise_z=None,
                   uptake_delay=0, release_delay=0, immerse_volume_origin=None, 
                   immerse_volume_destination=None, blow_extra=False, touch_wall=False):
        """
        Moves liquid from one sample to the other
        """
        self.uptakeLiquid(sample=sample_origin, volume=volume, uptake_delay=uptake_delay,
                          immerse_volume=immerse_volume_origin)
        # Raising Z level, to prevent the case when robot would hit something on its way
        if raise_z is not None:
            self.robot.move(z=raise_z)
        self.dispenseLiquid(sample=sample_destination, volume=volume, release_delay=release_delay,
                            immerse_volume=immerse_volume_destination, blow_extra=blow_extra)
        if touch_wall:
            self.touchWall(sample=sample_destination)
        
    
    
    def distributeLiquid(self, sample_origin, sample_destination_list, vol_list, raise_z=None,
                         raise_z_between_wells = None,
                         uptake_delay=0, release_delay=0, immerse_vol_origin=None,
                         immerse_volume_destination=None, touch_wall=False):
        """
        Takes liquid from one place and pipettes it into several samples sequentially, 
        according to the provided instructions
        """
        # Represents current volume of liquit inside pipettor's tip
        vol_in_tip = 0
        # This is how much total volume needs to be moved (to all samples)
        remaining_vol_to_move = sum(vol_list)
        # Represents absolute position (in microliters) to which to move
        # plunger while dispensing
        vol_to_move_plunger = 0
        for sample_destination, volume in zip(sample_destination_list, vol_list):
            # Every next cycle more liquid is dispensed, which is equivalent to 
            # moving plunger to more volume
            vol_to_move_plunger = vol_to_move_plunger + volume
            # Checking if tip has enough liquid in it
            # If not, taking liquid from sample of origin
            if vol_in_tip < volume:
                # Raising Z axis before moving to the origin sample
                if raise_z is not None:
                    self.robot.move(z=raise_z)
                # Moving to the sample origin
                self.getToSample(sample=sample_origin)
                # Plunger all the way down, to remove all liquid that may remain in 
                # the tip from previous pipetting
                self.movePlunger(-40)
                # Touch wall to remove a possible droplet
                self.touchWall(sample=sample_origin)
                vol_in_tip = 0 # Now tip is empty
                # Moving back up to make sure no liquid is taken when moving plunger up
                self.getToSample(sample=sample_origin)
                # Figuring out how much liquid to uptake
                if remaining_vol_to_move > self.max_allowed_vol:
                    vol_to_uptake = self.max_allowed_vol + self.plunger_slack_compensation_volume
                else:
                    vol_to_uptake = remaining_vol_to_move + self.plunger_slack_compensation_volume
                # Actually uptaking liquid
                self.uptakeLiquid(sample=sample_origin, volume=vol_to_uptake,
                                  uptake_delay=uptake_delay)
                vol_in_tip = vol_to_uptake
                # Dispensing a little of liquid back to the origin tube to 
                # compensate for the plunger movement slack
                self.dispenseLiquid(sample=sample_origin, volume=self.plunger_slack_compensation_volume,
                    release_delay=release_delay, plunger_retract=False)
                vol_in_tip = vol_in_tip - self.plunger_slack_compensation_volume
                # Resetting absolute position every time tip is refilled
                vol_to_move_plunger = volume + self.plunger_slack_compensation_volume
                # Touching the liquid to remove droplet
                curr_sample_vol = sample_origin.getVolume()
                z_immerse = sample_origin.sampleVolToZ(volume=curr_sample_vol, tool=self)
                self.robot.move(z=z_immerse)
                # Raising Z axis after uptaking liquid, to move towards destination sample
                if raise_z is not None:
                    self.robot.move(z=raise_z)
                # Moving towards destination sample
                self.getToSample(sample=sample_destination)
            # Adjusting Z level between destination samples
            if raise_z_between_wells is not None:
                self.robot.move(z=raise_z_between_wells)
            # Now pipetting liquid into the next destination
            # Take care not to retract plunger
            self.dispenseLiquid(sample=sample_destination, volume=vol_to_move_plunger, 
                                release_delay=release_delay, plunger_retract=False)
            vol_in_tip = vol_in_tip - volume
            # Touching wall to remove stuck groplet, if necessary
            if touch_wall:
                self.touchWall(sample=sample_destination)
            # Decreasing total remaining volume to move
            remaining_vol_to_move = remaining_vol_to_move - volume
            
    

    def getHowMuchLongerIsTheToolRelativeToTouchProbe(self):
        if self.tip_attached:
            return self.delta_length_for_calibration + self.tip_added_z_length
        else:
            return self.delta_length_for_calibration

    def getStalagmyteCoord(self):
        """
        Returns #stalagmyte (or #immobile_touch_probe) coordinates, that are 
        saved in the object after calibration
        """
        if self.tip_attached:
            return self.immob_probe_x, self.immob_probe_y, self.immob_probe_z - self.tip_added_z_length
        else:
            return self.immob_probe_x, self.immob_probe_y, self.immob_probe_z


# Some functions may involve both mobile and immobile touch probes simultaneously;
# and so, have to be moved out of the classes.
# Example is calibration of stalagmite against stalaktite; during which
# both are checked for whether they touch anything.

def approachUntilTouch(robot, touch_function, axis, step, speed_xy=None, speed_z=None, max_travel_dist=-1):
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
            max_travel_dist
                maximum distance allowed to travel before engaging into 
                sticky probe recovery. 
                -1 means no limit. Default is -1
    """
    
    # Getting speed defaults from the robot instance.
    if speed_xy is None:
        speed_xy = robot.speed_x
    if speed_z is None:
        speed_z = robot.speed_z
    
    # Obtaining initial coordinate
    # This is needed for probe unstucking protocol.
    starting_coord = robot.getAxisPosition(axis)
    
    dC = robot.axisToCoordinates(axis, step)
    
    while touch_function():
        robot.move_delta(dx=dC[0], dy=dC[1], dz=dC[2], speed_xy=speed_xy, speed_z=speed_z)
        # Checking to make sure robot did not go beyond maximum allowed travel distance
        current_coord = robot.getAxisPosition(axis)
        travelled_dist = abs(starting_coord - current_coord)
        if max_travel_dist >= 0 and travelled_dist > max_travel_dist:
            # Moving back to initial position, at which touch probe was physically touching something
            # It hopefully will unstuck
            robot.moveAxis(axis, starting_coord)
        
    
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
        
        # Determining max travel distance for retraction
        # To fix probe sticktion
        if key == 0:
            max_travel_dist = current_step_dict['step_back'] * 2
        else:
            max_travel_dist = step_dict[key-1]['step_back'] * 2
        
        # Going backwards until touch probe no longer touches anything
        approachUntilTouch(robot=probe.robot, touch_function=retract_touch_function,
            axis=axis,
            step=(-direction * current_step_dict['step_back']),
            speed_xy=current_step_dict['speed_xy_back'], 
            speed_z=current_step_dict['speed_z_back'],
            max_travel_dist=max_travel_dist)
        
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
            step_dict = self.step_dict
        return findWall(self, axis, direction, 
                   step_dict=step_dict, 
                   step_back_length=step_back_length)
        
    
    def findCenterInner(self, axis, step_dict=None, opposite_side_dist=0, direction=1, step_back_length=3):
        # Finding first wall
        front_wall = self.findWall(axis=axis, direction=direction, step_dict=step_dict,
                                   step_back_length=step_back_length)
        # Moving to the other wall
        self.robot.moveAxisDelta(axis=axis, value=-direction*opposite_side_dist)
        # Finding second wall
        rear_wall = self.findWall(axis=axis, direction=-direction, step_dict=step_dict, 
                                  step_back_length=step_back_length)
        # Calculating center
        center = (front_wall + rear_wall) / 2.0
        return center
    
    
    def findCenterOuter(self, axis, raise_height, dist_through_obstruct,
                        step_dict=None, opposite_side_dist=0, direction=1, 
                        step_back_length=3):
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
        front_wall = self.findWall(axis=axis, direction=direction, step_dict=step_dict, 
                                   step_back_length=step_back_length)
        # Raise gantry
        self.robot.move_delta(dz=-raise_height)
        # Move through obstruction
        self.robot.moveAxisDelta(axis=axis, value=direction*dist_through_obstruct)
        # Lower gantry back
        self.robot.moveAxisDelta(axis='z', value=raise_height)
        # Find opposite side of the wall
        rear_wall = self.findWall(axis=axis, direction=-direction, step_dict=step_dict, 
                                  step_back_length=step_back_length)
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


    def __init__(self, robot, com_port_number=None, 
                 tool_name='mobile_gripper', tool_type=None, rack_name=None, rack_type='mobile_gripper_rack', 
                 welcome_message='mobile gripper'):
        super().__init__(robot, com_port_number=com_port_number, 
                 tool_name=tool_name,
                 welcome_message=welcome_message)
        self.eol = ''
        self.gripper_has_something = False
        self.added_z_length = 0
        self.sample = None

    @classmethod
    def getTool(cls, robot, tool_name="mobile_gripper", rack_type='mobile_gripper_rack',
            welcome_message="mobile gripper"):
        """
        Get touch probe from its saved position and initializes the object
        """
        cls.tool_name = tool_name
        cls.welcome_message=welcome_message
        return super().getTool(robot, 
            tool_name=tool_name, welcome_message=welcome_message, rack_type=rack_type)

    def powerUp(self):
        self.writeAndWait("P on", confirm_message='\r\n')
        
    def powerDown(self):
        self.writeAndWait("P off", confirm_message='\r\n')
        
    def moveServo(self, angle):
        self.writeAndWait("G0 "+str(angle), confirm_message='\r\n')
        
    def operateGripper(self, angle, powerdown=True):
        self.powerUp()
        self.moveServo(angle)
        time.sleep(1.5)
        if powerdown:
            self.powerDown()

    def toDiameter(self, diameter, powerdown=True):
        """
        Opens gripper to specified diameter
        Inputs:
            diameter
                diameter to open gripper to, mm
            powerdown
                when True, power of the servo motor responsible for moving
                gripper jaws will be cut down after finishing movements.
                This prevents servo motor stalling, overheating and eventual failure.
        """
        k = self.tool_data['angle_to_diam_slope']
        b = self.tool_data['angle_to_diam_intercept']
        angle = k * diameter + b
        self.operateGripper(angle=angle, powerdown=powerdown)
        
        
    def setAngleToDiameterConstants(self, slope, intercept):
        """
        Specifies constants for function to that recalculates diameter to 
        servo motor angle.
        """
        self.tool_data['angle_to_diam_slope'] = slope
        self.tool_data['angle_to_diam_intercept'] = intercept
        # Saving slope and intercept parameters
        self.save()

    def grabSample(self, sample, vol_to_grab=None, dz_to_grab=None,
                   man_open_diam=None, man_grip_diam=None, powerdown=False,
                   extra_retraction_dz=20):
        """
        Grabs a specified sample
        Inputs
            sample  
                object of sample class, provides parameters necessary to interact with the sample
            vol_to_grab
                This is the volume level at which function will grab the sample
                If not provided, then maximum volume level will be used
            dz_to_grab
                Level relative to the top of the sample, at which function will grab the sample
                If not provided, maximum volume level will be used
            man_open_diam
                Allows to specify diameter to open gripper.
                If not provided, sample settings will be used
            man_grip_diam
                Allows to specify diameter to grab the sample
                If not provided, sample settings will be used
            powerdown
                If True value is set, servo power will be off after grabbing sample
                Default is False
            extra_retraction_dz
                Allows to set how much more to lift the sample after grabbing, 
                in addition to the sample settings
                Default is 20 mm
        """
        # Moving robot towards the sample
        self.getToSample(sample=sample)
        # Open gripper
        if man_open_diam is not None:
            open_diam = man_open_diam
        elif sample.isCapped():
            # TODO: add procedures for capped samples
            pass
        else:
            open_diam = sample.getUncappedGrippingOpenDiam()
        self.toDiameter(diameter=open_diam, powerdown=powerdown)
        
        # Moving gripper down to grab
        if dz_to_grab is not None:
            z_grab = sample.sampleRelativeZtoAbsoluteZ(dZ=dz_to_grab, tool=self)
        elif vol_to_grab is not None:
            z_grab = sample.sampleVolToZ(volume=vol_to_grab, tool=self)
        else:
            max_vol = sample.getMaxVolume()
            fraction_vol_to_grab = max_vol * 0
            # Currently gripper will be immersed to 0% of the volume
            # For example, if volume is 50 uL, then gripping will happend at 50 uL position.
            # TODO: make it so user can specify percent themselves.
            vol_to_grab = max_vol - fraction_vol_to_grab
            z_grab = sample.sampleVolToZ(volume=vol_to_grab, tool=self)
            
#        if vol_to_grab is None:
#            max_vol = sample.getMaxVolume()
#            fraction_vol_to_grab = max_vol * 0
#            # Currently gripper will be immersed to 0% of the volume
#            # For example, if volume is 50 uL, then gripping will happend at 50 uL position.
#            # TODO: make it so user can specify percent themselves.
#            vol_to_grab = max_vol - fraction_vol_to_grab
#        z_grab = sample.sampleVolToZ(volume=vol_to_grab, tool=self)
        self.robot.move(z=z_grab)
        
        # Actually grabbing the tube
        if man_grip_diam is not None:
            grab_diam = man_grip_diam
        elif sample.isCapped():
            # TODO: add procedures for capped samples
            pass
        else:
            grab_diam = sample.getUncappedGripDiam()
        self.toDiameter(diameter=grab_diam, powerdown=powerdown)
        # Temporary storing sample object in the tool, as it will be used
        # to calculate parameters to place it somewhere.
        self.sample = sample
        dist_top_to_grab_point = sample.getDepthFromVolume(vol_to_grab)
        self.sample.setSampleEngagedPosition(dist_top_to_grab_point)
        self.added_z_length = sample.getSampleRemainingLength(dist_top_to_grab_point)
        self.gripper_has_something = True
        # Calculating retraction height. It will be same as z_grab,
        # but now sampleVolToZ will account for added_z_length and extra_retraction_dz
        z_retract = sample.sampleVolToZ(volume=vol_to_grab, tool=self) - extra_retraction_dz
        
        ## Figuring the height to lift the sample, so it is out of the rack
        #dist_top_to_grab_point = sample.getDepthFromVolume(vol_to_grab)
        #dist_top_to_bottom = sample.getDepthFromVolume(0)
        #sample_protrude_from_gripper = dist_top_to_bottom - dist_top_to_grab_point
        #full_retraction_dz = sample_protrude_from_gripper + extra_retraction_dz
        #z_retract = z_grab - full_retraction_dz
        self.robot.move(z=z_retract)
        
    
    def placeSample(self, rack, column, row, vol_grabbed=None, man_open_diam=None, 
                    powerdown=True, retract=20, dz=0):
        """
        Places sample that the gripper currently holding into the specified position.
        Inputs:
            rack
                object of a rack class
            column, row 
                slot in the rack to place sample into
            vol_grabbed
                Only for compatibility, currently not used
            man_open_diam
                Specify the diameter to which to open the gripper. If not provided,
                function uses value from sample settings.
            powerdown
                After releasing the sample, power down servo motor. If False, than 
                the motor is kept powered up
            retract
                value at which to raise gripper after releasing the sample.
                Default is 20 mm
            dz
                When placing the sample, you can specify how much deeper the sample
                need to be placed. Default is 0, and the insertion is calculated
                according to the sample settings.
        """
        # Moving X and Y to the rack position
        self.getToPosition(rack=rack, column=column, row=row)
        x, y, z = rack.calcWorkingPosition(well_col=column, well_row=row, tool=self)
        # "placing" sample into the new position
        self.sample.place(rack, column, row)
        # Calculating Z to which to lower the sample 
        # Sample now has parameters of the destination rack and place
        rack_depth = self.sample.length - self.sample.getSampleHeightAboveRack()
        z_final = z + rack_depth + dz
        self.robot.move(z=z_final)
        # Opening gripper
        if man_open_diam is not None:
            open_diam = man_open_diam
        elif self.sample.isCapped():
            # TODO: add procedures for capped samples
            pass
        else:
            open_diam = self.sample.getUncappedGrippingOpenDiam()
        self.toDiameter(diameter=open_diam, powerdown=powerdown)
        # Making sample not in gripper
        self.sample.disengage()
        self.gripper_has_something = False
        self.added_z_length = 0
        sample = self.sample
        self.sample = None
        
        # Retracting
        self.robot.moveAxisDelta(axis='z', value=-retract)
        
        return sample
    
    
    def placePlate(self, rack, man_open_diam=None, powerdown=True, retract=20, dz=0):
        """
        Places the plate that is currently grabbed into the rack.
        This function assumes that the plate geometry matches rack (96 wells plate -> 96 wells rack)
        """
        # Moving X and Y to the rack position
        self.getToRackCenter(rack=rack)
        x, y, z = rack.calcRackCenterFullCalibration(tool=self)
        # "Placing" to the new rack
        self.sample.place(rack)
        # Calculating Z to which to lower the sample 
        # Sample now has parameters of the destination rack and place
        rack_depth = self.sample.length - self.sample.getSampleHeightAboveRack()
        z_final = z + rack_depth + dz
        self.robot.move(z=z_final)
        # Opening gripper
        if man_open_diam is not None:
            open_diam = man_open_diam
        elif self.sample.isCapped():
            # TODO: add procedures for capped samples
            pass
        else:
            open_diam = self.sample.getUncappedGrippingOpenDiam()
        self.toDiameter(diameter=open_diam, powerdown=powerdown)
        # Making sample not in gripper
        self.sample.disengage()
        self.gripper_has_something = False
        self.added_z_length = 0
        sample = self.sample
        self.sample = None
        
        # Retracting
        self.robot.moveAxisDelta(axis='z', value=-retract)
        
        return sample
        
    
    def pushSample(self, sample, man_open_diam=None, powerdown=True, dz=0):
        """
        Pushes the sample deeper into its current position.
        Some samples tend to pop up from the current position, or simply may not sit tight
        enough. This function gently presses on top of the sample.
        """
        self.getToSample(sample=sample)
        # Open gripper
        if man_open_diam is not None:
            open_diam = man_open_diam
        elif sample.isCapped():
            # TODO: add procedures for capped samples
            pass
        else:
            open_diam = sample.inner_diameter
        self.toDiameter(diameter=open_diam, powerdown=powerdown)
        
        z_start = self.robot.getAxisPosition(axis='z')
        
        z = sample.getSampleTopZ(tool=self)
        z_final = z + dz
        # Coarse approach
        self.robot.move(z=z-5)
        # Final slow approach
        self.robot.move(z=z_final, speed_z=300)
        self.robot.move(z=z_start)
        
    
    def moveSample(self, sample, rack, column, row, vol_to_grab=None, 
                   man_open_diam=None, man_grip_diam=None, powerdown=True,
                   z_after_pickup=None, retract_after_placing=20, dz=0, 
                   push_sample=False, push_dz=0, push_open_diam=None):
        # Grabbing sample
        # Not powering down
        self.grabSample(sample=sample, vol_to_grab=vol_to_grab,
                        man_open_diam=man_open_diam, man_grip_diam=man_grip_diam)
        # Optionally moving to a new Z position
        if z_after_pickup is not None:
            self.robot.move(z=z_after_pickup)
        # Placing sample to a new position
        sample = self.placeSample(rack=rack, column=column, row=row, vol_grabbed=vol_to_grab,
                                  man_open_diam=man_open_diam, powerdown=powerdown,
                                  retract=retract_after_placing, dz=dz)
        if push_sample:
            self.pushSample(sample=sample, man_open_diam=push_open_diam, powerdown=powerdown, dz=push_dz)
        return sample
        
    
    def discardSample(self, sample, waste_rack, vol_to_grab=None, man_open_diam=None, man_grip_diam=None,
                      z_after_pickup=None):
        self.moveSample(sample=sample, rack=waste_rack, column=0, row=0, 
                        vol_to_grab=vol_to_grab, man_open_diam=man_open_diam, man_grip_diam=man_grip_diam,
                        z_after_pickup=z_after_pickup)
    
    # TODO: drop sample immediately
    
    def getHowMuchLongerIsTheToolRelativeToTouchProbe(self):
        if self.gripper_has_something:
            
            return self.delta_length_for_calibration + self.added_z_length
        else:
            return self.delta_length_for_calibration 
        
    # Redeclining function to account for grabbed tube
    def getStalagmyteCoord(self):
        """
        Returns #stalagmyte (or #immobile_touch_probe) coordinates, that are 
        saved in the object after calibration
        """
        if self.gripper_has_something:
            return self.immob_probe_x, self.immob_probe_y, self.immob_probe_z - self.added_z_length
        else:
            return self.immob_probe_x, self.immob_probe_y, self.immob_probe_z


    
    def grabRack(self, rack, man_open_diam=None, man_close_diam=None, extra_retraction_dz=0,
                 powerdown=False, test=False):
        """
        Grabs a rack
        """
        
        self.getToRackCenter(rack)
        # Open gripper
        if man_open_diam is not None:
            open_diam = man_open_diam
        else:
            open_diam = rack.getGrippingOpenDiam(tool=self)
        self.toDiameter(diameter=open_diam, powerdown=powerdown)
        # Moving down to grabbing height
        z_grab = rack.getGrippingHeight(tool=self)
        self.robot.move(z=z_grab)
        # Closing gripper
        if man_close_diam is not None:
            close_diam = man_close_diam
        else:
            close_diam = rack.getGrippingCloseDiam(tool=self)
        self.toDiameter(diameter=close_diam, powerdown=powerdown)
        # Temporary storing sample object in the tool, as it will be used
        # to calculate parameters to place it somewhere.
        self.sample = rack
        self.gripper_has_something = True
        self.added_z_length = rack.getHeightBelowGripper(tool=self)
        # Calculating retraction height. It will be same as z_grab,
        # but now getGrippingHeight will account for added_z_length and extra_retraction_dz
        z_retract = rack.getGrippingHeight(tool=self) - extra_retraction_dz
        self.robot.move(z=z_retract)
        
        try:
            # In case rack is placed on top of another rack,
            # this tells the bottom rack that the top is removed.
            rack.bottom_item.removeTopItem()
        except:
            pass
        
        if test:
            param_dict = {}
            param_dict['open_diam'] = open_diam
            param_dict['z_grab'] = z_grab
            param_dict['close_diam'] = close_diam
            param_dict['z_retract'] = z_retract
            return param_dict
    
    
    def placeRack(self, destination_rack, man_open_diam=None, dz=0, retract=20, powerdown=False, test=False):
        """
        Places the rack that is currently grabbed in the gripper into the specified position.
        """
        # Moving X and Y to the rack position
        self.getToRackCenter(rack=destination_rack)
        x, y, z = destination_rack.calcRackCenterFullCalibration(tool=self)
        # "Placing" to the new rack
        destination_rack.placeItemOnTop(self.sample)
        # Calculating Z to which to lower the sample 
        # Sample now has parameters of the destination rack and place
        #z_final = z + destination_rack.getHeightFromFloor() + dz
        z_final = z + dz
        self.robot.move(z=z_final)
         # Opening gripper
        if man_open_diam is not None:
            open_diam = man_open_diam
        else:
            open_diam = self.sample.getGrippingOpenDiam(tool=self)
        self.toDiameter(diameter=open_diam, powerdown=powerdown)
        # Sample is no longer is the gripper. Changing gripper object properties accordingly
        #self.sample.disengage()
        self.gripper_has_something = False
        self.added_z_length = 0
        placed_rack = self.sample
        self.sample = None
        
        # Retracting
        self.robot.moveAxisDelta(axis='z', value=-retract)
        
        if test:
            param_dict = {}
            param_dict['destination_coord'] = (x, y, z)
            param_dict['rack_heigth'] = destination_rack.getHeightFromFloor()
            param_dict['z_final_absolute'] = z_final
            param_dict['open_diam'] = open_diam
            return placed_rack, param_dict
        else:
            return placed_rack
        

device_type_descriptions = [
    {"class": cart.arnie, "message": "Marlin", "type": "", "mobile": False}, 
    {"class": stationary_touch_probe, "message": "stationary touch probe", "type": "stationary_probe", "mobile": False}, 
    {"class": mobile_touch_probe, "message": "mobile touch probe", "type": "mobile_probe", "mobile": True},
    {"class": pipettor, "message": "Servo", "type": "pipettor", "mobile": True},
    {"class": mobile_gripper, "message": "mobile circular gripper", "type": "mobile_gripper", "mobile": True},
    ]