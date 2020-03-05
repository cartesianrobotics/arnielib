import unittest
import mock
import os
import json

# Parts of ArnieLib
import tools
import racks
import cartesian
import calibration


class tool_test_case(unittest.TestCase):
    
    @mock.patch('tools.stationary_touch_probe')
    @mock.patch('tools.mobile_touch_probe')
    @mock.patch('cartesian.arnie')
    def test_calibrateStationaryProbe__returns(self, mock_arnie, mock_mtp, mock_stp):
        # Defining mock objects
        ar = mock_arnie('COM1', 'COM2')
        mtp = mock_mtp('COM3')
        stp = mock_stp('COM4')
        
        stp.rack.getSimpleCalibrationPoints.return_value = (80, 65, 600, 20, 10, 10)
        
        tools.findCenterOuterTwoProbes = mock.MagicMock()
        tools.findWall = mock.MagicMock()
        tools.findCenterOuterTwoProbes.return_value = 66
        tools.findWall.return_value = 420
        
        # Testing
        x, y, z = calibration.calibrateStationaryProbe(mtp, stp)
        
        self.assertEqual(x, 66)
        self.assertEqual(y, 66)
        self.assertEqual(z, 420)


    #@mock.patch('tools.stationary_touch_probe')
    #@mock.patch('tools.mobile_touch_probe')
    #@mock.patch('cartesian.arnie')
    #def test_calibrateStationaryProbe__movements(self, mock_arnie, mock_mtp, mock_stp):
    #    # Defining mock objects
    #    ar = mock_arnie('COM1', 'COM2')
    #    mtp = mock_mtp('COM3')
    #    stp = mock_stp('COM4')
    #    
    #    stp.rack.getSimpleCalibrationPoints.return_value = (80, 65, 425, 20, 10, 10)
    #    
    #    tools.findCenterOuterTwoProbes = mock.MagicMock()
    #    tools.findWall = mock.MagicMock()
    #    tools.findCenterOuterTwoProbes.return_value = 66
    #    tools.findWall.return_value = 420
    #    
    #    # Testing
    #    x, y, z = calibration.calibrateStationaryProbe(mtp, stp)
    #    
    #    mtp.robot.move.assert_called_with(x=80, y=65, z=425, z_first=False)
    
    @mock.patch('tools.mobile_touch_probe')
    @mock.patch('cartesian.arnie')
    def test__calibrateRack__returns(self, mock_arnie, mock_mtp):
        # Defining mock objects
        ar = mock_arnie('COM1', 'COM2')
        mtp = mock_mtp('COM3')
        path = 'RackThatCannotBeNamed.json'
        if os.path.exists(path):
            os.remove(path)
        
        rack = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='p1000_tips', x_slot=0, y_slot=2)
        
        mtp.findCenterOuter = mock.MagicMock()
        mtp.findWall = mock.MagicMock()
        mtp.getStalagmyteCoord = mock.MagicMock()
        mtp.findCenterOuter.return_value = 266
        mtp.findWall.return_value = 420
        mtp.getStalagmyteCoord.return_value = (66, 66, 500)
    
        # Testing
        x, y, z = calibration.calibrateRack(mtp, rack)
        
        # Evaluating
        self.assertEqual(x, 266)
        self.assertEqual(y, 266)
        self.assertEqual(z, 420)      
        
        # Cleaning up
        try:
            os.remove(path)
        except:
            pass



            
    @mock.patch('tools.mobile_touch_probe')
    @mock.patch('cartesian.arnie')
    def test__calibrateRack__dataCorrectlySaved(self, mock_arnie, mock_mtp):
        # Defining mock objects
        ar = mock_arnie('COM1', 'COM2')
        mtp = mock_mtp('COM3')
        path = 'RackThatCannotBeNamed.json'
        if os.path.exists(path):
            os.remove(path)
        
        rack = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='p1000_tips', x_slot=0, y_slot=2)
        
        mtp.findCenterOuter = mock.MagicMock()
        mtp.findWall = mock.MagicMock()
        mtp.getStalagmyteCoord = mock.MagicMock()
        mtp.findCenterOuter.return_value = 266
        mtp.findWall.return_value = 420
        mtp.getStalagmyteCoord.return_value = (66, 66, 500)
    
        # Testing
        x, y, z = calibration.calibrateRack(mtp, rack)   

        # Evaluating
        with open('RackThatCannotBeNamed.json', 'r') as f:
            saved_dict = json.loads(f.read())
        
        self.assertEqual(saved_dict['name'], 'RackThatCannotBeNamed')
        self.assertEqual(saved_dict['type'], 'p1000_tips')
        self.assertEqual(saved_dict['n_x'], 0)
        self.assertEqual(saved_dict['n_y'], 2)
        self.assertEqual(saved_dict['position'], [266, 266, 420])
        self.assertEqual(saved_dict['pos_stalagmyte'], [66, 66, 500])
        
        # Cleaning up
        try:
            os.remove(path)
        except:
            pass



    @mock.patch('tools.stationary_touch_probe')
    @mock.patch('tools.mobile_tool')
    @mock.patch('cartesian.arnie')    
    def test__calibrateTool__returns(self, mock_arnie, mock_tool, mock_stp):
        # Defining mock objects
        ar = mock_arnie('COM1', 'COM2')
        stp = mock_stp('COM3')
        tool = mock_tool('COM4')
        path = 'ToolThatCannotBeNamed.json'
        if os.path.exists(path):
            os.remove(path)

        stp.rack.getSimpleCalibrationPoints.return_value = (80, 65, 600, 20, 10, 10)
        
        stp.findCenterOuter = mock.MagicMock()
        stp.findWall = mock.MagicMock()
        stp.findCenterOuter.return_value = 266
        stp.findWall.return_value = 420
        
        # Testing
        x, y, z = calibration.calibrateTool(tool, stp)
        
        # Evaluating
        self.assertEqual(x, 266)
        self.assertEqual(y, 266)
        self.assertEqual(z, 420)          

        # Cleaning up
        try:
            os.remove(path)
        except:
            pass        



    @mock.patch('tools.stationary_touch_probe')
    @mock.patch('tools.mobile_tool')
    @mock.patch('cartesian.arnie')    
    def test__calibrateTool__dataCorrectlySaved(self, mock_arnie, mock_tool, mock_stp):
        # Defining mock objects
        ar = mock_arnie('COM1', 'COM2')
        stp = mock_stp('COM3')
        tool = mock_tool('COM4')

        stp.rack.getSimpleCalibrationPoints.return_value = (80, 65, 600, 20, 10, 10)
        
        stp.findCenterOuter = mock.MagicMock()
        stp.findWall = mock.MagicMock()
        stp.findCenterOuter.return_value = 266
        stp.findWall.return_value = 420
        
        # Testing
        x, y, z = calibration.calibrateTool(tool, stp)
        
        # Evaluating
        tool.setStalagmyteCoord.assert_called_with(266, 266, 420)
            
            
            
if __name__ == '__main__':
    unittest.main()