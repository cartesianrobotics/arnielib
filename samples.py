import configparser
import logging
import json


class sample():
    """
    Handles general samples
    Stores things like operational parameters for each sample,
    their history, position etc.
    """
    
    def __init__(self, sample_name, sample_type, volume=0, sample_data=None):
        self.sample_data = sample_data
        
        if self.sample_data is None:
            self.sample_data = {'sample_name': sample_name,
                                'sample_type': sample_type,
                }
        
        # Volume of liquid in the tube
        self.volume = volume
        
        # Populating with saved settings
        config = configparser.ConfigParser()
        config_path = 'configs/' + sample_type + '.ini'
        config.read(config_path)
        
        # Loading properties
            
        # Loading parameters dictionary
        params_path = str(config['properties']['params'])
        filehandler = open('configs/'+params_path, 'r')
        self.params = json.loads(filehandler.read())
        filehandler.close()
        #try:
        #    params_path = str(config['properties']['params'])
        #    filehandler = open('configs/'+params_path, 'r')
        #    self.params = json.loads(filehandler.read())
        #    filehandler.close()
        #except:
        #    self.params = {}
            
    
    def place(self, rack, x_well, y_well):
        """
        Used to place a tube into an empty well of a rack.
        """
        self.sample_data['rack'] = rack
        self.sample_data['x_well'] = x_well
        self.sample_data['y_well'] = y_well
        
    
    def sampleDepthToZ(self, height, tool):
        """
        Moves the tool to a given height, relative to the top of the sample.
        Larger the height value, the deeper tool will be inserted
        """
        rack = self.sample_data['rack']
        x, y, z_rack = rack.calcWorkingPosition(self.sample_data['x_well'],
                                                self.sample_data['y_well'],
                                                tool)
        sample_top_dz = self.params['sample_top_dz'][rack.rack_data['type']]
        z_sample_0 = z_rack - sample_top_dz
        
        z = z_sample_0 + height
        return z


    def sampleVolToZ(self, volume, tool):
        """
        Calculates Z at which the end of the tool will be at 
        the level of the sample which corresponds to provided volume
        """
        rack = self.sample_data['rack']
        x, y, z_rack = rack.calcWorkingPosition(self.sample_data['x_well'],
                                                self.sample_data['y_well'],
                                                tool)
        sample_top_dz = self.params['sample_top_dz'][rack.rack_data['type']]
        # Absolute Z coordinate of the top of the sample
        z_sample_0 = z_rack - sample_top_dz
        # Dictionary that stores dependence of volume vs height
        # Ultimately provided in settings file
        vol_vs_z_dict = self.params['volume_vs_z']
        # Filling temporary dictionary of the dependence of standard volumes vs 
        # standard_vol - volume difference.
        diff_dict = {}
        for key in vol_vs_z_dict.keys():
            standard_vol = float(key)
            diff = abs(standard_vol - volume)
            diff_dict[key] = diff
        diff_val_list = list(diff_dict.values())
        # Finding two closest standard points to provided volume
        # They will be used to create linear function to find desired Z.
        temp = min(diff_val_list)
        diff_val_list.remove(temp)
        temp2 = min(diff_val_list)
        standard_vol_1 = [key for key in diff_dict if diff_dict[key] == temp][0]
        standard_vol_2 = [key for key in diff_dict if diff_dict[key] == temp2][0]
        standard_z_1 = vol_vs_z_dict[standard_vol_1]
        standard_z_2 = vol_vs_z_dict[standard_vol_2]
        
        # Using obtained points, calculating arguments of linear function, that
        # includes those points
        p = [float(standard_vol_1), standard_z_1]
        q = [float(standard_vol_2), standard_z_2]
        
        a = q[1] - p[1]
        b = p[0] - q[0]
        c = a * (p[0]) + b * (p[1])
        
        # Using obtained linear function, calculating Z relative to the top of the tube
        z_tube_insert = (c - a * volume) / b
        
        # Calculating absolute Z value
        z = z_sample_0 + z_tube_insert
        return z
        

    def samplePercentToZ(self, fraction, tool):
        """
        Calculate Z at which the end of the tool will be, corresponding
        to percent of sample height
        """
        rack = self.sample_data['rack']
        x, y, z_rack = rack.calcWorkingPosition(self.sample_data['x_well'],
                                                self.sample_data['y_well'],
                                                tool)
        sample_top_dz = self.params['sample_top_dz'][rack.rack_data['type']]
        # Absolute Z coordinate of the top of the sample
        z_sample_0 = z_rack - sample_top_dz
        # Dictionary that stores dependence of volume vs height
        # Ultimately provided in settings file
        vol_vs_z_dict = self.params['volume_vs_z']
        lowest_Z = vol_vs_z_dict["0"]
        z_tube_insert = lowest_Z * fraction
        z = z_sample_0 + z_tube_insert
        return z


    def getSampleCenterXY(self, tool):
        rack = self.sample_data['rack']
        x, y, z = rack.calcWorkingPosition(self.sample_data['x_well'],
                                           self.sample_data['y_well'],
                                           tool)
        return x, y
        