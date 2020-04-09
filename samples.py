import configparser
import logging
import json


class sample():
    """
    Handles general samples
    Stores things like operational parameters for each sample,
    their history, position etc.
    """

    # TODO: Make functions to calculate remaining sample depth from current volume (z, %) position
    
    def __init__(self, sample_name, sample_type, volume=0, sample_data=None, capped=False):
        self.sample_data = sample_data
        
        if self.sample_data is None:
            self.sample_data = {'sample_name': sample_name,
                                'sample_type': sample_type,
                }
        
        # Volume of liquid in the tube
        self.setVolume(volume)
        # Whether tube has cap
        if capped:
            self.addCap()
        else:
            self.removeCap()
        
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
        
        # Sample length
        try:
            self.length = float(config['geometry']['length'])
        except:
            self.length = 0
        
        #try:
        #    params_path = str(config['properties']['params'])
        #    filehandler = open('configs/'+params_path, 'r')
        #    self.params = json.loads(filehandler.read())
        #    filehandler.close()
        #except:
        #    self.params = {}
        
        # This parameter stores z value relative to the sample top, 
        # at which sample is engaged.
        # For example, if sample total length is 30 mm, 
        # and a gripper grabs it at upper 10 mm position, then
        # self.fample_engaged_dz = 10
        self.sample_engaged_dz = None
            
    
    def place(self, rack, x_well, y_well):
        """
        Used to place a tube into an empty well of a rack.
        """
        self.sample_data['rack'] = rack
        self.sample_data['x_well'] = x_well
        self.sample_data['y_well'] = y_well
    

    def getSampleHeightAboveRack(self):
        """
        Returns arbitrary height of sample above the rack where it is 
        currently placed (in mm).
        """
        rack = self.sample_data['rack']
        return self.params['sample_top_dz'][rack.rack_data['type']]
        
    
    def sampleDepthToZ(self, height, tool):
        """
        Moves the tool to a given height, relative to the top of the sample.
        Larger the height value, the deeper tool will be inserted
        """
        rack = self.sample_data['rack']
        x, y, z_rack = rack.calcWorkingPosition(self.sample_data['x_well'],
                                                self.sample_data['y_well'],
                                                tool)
        sample_top_dz = self.getSampleHeightAboveRack()
        z_sample_0 = z_rack - sample_top_dz
        
        z = z_sample_0 + height
        return z


    def getDepthFromVolume(self, volume):
        """
        Calculates distance from the top of the sample to the 
        position of certain volume.
        """
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
        # Getting closest standard volume to the provided volume
        standard_vol_1 = min(diff_dict, key=diff_dict.get)
        # Removing the standard volume from the dV dictionary
        diff_dict.pop(standard_vol_1, None)
        # Getting second closest standard volume 
        # After removing closest standard volume, same function will provide second closest.
        standard_vol_2 = min(diff_dict, key=diff_dict.get)
        # Getting Z levels associated with standard volumes
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
        
        return z_tube_insert


    def sampleVolToZ(self, volume, tool):
        """
        Calculates Z at which the end of the tool will be at 
        the level of the sample which corresponds to provided volume
        """
        # TODO: Factor out z_sample_0 calc
        rack = self.sample_data['rack']
        x, y, z_rack = rack.calcWorkingPosition(self.sample_data['x_well'],
                                                self.sample_data['y_well'],
                                                tool)
        sample_top_dz = self.getSampleHeightAboveRack()
        # Absolute Z coordinate of the top of the sample
        z_sample_0 = z_rack - sample_top_dz

        z_tube_insert = self.getDepthFromVolume(volume)
        
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
        sample_top_dz = self.getSampleHeightAboveRack()
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
        
        
    def getSampleTopZ(self, tool):
        """
        Returns absolute coordinate of the top of the sample
        """
        rack = self.sample_data['rack']
        x, y, z_rack = rack.calcWorkingPosition(self.sample_data['x_well'],
                                                self.sample_data['y_well'],
                                                tool)
        sample_top_dz = self.getSampleHeightAboveRack()
        # Absolute Z coordinate of the top of the sample
        z_sample_0 = z_rack - sample_top_dz
        return z_sample_0
        
    def setVolume(self, volume):
        """
        Specifies volume of liquid in the sample
        """
        self.volume = volume
        
    def getVolume(self):
        """
        Returns volume of liquid currently in the sample
        """
        return self.volume
        
    def getMaxVolume(self):
        """
        Returns max volume that the sample may theoretically have
        Obtains this data from volume vs z dictionary, that is provided in 
        config json file samplename_params.json
        """
        vol_vs_z_dict = self.params['volume_vs_z']
        vols_list = [float(x) for x in vol_vs_z_dict.keys()]
        max_vol = max(vols_list)
        return max_vol
    
    def setSampleEngagedPosition(self, dz):
        self.sample_engaged_dz = dz
        
    def disengage(self):
        self.sample_engaged_dz = None
    
    def getSampleRemainingLength(self, dz):
        """
        Returns remaining length of sample below given relative z.
        Inputs:
            dz 
                in mm, distance from top of the sample
        Returns:
            z_remaining
                in mm, distance from dz to the very bottom of the sample
                (not 0 volume mark, but the very bottom)
        """
        return self.length - dz

        
    def getUncappedGrippingOpenDiam(self):
        """
        Returns diameter to which to open gripper when approaching the sample
        """
        gripper_params = self.params['gripper_param']
        return gripper_params["open_to_approach_uncapped"]
        
    def getUncappedGripDiam(self):
        """
        Returns diameter at which gripper would grip the sample
        """
        gripper_params = self.params['gripper_param']
        return gripper_params["grip_uncapped"]
        
    def addCap(self):
        self.capped = True
        
    def removeCap(self):
        self.capped = False
        
    def isCapped(self):
        return self.capped
        
