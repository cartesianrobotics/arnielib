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
        
        # Loading dependence of volume in the tube vs. depth related to the tube top
        try:
            volume_heigth_dict_path = str(confir['properties']['volume_height_data'])
            filehandler = open('configs/'+volume_heigth_dict_path, 'r')
            self.volume_height_dict = json.loads(filehandler.read())
            filehandler.close()
        except:
            pass
            
        # Loading inner diameter
        try:
            self.inner_diameter = float(config['geometry']['inner_diameter'])
            
    
    def place(self, rack, x_well, y_well):
        """
        Used to place a tube into an empty well of a rack.
        """
        self.sample_data['rack'] = rack
        self.sample_data['x_well'] = x_well
        self.sample_data['y_well'] = y_well
        
    