"""
Module handling high-leve calibration routines
"""


# Internal arnielib modules
import tools


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
