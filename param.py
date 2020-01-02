import json

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
        try:
            filehandler = open(floor_calibr_file, "r")
        except FileNotFoundError:
            return
        # Loading structured data
        floor_data = json.loads(filehandler.read())
        slots_data = floor_data['slots']
    
    return slots_data[n_x][n_y]
    
