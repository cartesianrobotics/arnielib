import configparser
import param # TODO: Remove
import logging
import json

class rack():
    def __init__(self, rack_name, x_slot=None, y_slot=None, rack_type=None, rack_data=None):
        
        """
            Inputs
                rack_name
                    Unique identifier of a rack. There couls be more than one rack
                    of the same type simultaneoulsy present on the floor; such as 2 
                    racks for 1000 uL tips. In this case, they may be called 'p1000_1' and 'p1000_2'
                rack_type
                    Type of the rack; there may be several racks of the same type on the floor.
                    This is used to load type-related properties from config file
                    If not provided, type will be attempted to look in the file with unique 
                    rack properties. If not found, properties won't be loaded.
                x_slot, y_slot
                    Position of the rack in the slot of the floor
                rack_data
                    Instead of loading data from disc, you can initialize class 
                    directly providing dictionary with properties
        """
        
        # TODO: rack_data must contain two position parameters:
        # 1: slot x,y,z; obtained by empty slot calibration
        # 2: rack x,y,z; obtained by calibrating rack
        # In some cases, when calibrating rack Z is hard or impossible or makes no sense,
        # slot_z might be = to rack_z; but that is individual
        self.rack_data = rack_data
        
        # Dictionary storing sample objects
        # {sample_object: (x_n, y_n)}
        # x_n, y_n - position (well) in the rack
        self.samples_dict = {}
        
        # Attempting to read data from HD
        if self.rack_data is None:
            self.rack_data = self.openFileWithRackParameters(rack_name+'.json')
        
        # Populating dictionary with current rack properties
        if self.rack_data is None:
            self.rack_data = {}
        
        self.rack_data['name'] = rack_name
        if (x_slot is not None) and (y_slot is not None):
            self.overwriteSlot(x_slot, y_slot)
        if rack_type is None:
            try:
                rack_type = self.rack_data['type']
            except:
                pass
        if rack_type is not None:
            self.rack_data['type'] = rack_type
        
            # Using provided or saved rack type, load rack properties from config file
            config = configparser.ConfigParser()
            config_path = 'configs/' + rack_type + '.ini'
            
            #print (config_path)
            config.read(config_path)
            
            #print (config_path)
            
            self.z_height = float(config['geometry']['z_box_height'])
            self.max_height = float(config['geometry']['z_max_height'])
            self.x_width = float(config['geometry']['x_max_width'])
            self.y_width = float(config['geometry']['y_max_width'])
            self.z_working_height = float(config['geometry']['z_working_height'])
            
            self.x_init_calibrat_dist_from_wall = float(config['calibration']['x_init_distance_from_wall'])
            self.y_init_calibrat_dist_from_wall = float(config['calibration']['y_init_distance_from_wall'])
            self.z_init_calibrat_dist_from_wall = float(config['calibration']['z_init_distance_from_wall'])
            self.xy_calibrat_height_dz = float(config['calibration']['xy_calibration_height'])
            self.dz_clearance = float(config['calibration']['dz_clearance'])
            # Parameters to calibrate Z axis of a rack.
            # In case they are not provided in the config file, Z axis will be 
            # calibrated at the center of the rack.
            
            # TODO: Change Z according to X and Y
            try:
                self.z_calibration_dxdy_coord = [
                    float(config['calibration']['z_calibration_dx_coord']), 
                    float(config['calibration']['z_calibration_dy_coord']), 
                    ]
            except:
                self.z_calibration_dxdy_coord = [0, 0]
            try:
                self.z_calibration_dz = float(config['calibration']['z_calibration_dz'])
            except:
                self.z_calibration_dz = 0
            try:
                self.x_calibration_dxdy_coord = [
                    float(config['calibration']['x_calibration_dx_coord']), 
                    float(config['calibration']['x_calibration_dy_coord']),
                    float(config['calibration']['x_calibration_dz_coord']),
                    ]
            except:
                self.x_calibration_dxdy_coord = [0, 0, 0]
            try:
                self.y_calibration_dxdy_coord = [
                    float(config['calibration']['y_calibration_dx_coord']), 
                    float(config['calibration']['y_calibration_dy_coord']),
                    float(config['calibration']['y_calibration_dz_coord']),
                    ]
            except:
                self.y_calibration_dxdy_coord = [0, 0, 0]    
            
            
            self.columns = int(config['wells']['columns'])
            self.rows = int(config['wells']['rows'])
            self.dist_between_cols = float(config['wells']['distance_between_columns'])
            self.dist_between_rows = float(config['wells']['distance_between_rows'])
            self.dist_cntr_to_1st_col = float(config['wells']['distance_center_to_1st_column'])
            self.dist_cntr_to_1st_row = float(config['wells']['distance_center_to_1st_row'])
            
            

    def openFileWithRackParameters(self, path):
        try:
            filehandler = open(path, 'r')
            result = json.loads(filehandler.read())
            filehandler.close()
        except FileNotFoundError:
            return
        
        return result
    
    
    def overwriteSlot(self, x, y):
        self.rack_data['n_x'] = x
        self.rack_data['n_y'] = y
    
# TODO: Make a separate class to handle floor, get rid of param altogether.
    def getSavedSlotCenter(self):
        
        #try:
        #    [x, y, z] = self.rack_data['position']
        #except:
        x_slot = self.rack_data['n_x']
        y_slot = self.rack_data['n_y']
        
        x, y = param.calcSquareSlotCenterFromVertices(x_slot, y_slot)
        z = param.getSlotZ(x_slot, y_slot)
        
        return x, y, z
    
    
    def getCalibratedRackCenter(self):
        try:
            [x, y, z] = self.rack_data['position']
            return x, y, z
        except KeyError:
            logging.error('rack.getCalibratedRackCenter: Rack is not calibrated.')
            logging.error('Run calibration first. See calibration routines')
        
        
    def updateCalibratedRackCenter(self, x, y, z):
        self.rack_data['position'] = [x, y, z]

    def getStalagmyteCalibration(self):
        [x, y, z] = self.rack_data['pos_stalagmyte']
        return x, y, z
        
    def updateStalagmyteCalibration(self, x, y, z):
        self.rack_data['pos_stalagmyte'] = [x, y, z]
    
    
    def getHeightFromFloor(self):
        return self.z_height
    
    
    def getSimpleCalibrationPoints(self):

        x_cntr, y_cntr, z_cntr = self.getSavedSlotCenter()
        
        x_start = x_cntr - self.x_width / 2.0 - self.x_init_calibrat_dist_from_wall
        y_start = y_cntr
        z_start = z_cntr - self.getHeightFromFloor() + self.xy_calibrat_height_dz
        
        opposite_side_dist = self.x_width + self.x_init_calibrat_dist_from_wall * 2.0
        orthogonal_retraction = self.y_width / 2.0 + self.y_init_calibrat_dist_from_wall
        box_top_z_coord = self.calcAbsoluteTopZ()
        raise_height = abs(z_start - box_top_z_coord) + self.dz_clearance
        
        #print (raise_height, z_start, z_cntr, self.z_height, self.xy_calibrat_height_dz, box_top_z_coord, self.dz_clearance)
        
        return x_start, y_start, z_start, opposite_side_dist, orthogonal_retraction, raise_height    
    
    
    def getRelativeZCalibrationPoint(self):
        """
        Provides dX, dY, dZ to use in rack Z calibration.
        dX and dY should be added to center_X and center_Y, respectfully, and 
        dZ should be added to self.max_height
        """
        return self.z_calibration_dxdy_coord[0], self.z_calibration_dxdy_coord[1], self.z_calibration_dz
    
    
    def getRelativeCalibrationPoint(self, axis):
        """
        Provides dX, dY, dZ for a given axis to use in rack calibration.
        Input:
            axis    
                Axis for which to provide relative calibration points
        Returns:
            (dx, dy, dz)
                Delta for coordinates to be used during calibration
        """
        
        axis = axis.lower()
        if axis == 'x':
            return self.x_calibration_dxdy_coord
        elif axis == 'y':
            return self.y_calibration_dxdy_coord
        elif axis == 'z':
            return self.getRelativeZCalibrationPoint()
    
    
    def calcWellsPositions(self):
        
        [x, y, z] = self.getCalibratedRackCenter()
        
        coord_1st_x = x - self.dist_cntr_to_1st_col
        coord_1st_y = y - self.dist_cntr_to_1st_row
        
        coord_list = []
        coord_added_x = 0
        
        for i in range(self.columns):
            coord_i = coord_1st_x + coord_added_x
            coord_added_x += self.dist_between_cols
            
            coord_list_y = []
            coord_added_y = 0
            for j in range(self.rows):
                coord_j = coord_1st_y + coord_added_y
                coord_list_y.append((coord_i, coord_j))
                coord_added_y += self.dist_between_rows
            coord_list.append(coord_list_y)
        
        return coord_list
        
    
    def calcWellXY(self, well_col, well_row):
        coord_list = self.calcWellsPositions()
        return coord_list[well_col][well_row][0], coord_list[well_col][well_row][1]
    
    # TODO: This function, and calcRackCenterFullCalibration uses too much of the same code
    def calcWorkingPosition(self, well_col, well_row, tool=None):
        
        #print (self.rack_data)
        x, y = self.calcWellXY(well_col, well_row)
        x_slot, y_slot, z_calibr = self.getCalibratedRackCenter()
        z = z_calibr + self.z_working_height

        # Checking whether stalagmyte data are present in the rack object:
        try:
            self.rack_data['pos_stalagmyte']
            use_stalagmyte = True
        except:
            use_stalagmyte = False
            
        if use_stalagmyte:
            try:
                tool_stal_x, tool_stal_y, tool_stal_z = tool.getStalagmyteCoord()
            except:
                [tool_stal_x, tool_stal_y, tool_stal_z] =  self.rack_data['pos_stalagmyte']
            
            [tp_stal_x, tp_stal_y, tp_stal_z] = self.rack_data['pos_stalagmyte']
            
            dx = tp_stal_x - tool_stal_x
            dy = tp_stal_y - tool_stal_y
            dz = tp_stal_z - tool_stal_z
        else:
            dx = 0
            dy = 0
            dz = 0
        
        return x - dx, y - dy, z - dz
    
    
    def calcRackCenterFullCalibration(self, tool):
        """
        Given calibrated tool object, calculates X, Y, Z coordinates of the rack center,
        that takes into account both tool and rack calibrations.
        """
        [x, y, z] = self.getCalibratedRackCenter()
        z = z + self.z_working_height
        try:
            tool_stal_x, tool_stal_y, tool_stal_z = tool.getStalagmyteCoord()
        except:
            # If function was unable to get stalagmyte coordinates from tool
            # (will happen, for instance, whent the tool was not calibrated),
            # print error message
            print ("Unable to get stalagmyte coordinates from the tool")
            print ("The tool was likely not calibrated")
            print ("Perform tool calibration using tool.calibrateTool() and repeat")
            return
        [tp_stal_x, tp_stal_y, tp_stal_z] = self.rack_data['pos_stalagmyte']
        
        dx = tp_stal_x - tool_stal_x
        dy = tp_stal_y - tool_stal_y
        dz = tp_stal_z - tool_stal_z
        
        return x - dx, y - dy, z - dz
    
    
    def calcAbsoluteTopZ(self):
        [x, y, z] = self.getSavedSlotCenter()
        return z - self.max_height
    
    
    def updateCenter(self, x, y, z, x_btm_touch, y_btm_touch, z_btm_touch):
        self.updateCalibratedRackCenter(x, y, z)
        self.updateStalagmyteCalibration(x_btm_touch, y_btm_touch, z_btm_touch)

    
    def save(self):
        rack_name = self.rack_data['name']
        f = open(rack_name+'.json', 'w')
        f.write(json.dumps(self.rack_data))
        f.close()
        
    # ==================================================
    # Gripping functions
    
    def setGrippingProperties(self, open_diam, grip_diam, z_relative_to_top, gripper=None, gripper_name=None):
        """
        Sets gripping properties for the rack, saves into properties file (json)
        """
        # Finding gripper name. It is used to label settings when stored
        if gripper is None:
            gripper_name = gripper_name
        else:
            gripper_name = gripper.tool_data['name']
        
        try:
            gripper_dict = self.rack_data['gripper']
        except:
            gripper_dict = {}
        
        gripper_dict[gripper_name] = {
            'open_diam': open_diam,
            'grip_diam': grip_diam,
            'z_grip': z_relative_to_top,
        }
        
        self.rack_data['gripper'] = gripper_dict
        self.save()
        
        
    def getGrippingHeight(self, tool, extra_z=0):
        """
        Returns _absolute_ Z at which to perform gripping
        """
        gripper_name = tool.tool_data['name']
        z_relative_to_top = self.rack_data['gripper'][gripper_name]['z_grip']
        # calculating calibrated coordinates of the rack, accounting tool calibration
        x, y, z = self.calcRackCenterFullCalibration(tool=tool)
        z_abs = z + z_relative_to_top + extra_z
        return z_abs
    
    def getGrippingOpenDiam(self, tool):
        """
        Returns number that indicates how wide a gripper should be opened so it 
        can approach the rack to pick it up.
        """
        gripper_name = tool.tool_data['name']
        open_diam = self.rack_data['gripper'][gripper_name]['open_diam']
        return open_diam
        
    
    def getGrippingCloseDiam(self, tool):
        """
        Returns number that indicates the width of the gripper to close to grab the rack
        """
        gripper_name = tool.tool_data['name']
        grip_diam = self.rack_data['gripper'][gripper_name]['grip_diam']
        return grip_diam
        
        
    def getHeightBelowGripper(self, tool):
        """
        Returns distance from the bottom of the rack to the bottom of the gripping tool,
        that is gripping on the rack.
        """
        gripper_name = tool.tool_data['name']
        z_relative_to_top = self.rack_data['gripper'][gripper_name]['z_grip']
        return self.max_height - z_relative_to_top


    def performFakeCalibration(self):
        """
        Fills calibration parameters with the slot coordinates.
        Use when for some reason calibration is impossible or not required (approximate value is fine)
        """
        x, y, z = self.getSavedSlotCenter()
        self.updateCalibratedRackCenter(x, y, z)
        

class stackable(rack):
    """
    Handles stackable racks, i.e., ones that can be stacked over each other
    
    There is a general need to place racks on top of each other. 
    This class describes the behavior of such racks.
    """
    
    # CURRENT TODO: Remove those functions, add ability to return object of an upper stackable, or None if that one
    # is the top one.
    
    def __init__ (self, rack_name, x_slot=None, y_slot=None, rack_type=None, rack_data=None):
        super().__init__(rack_name, x_slot, y_slot, rack_type, rack_data)
        # When a stackable is created, it is assumed to be on top of the stack. 
        # Therefore, the object of a stackable above that will be None.
        self.top_item = None
        self.bottom_item = None
    
    def placeItemOnTop(self, top_item):
        self.top_item = top_item
        # This lets the top item know its bottom item
        self.top_item.bottom_item = self
        try:
            # If racks are calibrated, the top item receives calibration from the bottom one.
            x, y, z = self.getCalibratedRackCenter()
            z_item_on_top = z - self.top_item.max_height
            self.top_item.rack_data['position'] = [x, y, z_item_on_top]
            xs, ys, zs = self.getStalagmyteCalibration()
            top_item.updateStalagmyteCalibration(xs, ys, zs)
        except:
            # If not, no calibration is transferred.
            pass
        # The top item receives the same slot info as the current item
        x_slot = self.rack_data['n_x']
        y_slot = self.rack_data['n_y']
        self.top_item.overwriteSlot(x_slot, y_slot)
        # Setting new height from the floor. It is equal to the current heigth + heigth of the top item (from config)
        config = configparser.ConfigParser()
        config_path = 'configs/' + self.top_item.rack_data['type'] + '.ini'
        config.read(config_path)
        top_item_z_height_from_config = float(config['geometry']['z_box_height'])
        self.top_item.z_height = self.getHeightFromFloor() + top_item_z_height_from_config
        
    def getTopItem(self):
        return self.top_item
        
    def removeTopItem(self, update_calibration=True):
        """
        "Removes" the rack which was sitting on top of the current rack.
        """
        if update_calibration:
            # Situation when the top rack was calibrated, but the current one was not.
            top_item = self.getTopItem()
            x_calibrated, y_calibrated, z_calibr_top = top_item.getCalibratedRackCenter()
            z_calibr = z_calibr_top + top_item.max_height
            self.updateCalibratedRackCenter(x_calibrated, y_calibrated, z_calibr)
        # Upon removal, current rack becomes the top one (and so, a gripper may grab it)
        self.top_item = None


    # TODO: Make a separate class to handle floor, get rid of param altogether.
    def getSavedSlotCenter(self):
        
        if self.bottom_item is not None:
            x, y, z = self.bottom_item.getSavedSlotCenter()
        else:        
            x_slot = self.rack_data['n_x']
            y_slot = self.rack_data['n_y']
            
            x, y = param.calcSquareSlotCenterFromVertices(x_slot, y_slot)
            z = param.getSlotZ(x_slot, y_slot)
        
        return x, y, z

    
    def updateCenter(self, x, y, z, x_btm_touch, y_btm_touch, z_btm_touch):
        self.updateCalibratedRackCenter(x, y, z)
        self.updateStalagmyteCalibration(x_btm_touch, y_btm_touch, z_btm_touch)
        if self.bottom_item:
           # TODO: Stackable racks need to have 2 variables: distance from floor to the rack top, and 
           # distance from the bottom of the rack to its top (latter one is from config)
           config = configparser.ConfigParser()
           config_path = 'configs/' + self.rack_data['type'] + '.ini'
           config.read(config_path)
           height_from_config = float(config['geometry']['z_box_height'])
           z = z + height_from_config
           self.bottom_item.updateCenter(x, y, z, x_btm_touch, y_btm_touch, z_btm_touch)


        
    
# TODO: create a unified class "item", that will be a parent
# for all racks, samples, tools etc, handling common operations such as save/load parameters,
# positions, calibration etc.

class stack(object):
    """
    Handles a stack of racks
    
    Main functionality for stackable racks is to place a new rack on top,
    know what is in the stack and extract necessary rack from the stack.
    """
    
    def __init__ (self, name):
        self.stack_data = self._loadParameters(name+'.json')


    def _loadParameters(self, path):
        """
        Loads parameters of the stack from a file, using provided path
        """
        try:
            filehandler = open(path, 'r')
            result = json.loads(filehandler.read())
            filehandler.close()
        except FileNotFoundError:
            return
        
        return result

        
    

class consumables(rack):
    """
    Handles racks with consumables, such as pipette tips
    """            
    def getReadyItemsList(self):
        try: 
            return self.rack_data['ready_items_list']
        except:
            return []
            
            
    def setItemsAsReady(self, coord_list):
        """
        Specifies list of positions in rack, where ready items are stored
        Inputs:
            coord_list
                List of positins for consumable items. 
                Example: [(0, 0), (0, 1), (3, 4), ...]
        """
        present_items = self.getReadyItemsList()
        present_items = present_items + coord_list
        self.rack_data['ready_items_list'] = present_items
        self.save()
        
        
    def removeConsumableItems(self, coord_list):
        present_items = self.getReadyItemsList()
        for item in coord_list:
            try:
                present_items.remove(item)
            except:
                pass
        self.rack_data['ready_items_list'] = present_items
        self.save()
        
    
    def getNextConsumable(self, discard=True):
        ready_items = self.getReadyItemsList()
        item = ready_items[0]
        self.removeConsumableItems([item])
        return item
    
    
    def replaceConsumables(self):
        """
        Replentish consumables, making all the possible wells for given rack filled with
        ready to use consumables. Real world analog is replacing the rack of tips at the same spot
        """
        coord_list = []
        for i in range(self.columns):
            for j in range (self.rows):
                coord_list.append((i, j))
        self.rack_data['ready_items_list'] = []
        self.setItemsAsReady(coord_list)