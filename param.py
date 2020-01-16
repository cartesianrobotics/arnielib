"""
This module handles parameters storage and basic manipulation
"""


import json
import os
from shutil import copyfile
import re
from datetime import datetime
import logging

DEFAULT_FLOOR_CALIBR_FILE = "floor.json"
DEFAULT_TOOL_CALIBR_FILE = "tools.json"

def getSlotCalibrationData(n_x, n_y, 
                  slots_data=None, 
                  floor_calibr_file=DEFAULT_FLOOR_CALIBR_FILE):
    
    """
    Returns calibration data for a given slots
    
    Inputs:
        n_x, n_y
            Slot coordinates. Currently robot has 6x4 = 24 slots,
            6 columns and 4 lines. n_x represents column of the slot, from 0 to 5.
            n_y represents row of the slot, from 0 to 3.
        slots_data
            Option to provide your own slot calibration data.
            The data must be in the form:
                [ [ {data for slot 0,0},
                    {data for slot 1,0},
                    ...
                    {data for slot 5,0} ],
                  [ {data for slot 0,1},
                    ...
                    {data for slot 5,1} ],
                  ...
                ]
        floor_calibr_file
            path to the file where calibration data is saved in
            json format. Root dictionary must contain 
            key "slots", which value is slots_data
            Default is floor.json. This is used if slots_data not provided
    """
    
    if slots_data is None:
        # Opening data from default storage
        # If file does not exist, function exits
        floor_data = loadData(floor_calibr_file)
        slots_data = floor_data['slots']
    
    return slots_data[n_x][n_y]
    

def replaceFile(path_to_replace, data):
    """
    Replaces a file or creates a new one with given name
    """
    
    if os.path.exists(path_to_replace):
        time_str = str(datetime.now()).replace(":", "_")
        filename = re.split(pattern="/", string=path_to_replace)[-1]
        new_filename = time_str + filename
        new_path = path_to_replace.replace(filename, new_filename)
        copyfile(path_to_replace, new_path)
        
    filehandler = open(path_to_replace, 'w')
    filehandler.write(json.dumps(data))
    filehandler.close()

    
def loadData(path):
    try:
        filehandler = open(path, "r")
    except FileNotFoundError:
        return
        
    return json.loads(filehandler.read())

    
def calcSquareSlotCenterFromVertices(n_x, n_y, 
                                   slots_data=None, 
                                   floor_calibr_file=DEFAULT_FLOOR_CALIBR_FILE):
    """
    Given vertices X and Y coordinates, will
    calculate X and Y coordinates of the center of the slot.
    
    Data should look like that:
    {'LB': [167.95000000000002, 122.15],
    'RT': [317.36, 11.150000000000002],
    'LT': [168.95000000000002, 10.950000000000003],
    'floor_z': 604.1,
    'RB': [316.36, 122.35]}
    """
    slot = getSlotCalibrationData(n_x, n_y, 
                                  slots_data=slots_data, floor_calibr_file=floor_calibr_file)
    return [(slot['LT'][0] + slot['RB'][0]) / 2, (slot['LT'][1] + slot['RB'][1]) / 2]
    

def getSlotZ(n_x, n_y, 
             slots_data=None, 
             floor_calibr_file=DEFAULT_FLOOR_CALIBR_FILE):
             
    """
    Will return Z coordinate of the slot.
    
    Data should look like that:
    {'LB': [167.95000000000002, 122.15],
    'RT': [317.36, 11.150000000000002],
    'LT': [168.95000000000002, 10.950000000000003],
    'floor_z': 604.1,
    'RB': [316.36, 122.35]}
    """    
    slot = getSlotCalibrationData(n_x, n_y, 
                                  slots_data=slots_data, floor_calibr_file=floor_calibr_file)
    return slot['floor_z']


# Functions handling communications with tools
# ------------------------------------------------------------------------------------------------
    
def getToolByName(name, data=None, tool_file=DEFAULT_TOOL_CALIBR_FILE):

    # If custom data are not provided, use those from standard file
    if data is None:
        data = loadData(tool_file)
    
    for tool in data:
        try:
            saved_tool_name = tool['type']
            if saved_tool_name == name:
                return tool
        except:
            pass

            
def getToolBySlot(x, y, data):
    for tool in data:
        try:
            saved_x = tool['n_x']
            saved_y = tool['n_y']

            if (saved_x == x) and (saved_y == y):
                return tool
        except:
            pass

    
def getToolDockingPoint(toolname=None, slot=None, data=None, tool_file=DEFAULT_TOOL_CALIBR_FILE):
    """
    Will try to load docking coordinates saved in the file; 
    if not successful, will try to calculate from provided data.
    """
    
    # If custom data are not provided, use those from standard file
    if data is None:
        data = loadData(tool_file)

    if toolname is not None:
        tool_data = getToolByName(toolname, data)
    elif slot is not None:
        tool_data = getToolBySlot(slot[0], slot[1], data)
    else:
        return
    
    return tool_data['position']
    

def saveTool(new_tool_data, toolname=None, slot=None, data=None, tool_file=DEFAULT_TOOL_CALIBR_FILE):
    """
    Saves all info about a tool
    """
    
    # If custom data are not provided, use those from standard file
    if data is None:
        data = loadData(tool_file)
        
    if toolname is not None:
        tool_data = getToolByName(toolname, data)
    elif slot is not None:
        tool_data = getToolBySlot(slot[0], slot[1], data)
    else:
        return
    
    tool_index = data.index(tool_data)
    data[tool_index] = new_tool_data
    
    replaceFile(tool_file, data)
    
# Functions to handle tool endpoints
# --------------------------------------------------------------------------------------------

def getToolEndPoint(toolname=None, slot=None, data=None, tool_file=DEFAULT_TOOL_CALIBR_FILE):
    """
    Obtain coordinates of interactions between tool endpoint and 
    stationary probe "stalagmite"
    """
    
    # If custom data are not provided, use those from standard file
    if data is None:
        data = loadData(tool_file)
        
    if toolname is not None:
        tool_data = getToolByName(toolname, data)
    elif slot is not None:
        tool_data = getToolBySlot(slot[0], slot[1], data)
    else:
        return
        
    return tool_data['tip']
    

def saveToolEndPoint(x, y, z, 
                     toolname=None, slot=None, data=None, tool_file=DEFAULT_TOOL_CALIBR_FILE):
    """
    Save coordinates at which tool endpoint and stationary probe interact.
    """
    
    # If custom data are not provided, use those from standard file
    if data is None:
        data = loadData(tool_file)
        
    if toolname is not None:
        tool_data = getToolByName(toolname, data)
    elif slot is not None:
        tool_data = getToolBySlot(slot[0], slot[1], data)
    else:
        return
        
    tool_data['tip'] = [x, y, z]
    replaceFile(tool_file, data)