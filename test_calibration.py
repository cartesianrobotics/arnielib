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


    def test__calibrateRack__stackable(self):
        cartesian.arnie = mock.MagicMock()
        tools.mobile_touch_probe = mock.MagicMock()
        
        # Initializing robot with a tool (mocked)
        ar = cartesian.arnie('COM1', 'COM2')
        tp = tools.mobile_touch_probe('COM3')
        
        
        # Touch probe parameters
        tp.getStalagmyteCoord = mock.MagicMock()
        tp.getStalagmyteCoord.return_value = (66, 66, 500)
        
        # Initializing stack of racks
        r = racks.stackable(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        r_below = racks.stackable(rack_name='BottomRackThatCannotBeNamed', rack_type='test_rack')
        r_below.overwriteSlot(1, 4)
        
        # Parameters of a bottom rack
        r_below.getSavedSlotCenter = mock.MagicMock()
        r_below.getSavedSlotCenter.return_value = (200, 100, 600)
        
        # Forming a stack by placing top rack onto the bottom rack
        r_below.placeItemOnTop(r)
        
        
        # Mocking findCenterOuter function to give different outputs for 'x' and 'y'
        tp.findCenterOuter = mock.MagicMock(side_effect=[205, 95])
        tp.findWall = mock.MagicMock()
        tp.findWall.return_value = 301
        
        # Performing calibration
        x, y, z = calibration.calibrateRack(tp, r)
        
        # Evaluating outputs
        self.assertEqual(x, 205)
        self.assertEqual(y, 95)
        self.assertEqual(z, 301)
        
        # Evaluating robot movements based on provided parameters
        tp.robot.move.assert_has_calls([mock.call(x=129, y=100, z=406, z_first=False),
                                        mock.call(x=205, y=54),
                                        mock.call(x=205, y=95),
                                        mock.call(z=400)])
        

            
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

            
    @mock.patch('tools.stationary_touch_probe')
    @mock.patch('tools.mobile_tool')
    @mock.patch('cartesian.arnie')    
    def test__calibrateToolCustomPoints(self, mock_arnie, mock_tool, mock_stp):
        """
        At the moment, the test only confirms the function runs without errors.
        """
        ar = mock_arnie('COM1', 'COM2')
        stp = mock_stp('COM3')
        tool = mock_tool('COM4')
        
        stp.rack.getCalibratedRackCenter.return_value = (200, 100, 500)
        
        # Testing
        x, y, z = calibration.calibrateToolCustomPoints(tool, stp)
        

    @mock.patch('tools.stationary_touch_probe')
    @mock.patch('tools.mobile_tool')
    @mock.patch('cartesian.arnie')    
    def test__calibrateToolCustomPoints__step_back_length_usage(self, mock_arnie, mock_tool, mock_stp):
        """
        At the moment, the test only confirms the function runs without errors.
        """
        ar = mock_arnie('COM1', 'COM2')
        stp = mock_stp('COM3')
        tool = mock_tool('COM4')
        
        stp.rack.getCalibratedRackCenter.return_value = (200, 100, 500)
        tool.step_back_length = -3
        
        tool.immobile_probe_calibration_points = {}
        tool.immobile_probe_calibration_points['x_Xfrontal'] = -35
        tool.immobile_probe_calibration_points['x_Xrear'] = 32
        tool.immobile_probe_calibration_points['raise_z'] = 42
        tool.immobile_probe_calibration_points['z_Y'] = -20
        tool.immobile_probe_calibration_points['y_Yfrontal'] = -53.0
        tool.immobile_probe_calibration_points['y_Yrear'] = 53.0
        tool.immobile_probe_calibration_points['y_X'] = 0.0
        tool.immobile_probe_calibration_points['z_X'] = 4.0
        tool.immobile_probe_calibration_points['x_Y'] = 0.0
        tool.immobile_probe_calibration_points['z_Y'] = -20.0
        tool.immobile_probe_calibration_points['dx_Z'] = 0
        tool.immobile_probe_calibration_points['dy_Z'] = -40
        
        # Testing
        x, y, z = calibration.calibrateToolCustomPoints(tool, stp)
        
        stp.findCenterOuter.assert_called_with(axis='y', 
            raise_height=42, dist_through_obstruct=106.0, step_back_length=-3)

            
            
if __name__ == '__main__':
    unittest.main()