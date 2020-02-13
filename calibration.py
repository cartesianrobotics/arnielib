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



def findXYCenterOuterMultiPoint(probe, 
                                exp_cntr_x, exp_cntr_y, 
                                object_size_x, object_size_y, 
                                init_dist_to_obj_x, init_dist_to_obj_y,
                                x_points_list, y_points_list,
                                z_floor, z_meas, z_retract, safe_z=0,
                                second_probe=None):
    
    ar = probe.robot
    
    # Finding distance between provided center and the edge of the object
    side_to_center_x = object_size_x / 2.0
    side_to_center_y = object_size_y / 2.0
    
    # Finding coordinates at which to start measurement (must be away from the object)
    meas_point_x = exp_cntr_x - side_to_center_x - init_dist_to_obj_x
    meas_point_y = exp_cntr_y - side_to_center_y - init_dist_to_obj_y
    
    # Finding coordinates to measure opposite side of the object
    meas_point_x_opposite = exp_cntr_x + side_to_center_x + init_dist_to_obj_x
    meas_point_y_opposite = exp_cntr_y + side_to_center_y + init_dist_to_obj_y
    
    # Moving towards the initial measuring point, 
    # to measure X coordinate of the left side of the object
    ar.move(z=safe_z)
    ar.move(x=meas_point_x, y=exp_cntr_y, z=z_meas, z_first=False)
    
    # Measuring X coordinates of the left wall
    left_x_list = tools.findWallManyPoints(probe=probe, axis='x', direction=1, 
                  touch_coord_list=x_points_list)
    
    # Moving to the opposite side by X coordinate
    ar.moveAxisDelta(axis='z', value=-z_retract)
    ar.move(x=meas_point_x_opposite, y=exp_cntr_y, z=z_meas, z_first=False)
    
    # Measuring X coordinates of the opposite (right) wall
    right_x_list = tools.findWallManyPoints(probe=probe, axis='x', direction=-1, 
                  touch_coord_list=x_points_list)
    
    # Calculating x_center
    left_x_avg = sum(left_x_list) / (len(left_x_list) * 1.0)
    right_x_avg = sum(right_x_list) / (len(right_x_list) * 1.0)
    x_center = (left_x_avg + right_x_avg) / 2.0
    
    # Moving towards initial measuring point
    # to measure Y coordinate of the upper (closer to homing position) side
    ar.moveAxisDelta(axis='z', value=-z_retract)
    ar.move(x=x_center, y=meas_point_y, z=z_meas, z_first=False)
    
    # Measuring Y coordinate of the upper wall (closer to the homing position)
    upper_y_list = tools.findWallManyPoints(probe=probe, axis='y', direction=1, 
                  touch_coord_list=y_points_list)
    
    # Moving to the opposite side by Y coordinate
    ar.moveAxisDelta(axis='z', value=-z_retract)
    ar.move(x=x_center, y=meas_point_y_opposite, z=z_meas, z_first=False)
    
    # Measuring Y coordinate of the lower wall (further from the homing position).
    lower_y_list = tools.findWallManyPoints(probe=probe, axis='y', direction=-1, 
                  touch_coord_list=y_points_list)
    
    # Calculating y_center
    upper_y_avg = sum(upper_y_list) / (len(upper_y_list) * 1.0)
    lower_y_avg = sum(lower_y_list) / (len(lower_y_list) * 1.0)
    y_center = (upper_y_avg + lower_y_avg) / 2.0
    
    # Resuts
    return x_center, y_center


# TODO: Remove as this function also appears at rack class.
def calcWellsXY(x_cntr, y_cntr, x_dist_1st_cntr, y_dist_1st_cntr, dist_wells_x, dist_wells_y, x_wells, y_wells):
    """
    Calculates coordinates of all wells based on plate center
    """
    # Coordinates of the first well
    coord_1st_x = x_cntr - x_dist_1st_cntr
    coord_1st_y = y_cntr - y_dist_1st_cntr
    
    coord_list = []
    coord_added_x = 0
    
    for i in range(x_wells):
        coord_i = coord_1st_x + coord_added_x
        coord_added_x += dist_wells_x
        
        coord_list_y = []
        coord_added_y = 0
        for j in range(y_wells):
            coord_j = coord_1st_y + coord_added_y
            coord_list_y.append((coord_i, coord_j))
            coord_added_y += dist_wells_y
        coord_list.append(coord_list_y)
    
    return coord_list


def calibrateStalagmite(probe, immoprobe, n_x, n_y, ball_diam=16, stalagmite_height=110,
        calibration_dz=10, dist_from_wall=10):
    """
    Calibrate stalagmite against stalaktite
    Function assumes that mobile touch probe is already picked up, 
    immobile touch probe installed, and both are connected.
    
    Inputs:
        probe
            Object of a "stalaktite" mobile touch probe
        immoprobe
            Object of a "stalagmite" immobile touch probe
        n_x, n_y 
            slot position, column and row, correspondingly.
        ball_diam
            stalagmite tip ball diameter
        stalagmite_height
            distance from floor to the tip of the stalagmite
            Default is 110.
        calibration_dz
            Calibration will be started at height z_cal = z_floor - stalagmite_height + calibration_dz
        dist_from_wall
            How far from the wall to start calibraiton
    """
    
    # Finding center of the slot where the stalagmite is installed
    # Using previous floor calibration
    x, y = param.calcSquareSlotCenterFromVertices(n_x=n_x, n_y=n_y)
    # Finding coordinates of slot bottom
    z = param.getSlotZ(n_x=n_x, n_y=n_y)
    
    # Calculating other parameters for calibration
    half_size = ball_diam / 2.0
    opposite_side_dist = ball_diam + dist_from_wall * 2
    # How much to retract by Y after finishing X calibration
    orthogonal_retraction = half_size + dist_from_wall
    
    # Finding coordinates from where to start calibration
    start_x = x - half_size - dist_from_wall
    start_y = y
    start_z = z - stalagmite_height - calibration_dz
    
    # Moving robot (with probe already attached) to the starting coordinates
    probe.robot.move(x=start_x, y=start_y, z=start_z, z_first=False)
    
    # Performing actual calibration
    
    
