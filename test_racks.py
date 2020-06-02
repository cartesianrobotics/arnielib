import unittest
import mock
import racks
import os
import json
import configparser

class racks_test_case(unittest.TestCase):
    
    def test_no_rack_data_file(self):
        path = 'p1000_tips.json'
        new_path = 'p1000_tips_temp.json'
        if os.path.exists(path):
            os.rename(path, new_path)
        
        result = os.path.exists(path)
        self.assertFalse(result)
        
        if os.path.exists(new_path):
            os.rename(new_path, path)
    
    def test_init_no_rack_data_file(self):
        path = 'p1000_tips.json'
        new_path = 'p1000_tips_temp.json'
        if os.path.exists(path):
            os.rename(path, new_path)
        
        p1000 = racks.rack(rack_name="p1000_1")
        self.assertEqual(p1000.rack_data, {'name': 'p1000_1'})
        
        p1000 = racks.rack(rack_name="p1000_1", x_slot=0, y_slot=0)
        self.assertEqual(p1000.rack_data, {'name': 'p1000_1', 'n_x': 0, 'n_y': 0})
        
        p1000 = racks.rack(rack_name="p1000_1", rack_type='p1000_tips')
        self.assertEqual(p1000.rack_data, {'name': 'p1000_1', 'type': 'p1000_tips'})
        self.assertEqual(p1000.z_height, 76.0)
        
        if os.path.exists(new_path):
            os.rename(new_path, path)
            
    def test__init__noRackDataFile__2(self):
        path = 'RackThatCannotBeNamed.json'
        if os.path.exists(path):
            os.remove(path)
        p1000 = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='p1000_tips', x_slot=0, y_slot=2)
        
        self.assertIn('name', p1000.rack_data)
        self.assertIn('n_x', p1000.rack_data)
        self.assertIn('n_y', p1000.rack_data)
        self.assertIn('type', p1000.rack_data)
    
            
    def test_init_external_data_provided(self):
        path = 'p1000_tips.json'
        new_path = 'p1000_tips_temp.json'
        if os.path.exists(path):
            os.rename(path, new_path)
        
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x': 0, 'n_y': 0, 'type': 'p1000_tips'})
        self.assertEqual(p1000.rack_data, {'name': 'p1000_1', 'n_x': 0, 'n_y': 0, 'type': 'p1000_tips'})
        
        if os.path.exists(new_path):
            os.rename(new_path, path)
            
    def test_init_loading_data(self):
        path = 'p1000_1.json'
        new_path = 'p1000_1_temp.json'

        if os.path.exists(path):
            try:
                os.rename(path, new_path)
            except:
                pass
        
        # Creating test file
        f = open(path, 'w')
        f.write(json.dumps({'name': 'p1000_1', 'n_x': 0, 'n_y': 0, 'type': 'p1000_tips'}))
        f.close()
        p1000 = racks.rack(rack_name="p1000_1")
        self.assertEqual(p1000.rack_data, {'name': 'p1000_1', 'n_x': 0, 'n_y': 0, 'type': 'p1000_tips'})
        
        os.remove(path)
        if os.path.exists(new_path):
            os.rename(new_path, path)
        
    def test_overwriteSlot(self):
        path = 'p1000_1.json'
        new_path = 'p1000_1_temp.json'

        if os.path.exists(path):
            try:
                os.rename(path, new_path)
            except:
                pass
        
        # Creating test file
        f = open(path, 'w')
        f.write(json.dumps({'name': 'p1000_1', 'n_x': 0, 'n_y': 0, 'type': 'p1000_tips'}))
        f.close()
        
        p1000 = racks.rack(rack_name="p1000_1")
        self.assertEqual(p1000.rack_data['n_x'], 0)
        self.assertEqual(p1000.rack_data['n_y'], 0)
        p1000.overwriteSlot(3, 4)
        self.assertEqual(p1000.rack_data['n_x'], 3)
        self.assertEqual(p1000.rack_data['n_y'], 4)
        
        os.remove(path)
        if os.path.exists(new_path):
            os.rename(new_path, path)

    def test_getSavedSlotCenter(self):
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2})
        x, y, z = p1000.getSavedSlotCenter()
        
        self.assertAlmostEqual(x, 92.195, 1)
        self.assertAlmostEqual(y, 285.6, 1)
        self.assertAlmostEqual(z, 604.4, 1)


#    def test_getSimpleCalibrationPoints(self):
#        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
#        x, y, z, opposite_x, retract_y, raise_z = p1000.getSimpleCalibrationPoints()
#        self.assertAlmostEqual(x, 25.694, 1)
#        self.assertAlmostEqual(y, 285.6, 1)
#        self.assertAlmostEqual(z, 532.4, 1)
#        self.assertAlmostEqual(opposite_x, 158.695, 1)
#        self.assertAlmostEqual(retract_y, 47.5, 1)
#        self.assertAlmostEqual(raise_z, 20, 1)
    
    def test_sanity_getSimpleCalibrationPoints(self):
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        x, y, z, opposite_x, retract_y, raise_z = p1000.getSimpleCalibrationPoints()
        self.assertGreater(opposite_x, x)
        self.assertGreater(raise_z, 0)
        self.assertLess(opposite_x-x, 150)
        self.assertLess(retract_y*2, 110)
    
    def test_getSimpleCalibrationPoints_StartingTooCloseToObject(self):
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        x, y, z, opposite_x, retract_y, raise_z = p1000.getSimpleCalibrationPoints()
        x_cntr, y_cntr, z_cntr = p1000.getSavedSlotCenter()
        self.assertLess(x_cntr - x, 150/2.0)
        self.assertGreater(x_cntr - x, p1000.x_width/2.0)
        self.assertLess(x, x_cntr - p1000.x_width/2.0)
        
    def test_getSimpleCalibrationPoints_raiseHeightRelativeNotAbsoute(self):
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        x, y, z, opposite_x, retract_y, raise_z = p1000.getSimpleCalibrationPoints()
        x_cntr, y_cntr, z_cntr = p1000.getSavedSlotCenter()
        self.assertLess(raise_z, p1000.max_height)
        self.assertLess(z - raise_z, z_cntr - p1000.max_height)


#    def test_calcWellXY_NotCalibrated(self):
#        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
#        #x, y = p1000.calcWellXY(0, 0)
#        #self.assertAlmostEqual(x, 42.694, 1)
#        #self.assertAlmostEqual(y, 254.100, 1)
#        #x, y = p1000.calcWellXY(11, 7)
#        #self.assertAlmostEqual(x, 141.695, 1)
#        #self.assertAlmostEqual(y, 317.1, 1)
#        self.assertTrue(True)
#        self.assertRaises(KeyError, p1000.calcWellXY, 0, 0)
    
    def test_calcWellXY_Calibrated(self):
        p1000 = racks.rack(rack_name="p1000_1", 
            rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips', 'position': [100, 200, 600]})
        x, y = p1000.calcWellXY(0, 0)
        self.assertGreater(x, 40)
        self.assertLess(x, 60)
        self.assertGreater(y, 150)
        self.assertLess(y, 180)
        x, y = p1000.calcWellXY(11, 7)
        self.assertGreater(x, 140)
        self.assertLess(x, 160)
        self.assertGreater(y, 220)
        self.assertLess(y, 240)

        
    def test_sanity_calcWellXY(self):
        p1000 = racks.rack(rack_name="p1000_1", 
            rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips', 'position': [100, 200, 600]})
        x1, y1 = p1000.calcWellXY(0, 0)
        x2, y2 = p1000.calcWellXY(11, 7)
        self.assertGreater(x2, x1)
        self.assertGreater(y2, y1)
        self.assertAlmostEqual(x2-x1, 11*8.89, 1)
        self.assertAlmostEqual(y2-y1, 7*8.89, 1)


    def test_calcAbsoluteTopZ(self):
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        p1000.max_height = 200
        p1000.getSavedSlotCenter = mock.MagicMock()
        p1000.getSavedSlotCenter.return_value = [100, 200, 600]
        calculated_max_z = p1000.calcAbsoluteTopZ()
        self.assertEqual(calculated_max_z, 400)
        
        
    def test_calcWorkingPosition(self):
        p1000_rack = racks.rack(
            rack_name="p1000_1_test", 
            rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        p1000_rack.updateCenter(x=100, y=200, z=600, x_btm_touch=90, y_btm_touch=66, z_btm_touch=500)
        p1000_rack.z_working_height = 0
        
        # Making sure the rack center outpit is consistent with the input
        self.assertEqual(600, p1000_rack.getCalibratedRackCenter()[2])
        
        # Mock class to provide tool calibration data
        class tool():
            
            def getStalagmyteCoord(self):
                return [91, 65, 400]
        tool = tool()
        
        # not corrected coordinates
        x_nc, y_nc = p1000_rack.calcWellXY(well_col=0, well_row=0)
        x_slot, y_slot, z_calibr = p1000_rack.getCalibratedRackCenter()
        z_nc = z_calibr - p1000_rack.z_working_height
        
        # corrected coordinates
        x_corr, y_corr, z_corr = p1000_rack.calcWorkingPosition(well_col=0, well_row=0, tool=tool)
        
        self.assertEqual(x_corr-x_nc, 1)
        self.assertEqual(y_corr-y_nc, -1)
        self.assertEqual(z_corr-z_nc, -100)
    

    def test_calcWorkingPosition_NoToolProvided(self):
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        p1000.updateCenter(x=100, y=200, z=600, x_btm_touch=90, y_btm_touch=66, z_btm_touch=500)
        p1000.z_working_height = 0
        
        # not corrected coordinates
        x_nc, y_nc = p1000.calcWellXY(well_col=0, well_row=0)
        x_slot, y_slot, z_calibr = p1000.getCalibratedRackCenter()
        z_nc = z_calibr - p1000.z_working_height
        
        # corrected coordinates
        x_corr, y_corr, z_corr = p1000.calcWorkingPosition(well_col=0, well_row=0)
        
        self.assertEqual(x_corr-x_nc, 0)
        self.assertEqual(y_corr-y_nc, 0)
        self.assertEqual(z_corr-z_nc, 0)
        

    def test_calcWorkingPosition_noStalagmyteDataProvided(self):
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        p1000.rack_data['position'] = [100,200,600]
        p1000.z_working_height = 0
        
        # Mock class to provide tool calibration data
        class tool():
            def __init__(self):
                self.tool_data = {}
                self.tool_data['pos_stalagmyte'] = [91, 65, 400]
        tool = tool()
        
        # not corrected coordinates
        x_nc, y_nc = p1000.calcWellXY(well_col=0, well_row=0)
        x_slot, y_slot, z_calibr = p1000.getCalibratedRackCenter()
        z_nc = z_calibr - p1000.z_working_height
        
        # corrected coordinates
        x_corr, y_corr, z_corr = p1000.calcWorkingPosition(well_col=0, well_row=0, tool=tool)
        
        self.assertEqual(x_corr-x_nc, 0)
        self.assertEqual(y_corr-y_nc, 0)
        self.assertEqual(z_corr-z_nc, 0)        
    
        
    def test_updateCenter_NotCalibrated(self):
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        p1000.updateCenter(x=100, y=200, z=600, x_btm_touch=90, y_btm_touch=66, z_btm_touch=500)
        self.assertEqual(p1000.rack_data['position'], [100, 200, 600])
        self.assertEqual(p1000.rack_data['pos_stalagmyte'], [90, 66, 500])
        
    def test_updateCenter_Calibrated(self):
        p1000 = racks.rack(rack_name="p1000_1", 
            rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips', 'position': [100, 200, 600]})
        p1000.updateCenter(x=105, y=195, z=605, x_btm_touch=90, y_btm_touch=66, z_btm_touch=500)
        self.assertEqual(p1000.rack_data['position'], [105, 195, 605])
        self.assertEqual(p1000.rack_data['pos_stalagmyte'], [90, 66, 500])

    def test_saveTool(self):
        path = 'p1000_1.json'
        new_path = 'p1000_1_temp.json'
        if os.path.exists(path):
            os.rename(path, new_path)
        
        self.assertFalse(os.path.exists(path))
        
        p1000 = racks.rack(rack_name="p1000_1", 
            rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips', 'position': [100, 200, 600]})
        p1000.save()
        
        self.assertTrue(os.path.exists(path))
        
        p1000 = racks.rack(rack_name="p1000_1")
        self.assertEqual(p1000.rack_data, 
            {'name': "p1000_1", 'n_x':0, 'n_y':2, 'type': 'p1000_tips', 'position': [100, 200, 600]})
        
        os.remove(path)
        self.assertFalse(os.path.exists(path))
        if os.path.exists(new_path):
            os.rename(new_path, path)
        

    def test__getRelativeZCalibrationPoint(self):
        
        r = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='p1000_tips', x_slot=0, y_slot=2)
        
        config = configparser.ConfigParser()
        config_path = 'configs/p1000_tips.ini'
        config.read(config_path)
        
        saved_dxdy_list = [
            float(config['calibration']['z_calibration_dx_coord']),
            float(config['calibration']['z_calibration_dy_coord']),
        ]
        
        self.assertEqual(r.z_calibration_dxdy_coord, saved_dxdy_list)
        self.assertEqual(
            r.z_calibration_dz, float(config['calibration']['z_calibration_dz']))


    def test__getRackCenterFullCalibration(self):
        r = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        
        r.rack_data['position'] = [400, 200, 500]
        r.rack_data['pos_stalagmyte'] = [200, 100, 400]
        
        class tool():
            def getStalagmyteCoord(self):
                return [210, 95, 420]
        mock_tool = tool()

        x, y, z = r.calcRackCenterFullCalibration(mock_tool)
        
        self.assertEqual(x, 410)
        self.assertEqual(y, 195)
        self.assertEqual(z, 520)
        


    # Rack gripping functions
    def test__getGrippingHeight(self):
        
        r = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        
        r.calcRackCenterFullCalibration = mock.MagicMock()
        r.calcRackCenterFullCalibration.return_value = (200, 100, 500)
        gripper_dict = {'test_gripper': {'z_grip': 20}}
        r.rack_data['gripper'] = gripper_dict
        
        class tool():
            def __init__(self):
                self.tool_data = {}
                self.tool_data['name'] = 'test_gripper'
        mock_tool = tool()
                
        z = r.getGrippingHeight(tool=mock_tool)
        self.assertEqual(z, 520)
        z = r.getGrippingHeight(tool=mock_tool, extra_z=5)
        self.assertEqual(z, 525)
    
    def test__getGrippingOpenDiam(self):
        r = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        
        r.calcRackCenterFullCalibration = mock.MagicMock()
        r.calcRackCenterFullCalibration.return_value = (200, 100, 500)
        gripper_dict = {'test_gripper': {'open_diam': 90}}
        r.rack_data['gripper'] = gripper_dict
        
        class tool():
            def __init__(self):
                self.tool_data = {}
                self.tool_data['name'] = 'test_gripper'
        mock_tool = tool()
        
        d = r.getGrippingOpenDiam(tool=mock_tool)
        self.assertEqual(d, 90)

    def test__getGrippingCloseDiam(self):
        r = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        
        r.calcRackCenterFullCalibration = mock.MagicMock()
        r.calcRackCenterFullCalibration.return_value = (200, 100, 500)
        gripper_dict = {'test_gripper': {'grip_diam': 80}}
        r.rack_data['gripper'] = gripper_dict
        
        class tool():
            def __init__(self):
                self.tool_data = {}
                self.tool_data['name'] = 'test_gripper'
        mock_tool = tool()
        
        d = r.getGrippingCloseDiam(tool=mock_tool)
        self.assertEqual(d, 80)

    
    def test__setGrippingProperties(self):
    
        # Cleaning rack data file that may remain after previous manipulations
        try:
            os.remove('RackThatCannotBeNamed.json')
        except:
            pass
            
        r = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        
        self.assertFalse('gripper' in r.rack_data)
        
        class tool():
            def __init__(self):
                self.tool_data = {}
                self.tool_data['name'] = 'test_gripper'
        mock_tool = tool()
        
        r.setGrippingProperties(90, 80, 20, gripper=mock_tool)
        
        self.assertTrue('gripper' in r.rack_data)
        self.assertTrue('test_gripper' in r.rack_data['gripper'])
        self.assertTrue('open_diam' in r.rack_data['gripper']['test_gripper'])
        self.assertTrue('grip_diam' in r.rack_data['gripper']['test_gripper'])
        self.assertTrue('z_grip' in r.rack_data['gripper']['test_gripper'])
        
        del r
        
        # Repeating same checks to see if the data will be properly loaded
        # from file
        r = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        self.assertTrue('gripper' in r.rack_data)
        self.assertTrue('test_gripper' in r.rack_data['gripper'])
        self.assertTrue('open_diam' in r.rack_data['gripper']['test_gripper'])
        self.assertTrue('grip_diam' in r.rack_data['gripper']['test_gripper'])
        self.assertTrue('z_grip' in r.rack_data['gripper']['test_gripper'])
        
        # Cleaning rack data file after manipulations
        try:
            os.remove('RackThatCannotBeNamed.json')
        except:
            pass


    def test__getHeigthBelowGripper(self):
        r = racks.rack(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        gripper_dict = {'test_gripper': {'z_grip': 20}}
        r.rack_data['gripper'] = gripper_dict
        r.max_height = 100
        
        class tool():
            def __init__(self):
                self.tool_data = {}
                self.tool_data['name'] = 'test_gripper'
        mock_tool = tool()
        
        h = r.getHeightBelowGripper(tool=mock_tool)
        self.assertEqual(h, 80)

    def test__getStalagmyteCalibration(self):
        r = racks.stackable(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        # Simulating stalagmyte calibration data
        r.rack_data['pos_stalagmyte'] = [200, 100, 400]
        self.assertEqual(r.getStalagmyteCalibration(), (200, 100, 400))


    def test__getCalibratedRackCenter(self):
        r = racks.stackable(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        r.rack_data['position'] = [400, 200, 500]
        self.assertEqual(r.getCalibratedRackCenter(), (400, 200, 500))


# =============================================================================
# Testing stackable racks
# =============================================================================
    
    def test__stackableOnTop(self):
        """
        This one tests behaviour of a stackable rack on top of a stack
        """
        r = racks.stackable(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        r_below = racks.stackable(rack_name='BottomRackThatCannotBeNamed', rack_type='test_rack')
        
        r.max_height = 100
        
        self.assertEqual(r.top_item, None)
        self.assertEqual(r.getTopItem(), None)
        
        # Now simulating the bottom rack being calibrated, and then a new one
        # placed on top of the bottom rack.
        r_below.rack_data['position'] = [400, 200, 500]
        r_below.rack_data['pos_stalagmyte'] = [200, 100, 400]
        self.assertEqual(r_below.getCalibratedRackCenter(), (400, 200, 500))
        r_below.placeItemOnTop(r)
        # Stackable rack has height 100 mm, so the new top will be 100 mm above calibrated value
        # X and Y values stays the same.
        self.assertEqual(r.getCalibratedRackCenter(), (400, 200, 500-100))
        self.assertEqual(r_below.getTopItem(), r)
        
        # Now simulating removal of the top rack from the bottom rack
        r_below.removeTopItem()
        self.assertEqual(r_below.getTopItem(), None)
        # Coordinates should stay the same as before
        self.assertEqual(r_below.getCalibratedRackCenter(), (400, 200, 500))
        
        # Now simulating the case when the neq rack was placed on top, calibrated,
        # received new calibration values and then removed.
        r_below.placeItemOnTop(r)
        r.updateCalibratedRackCenter(402, 198, 405) # new values are slightly different then old ones.
        r_below.removeTopItem()
        self.assertEqual(r_below.getCalibratedRackCenter(), (402, 198, 505))

        # The case when a user manually places a stack onto the robot.
        r = racks.stackable(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        r_below = racks.stackable(rack_name='BottomRackThatCannotBeNamed', rack_type='test_rack')
        r.max_height = 100
        # User would initialize those racks manually. Both racks has no calibration at this point
        self.assertRaises(KeyError, lambda x: r_below.rack_data['position'], 1)
        self.assertRaises(KeyError, lambda x: r.rack_data['position'], 1)
        racks.logging.error = mock.MagicMock() # removing logging error message for not calibrated rack
        r_below.placeItemOnTop(r)
        self.assertEqual(r_below.getTopItem(), r)
        # Simulating calibration routine
        # This is a very simple simulation, need to test an actual calibration routine
        # Top rack is calibrated, as the bottom ones are impossible to calibrate
        r.updateCalibratedRackCenter(x=402, y=198, z=405)
        r.updateStalagmyteCalibration(x=200, y=100, z=400)
        # Checking whether upper rack received its calibration parameters
        self.assertEqual(r.getCalibratedRackCenter(), (402, 198, 405))
        self.assertEqual(r.getStalagmyteCalibration(), (200, 100, 400))
        # Removing top rack
        r_below.removeTopItem()
        # Checking whether the bottom rack received calibration data 
        # And that the bottom rack height is correctly calculated
        self.assertEqual(r_below.getCalibratedRackCenter(), (402, 198, 505))
        self.assertEqual(r.getStalagmyteCalibration(), (200, 100, 400))
        
    
        
if __name__ == '__main__':
    unittest.main()