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
        # Sample inner diameter
        # Currently used to touch wall
        # TODO: Add table of touch wall distances depending on the tube volume
        try:
            self.inner_diameter = float(config['geometry']['inner_diameter'])
        except:
            self.inner_diameter = 0
        
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

    
    def sampleRelativeZtoAbsoluteZ(self, dZ, tool):
        """
        Calculates absolute Z value based on provided dZ value relative to the 
        sample top.
        For example, if the sample top is positioned at 500, and dZ = 20,
        then function returns 520; at this absolute height, the distance between
        the top of the sample and the tool's calibrated point will be 20 mm.
        """
        z = getSampleTopZ(tool=tool)
        new_z = z + dZ
        return new_z
    
    
    def getSampleCenterXY(self, tool):
        rack = self.sample_data['rack']
        x, y, z = rack.calcWorkingPosition(self.sample_data['x_well'],
                                           self.sample_data['y_well'],
                                           tool)
        return x, y
        
    # TODO: refactor samplePercentToZ, sampleVolToZ and others that may reapeat the code
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
        

class plate():
    """
    Handles plates. Plate may be a real "plate", such as 96-well plate, or the other
    type of sample array. For example, 8-PCR tube stripe is also considered a plate.
    """
    
    #TODO: Sometimes plates are smaller than corresponding racks. Need capability to shift
    # plate related to rack
    
    def __init__(self, plate_name, plate_type):
        """
        Initializes plate of samples (array of samples)
        
        There should be a config files placed in configs/%plate_type%.ini and configs/%plate_type%_well.ini
        """
        
        self.plate_data = {}
        # Reading parameters for config file
        config = configparser.ConfigParser()
        config_path = 'configs/' + plate_type + '.ini'
        config.read(config_path)
        
        self.columns = int(config['wells']['columns'])
        self.rows = int(config['wells']['rows'])
        self.dist_between_cols = float(config['wells']['distance_between_columns'])
        self.dist_between_rows = float(config['wells']['distance_between_rows'])
        self.dist_cntr_to_1st_col = float(config['wells']['distance_center_to_1st_column'])
        self.dist_cntr_to_1st_row = float(config['wells']['distance_center_to_1st_row'])

        self.samples_list = self._initSamples(plate_name, plate_type)
        # Use length of an individual well as a length of the plate
        self.length = self._getZeroSample().length
        
    def _initSamples(self, plate_name, plate_type):
        samples_list = []
        for col in range(self.columns):
            for row in range(self.rows):
                s_name = plate_name + '_col_' + str(col) + '_row_' + str(row)
                s = sample(sample_name=s_name, sample_type=plate_type+'_well')
                # Setting a position of a sample
                s.sample_data['x_well'] = col
                s.sample_data['y_well'] = row
                samples_list.append(s)
        return samples_list
    
    def _getZeroSample(self):
        return self.getSample(0, 0)
    
    def getSample(self, column, row):
        for s in self.samples_list:
            if (s.sample_data['x_well'] == column) and (s.sample_data['y_well'] == row):
                return s
            
    def getSamples(self, col_row_list):
        """
        Returns list of samples objects
        Input:
            col_row_list
                List of sample coordinates in the plate. Each coordinate is 2 element list: [column, row]
                Example: [[3, 1], [6, 7], [11, 0]]
        Returns:
            List of sample objects
        """
        samples_to_return_list = []
        for col_row in col_row_list:
            col = col_row[0]
            row = col_row[1]
            s = self.getSample(col, row)
            samples_to_return_list.append(s)
        return samples_to_return_list
    
    def getAllSamples(self):
        return self.samples_list
    
    def place(self, rack):
        self.plate_data['rack'] = rack
        sample_list = self.getAllSamples()
        for s in sample_list:
            s.sample_data['rack'] = rack

            
    def getSampleCenterXY(self, tool):
        """
        Obtain X and Y coordinates of the center of the plate
        """
        rack = self.plate_data['rack']
        x, y, z = rack.calcRackCenterFullCalibration(tool)
        return x, y

    
    def getSampleTopZ(self, tool):
        """
        Returns absolute Z coordinate of the top of the plate
        """
        return self._getZeroSample().getSampleTopZ(tool)

        
    def getMaxVolume(self):
        """
        Returns maximum volume of an individual well
        """
        return self._getZeroSample().getMaxVolume()

        
    def sampleVolToZ(self, volume, tool):
        """
        Calculates Z at which the end of the tool will be at 
        the level of the sample which corresponds to provided volume
        """
        
        return self._getZeroSample().sampleVolToZ(volume, tool)
        

    def sampleDepthToZ(self, height, tool):
        """
        Moves the tool to a given height, relative to the top of the sample.
        Larger the height value, the deeper tool will be inserted
        """
        return self._getZeroSample().sampleDepthToZ(height, tool)


    def getDepthFromVolume(self, volume):
        """
        Calculates distance from the top of the sample to the 
        position of certain volume.
        """
        return self._getZeroSample().getDepthFromVolume(volume)


    def samplePercentToZ(self, fraction, tool):
        """
        Calculate Z at which the end of the tool will be, corresponding
        to percent of sample height
        """
        return self._getZeroSample().samplePercentToZ(fraction, tool)


    def sampleRelativeZtoAbsoluteZ(self, dZ, tool):
        """
        Calculates absolute Z value based on provided dZ value relative to the 
        sample top.
        For example, if the sample top is positioned at 500, and dZ = 20,
        then function returns 520; at this absolute height, the distance between
        the top of the sample and the tool's calibrated point will be 20 mm.
        """
        return self._getZeroSample().sampleRelativeZtoAbsoluteZ(dZ, tool)
        
    def setSampleEngagedPosition(self, dz):
        zs = self._getZeroSample()
        zs.setSampleEngagedPosition(dz)
        
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
        
        return self._getZeroSample().length - dz    

    def getSampleHeightAboveRack(self):
        """
        Returns arbitrary height of sample above the rack where it is 
        currently placed (in mm).
        """
        return self._getZeroSample().getSampleHeightAboveRack()      
        
        
    def disengage(self):
        self._getZeroSample().sample_engaged_dz = None