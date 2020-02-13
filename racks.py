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
        
        self.rack_data = rack_data
        
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
            config.read(config_path)
        
            self.z_height = float(config['geometry']['z_box_height'])
            self.max_height = float(config['geometry']['z_max_height'])
            self.x_width = float(config['geometry']['x_max_width'])
            self.y_width = float(config['geometry']['y_max_width'])
            
            self.x_init_calibrat_dist_from_wall = float(config['calibration']['x_init_distance_from_wall'])
            self.y_init_calibrat_dist_from_wall = float(config['calibration']['y_init_distance_from_wall'])
            self.z_init_calibrat_dist_from_wall = float(config['calibration']['z_init_distance_from_wall'])
            self.xy_calibrat_height_dz = float(config['calibration']['xy_calibration_height'])
            self.dz_clearance = float(config['calibration']['dz_clearance'])
            
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
        
        x_slot = self.rack_data['n_x']
        y_slot = self.rack_data['n_y']
        
        x, y = param.calcSquareSlotCenterFromVertices(x_slot, y_slot)
        z = param.getSlotZ(x_slot, y_slot)
        
        return x, y, z
    
    
    def getSimpleCalibrationPoints(self):
        x_cntr, y_cntr, z_cntr = self.getSavedSlotCenter()
        
        x_start = x_cntr - self.x_width / 2.0 - self.x_init_calibrat_dist_from_wall
        y_start = y_cntr
        z_start = z_cntr - self.z_height + self.xy_calibrat_height_dz
        
        opposite_side_dist = x_start + self.x_width + self.x_init_calibrat_dist_from_wall * 2.0
        orthogonal_retraction = self.y_width / 2.0 + self.y_init_calibrat_dist_from_wall
        box_top_z_coord = z_cntr - self.max_height
        raise_height = abs(z_start - box_top_z_coord) - self.dz_clearance
        
        return x_start, y_start, z_start, opposite_side_dist, orthogonal_retraction, raise_height    
    
    
    def calcWellsPositions(self):
        
        try:
            [x, y, z] = self.rack_data['position']
        except:
             x, y, z = self.getSavedSlotCenter()
             
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
    
    
    def updateCenter(self, x, y, z, x_btm_touch, y_btm_touch, z_btm_touch):
        try:
            pos = self.rack_data['position']
            pos_btm_touch = self.rack_data['pos_stalagmyte']
        except:
            pos = [0, 0, 0]
            pos_btm_touch = [0, 0, 0]
        
        pos[0] = x
        pos[1] = y
        pos[2] = z
        
        pos_btm_touch[0] = x_btm_touch
        pos_btm_touch[1] = y_btm_touch
        pos_btm_touch[2] = z_btm_touch
        
        self.rack_data['position'] = pos
        self.rack_data['pos_stalagmyte'] = pos_btm_touch

    
    def save(self):
        rack_name = self.rack_data['name']
        f = open(rack_name+'.json', 'w')
        f.write(json.dumps(self.rack_data))
        f.close()
