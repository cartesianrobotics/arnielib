"""
Module handling high-leve calibration routines
"""


# Internal arnielib modules
import tools
import param


def findObjectXYCenterInner(probe, expected_travel_x=0, expected_travel_y=0,
                            move_x_relative_to_center=0, move_y_relative_to_center=0):
    """
    Finds center of the hole from inside by X and Y. Shape does not matter.
    Robot is assumed to be already in position to touch walls from inside.
    """
    
    center_x = probe.findCenterInner('x', opposite_side_dist=expected_travel_x)
    probe.robot.move(x=center_x+move_x_relative_to_center)
    center_y = probe.findCenterInner('y', opposite_side_dist=expected_travel_y)
    probe.robot.move(y=center_y+move_y_relative_to_center)
    
    return center_x, center_y

    
def findXYInnerManyPoints(probe, points, step):
    
    x_center_list = []
    y_center_list = []
    
    start_x, start_y, start_z = probe.robot.getPosition()
    
    for i in range(points):
        center_x = probe.findCenterInner('x')
        probe.robot.move(x=center_x)
        probe.robot.move_delta(dy=step)
        x_center_list.append(center_x)
    x_center = sum(x_center_list) / (points * 1.0)
    
    probe.robot.move(start_x, start_y)
    for i in range(points):
        center_y = probe.findCenterInner('y')
        probe.robot.move(y=center_y)
        probe.robot.move_delta(dx=step)
        y_center_list.append(center_y)
    y_center = sum(y_center_list) / (points * 1.0)
    
    return x_center, y_center


def findXYCenterOuter(probe, raise_height, opposite_side_dist, orthogonal_retraction,
                      move_x_relative_to_center=0, move_y_relative_to_center=0):
    """
    Finds center of the hole from outside by X and Y. Shape does not matter.
    Robot is assumed to be already in position to touch one of the walls from outside
    """
    # Getting starting coordinates
    start_x, start_y, start_z = probe.robot.getPosition()
    # Finding center by X coordinate
    center_x = probe.findCenterOuter(axis='x', raise_height=raise_height,
                                     dist_through_obstruct=opposite_side_dist)
    # Moving up, so robot can get to the position for Y calibration
    probe.robot.move_delta(dz=-raise_height)
    # Moving to the position for Y calibration
    probe.robot.move(x=center_x+move_x_relative_to_center, 
                     y=start_y-orthogonal_retraction+move_y_relative_to_center)
    # Moving down to the calibration height
    probe.robot.move_delta(dz=raise_height)
    # Finding center by Y coordinate
    center_y = probe.findCenterOuter(axis='y', raise_height=raise_height,
                                     dist_through_obstruct=opposite_side_dist)
    return center_x, center_y


def calibrateMobileToolHolderOuter(probe, tool_name, 
                                   holder_size,
                                   n_x, n_y, 
                                   tool_height,
                                   z_meas_dx, z_meas_dy,
                                   dz_tool_pickup,
                                   calibration_dz=5,
                                   raise_height=10,
                                   dist_from_wall=10):
    """
    Calibrates tool holder and saves results on disc.
    
    Inputs:
        probe
           object of mobile_touch_probe class
        tool_name
            name of the tool (uses to save on disc, later will be used to call the tool
        holder_size
            diameter of the tool holder. 
            Used to find starting point for calibration and to calculate how far to move
            to the other side of the holder
        n_x, n_y 
            slot position, column and row, correspondingly.
        start_dx, start_dy
            robot will start calibration from this position, relative to the center of 
            the slot.
            Slot center is calculated from floor calibration, saved at floor.json
        tool_height 
            Height of the tool from floor. 
        calibration_dz
            Calibration will be started at height z_cal = z_floor - tool_height + calibration_dz
        raise_height
            Height at which robot will rize above the tool
        z_meas_dx, z_meas_dy
            coordinated relative to the center of the tool (newly calculated), at which
            Z calibration will be performed
        dz_tool_pickup
            height at which to pickup tool relative to calibrated z
        dist_from_wall
            How far from the wall to start calibraiton
    """
    # Finding center of the slot where the tool is
    # Using previous floor calibration
    x, y = param.calcSquareSlotCenterFromVertices(n_x=n_x, n_y=n_y)
    # Finding coordinates of slot bottom
    z = param.getSlotZ(n_x=n_x, n_y=n_y)
    
    # Calculating other parameters for calibration
    half_size = holder_size / 2.0
    opposite_side_dist = holder_size + dist_from_wall * 2
    # How much to retract by Y after finishing X calibration
    orthogonal_retraction = half_size + dist_from_wall
    
    # Finding coordinates from where to start calibration
    start_x = x - half_size - dist_from_wall
    start_y = y
    start_z = z - tool_height + calibration_dz

    
    # Moving robot (with probe already attached) to the starting coordinates
    probe.robot.move(x=start_x, y=start_y, z=start_z, z_first=False)
    x, y = findXYCenterOuter(probe, raise_height=raise_height, 
                             opposite_side_dist=opposite_side_dist,
                             orthogonal_retraction=orthogonal_retraction)
                             
    # Now calibrating z coordinate
    # Finding coordinates from where to calibrate Z
    z_meas_x = x + z_meas_dx
    z_meas_y = y + z_meas_dy
    # Moving up
    probe.robot.move_delta(dz=-raise_height)
    # Moving to Z calibration position
    probe.robot.move(x=z_meas_x, y=z_meas_y)
    # Calibrating z
    z = probe.findWall('z', 1)
    # Calculating pickup tool coordinate:
    z_pickup = z + dz_tool_pickup
    
    # Saving data on disk
    tool_data = {
        'position': [x, y, z_pickup],
        'n_y': n_y,
        'n_x': n_x,
        'type': tool_name,
        'tip': [-1, -1, -1],
    }
    param.saveTool(tool_data, slot=(n_x, n_y))
    
    return tool_data
    