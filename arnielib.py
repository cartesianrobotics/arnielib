"""
TODO:
1. Make commands interruptable. - Need electronics powerful enough, and firmware that supports it.
2. Make a function for swapping tools. 
3. Stalactite screw length calibration.
4. Make things more mathematically reasonable.
5. Add checks like only calibrate if the stalactite is connected.
6. Tip means both the tip of a tool and a plastic pipettor tip. Rename.
7. Make a command for moving or removing tools. 
8. Make a variable that tracks whether a pipettor has a tip on. 
9. Lift it to a safe height instead of homing. Check functons that don't do it and add if needed. 
10. Rename tool type into something else. 
11. Check if the pipettor is locked after connection. 
12. Update calibration of tools when stalactite tip is recalibrated. 
13. Make a "move_units" function that moves in units and is only used for floor and ziggurat calibration. Make "move" take mm instead of units. 
14. Pre-home routine for tools
15. Sometimes "connect" function fails returning error when checking for the device list. Need to be fixed
16. Add function that allows to enter a new rack without edditinng the library.
17. Add option to mute functions, as it is very painfull to use in jupyter
18. User should enter parameters of racks at calibration or calling; save it as documents and store wherever they want it.
19. For some reason, move commands refuse to accept value "0". They just don't perform a movement.
"""

"""
Sequence of operations to add a new rack
12/17/2019, adding a new magnetic rack for 1.7 mL Eppendorf tubes
1. Creating a new type in "rack_dict" and add the measurements.
2. Need to calibrate it (if it is not rectangular, that complicates things).
3. For custom racks, make sure you provide custom offsets and custom deltas in the function "calibrate_rack".
"""
    
import serial
import time
import math
import json
import re
import os 
from copy import deepcopy
from datetime import datetime
from shutil import copyfile

import sys
import glob

# Importing sub-libraries of arnielib
import low_level_comm as llc
import cartesian as cart

message_level = "verbose"
robots = []
safe_height = 590

# Arnie parameters


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
    
rack_types = ["96_well", "eppendorf", "50_ml", "magnetic_eppendorf"]
rack_dict = {
    "96_well": {"rack_height": 16, "n_columns": 12, "n_rows": 8, "dist_between_wells_x": 9, "dist_between_wells_y": 9, "dist_center_to_well_00": [49.5, 31.5], "tube_height_above_rack": 10, "tube_height": 21, "tube_width": 6},
    "eppendorf": {"rack_height": 94, "n_columns": 8, "n_rows": 4, "dist_between_wells_x": 17, "dist_between_wells_y": 23, "dist_center_to_well_00": [59.5, 28], "tube_height_above_rack": 13, "tube_height": 39, "tube_width": 10},
    "50_ml": {"rack_height": 94, "n_columns": 3, "n_rows": 2, "dist_between_wells_x": 50, "dist_between_wells_y": 50, "dist_center_to_well_00": [50, 25], "tube_height_above_rack": 21, "tube_height": 113, "tube_width": 27},
    "magnetic_eppendorf": {"rack_height": 94, "n_columns": 8, "n_rows": 2, "dist_between_wells_x": 15, "dist_between_wells_y": 78.6, "dist_center_to_well_00": [52.5, 34.8], "tube_height_above_rack": 13, "tube_height": 39, "tube_width": 10},
    }


# Tip trays parameters
EXPECTED_TIP_TRAY_HEIGHT = 68 # mm from the floor; physically measured
SAFE_TIP_TRAY_HEIGHT = 100 # mm from the floor; this is the height that robot is guaranteed not to hit anything around the tip tray

# Movement parameters
# Default movement speed:
DEFAULT_X_SPEED = 8000
DEFAULT_Y_SPEED = 8000
DEFAULT_Z_SPEED = 5000 # Safe speed to move Z up; moving down may be much faster.
# TODO: Not implemented yet; make functions that differentiate between up and down Z axis movement,
# and automatically use this default.
DEFAULT_Z_SPEED_DOWN = 15000 # Default speed when robot moves Z axis down. 



pipettor_volumes = [1000, 200, 20]
pipettor_types = ["single", "multi"]

def log(text):
    log_file = open("log.txt", "a")
    log_file.write(text)
    log_file.write("\n")
    log_file.close()

def message_log(port, text, read_or_write):
    log_file = open("message_log.txt", "a")
    log_file.write(port + " " + read_or_write + " " + text)
    log_file.write("\n")
    log_file.close()
    
def log_value(name, value, axis):
    log(name + ' ' + axis + ' ' + str(value))

def axis_index(axis):
    result = axis.upper()
    axes = ["X", "Y", "Z"]
    if result not in axes:
        print("ERROR: wrond axis provided: " + axis)
        return -1
    else:
        result = axes.index(result)
        return result

def find_tool_i_by_type(robot, type):
    for tool_i in range(len(robot.tools)):
        if robot.tools[tool_i]["type"] == type:
            return tool_i
    return -1

def find_tools_by_type(robot, type):
    result = []
    for tool_i in range(len(robot.tools)):
        if robot.tools[tool_i]["type"] == type:
            result.append(tool_i)
    return result

# x_n, y_n -- coordinates of the slot the tool is stored in. Returns the index of that tool in the arnie.tools list. 
def find_tool_i_by_coord(robot, x_n, y_n):
    for tool_i in range(len(robot.tools)):
        tool = robot.tools[tool_i]
        if tool["n_x"] == x_n and tool["n_y"] == y_n:
            return tool_i
    
    return -1
    




        
GenCenter = lambda xmin, xmax: xmin + (xmax - xmin)/2.0
GenCenterXYZ = lambda xmin, xmax, ymin, ymax, zmin, zmax: (
    GenCenter(xmin, xmax), 
    GenCenter(ymin, ymax),
    GenCenter(zmin, zmax),
)



def move_delta_mm(robot, dx=0, dy=0, dz=0):
    if abs(dx) > 0.001 and robot.params["units_in_mm"][0] == -1:
        print("ERROR: X axis units are not calibrated.")
        return
    if abs(dy) > 0.001 and robot.params["units_in_mm"][1] == -1:
        print("ERROR: Y axis units are not calibrated.")
        return
    if abs(dz) > 0.001 and robot.params["units_in_mm"][2] == -1:
        print("ERROR: Z axis units are not calibrated.")
        return
        
    robot.move_delta(dx=dx * robot.params["units_in_mm"][0], dy=dy * robot.params["units_in_mm"][1], dz=dz * robot.params["units_in_mm"][2])


def find_wall(robot, axis, direction, name="unknown", touch_function=None, 
              step_decrease_list=[8.1, 2.7, 0.9, 0.3, 0.1],
              speed_xy_list=[1000, 500, 300, 100, 50], speed_z_list=[5000, 4000, 3000, 2000, 1000], 
              step_back_length=5):
    """
    Find coordinate of the wall on given "axis".
    Robot assumed to be connected to mobile touch probe, or a "stalaktite".
    Will move on "axis" into "direction", until stalaktite detects collision. Then it 
    retracts until stalaktite stops detecting collision. Then it approaches again with finer steps,
    until collision detected. Then retracts and approaches again with extra fine steps. 
    
    After that, it retracts on "step_back_length".
    
    Parameters:
        - robot - robot instance
        - axis - axis at which to perform calibration; only allowed "X", "Y" or "Z".
        - direction - direction at which to move robot; eiter +1 or -1. +1 moves further from homing point; -1 - towards homing point
        - name - only used for logging; not influences operation. Default is "unknown".
        - touch_function - unclear
        - step_decrease_list - list of 5 elements; each element is how far to move each step until checking the touch probe state.
            default is [8.1, 2.7, 0.9, 0.3, 0.1]
        - speed_xy_list - list of 5 elements, which are the speed at which to do movement in XY direction.
            default is [1000, 500, 300, 100, 50]
        - speed_z_list - list of 5 elements, which are the speed at which to do movement in Z direction.
            default is [5000, 4000, 3000, 2000, 1000]
        - step_back_length - distance to retract after finishing calibration; default is 5.
    
    Returns coordinate at which collision was detected during finest approach.
    """
    # Sanity checks --------------------------------------------------------------------------------------------------------------------
    # direction should be either 1 or -1
    if direction != 1 and direction != -1:
        print("ERROR: invalid direction.")
        print(direction)
        return
    
    # Checking whether axes specified properly
    axis = axis.upper()
    if axis != "X" and axis != "Y" and axis != "Z":
        print("ERROR: wrong axis specified. Only allowed X, Y or Z")
        print(axis)
        return
    
    # TODO: This check had to be commented out because this function is used for stalagmite calibration too. Bring it back somehow?
    #if robot.current_tool == None or robot.current_tool["type"] != "mobile_probe":
    #   print("ERROR: No probe attached.")
    #   return
    
    # TODO: This is terrible. Sort it out. 
    if robot.current_tool_device != None:
        probe = robot.current_tool_device
    else:
        probe = None
    # ---------------------------------------------------------------------------------------------------------------------------------
    
    # Performing approaches while detecting collision with stalaktite
    ApproachUntilTouch(robot, probe, axis, direction * step_decrease_list[0], touch_function=touch_function, speed_xy=speed_xy_list[0], speed_z=speed_z_list[0])
    retract_until_no_touch(robot, probe, axis, -direction * step_decrease_list[1], touch_function=touch_function, speed_xy=speed_xy_list[1], speed_z=speed_z_list[1])
    ApproachUntilTouch(robot, probe, axis, direction * step_decrease_list[2], touch_function=touch_function, speed_xy=speed_xy_list[2], speed_z=speed_z_list[2])
    retract_until_no_touch(robot, probe, axis, -direction * step_decrease_list[3], touch_function=touch_function, speed_xy=speed_xy_list[3], speed_z=speed_z_list[3])
    wall_coord = ApproachUntilTouch(robot, probe, axis, direction * step_decrease_list[4], touch_function=touch_function, speed_xy=speed_xy_list[4], speed_z=speed_z_list[4])
    result = wall_coord[axis_index(axis)]
    
    #Handling retractiong after calibration is finished
    retraction_len_and_dir = step_back_length * -direction
    if axis == "X":
        robot.move_delta(dx=retraction_len_and_dir)
    elif axis == "Y":
        robot.move_delta(dy=retraction_len_and_dir)
    else:
        robot.move_delta(dz=retraction_len_and_dir)

    log_value(name, result, axis)
    return result

def find_wall_approx(robot, axis, direction, name="unknown", expect=-1, tolerance=-1):
    # direction should be either 1 or -1
    if direction != 1 and direction != -1:
        print("ERROR: invalid direction.")
        print(direction)
        return
        
    if robot.current_tool == None or robot.current_tool["type"] != "mobile_probe":
        print("ERROR: No probe attached.")
        return
    
    if axis == "Z": 
        approach_step = 45.0 # CONSTANT
    else:
        approach_step = 10.0 # CONSTANT
    
    wall_coord = ApproachUntilTouch(robot, robot.current_tool_device, axis, direction * approach_step, expect, tolerance) # CONSTANT
    if wall_coord == -1:
        return -1
        
    result = wall_coord[axis_index(axis)]
    retract_until_no_touch(robot, robot.current_tool_device, axis, -direction * approach_step) # CONSTANT
    step_back = [0, 0, 0]
    if axis == "Z": 
        step_back_length = 30 # CONSTANT
    else:
        step_back_length = 5 # CONSTANT
    step_back[axis_index(axis)] = -direction * step_back_length
    robot.move_delta(dx=step_back[0], dy=step_back[1], dz=step_back[2])
    log_value(name, result, axis)
    return result

def find_wall_end(robot, axis_1, dir_1, axis_2, dir_2, tolerance, name="unknown"):
    # axis_1 -- perpendicular to the wall
    
    def shift_until_no_wall(baseline, approach_step):
        while True:
            step = [0, 0, 0]
            step[axis_index(axis_2)] = dir_2 * approach_step
            robot.move_delta(dx=step[0], dy=step[1], dz=step[2])
            wall = find_wall_approx(robot, axis_1, dir_1, "-fwe-" + str(approach_step) + "-" + name, baseline, tolerance)
            if wall == -1:
                return robot.getPosition()[axis_index(axis_2)]
            
    start_position = robot.getPosition()
    start_position_axis_1 = start_position[axis_index(axis_1)]

    if axis_1 == "Z": 
        approach_step_1 = 45.0 # CONSTANT
        approach_step_2 = 5.0
    else:
        approach_step_1 = 10.0 # CONSTANT
        approach_step_2 = 3.0
        
    approach_step_3 = 0.5

    baseline = find_wall_approx(robot, axis_1, dir_1, "-fwe-baseline" + name)
    shift_until_no_wall(baseline, approach_step_1)
    
    retract_dest = [0, 0, 0]
    retract_dest[axis_index(axis_1)] = start_position_axis_1
    robot.move(x=retract_dest[0], y=retract_dest[1], z=retract_dest[2])
    
    step = [0, 0, 0]
    step[axis_index(axis_2)] = -dir_2 * approach_step_1
    robot.move_delta(dx=step[0], dy=step[1], dz=step[2])
    
    result = shift_until_no_wall(baseline, approach_step_3)
    return result

# This function is for testing calibration precision. The probe should touch the screw.
def touch_left_top(robot, n_x, n_y):
    if not robot.calibrated:
        print("ERROR: The robot is not calibrated.")
        return
    target = robot.params['slots'][n_x][n_y]['LT']
    robot.move(z=safe_height)
    robot.move(x=target[0], y=target[1])
    find_wall(robot, "Z", 1, "left_top_screw_" + str(n_x) + "_" + str(n_y))
    robot.move(z=safe_height)

# This function is pretty janky. It measures the stalactite rack from the inside and the outside.
def test_stalactite(robot, x_n, y_n):
    floor_z = robot.params["slots"][x_n][y_n]["floor_z"]
    floor_to_circle_rack_height = 105
    center_z = floor_z - (floor_to_circle_rack_height - 3) * robot.params["units_in_mm"][2]
    
    tool_i = find_tool_i_by_type(robot, "mobile_probe")
    
    robot.move(z = center_z - 200)
    
    calibrate_mobile_probe_rack(robot, x_n, y_n)
    
    robot.move(z = center_z - 200)
    
    outer = calibrate_circle_outer(robot, x_n, y_n, center_z)
    inner = robot.tools[tool_i]["position"]
    
    print(inner)
    print(outer)
    print([inner[0] - outer[0], inner[1] - outer[1]])

def calibrate_mobile_probe_rack(robot, x_n, y_n):
    center_xy = calc_slot_center(robot, x_n, y_n)
    floor_to_circle_rack_height = 105
    floor_z = robot.params["slots"][x_n][y_n]["floor_z"]
    center_z = floor_z - (floor_to_circle_rack_height - 3) * robot.params["units_in_mm"][2]
    rack_circle = calibrate_circle(robot, [center_xy[0], center_xy[1], center_z])
    robot.current_tool["position"][0] = rack_circle[0]
    robot.current_tool["position"][1] = rack_circle[1]
    floor_to_bed_rack_height = 60
    length_screw_mm = 33.9
    robot.current_tool["position"][2] = floor_z - (floor_to_bed_rack_height - length_screw_mm) * robot.params["units_in_mm"][2]
    robot.current_tool["n_x"] = x_n
    robot.current_tool["n_y"] = y_n
    robot.current_tool["slot"] = deepcopy(robot.params["slots"][x_n][y_n])
    
    tool_exists = False
    for tool_i in range(len(robot.tools)):
        tool = robot.tools[tool_i]
        if tool["n_x"] == x_n and tool["n_y"] == y_n:
            robot.tools[tool_i] = robot.current_tool
            tool_exists = True
            break
    
    if not tool_exists:
        robot.tools.append(robot.current_tool)
        
    update_tools(robot)

def calibrate_mobile_gripper(robot, x_n, y_n):
    rack_height_mm = 44
    expected_z = robot.params["slots"][x_n][y_n]["floor_z"] - ((rack_height_mm - 3) * robot.params["units_in_mm"][2])
    
    center = calibrate_circle_outer(robot, x_n, y_n, expected_z)
    
    # TODO: This bookkeeping has to happen after each tool calibration. Factor it out?  
    tool = deepcopy(default_tool)
    tool["position"][0] = center[0]
    tool["position"][1] = center[1]
    length_screw_mm = 33.9
    stalactite_height = 147
    tool_height = 160
    tool["position"][2] = robot.params["slots"][x_n][y_n]["floor_z"] + (- tool_height + length_screw_mm + stalactite_height) * robot.params["units_in_mm"][2]
    
    tool["n_x"] = x_n
    tool["n_y"] = y_n
    slot = robot.params["slots"][x_n][y_n]
    tool["slot"] = deepcopy(slot)
    tool["type"] = "mobile_gripper"
    tool["params"] = {}
    
    tool_i = find_tool_i_by_coord(robot, x_n, y_n)
    if tool_i != -1:
        robot.tools[tool_i] = tool
    else:
        robot.tools.append(tool)
        
    update_tools(robot)

def calibrate_pipettor(robot, x_n, y_n, volume, pipettor_type):
    pipettor_height_mm = 157
    #expected_z = robot.params["slots"][x_n][y_n]["floor_z"] - ((pipettor_height_mm - 3) * robot.params["units_in_mm"][2])
    expected_z = robot.params["slots"][x_n][y_n]["floor_z"] - ((pipettor_height_mm - 3))
    
    # TODO: Replace all of this with a calibrate_circle_outer call. Like in calibrate_mobile_gripper. 
    
    robot.home("Z")
    goto_slot_lt(robot, x_n, y_n)
    robot.move(z=expected_z)
    robot.move_delta(dx=robot.params['slot_width'] / 2)
    north = find_wall(robot, "Y", 1, "calibrate_pipettor-north")

    #robot.move_delta(dz = -robot.params['units_in_mm'][2] * 30)
    robot.move_delta(dz = -30)
    goto_slot_lt(robot, x_n, y_n)
    robot.move(z=expected_z)
    robot.move_delta(dy=robot.params['slot_height'] / 2)
    east = find_wall(robot, "X", 1, "calibrate_pipettor-east")
    
    #robot.move_delta(dz = -robot.params['units_in_mm'][2] * 30)
    robot.move_delta(dz = -30)
    goto_slot_rb(robot, x_n, y_n)
    robot.move(z=expected_z)
    robot.move_delta(dx=-robot.params['slot_width'] / 2)
    south = find_wall(robot, "Y", -1, "calibrate_pipettor-south")
    
    #robot.move_delta(dz = -robot.params['units_in_mm'][2] * 30)
    robot.move_delta(dz = -30)
    goto_slot_rb(robot, x_n, y_n)
    robot.move(z=expected_z)
    robot.move_delta(dy=-robot.params['slot_height'] / 2)
    west = find_wall(robot, "X", -1, "calibrate_pipettor-west")

    # TODO: This bookkeeping has to happen after each tool calibration. Factor it out?  
    tool = deepcopy(default_tool)
    tool["position"][0] = (east + west) / 2
    tool["position"][1] = (north + south) / 2
    length_screw_mm = 33.9
    stalactite_height = 147
    tool_height = 252
    #tool_height = 254
    #tool["position"][2] = robot.params["slots"][x_n][y_n]["floor_z"] + (- tool_height + length_screw_mm + stalactite_height) * robot.params["units_in_mm"][2]
    tool["position"][2] = robot.params["slots"][x_n][y_n]["floor_z"] + (- tool_height + length_screw_mm + stalactite_height)
    
    tool["n_x"] = x_n
    tool["n_y"] = y_n
    slot = robot.params["slots"][x_n][y_n]
    tool["slot"] = deepcopy(slot)
    tool["type"] = "pipettor"
    tool["params"] = {"volume": volume, "pipettor_type": pipettor_type}
    
    tool_i = find_tool_i_by_coord(robot, x_n, y_n)
    if tool_i != -1:
        robot.tools[tool_i] = tool
    else:
        robot.tools.append(tool)
        
    update_tools(robot)

def calibrate_tip(robot, x_n, y_n, touch_function, initial_height_mm, initial_point=None):
    if initial_point == None:
        initial_point = calc_slot_center(robot, x_n, y_n)
        
    slot = robot.params["slots"][x_n][y_n]
    u_in_mm = robot.params["units_in_mm"]

    robot.home("Z")
    robot.move(x=initial_point[0], y=initial_point[1])

    robot.move(z=slot["floor_z"] - (initial_height_mm + 10) * u_in_mm[2])
    height = find_wall(robot, "Z", 1, "calibrate_tip-height", touch_function)
    
    move_delta_mm(robot, dx=10 * u_in_mm[0])
    robot.move(z=height + 5 * u_in_mm[2])
    east = find_wall(robot, "X", -1, "calibrate_tip-east", touch_function)
    robot.move(z=height - 5 * u_in_mm[2])
    robot.move(x=initial_point[0], y=initial_point[1])
    
    move_delta_mm(robot, dx=-10 * u_in_mm[0])
    robot.move(z=height + 5 * u_in_mm[2])
    west = find_wall(robot, "X", 1, "calibrate_tip-west", touch_function)
    robot.move(z=height - 5 * u_in_mm[2])
    robot.move(x=initial_point[0], y=initial_point[1])
    
    move_delta_mm(robot, dy=10 * u_in_mm[1])
    robot.move(z=height + 5 * u_in_mm[2])
    south = find_wall(robot, "Y", -1, "calibrate_tip-south", touch_function)
    robot.move(z=height - 5 * u_in_mm[2])
    robot.move(x=initial_point[0], y=initial_point[1])
    
    move_delta_mm(robot, dy=-10 * u_in_mm[1])
    robot.move(z=height + 5 * u_in_mm[2])
    north = find_wall(robot, "Y", 1, "calibrate_tip-north", touch_function)
    robot.move(z=height - 5 * u_in_mm[2])
    
    result = [(east + west) / 2, (south + north) / 2, height]
    
    robot.move(x = result[0], y = result[1])
    
    return result

    
def calibrate_pipettor_tip(robot, x_n, y_n, initial_point=None):
    # x_n, y_n -- coordinates of the slot that contains the stalagmite.
    stalagmite_height_mm = 130
    
    stat_probe = None
    for device in robot.tool_devices:
        if device.description["type"] == "stationary_probe":
            stat_probe = device
            break
    
    if stat_probe == None:
        print("ERROR: No stationary probe is connected.")
        return
    
    position = calibrate_tip(robot, x_n, y_n, stat_probe.isTouched, stalagmite_height_mm + 50, initial_point)
    
    # tool_i = find_tool_i_by_coord(robot, pip_x, pip_y)
    # robot.tools[tool_i]["tip"] =  position
    robot.current_tool["tip"] = position
    update_tools(robot)

def get_tool(robot, type, subtype=None, volume=None, z_dest_delta=0):
    tools = find_tools_by_type(robot, type)
    if len(tools) == 0:
        print("ERROR: No such tool exists: " + type + ".")
        return
    
    if type == "pipettor":
        if subtype == None:
            print("ERROR: Pipettor type has to be specified.")
            return
        if volume == None:
            print("ERROR: Pipettor volume has to be specified.")
            return
        if subtype not in pipettor_types:
            print("ERROR: Unknown pipettor type: " + str(subtype) + ".")
            return
        if volume not in pipettor_volumes:
            print("ERROR: Unknown pipettor volume: " + str(volume) + ".")
            return
        
        tool_to_pickup = None
        for tool_i in tools:
            tool = robot.tools[tool_i]
            if tool["params"]["volume"] == volume and tool["params"]["pipettor_type"] == subtype:
                tool_to_pickup = tool
                break
        if tool_to_pickup == None:
            print("ERROR: No such pipettor is calibrated.")
            return
    else:
        tool_to_pickup = robot.tools[tools[0]]
        
    robot.get_tool(tool_to_pickup["n_x"], tool_to_pickup["n_y"], z_dest_delta=z_dest_delta)

def calibrate_mobile_probe_tip(robot, x_n, y_n, initial_point=None, stalagmite_height=130):
    # x_n, y_n -- coordinates of the slot that contains the stalagmite.
    
    stat_probe = None
    for device in robot.tool_devices:
        if device.description["type"] == "stationary_probe":
            stat_probe = device
            break
    
    if stat_probe == None:
        print("ERROR: No stationary probe is connected.")
        return
    
    mob_probe = robot.current_tool_device
    def touch_function():
        return stat_probe.isTouched() or mob_probe.isTouched()
    
    position = calibrate_tip(robot, x_n, y_n, touch_function, stalagmite_height, initial_point)
    robot.move(z=position[2])
    
    tool_i = find_tool_i_by_type(robot, "mobile_probe")
    robot.tools[tool_i]["params"] = {"tip": position}
    update_tools(robot)

def rectangle_center(rect):
    center_x = (rect["east1"] + rect["east2"] + rect["west1"] + rect["west2"]) / 4
    center_y = (rect["north1"] + rect["north2"] + rect["south1"] + rect["south2"]) / 4
    return [center_x, center_y]

def rectangle_center_2(rect):
    # north1, north2, east1, east2, south1, south2, west1, west2
    center_x = (rect[2] + rect[3] + rect[6] + rect[7]) / 4
    center_y = (rect[0] + rect[1] + rect[4] + rect[5]) / 4
    return [center_x, center_y]

def calibrate_rectangle(robot, rect, safe_height, measure_height, name="Default name", X_offset_frac=3.0, Y_offset_frac=3.0):
    """
    Calibrates any rectangular object. Returns list of 8 parameters:
        north1, north2 - "Y" values of furthest side of the rectangle
        east1, east2 - "X" values of rightmost side of the rectanlge
        south1, south2 - "Y" values of nearest side of the rectangle
        west1, west2 - "X" values of leftmost side of the rectanlge
        
        For the record, left side is closer to the "home" position than right side
        "firthest" is closer to the "home" than "nearest"; "nearest" is closer to observer
        
    Robot assumed to be already positioned above the needed slot.
        
    Parameters:
        robot - robot instance
        rect - dictionary that contains parameters of the rectangle to calibrate
            "LT" - coordinates of left top vertex of the rectangle, [x, y]
            "LB" - coordinates of left bottom side of the rectangle, [x, y]
            "RT" - coordinates of right top side of the rectangle, [x, y]
            "RB" - coordinates of right bottom side of the rectangle, [x, y]
            Slot is the rectangle on the floor, where a rack may be positioned
            Slots are calibrated initially using "calibrate"
            For exampple, slot parameters may be used  as starting parameters (but not necessary)
        safe_height - height at which robot won't hit anything within a given slot
        measure_height - height at which actual measurement must be taken with stalaktite
        name - Name used to write measurements into log (does not affect anything)
    """
    
    lt = rect["LT"]
    lb = rect["LB"]
    rt = rect["RT"]
    rb = rect["RB"]
    rect_width = ((rt[0] - lt[0]) + (rb[0] - lb[0])) / 2
    rect_height = ((lb[1] - lt[1]) + (rb[1] - rt[1])) / 2

    robot.move(z=safe_height)
    robot.move(x=lt[0] + rect_width / X_offset_frac, y=lt[1])
    robot.move(z=measure_height)
    north1 = find_wall(robot, "Y", 1, name + "calibrate_rectangle-north1")
    robot.move(x=rt[0] - rect_width / X_offset_frac, y=rt[1])
    #robot.move_delta(dx=rect_width / 3)
    north2 = find_wall(robot, "Y", 1, name + "calibrate_rectangle-north2")
    
    # I wanted to calibrate the height of the rack here, but then decided to do it in the center. 
    # find_wall_end(robot, "Y", 1, "Z", -1, 10 * robot.params["units_in_mm"][2], name="calibrate_rectangle-north")
    
    robot.move(z=safe_height)
    robot.move(x=rt[0], y=rt[1] + rect_height / Y_offset_frac)
    robot.move(z=measure_height)
    east1 = find_wall(robot, "X", -1, name + "calibrate_rectangle-east1")
    robot.move(x=rb[0], y=rb[1] - rect_height / Y_offset_frac)
    #robot.move_delta(dy=rect_height / 3)
    east2 = find_wall(robot, "X", -1, name + "calibrate_rectangle-east2")

    robot.move(z=safe_height)
    robot.move(x=rb[0] - rect_width / X_offset_frac, y=rb[1])
    robot.move(z=measure_height)
    south2 = find_wall(robot, "Y", -1, name + "calibrate_rectangle-south2")
    robot.move(x=lb[0] + rect_width / X_offset_frac, y=lb[1])
    #robot.move_delta(dx=-rect_width / 3)
    south1 = find_wall(robot, "Y", -1, name + "calibrate_rectangle-south1")
    
    robot.move(z=safe_height)
    robot.move(x=lb[0], y=lb[1] - rect_height / Y_offset_frac)
    robot.move(z=measure_height)
    west2 = find_wall(robot, "X", 1, name + "calibrate_rectangle-west2")
    robot.move(x=lt[0], y=lt[1] + rect_height / Y_offset_frac)
    #robot.move_delta(dy=-rect_height / 3)
    west1 = find_wall(robot, "X", 1, name + "calibrate_rectangle-west1")
    robot.move(z=safe_height)
    
    return [north1, north2, east1, east2, south1, south2, west1, west2]

def calibrate_tip_tray(robot, x_n, y_n, tray_volume, 
        expected_tray_height=EXPECTED_TIP_TRAY_HEIGHT,
        safe_tray_height=SAFE_TIP_TRAY_HEIGHT):
        
    """
    Calibrates a tip tray
    
    Function is used for any tip tray; it may be 1000, 300, 200, 20 uL trays
    (may be used for any other trays that may appear)
    
    Parameters:
        - robot - arnie's instance
        - x_n, y_n - which slot the tray is positioned (Arnie has X slots 0-5 and Y slots 0-3)
        - expected_tray_height - Height from the floor at which to perform X, Y calibration, mm
        - safe_tray_height - Height at which one is not afraid to crash robot to anything around given slot; should be above calibration height.
        
    Results are saved into tools.json
    """
    
    slot = robot.params["slots"][x_n][y_n]
    robot.home("Z")
    goto_slot_lt(robot, x_n, y_n)
    
    floor = slot["floor_z"]
    
    tray_safe_height = floor - safe_tray_height * robot.params["units_in_mm"][2]
    tray_measure_height = floor - expected_tray_height * robot.params["units_in_mm"][2]
    
    north1, north2, east1, east2, south1, south2, west1, west2 = calibrate_rectangle(robot, robot.params["slots"][x_n][y_n], tray_safe_height, tray_measure_height, "calibrate_tip_tray-")
    
    center = [(east1 + east2 + west1 + west2) / 4, (north1 + north2 + south1 + south2) / 4]
    robot.move(z=tray_safe_height)
    robot.move(x=center[0], y=center[1])
    
    # TODO: This bookkeeping has to happen after each tool calibration. Factor it out?  
    tool = deepcopy(default_tool)
    
    tool["n_x"] = x_n
    tool["n_y"] = y_n
    tool["slot"] = deepcopy(slot)
    tool["type"] = "tip_tray"
    
    tool["params"] = {
        "north1": north1,
        "north2": north2,
        "south1": south1,
        "south2": south2,
        "east1": east1,
        "east2": east2,
        "west1": west1,
        "west2": west2,
        "width_n": 12,
        "height_n": 8,
        "volume": tray_volume
    }
    
    tool_i = find_tool_i_by_coord(robot, x_n, y_n)
    if tool_i == -1:
        robot.tools.append(tool)
    else: 
        robot.tools[tool_i] = tool
    update_tools(robot)

def calibrate_rack(robot, x_n, y_n, rack_type):
    if rack_type not in rack_types:
        print("ERROR: unknown rack type: " + rack_type + ".")
        print("Known rack types:")
        print(rack_types)
        return

    slot = robot.params["slots"][x_n][y_n]
    u_mm = robot.params["units_in_mm"]
    
    robot.home("Z")
    goto_slot_lt(robot, x_n, y_n)
    
    rack_level = slot["floor_z"] - u_mm[2] * (rack_dict[rack_type]["rack_height"] - 2)
    
    # Parameters used to calculate at which point to perform measurement 
    # relative to the vertices of a slot where rack is positioned
    # Higher the number, the closer to the vertices robot will calibrate.
    X_offset_frac = 3.0
    Y_offset_frac = 3.0
    
    # Parameters used to calculate at which point to measure Z
    # By default, Z is measured at the center of a rack, after X and Y are calculated
    # Here are deltas to add to the center coordinates, so the height of a rack is calculated 
    # not at the center
    # In robot units, not mm.
    deltaX = 0
    deltaY = 0

    n_columns = rack_dict[rack_type]["n_columns"]
    n_rows = rack_dict[rack_type]["n_rows"]
    
    if rack_type == "magnetic_eppendorf":
        # This rack has custom offsets for calibration
        Y_offset_frac = 7.0
        deltaX = -45 * u_mm[0]
        deltaY = -46 * u_mm[1]
        
    
    # Recalculating mm into robot units
    rack_safe_height = rack_level - 100 * u_mm[2]
    
    north1, north2, east1, east2, south1, south2, west1, west2 = calibrate_rectangle(
        robot, 
        robot.params["slots"][x_n][y_n], 
        rack_safe_height, 
        rack_level, 
        "calibrate_rack-",
        X_offset_frac=X_offset_frac,
        Y_offset_frac=Y_offset_frac)

    rack_center = [(west1 + east1 + west2 + east2) / 4, (north1 + south1 + north2 + south2) / 4]

    robot.move(x = rack_center[0]+deltaX, y = rack_center[1]+deltaY)
    rack_height = find_wall(robot, "Z", 1, "calibrate_rack-rack_center")
    robot.move(z=rack_height)
    
    # TODO: This bookkeeping has to happen after each tool calibration. Factor it out?  
    rack_tool = deepcopy(default_tool)
    rack_tool["position"][0] = rack_center[0]
    rack_tool["position"][1] = rack_center[1]
    rack_tool["position"][2] = rack_height
    
    rack_tool["n_x"] = x_n
    rack_tool["n_y"] = y_n
    rack_tool["slot"] = deepcopy(slot)
    rack_tool["type"] = "rack"
    
    rack_tool["params"] = {
        "north1": north1,
        "north2": north2,
        "south1": south1,
        "south2": south2,
        "east1": east1,
        "east2": east2,
        "west1": west1,
        "west2": west2,
        "height": rack_height,
        "width_n": n_columns,
        "height_n": n_rows,
        "rack_type": rack_type
    }
    
    tool_i = find_tool_i_by_coord(robot, x_n, y_n)
    if tool_i == -1:
        robot.tools.append(rack_tool)
    else:
        robot.tools[tool_i] = rack_tool
        
    update_tools(robot)

def calc_well_position(rect, x_n, y_n, well_x_n, well_y_n, u_mm, rack_type="96_well"):
    west1 = rect["west1"]
    west2 = rect["west2"]
    east1 = rect["east1"]
    east2 = rect["east2"]
    north1 = rect["north1"]
    north2 = rect["north2"]
    south1 = rect["south1"]
    south2 = rect["south2"]
    
    # TODO: More precise positioning that takes skewness into account.
    rack_center = [(west1 + east1 + west2 + east2) / 4, (north1 + south1 + north2 + south2) / 4]
    
    dist_between_wells_x = rack_dict[rack_type]["dist_between_wells_x"] * u_mm[0]
    dist_between_wells_y = rack_dict[rack_type]["dist_between_wells_y"] * u_mm[1]
    well_00_x = rack_center[0] - rack_dict[rack_type]["dist_center_to_well_00"][0] * u_mm[0]
    well_00_y = rack_center[1] - rack_dict[rack_type]["dist_center_to_well_00"][1] * u_mm[1]

    dest_x = well_00_x + well_x_n * dist_between_wells_x
    dest_y = well_00_y + well_y_n * dist_between_wells_y
    
    return [dest_x, dest_y]

def probe_coord_to_tool_coord(robot, tool_tip, probe_coord):
    probe_i = find_tool_i_by_type(robot, "mobile_probe")
    probe_tip = robot.tools[probe_i]["params"]["tip"]
    tool_coord = [0, 0, 0]
    tool_coord[0] = probe_coord[0] - probe_tip[0] + tool_tip[0]
    tool_coord[1] = probe_coord[1] - probe_tip[1] + tool_tip[1]
    tool_coord[2] = probe_coord[2] - probe_tip[2] + tool_tip[2]
    return tool_coord

def test_tip_tray_calibration(robot, x_n, y_n):
    tool_i = find_tool_i_by_coord(robot, x_n, y_n)
    
    if robot.current_tool["type"] != "pipettor":
        print("ERROR: No pipettor is attached.")
        return
    
    if tool_i == -1:
        print("ERROR: No tool in slot (" + str(x_n) + ", " + str(y_n) + ").")
        return
    
    tool = robot.tools[tool_i]
    if tool["type"] != "tip_tray":
        print("ERROR: The tool in slot (" + str(x_n) + ", " + str(y_n) + ") is not a tip tray.")
        return
    
    u_in_mm = robot.params["units_in_mm"]
    
    columns = [0, 11] # range(tool["params"]["width_n"])
    rows = [0, 7] # range(tool["params"]["height_n"])
    
    for column_i in columns:
        for row_i in rows:
            pickup_tip(robot, x_n, y_n, column_i, row_i)
            robot.move_delta(dz = -50 * u_in_mm[2])
            robot.current_tool_device.drop_tip()
            time.sleep(7)

def pickup_tip(robot, x_n, y_n, well_x_n, well_y_n):
    # TODO: Step 1: check that the box in the slot (x_n, y_n) has the tips that the current pipettor takes. Step 2: Get rid of x_n, y_n, well_x_n, well_y_n and calculate everything automatically. 
    # TODO: Lift to a safe height.
    slot = robot.params["slots"][x_n][y_n]
    u_in_mm = robot.params["units_in_mm"]
    tool_i = find_tool_i_by_coord(robot, x_n, y_n)
    if tool_i == -1:
        print("ERROR: No tool in slot (" + str(x_n) + ", " + str(y_n) + ").")
        return
        
    tool = robot.tools[tool_i]
    
    if tool["type"] != "tip_tray":
        print("ERROR: The tool in  slot (" + str(x_n) + ", " + str(y_n) + ") is not a tip tray.")
        return
    
    stal_dest_x, stal_dest_y = calc_well_position(tool["params"], x_n, y_n, well_x_n, well_y_n, u_in_mm, "96_well")
    
    tray_volume = tool["params"]["volume"]
    
    if tray_volume == 1000:
        approach_height = 95
        dest_height = 82
    elif tray_volume == 200:
        approach_height = 60
        dest_height = 49.5
    elif tray_volume == 20:
        approach_height = 60
        dest_height = 40
    else:
        print("ERROR: Unknown volume: " + str(tray_volume))
        return
    
    stal_appr_z = slot["floor_z"] - u_in_mm[2] * approach_height
    stal_dest_z = slot["floor_z"] - u_in_mm[2] * dest_height
    
    pip_tip = robot.current_tool["tip"]
    if pip_tip[0] < 0 or pip_tip[1] < 0 or pip_tip[2] < 0:
        print("ERROR: Pipettor tip is not calibrated.")
        return
    
    stal_i = find_tool_i_by_type(robot, "mobile_probe")
    stal_tip = robot.tools[stal_i]["params"]["tip"]
    
    dest_x = stal_dest_x - stal_tip[0] + pip_tip[0]
    dest_y = stal_dest_y - stal_tip[1] + pip_tip[1]
    appr_z = stal_appr_z - stal_tip[2] + pip_tip[2]
    dest_z = stal_dest_z - stal_tip[2] + pip_tip[2]
    
    robot.move(x=dest_x, y=dest_y)
    robot.move(z=appr_z)
    robot.move(z=dest_z, speed_z = 1000)
    
    robot.move_delta(dz = -100 * u_in_mm[2])

def return_tip(robot, x_n, y_n, well_x_n, well_y_n):
    slot = robot.params["slots"][x_n][y_n]
    u_in_mm = robot.params["units_in_mm"]
    tool_i = find_tool_i_by_coord(robot, x_n, y_n)
    if tool_i == -1:
        print("ERROR: No tool in slot (" + str(x_n) + ", " + str(y_n) + ").")
        return
        
    tool = robot.tools[tool_i]
    
    if tool["type"] != "tip_tray":
        print("ERROR: The tool in  slot (" + str(x_n) + ", " + str(y_n) + ") is not a tip tray.")
        return
    
    stal_dest_x, stal_dest_y = calc_well_position(tool["params"], x_n, y_n, well_x_n, well_y_n, u_in_mm, "96_well")
    
    tray_volume = tool["params"]["volume"]
    
    if tray_volume == 1000:
        approach_height = 95
        dest_height = 84
    elif tray_volume == 200:
        approach_height = 60
        dest_height = 49.5
    elif tray_volume == 20:
        approach_height = 60
        dest_height = 42
    else:
        print("ERROR: Unknown volume: " + str(tray_volume))
        return
    
    stal_appr_z = slot["floor_z"] - u_in_mm[2] * approach_height
    stal_dest_z = slot["floor_z"] - u_in_mm[2] * dest_height
    
    pip_tip = robot.current_tool["tip"]
    if pip_tip[0] < 0 or pip_tip[1] < 0 or pip_tip[2] < 0:
        print("ERROR: Pipettor tip is not calibrated.")
        return
    
    stal_i = find_tool_i_by_type(robot, "mobile_probe")
    stal_tip = robot.tools[stal_i]["params"]["tip"]
    
    dest_x = stal_dest_x - stal_tip[0] + pip_tip[0]
    dest_y = stal_dest_y - stal_tip[1] + pip_tip[1]
    appr_z = stal_appr_z - stal_tip[2] + pip_tip[2]
    dest_z = stal_dest_z - stal_tip[2] + pip_tip[2]
    
    robot.move(x=dest_x, y=dest_y)
    robot.move(z=appr_z)
    robot.current_tool_device.drop_tip()
    
    robot.move_delta(dz = -100 * u_in_mm[2])

def move_tube(robot, source_x, source_y, source_well_x, source_well_y, dest_x, dest_y, dest_well_x, dest_well_y):
    u_mm = robot.params["units_in_mm"]
    gripper = robot.current_tool_device
    if robot.current_tool["type"] != "mobile_gripper":
        print("ERROR: Current tool is not a gripper.")
        return
        
    # TODO: Right now this only works for eppendorf tubes. Make it work for other types. 
    gripper.operate_gripper(100)
    
    robot.move(z=u_mm[2] * 10)
    approach_well(robot, source_x, source_y, source_well_x, source_well_y)
    gripper.operate_gripper(30)
    time.sleep(2)
    
    robot.move(z=u_mm[2] * 10)
    approach_well(robot, dest_x, dest_y, dest_well_x, dest_well_y)
    gripper.operate_gripper(100)
    time.sleep(2)
    
    robot.move(z=u_mm[2] * 10)
    
    

# Positions the tip of the pipettor 2mm above the well. 
# Assumes that the robot is within safe region from the well. 
# Meaning, if it goes by xy first and by z after that, it won't hit anything. 
# Pay attention to navigation and use at your own risk.
def approach_well(robot, x_n, y_n, well_x_n, well_y_n):
    slot = robot.params["slots"][x_n][y_n]
    u_in_mm = robot.params["units_in_mm"]
    rack_i = find_tool_i_by_coord(robot, x_n, y_n)
    if rack_i == -1:
        print("ERROR: No tool in slot (" + str(x_n) + ", " + str(y_n) + ").")
        return
    
    rack = robot.tools[rack_i]
    
    if rack["type"] != "rack":
        print("ERROR: The tool in  slot (" + str(x_n) + ", " + str(y_n) + ") is not a rack.")
        return
    
    rack_type = rack["params"]["rack_type"]
    
    tube_height_above_rack = rack_dict[rack_type]["tube_height_above_rack"]
    
    stal_dest_x, stal_dest_y = calc_well_position(rack["params"], x_n, y_n, well_x_n, well_y_n, u_in_mm, rack_type)
    
    dest_height = tube_height_above_rack + rack_dict[rack_type]["rack_height"] + 2
    
    if robot.current_tool == None:
        print("ERROR: No pipettor is attached.")
        return
    
    c_tool = robot.current_tool
    stal_i = find_tool_i_by_type(robot, "mobile_probe")
    
    if c_tool["type"] == "pipettor":
        pipettor_volume = c_tool["params"]["volume"]
        pipettor_type = c_tool["params"]["pipettor_type"]
        
        if pipettor_type == "multi":
            print("ERROR: This feature is under construction.")
            return
        
        if pipettor_volume == 1000:
            tip_height_mm = 76
        elif pipettor_volume == 200:
            tip_height_mm = 42
        elif pipettor_volume == 20:
            tip_height_mm = 32
        else:
            print("ERROR: Unknown pipettor type.")
            return
        
        stal_dest_z = slot["floor_z"] - u_in_mm[2] * (dest_height + tip_height_mm)
        
        tool_tip = c_tool["tip"]
        stal_tip = robot.tools[stal_i]["params"]["tip"]
    elif c_tool["type"] == "mobile_gripper":
        stal_tip = robot.tools[stal_i]["params"]["tip"]
        tool_tip = deepcopy(stal_tip)
        length_screw_mm = 33.9
        stalactite_height = 147
        tool_height = 160
        tool_tip[2] += (-tool_height + length_screw_mm + stalactite_height) * u_in_mm[2]
        stal_dest_z = slot["floor_z"] - u_in_mm[2] * (dest_height - 10)
    else:
        print("ERROR: Attached tool is not a pipettor or a gripper.")
        return
    
    dest_x = stal_dest_x - stal_tip[0] + tool_tip[0]
    dest_y = stal_dest_y - stal_tip[1] + tool_tip[1]
    dest_z = stal_dest_z - stal_tip[2] + tool_tip[2]

    robot.move(x=dest_x, y=dest_y)
    robot.move(z=dest_z)
    
def set_plunger_level(pipettor, level):
    pipettor.write_wait("G0 X-" + str(level))

def set_pipettor_speed(pipettor, speed):
    pipettor.write_wait("$110=" + str(speed) + "\n")
    
# All pipetting functions assume that the pipettor tip hovers 2mm above the well, and return to that position at the end.
def uptake_liquid(robot, x_n, y_n, expected_liquid_level, plunger_level, delay=0, speed=700):
    # TODO: Calculate x_n and y_n from the position. 
    # expected liquid level is the liquid level that is expected to be at the end (or higher).
    u_mm = robot.params["units_in_mm"]
    
    rack_i = find_tool_i_by_coord(robot, x_n, y_n)
    if rack_i == -1:
        print("ERROR: No tool in slot (" + str(x_n) + ", " + str(y_n) + ").")
        return
        
    rack = robot.tools[rack_i]
    
    if rack["type"] != "rack":
        print("ERROR: The tool in  slot (" + str(x_n) + ", " + str(y_n) + ") is not a rack.")
        return
    
    rack_type = rack["params"]["rack_type"]

    tube_height = rack_dict[rack_type]["tube_height"]
        
    if robot.current_tool["params"]["volume"] == 20:
        if speed > 400:
            speed = 400
    
    pipettor = robot.current_tool_device
    
    drop = (tube_height - expected_liquid_level + 2) * u_mm[2]
    
    set_pipettor_speed(pipettor, speed)
    set_plunger_level(pipettor, plunger_level)
    robot.move_delta(dz = drop)
    set_plunger_level(pipettor, 0)
    time.sleep(delay)
    robot.move_delta(dz = -drop)
    
def release_liquid(robot, x_n, y_n, plunger_level, delay=0, speed=700):
    # TODO: Specify how deep to descend in a separate parameter. 
    # TODO: Specify which wall to touch (if any) in a parameter. 
    # TODO: Calculate x_n and y_n from the position. 
    # expected liquid level is the liquid level that is expected to be at the end (or higher).
    u_mm = robot.params["units_in_mm"]
    
    rack_i = find_tool_i_by_coord(robot, x_n, y_n)
    if rack_i == -1:
        print("ERROR: No tool in slot (" + str(x_n) + ", " + str(y_n) + ").")
        return
        
    rack = robot.tools[rack_i]
    
    if rack["type"] != "rack":
        print("ERROR: The tool in  slot (" + str(x_n) + ", " + str(y_n) + ") is not a rack.")
        return
    
    rack_type = rack["params"]["rack_type"]
    
    tube_height = rack_dict[rack_type]["tube_height"]
    tube_width = rack_dict[rack_type]["tube_width"]
    
    touch_wall_height_fraction = 1/5
    if robot.current_tool["params"]["volume"] == 20:
        touch_wall_height_fraction = 2/3
        if speed > 400:
            speed = 400
    
    pipettor = robot.current_tool_device
    
    drop = (tube_height * touch_wall_height_fraction + 2) * u_mm[2] # CONSTANT
    touch_wall = tube_width * u_mm[1] * 3/4
    
    set_pipettor_speed(pipettor, speed)
    robot.move_delta(dz = drop)
    set_plunger_level(pipettor, plunger_level)
    time.sleep(delay)
    set_plunger_level(pipettor, plunger_level + 5)
    robot.move_delta(dy = touch_wall)
    robot.move_delta(dy = -touch_wall)
    robot.move_delta(dz = -drop)
    set_plunger_level(pipettor, 0)

# Assumes a 50 ml source rack with a full tube in 0, 0 slot and an eppendorf destination rack with empty tubes in all slots
def calibrate_volume(robot, source_x, source_y, dest_x, dest_y):
    dest_width = 8
    dest_height = 4
    
    u_mm = robot.params["units_in_mm"]

    robot.move(z = 100 * u_mm[2])
    
    plunger_level = 1
    data_point_i = 0
    
    for row_i in [0, 2, 3]:
        for column_i in range(dest_width):
            approach_well(robot, source_x, source_y, 0, 0)
            uptake_liquid(robot, source_x, source_y, 50, plunger_level)
            approach_well(robot, dest_x, dest_y, column_i, row_i)
            release_liquid(robot, dest_x, dest_y, plunger_level)
            robot.move_delta(dz = -150 * u_mm[2])
            data_point_i += 1
            if data_point_i == 4:
                data_point_i = 0
                plunger_level += 5

# Makes the stalactite go to a certain well in a rack. TODO: Replace with "approach well". 
def goto_rack_well(robot, x_n, y_n, well_x_n, well_y_n):
    tool_i = find_tool_i_by_coord(robot, x_n, y_n)
    if tool_i == -1:
        print("ERROR: No tool in slot (" + str(x_n) + ", " + str(y_n) + ").")
        return
        
    tool = robot.tools[tool_i]
    
    if tool["type"] != "rack":
        print("ERROR: The tool in  slot (" + str(x_n) + ", " + str(y_n) + ") is not a rack.")
        return
        
    u_mm = robot.params["units_in_mm"]
    
    rack_type = tool["params"]["rack_type"]
    
    dest_x, dest_y = calc_well_position(tool["params"], x_n, y_n, well_x_n, well_y_n, u_mm, rack_type)
    dest_z = tool["params"]["height"] - 1 * u_mm[2]
    
    robot.move(x=dest_x, y=dest_y)
    robot.move(z=dest_z)

# Makes the stalactite visit the center of every well of a rack. 
def check_rack_calibration(robot, x_n, y_n):
    tool_i = find_tool_i_by_coord(robot, x_n, y_n)
    if tool_i == -1:
        print("ERROR: No tool in slot (" + str(x_n) + ", " + str(y_n) + ").")
        return  
        
    tool = robot.tools[tool_i]
    
    if tool["type"] != "rack":
        print("ERROR: The tool in  slot (" + str(x_n) + ", " + str(y_n) + ") is not a rack.")
        return
    
    robot.home("Z")
    
    for column_i in range(tool["params"]["width_n"]):
        for row_i in range(tool["params"]["height_n"]):
            goto_rack_well(robot, x_n, y_n, column_i, row_i)
    
def check_floor_calibration(robot):
    w_n = robot.params["width_n"]
    h_n = robot.params["height_n"]
    
    for row_i in range(h_n):
        for col_i in range(w_n):
            goto_slot_lt(robot, col_i, row_i)
            goto_slot_lb(robot, col_i, row_i)
            goto_slot_rb(robot, col_i, row_i)
            goto_slot_rt(robot, col_i, row_i)

def calibrate_circle_outer(robot, x_n, y_n, expected_z):
    robot.home("Z")
    goto_slot_lt(robot, x_n, y_n)
    robot.move(z=expected_z)
    robot.move_delta(dx=robot.params['slot_width'] / 2)
    north = find_wall(robot, "Y", 1, "calibrate_circle_outer-north")

    robot.move_delta(dz = -robot.params['units_in_mm'][2] * 30)
    goto_slot_lt(robot, x_n, y_n)
    robot.move(z=expected_z)
    robot.move_delta(dy=robot.params['slot_height'] / 2)
    east = find_wall(robot, "X", 1, "calibrate_circle_outer-east")
    
    robot.move_delta(dz = -robot.params['units_in_mm'][2] * 30)
    goto_slot_rb(robot, x_n, y_n)
    robot.move(z=expected_z)
    robot.move_delta(dx=-robot.params['slot_width'] / 2)
    south = find_wall(robot, "Y", -1, "calibrate_circle_outer-south")
    
    robot.move_delta(dz = -robot.params['units_in_mm'][2] * 30)
    goto_slot_rb(robot, x_n, y_n)
    robot.move(z=expected_z)
    robot.move_delta(dy=-robot.params['slot_height'] / 2)
    west = find_wall(robot, "X", -1, "calibrate_circle_outer-west")

    return [(east + west) / 2, (south + north) / 2]

def calibrate_circle(robot, approx_center):
    robot.move(z=approx_center[2] - 100)
    robot.move(x=approx_center[0], y=approx_center[1])
    robot.move(z=approx_center[2])

    x_pos = find_wall(robot, "X", 1, "calibrate_circle-x_pos")
    x_neg = find_wall(robot, "X", -1, "calibrate_circle-x_neg")
    
    center_x = (x_pos + x_neg) / 2
    robot.move(x=center_x)
    
    y_pos = find_wall(robot, "Y", 1, "calibrate_circle-y_pos")
    y_neg = find_wall(robot, "Y",   -1, "calibrate_circle-y_neg")
    
    radius_1 = (y_pos - y_neg) / 2
    center_y = (y_pos + y_neg) / 2
    robot.move(y=center_y)
    
    
    x_pos = find_wall(robot, "X", 1, "calibrate_circle-x_pos2")
    x_neg = find_wall(robot, "X", -1, "calibrate_circle-x_neg2")
    radius_2 = (x_pos - x_neg) / 2
    
    radius = (radius_1 + radius_2) / 2
    
    return center_x, center_y, radius

def calibrate_slot(robot, n_x, n_y, retract_z=2.5):
    calibration_start_time = time.time()

    approx_const = 0.9

    robot.move(z=safe_height)
    go_to_slot_center_calibration(robot, n_x, n_y)
    z_max = find_wall(robot, "Z", 1, "calibrate_slot-center" + str(n_x) + "_" + str(n_y))
    robot.move(z=z_max - retract_z)
    
    inner_slot_w = robot.params['slot_width'] - robot.params['plank_width']
    inner_slot_h = robot.params['slot_height'] - robot.params['flower_height']
    
    current_slot = deepcopy(default_slot)   
    current_slot["floor_z"] = z_max
    
    robot.move_delta(dx= -inner_slot_w * approx_const / 2, dy= -inner_slot_h * approx_const / 2)
    current_slot['LT'][0] = find_wall(robot, "X", -1, "calibrate_slot-LT" + str(n_x) + "_" + str(n_y)) - robot.params['plank_width'] / 2
    current_slot['LT'][1] = find_wall(robot, "Y", -1, "calibrate_slot-LT" + str(n_x) + "_" + str(n_y)) - robot.params['flower_height'] / 2
    
    robot.move_delta(dy= inner_slot_h * approx_const)
    current_slot['LB'][0] = find_wall(robot, "X", -1, "calibrate_slot-LB" + str(n_x) + "_" + str(n_y)) - robot.params['plank_width'] / 2
    current_slot['LB'][1] = find_wall(robot, "Y", 1, "calibrate_slot-LB" + str(n_x) + "_" + str(n_y)) + robot.params['flower_height'] / 2
    
    robot.move_delta(dx= inner_slot_w * approx_const)
    current_slot['RB'][0] = find_wall(robot, "X", 1, "calibrate_slot-RT" + str(n_x) + "_" + str(n_y)) + robot.params['plank_width'] / 2
    current_slot['RB'][1] = find_wall(robot, "Y", 1, "calibrate_slot-RT" + str(n_x) + "_" + str(n_y)) + robot.params['flower_height'] / 2
    
    robot.move_delta(dy= -inner_slot_h * approx_const)
    current_slot['RT'][0] = find_wall(robot, "X", 1, "calibrate_slot-RB" + str(n_x) + "_" + str(n_y)) + robot.params['plank_width'] / 2
    current_slot['RT'][1] = find_wall(robot, "Y", -1, "calibrate_slot-RB" + str(n_x) + "_" + str(n_y)) - robot.params['flower_height'] / 2
    
    robot.move(z=safe_height)
    
    robot.params['slots'][n_x][n_y] = current_slot
    
    calibration_end_time = time.time()
    print("Slot calibration time: ")
    print(calibration_end_time - calibration_start_time)

def calc_slot_center(robot, n_x, n_y):
    slot = robot.params["slots"][n_x][n_y]
    return [(slot['LT'][0] + slot['RB'][0]) / 2, (slot['LT'][1] + slot['RB'][1]) / 2]

def goto_slot_center(robot, n_x, n_y):
    slot = robot.params["slots"][n_x][n_y]
    center = [(slot['LT'][0] + slot['RB'][0]) / 2, (slot['LT'][1] + slot['RB'][1]) / 2]
    robot.move(x = center[0], y = center[1])

def goto_slot_lt(robot, n_x, n_y):
    slot = robot.params["slots"][n_x][n_y]
    robot.move(x = slot['LT'][0], y = slot['LT'][1])
    
def goto_slot_lb(robot, n_x, n_y):
    slot = robot.params["slots"][n_x][n_y]
    robot.move(x = slot['LB'][0], y = slot['LB'][1])
    
def goto_slot_rt(robot, n_x, n_y):
    slot = robot.params["slots"][n_x][n_y]
    robot.move(x = slot['RT'][0], y = slot['RT'][1])
    
def goto_slot_rb(robot, n_x, n_y):
    slot = robot.params["slots"][n_x][n_y]
    robot.move(x = slot['RB'][0], y = slot['RB'][1])
    
def ziggurat_calibration(robot, x_n, y_n):
    # x_n, y_n -- ziggurat coordinates.

    if not robot.calibrated:
        print("ERROR: The robot is not calibrated. Use calibrate(robot) first.")
        return
    
    def find_next_step(axis, expected_width):
        initial_wall = find_wall(robot, axis, 1, "ziggurat_calibration-find_next_step")
        while True:
            # TODO: Make a rough approimaion of units in mm by z axis and express this 60 in 10 mm times that.
            robot.move_delta(dz=-60)
            next_wall = find_wall(robot, axis, 1, "ziggurat_calibration-find_next_step")
            if next_wall - initial_wall > expected_width * 0.8:
                return next_wall
    
    n_steps = 3
    dxs = []
    dys = []
    dzs = []
    
    robot.home("Z")

    goto_slot_lt(robot, x_n, y_n)   
    robot.move(z=5400)
    robot.move(z=safe_height)
    robot.move_delta(dy=robot.params['slot_height'] / 2)
    
    old_x = find_wall(robot, "X", 1, "ziggurat_calibration-x1")
    old_z = find_wall(robot, "Z", 1, "ziggurat_calibration-z11")
    
    for step_i in range(n_steps):
        new_x = find_next_step("X", 10 * robot.params['units_in_mm'][0])
        new_z = find_wall(robot, "Z", 1, "ziggurat_calibration-z" + str(step_i) + "1")
        if step_i == n_steps - 1:
            dxs.append((new_x - old_x) / 2)
        else: 
            dxs.append(new_x - old_x)
        dzs.append(old_z - new_z)
        old_x = new_x
        old_z = new_z
    
    robot.move(z=5400)
    goto_slot_lt(robot, x_n, y_n)
    robot.move(z=safe_height)
    robot.move_delta(dx=robot.params['slot_width'] / 2)
    
    old_y = find_wall(robot, "Y", 1, "ziggurat_calibration-y1")
    old_z = find_wall(robot, "Z", 1, "ziggurat_calibration-z12")
    
    for step_i in range(n_steps):
        new_y = find_next_step("Y", 10 * robot.params['units_in_mm'][0])
        new_z = find_wall(robot, "Z", 1, "ziggurat_calibration-z" + str(step_i) + "2")
        dys.append(new_y - old_y)
        dzs.append(old_z - new_z)
        old_y = new_y
        old_z = new_z
    
    robot.params['units_in_mm'][0] = sum(dxs) / len(dxs) / 10
    robot.params['units_in_mm'][1] = sum(dys) / len(dys) / 10
    robot.params['units_in_mm'][2] = sum(dzs) / len(dzs) / 10

    print(robot.params['units_in_mm'])
    print(dxs)
    print(dys)
    print(dzs)
    
    update_floor(robot)

def calibrate_floor(robot, expected_slot_size=[139, 86], safe_z=590, retract_xy=5, retract_z=3):
    """
    Basic floor calibration function. To be used after robot assembly (or major rework).
    Will touch every slot.
    """
    #if robot.current_tool["type"] != "stationary_probe": 
    #   print("ERROR: No probe connected.")
    #   return
    
    calibration_start_time = time.time()
    
    slot_width_mm = 150
    slot_height_mm = 110
    
    expected_slot_width = expected_slot_size[0]
    expected_slot_height = expected_slot_size[1]
    approx_const = 0.9
    
    n_slots_width = 6
    n_slots_height = 4
    robot.params = {
        'width_n': n_slots_width,
        'height_n': n_slots_height,
        'slots': [[0 for j in range(n_slots_height)] for i in range(n_slots_width)],
        'slot_width': -1,
        'slot_height': -1,
        'plank_width': -1,
        'flower_height': -1,
        'units_in_mm': [-1.0, -1.0, -1.0]
    }

    # Temporary commented to shorten debugging time
    #robot.home()
    robot.min = robot.getPosition()
    robot.max = [0, 0, 0]
    
    # Finding rough distance to the floor
    robot.move(z=safe_z)
    robot.max[2] = find_wall(robot, "Z", 1, "calibrate-0-0-floor")
    
    # Calibrating top-left plank
    # --------------------------
    robot.move(z=robot.max[2] - retract_z)  # Move robot up not to touch floor
    robot.move(y = 50) # Move robot approx to the center of the top-left plank
    # Now approaching first plank from left to right (from home position)
    first_plank_left_y = find_wall(robot, "X", 1, "calibrate-first_plank_left")
    robot.move(z=safe_z)    # Moving up not to get to the other side of the plank, above it.
    robot.move_delta(dx=15) # Moving to the other side of the plank
    
    robot.move(z=robot.max[2] - retract_z) # Moving robot down so it is below the slot border level
    pos = robot.getPosition()
    slot_wall_x_down = find_wall(robot, "X", -1, "calibrate-first_slot_down")  # Approaching slot from the other direction
    robot.move_delta(dx=expected_slot_width * approx_const) # Move to the other side of the slot, same Y

    slot_wall_x_up = find_wall(robot, "X", 1, "calibrate-first_slot_up")    # Approaching second plank on the top-left slot (00)
#   robot.move_delta(dx=-retract_xy)    # Moving X slightly back, so robot does not touch plank while calibrating Y
    slot_wall_y_down = find_wall(robot, "Y", -1, "calibrate-first_slot_down")   # Finding upper Y border
    robot.move_delta(dy=expected_slot_height * approx_const)    # Moving to the other Y border of the top-left slot (00)
    slot_wall_y_up = find_wall(robot, "Y", 1, "calibrate-first_slot_up")    # Finding lower Y border
    
    # Calculating top-left slot (00) parameters
    first_center = [(slot_wall_x_down + slot_wall_x_up) / 2, (slot_wall_y_down + slot_wall_y_up) / 2]
    log_value("calibrate-first_center_approx", first_center[0], "X")
    log_value("calibrate-first_center_approx", first_center[1], "Y")
    
    robot.move(z=safe_height)
    robot.move_delta(dy=35)
    robot.move(z=robot.max[2] - retract_z)
    tmp_y_measurement = find_wall(robot, "Y", -1, "calibrate-flower_top")   

    plank_width = slot_wall_x_down - first_plank_left_y
    flower_height = tmp_y_measurement - slot_wall_y_up
    robot.params['plank_width'] = plank_width
    robot.params['flower_height'] = flower_height
    
    robot.first_slot = [slot_wall_x_down, slot_wall_x_up, slot_wall_y_down, slot_wall_y_up, robot.max[2]]
    
    robot.params['slot_width'] = slot_wall_x_up - slot_wall_x_down + plank_width
    robot.params['slot_height'] = slot_wall_y_up - slot_wall_y_down + flower_height
    # TODO: Update it after calibration. 
    
    check_slot_n_y = robot.params['height_n'] - (1 - robot.params['height_n'] % 2)
    last_slot_center_estimate = [slot_wall_x_down + (robot.params['width_n'] - 0.5) * robot.params['slot_width'], slot_wall_y_down + (check_slot_n_y - 0.5) * robot.params['slot_height']]
    log_value("calibrate-last_center_approx1", last_slot_center_estimate[0], "X")
    log_value("calibrate-last_center_approx1", last_slot_center_estimate[1], "Y")
    
    
    robot.move(z=safe_height)
    robot.move(x = last_slot_center_estimate[0], y = last_slot_center_estimate[1])

    find_wall(robot, "Z", 1, "calibrate-last_slot_center", step_back_length=2.5)    

    robot.move_delta(dx= -expected_slot_width * approx_const / 2)
    slot_wall_x_down = find_wall(robot, "X", -1, "calibrate-last_slot_down")
    robot.move_delta(dx=expected_slot_width * approx_const)
    slot_wall_x_up = find_wall(robot, "X", 1, "calibrate-last_slot_up")
    robot.move_delta(dy= -expected_slot_height * approx_const / 2)
    slot_wall_y_down = find_wall(robot, "Y", -1, "calibrate-last_slot_down")
    robot.move_delta(dy=expected_slot_height * approx_const)
    slot_wall_y_up = find_wall(robot, "Y", 1, "calibrate-last_slot_up")
    
    robot.move_delta(dz=-7)
    
    robot.last_slot = [slot_wall_x_down, slot_wall_x_up, slot_wall_y_down, slot_wall_y_up, robot.getPosition()[2]]

    last_center = [(slot_wall_x_down + slot_wall_x_up) / 2, (slot_wall_y_down + slot_wall_y_up) / 2]
    log_value("calibrate-last_center_approx2", last_center[0], "X")
    log_value("calibrate-last_center_approx2", last_center[1], "Y")
    
    # units_in_mm parameter is used when moving step is different than mm.
    # 12/25/2019 Sergii corrected firmware, so now movement unit is mm.
    # TODO. units_in_mm parameter should be either completely removed, or be optional.
    # For now, I am adding it for compatibility.
    
    #robot.params['units_in_mm'][0] = (last_center[0] - first_center[0]) / ((robot.params['width_n'] - 1) * slot_width_mm)
    #robot.params['units_in_mm'][1] = (last_center[1] - first_center[1]) / ((check_slot_n_y - 1) * slot_height_mm)
    robot.params['units_in_mm'][0] = 1.0
    robot.params['units_in_mm'][1] = 1.0
    robot.params['units_in_mm'][2] = 1.0
    
    robot.params['slot_width'] = slot_wall_x_up - slot_wall_x_down + plank_width
    robot.params['slot_height'] = slot_wall_y_up - slot_wall_y_down + flower_height 
    
    for n_x in range(robot.params['width_n']):
        for n_y2 in range(math.floor(robot.params['height_n'] / 2)):
            calibrate_slot(robot, n_x, n_y2 * 2)
            
    robot.calibrated = True
    
    fill_slots(robot)
#   ziggurat_calibration(robot)
    
    update_floor(robot)
    
    calibration_end_time = time.time()
    print("Calibration time: ")
    print(calibration_end_time - calibration_start_time)



# TODO: inline this function.
def fill_slots(robot):
    for n_x in range(robot.params['width_n']):
        for n_y2 in range(math.floor(robot.params['height_n'] / 2)):
            robot.params['slots'][n_x][n_y2 * 2 + 1] = deepcopy(default_slot)
            
            print("row" + str(n_y2 * 2 + 1))
            
            if n_y2 * 2 + 1 < math.floor(robot.params['height_n']):
                robot.params['slots'][n_x][n_y2 * 2 + 1]["LT"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2]["LB"])
                robot.params['slots'][n_x][n_y2 * 2 + 1]["RT"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2]["RB"])
                robot.params['slots'][n_x][n_y2 * 2 + 1]["floor_z"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2]["floor_z"])
                if n_y2 * 2 + 2 < math.floor(robot.params['height_n']) - 1:
                    robot.params['slots'][n_x][n_y2 * 2 + 1]["LB"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2 + 2]["LT"])
                    robot.params['slots'][n_x][n_y2 * 2 + 1]["RB"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2 + 2]["RT"])
                else:
                    robot.params['slots'][n_x][n_y2 * 2 + 1]["LB"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2]["LB"])
                    robot.params['slots'][n_x][n_y2 * 2 + 1]["RB"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2]["RB"])
                    robot.params['slots'][n_x][n_y2 * 2 + 1]["LB"][1] += robot.params['slot_height']
                    robot.params['slots'][n_x][n_y2 * 2 + 1]["RB"][1] += robot.params['slot_height']

def go_to_slot_center_calibration(robot, n_x, n_y):
    if n_x < 0 or n_x >= robot.params['width_n']:
        print("ERROR: Invalid x coordinate: " + str(n_x))
        return
        
    if n_y < 0 or n_y >= robot.params['height_n']:
        print("ERROR: Invalid y coordinate: " + str(n_y))
        return
        
    first_slot_center = [(robot.first_slot[0] + robot.first_slot[1])/2, (robot.first_slot[2] + robot.first_slot[3])/2]
    last_slot_center = [(robot.last_slot[0] + robot.last_slot[1])/2, (robot.last_slot[2] + robot.last_slot[3])/2]
        
    destination_x = first_slot_center[0] + n_x * robot.params['slot_width']
    destination_y = first_slot_center[1] + n_y * robot.params['slot_height']
    
    log_value("go_to_slot_center_calibration-center_approx_" + str(n_x) + "_" + str(n_y), destination_x, "X")
    log_value("go_to_slot_center_calibration-center_approx_" + str(n_x) + "_" + str(n_y), destination_y, "Y")
    
    robot.move(x=destination_x, y=destination_y)

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

def retract_until_no_touch(arnie, touch_probe, axis, step, touch_function=None, speed_xy=4000, speed_z=2000):
    if touch_function == None:
        touch_function = touch_probe.isTouched
        
    delta_coord = AxisToCoordinates(axis, step)
    
    if delta_coord != [0, 0, 0] and delta_coord != [None, None, None]:
        while touch_function():
            arnie.move_delta(dx=delta_coord[0], dy=delta_coord[1], dz=delta_coord[2], speed_xy=speed_xy, speed_z=speed_z)
    else:
        print ("Interrupted because wrong axis was provided.")
        return
        
    x, y, z = arnie.getPosition()
    return x, y, z
    
def ApproachUntilTouch(arnie, touch_probe, axis, step, expectation=-1, tolerance=-1, touch_function=None, speed_xy=8000, speed_z=5000):
    """
    Arnie will move along specified "axis" by "step"
    Provide:
        arnie - instance of Arnie object
        touch_probe - instance of touch_probe object
        axis - string, "x", "y" or "z"
        step - distance to move at every step
    """
    
    if touch_function == None:
        touch_function = touch_probe.isTouched
    
    delta_coord = AxisToCoordinates(axis, step)
    
    if delta_coord != [0, 0, 0] and delta_coord != [None, None, None]:
        while not touch_function():
            # ApproachUntilTouch forward by a tiny step 
            arnie.move_delta(dx=delta_coord[0], dy=delta_coord[1], dz=delta_coord[2], speed_xy=speed_xy, speed_z=speed_z)
            if expectation != -1 and tolerance != -1:
                position = arnie.getPosition()
                if abs(position[axis_index(axis)] - expectation) > tolerance:
                    return -1
    else:
        print ("Interrupted because wrong axis was provided.")
        return
        
    x, y, z = arnie.getPosition()
    
    return x, y, z

def update_floor(robot):
    if os.path.exists("floor.json"):
        time_str = str(datetime.now()).replace(":", "_")
        copyfile("floor.json", time_str + "floor.json")
    file = open('floor.json', 'w')
    file.write(json.dumps(robot.params))
    file.close()

def load_floor(robot):
    file = open("floor.json", "r")
    params_string = file.read()
    robot.params = json.loads(params_string)
    file.close()

def update_tools(robot):
    if os.path.exists("tools.json"):
        time_str = str(datetime.now()).replace(":", "_")
        copyfile("tools.json", time_str + "tools.json")
    file = open('tools.json', 'w')
    file.write(json.dumps(robot.tools))
    file.close()

def load_tools(robot):
    file = open("tools.json", "r")
    tools_string = file.read()
    robot.tools = json.loads(tools_string)
    file.close()

def connect_tool(port_name, robot=None):
    device = llc.serial_device(port_name)
    #msg = device.recent_message

    recognized_desc = None
    for desc in device_type_descriptions:
        if device.isWelcomeMessageMatches(desc["message"]):
        #if re.search(pattern=desc["message"], string=msg):
            recognized_desc = desc
            break
        
    if recognized_desc == None:
        print("ERROR: Device is unrecognized.")
        return

    device.__class__ = recognized_desc["class"]
    device.description = recognized_desc
    
    try:
        device.firstActions(home=True)
    except AttributeError:
        pass
    
    if robot != None:
        if recognized_desc["mobile"]:
            robot.current_tool_device = device
        else:
            robot.tool_devices.append(device)
    
    if device.__class__ == pipettor:
        # Sergii, 12/17/2019
        # Quick fix for the "Alarm" error after picking up the tool,
        # which hangs the operation and prevents homing from succeeding
        device.write("$X")
        device.write("G0 X-5")
        # Homing the pipettor
        device.home()
    
    return device



def connect():
    ports = llc.listSerialPorts()
    robot = None
    available_devices = []
    
    for port_name in ports:
        device = connect_tool(port_name)
        if device.__class__ == cart.arnie:
            robot = device
        else: 
            available_devices.append(device)

    if robot == None:
        if len(robots) == 0:
            print("ERROR: No robot detected.")
            print(ports)
            return
        else: 
            robot = robots[0]
    
    if os.path.exists("floor.json"):
        load_floor(robot)
        robot.calibrated = True
    
    if os.path.exists("tools.json"):
        load_tools(robot)
    
    # TODO: current_device is never used. Rename current_tool_device into current_device.
    robot.current_device = None
    robot.current_tool_device = None
    robot.current_tool = None
    
    for device in available_devices:
        if device.description["mobile"]:
            robot.current_tool_device = device
            tool_i = find_tool_i_by_type(robot, device.description["type"])
            if tool_i == -1:
                robot.current_tool = deepcopy(default_tool)
                robot.current_tool["type"] = device.description["type"]
            else:
                robot.current_tool = deepcopy(robot.tools[tool_i])
        else:
            robot.tool_devices.append(device)   

    robots.append(robot)
    print("Connected. Homing.")
        
    log("Start")
    log(str(datetime.now()))
    
    print("Done.")
    return robot
