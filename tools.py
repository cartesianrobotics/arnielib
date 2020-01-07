"""
Module handling tools for the robot, both mobile and floor-based
"""

import logging
from copy import deepcopy

# Internal arnielib modules
import low_level_comm as llc
import param
import cartesian as cart    # TODO: Remove it when finishing refactoring.

SPEED_Z_MOVING_DOWN = 15000 # Robot can move down much faster than up.

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
    
    def __init__(self, robot, com_port_number=None, 
                 welcome_message=""):
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
        super().__init__(com_port_number, welcome_message=welcome_message)

        
    @classmethod
    def getToolAtCoord(cls, robot, x, y, z, z_init=0, speed_xy=None, speed_z=None, welcome_message=""):
        """
        Get tool positioned at known absolute coordinates x, y, z.
        """
        
        # Producing a list of present serial ports BEFORE engaging a new tool
        initial_ports_list = llc.listSerialPorts()
        
        # Moving to the save height, so nothing is kicked by a robot
        robot.move(z=z_init, speed_z=None)
        # Opening docker
        robot.openTool()
        # Moving to the tool coordinate
        robot.move(x=x, y=y, z=z, z_first=False, 
            speed_xy=speed_xy, speed_z=SPEED_Z_MOVING_DOWN)
        # Closing docker (hopefully gripping the tool)
        robot.closeTool()
        robot.move(z=z_init)
        
        # Obtaining updated list of serial devices. Now a new device should be present there.
        updated_ports_list = llc.listSerialPorts()
        # Obtaining newly appeared port
        new_port = list(set(updated_ports_list) - set(initial_ports_list))[0]
        
        cls.x_dock = x
        cls.y_dock = y
        cls.z_dock = z
        cls.z_safe = z_init
        
        return cls(robot=robot, com_port_number=new_port, welcome_message=welcome_message)
        
    @classmethod
    def getToolFromSerialDev(cls, robot, device, welcome_message=""):
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
        
        # Moving robot to the safe height, where it will not accidentally touch anything.
        self.robot.move(z=z_init)
        # Moving to the tool release position
        self.robot.move(x=x, y=y, z=z, z_first=False, speed_xy=speed_xy, speed_z=SPEED_Z_MOVING_DOWN)
        # Opening tool
        self.robot.openTool()
        # Moving back to the safe position
        self.robot.move(z=z_init)


class pipettor(tool):
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


class mobile_touch_probe(tool):
    def isTouched(self):
        self.write('d')
        response = self.readAll()
        print("Mobile touch probe response: " + response)
        return bool(int(re.split(pattern='/r/n', string=response)[0]))
    
    
    @classmethod
    def getTool(cls, robot):
        """
        Get touch probe from its saved position and initializes the object
        """
        cls.tool_name = "mobile_probe"
        cls.welcome_message="mobile touch probe"
        return super().getTool(robot, 
            tool_name=cls.tool_name, welcome_message=cls.welcome_message)




    
class mobile_gripper(tool):
    def operate_gripper(self, level):
        self.write(str(level))

    
class stationary_touch_probe(tool):
    def isTouched(self):
        self.write('d')
        response = self.readAll()
        print("Stationary touch probe response: " + response)
        return bool(int(re.split(pattern='/r/n', string=response)[0]))


device_type_descriptions = [
    {"class": cart.arnie, "message": "Marlin", "type": "", "mobile": False}, 
    {"class": stationary_touch_probe, "message": "stationary touch probe", "type": "stationary_probe", "mobile": False}, 
    {"class": mobile_touch_probe, "message": "mobile touch probe", "type": "mobile_probe", "mobile": True},
    {"class": pipettor, "message": "Servo", "type": "pipettor", "mobile": True},
    {"class": mobile_gripper, "message": "mobile circular gripper", "type": "mobile_gripper", "mobile": True},
    ]