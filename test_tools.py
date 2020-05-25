import unittest
import tools
import os
import json
import mock
import cartesian
import low_level_comm as llc
import configparser


class tool_test_case(unittest.TestCase):
    

    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')    
    def test_genericToolEmptyInit(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        mock_readAll.assert_called()
        self.assertEqual(generic_tool.actual_welcome_message, "Welcome returned from the device")
        mock_cartesian.assert_called()
        mock_serialdev.assert_called()
        mock_serialdev.assert_called_with('COM3', 115200, timeout=0.1)

    
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test_genericToolEmptyInit__tool_data(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        tool_data = generic_tool.tool_data
        self.assertEqual(tool_data, {'name': 'generic_tool', 'welcome_message': 'welcome'})
    
    
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')   
    def test_genericToolEmptyInit__rack_data(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        rack_data = generic_tool.rack.rack_data
        self.assertIn('name', rack_data)
        self.assertNotIn('somerandomnamewhichwillneveroccurinreallife', rack_data)
    
    
    @mock.patch('tools.racks.rack')
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')   
    def test_genericToolEmptyInit__properRackName(self, mock_serialdev, mock_readAll, mock_cartesian, mock_racks):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        mock_racks.assert_called_with(rack_name='generic_tool_rack', rack_type='generic_tool_rack')

    
    @mock.patch('tools.racks.rack')
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')   
    def test_genericToolEmptyInit__otherRackName(self, mock_serialdev, mock_readAll, mock_cartesian, mock_racks):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.tool(ar, 'COM3', tool_name='generic_tool', 
                    welcome_message='welcome', rack_name='generic_tool_rack_2')
        mock_racks.assert_called_with(rack_name='generic_tool_rack_2', rack_type='generic_tool_rack')
    
    
    @mock.patch('tools.json.dumps')
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')    
    def test_save(self, mock_serialdev, mock_readAll, mock_cartesian, mock_json_dumps):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        mock_json_dumps.return_value = "{'a': 'b'}"
        generic_tool.save()
        mock_json_dumps.assert_called_with({'name': 'generic_tool', 'welcome_message': 'welcome'})
        try:
            os.remove('generic_tool.json')
        except:
            pass


    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')           
    def test_openFileWithToolParameters_realData(self, mock_serialdev, mock_readAll, mock_cartesian):
        
        # Preparing for the test
        try:
            os.remove('generic_tool.json')
        except:
            pass
        
        with open('generic_tool.json', 'w') as f:
            f.write(json.dumps({'a': 'b'}))
        
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        
        # Test
        result_data_dict = generic_tool.openFileWithToolParameters('generic_tool.json')
        self.assertEqual(result_data_dict, {'a': 'b'})
        self.assertEqual(generic_tool.tool_data, {'a': 'b', 'name': 'generic_tool', 'welcome_message': 'welcome'})
        
        # Cleaning up after the test
        try:
            os.remove('generic_tool.json')
        except:
            pass

    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')  
    def test_obtainSlotCenter(self, mock_serialdev, mock_readAll, mock_cartesian):
        try:
            os.remove('generic_tool_rack.json')
        except:
            pass
        
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        generic_tool.rack.overwriteSlot(1,0)
        slot_center = generic_tool.rack.getSavedSlotCenter()
        self.assertGreater(slot_center[0], 230)
        self.assertLess(slot_center[0], 260)
        self.assertGreater(slot_center[1], 50)
        self.assertLess(slot_center[1], 80)
        self.assertGreater(slot_center[2], 500)
        self.assertLess(slot_center[2], 700)


# ======================================================================================
# mobile_tool class
# ======================================================================================

    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test__mobile_tool__init__(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.mobile_tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        mock_readAll.assert_called()
        self.assertEqual(generic_tool.actual_welcome_message, "Welcome returned from the device")
        mock_cartesian.assert_called()
        mock_serialdev.assert_called()
        mock_serialdev.assert_called_with('COM3', 115200, timeout=0.1)
        

    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test_mobile_tool_getToolFromSerialDev(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        serial_device = llc.serial_device('COM3')
        generic_tool = tools.mobile_tool.getToolFromSerialDev(robot=ar, 
                device=serial_device, welcome_message='welcome', tool_name='generic_tool')
        mock_readAll.assert_called()
        self.assertEqual(generic_tool.actual_welcome_message, "Welcome returned from the device")
        mock_cartesian.assert_called()
        mock_serialdev.assert_called()
        mock_serialdev.assert_called_with('COM3', 115200, timeout=0.1)
        tool_data = generic_tool.tool_data
        self.assertEqual(tool_data, {'name': 'generic_tool', 'welcome_message': 'welcome'})

    
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test_mobile_tool_getToolAtCoord(self, 
                mock_serialdev, mock_readAll, mock_cartesian):
                
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        ar.getToolAtCoord = mock.MagicMock()
        generic_tool = tools.mobile_tool.getToolAtCoord(robot=ar, 
                x=50, y=66, z=450, z_init=0, speed_xy=2000, speed_z=3000, 
                welcome_message='welcome', tool_name='generic_tool')
                
        ar.getToolAtCoord.assert_called_with(50, 66, 450, z_init=0, speed_xy=2000, speed_z=3000)
        
    
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test__mobile_tool__getTool(self, 
                mock_serialdev, mock_readAll, mock_cartesian):

        # Preparing for the test
        try:
            os.remove('generic_tool.json')
        except:
            pass
        
        with open('generic_tool_rack.json', 'w') as f:
            f.write(json.dumps({'a': 'b', 'position': [50, 66, 450]}))

        # Setting mocks        
        mock_readAll.return_value = "Welcome returned from the device"
        
        # Initializing
        ar = cartesian.arnie('COM1', 'COM2')
        ar.getToolAtCoord = mock.MagicMock()
        serial_device = llc.serial_device('COM3')
        generic_tool = tools.mobile_tool.getTool(robot=ar, 
                welcome_message='welcome', tool_name='generic_tool')
        
        z_pickup = 450 - generic_tool.rack.z_working_height
        
        # Testing
        ar.getToolAtCoord.assert_called_with(50, 66, z_pickup, z_init=0, speed_xy=None, speed_z=None)
        
        # Cleaning up after the test
        try:
            os.remove('generic_tool.json')
        except:
            pass
        try:
            os.remove('generic_tool_rack.json')
        except:
            pass


    @mock.patch('tools.json.dumps')
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')    
    def test_mobile_tool_save(self, mock_serialdev, mock_readAll, mock_cartesian, mock_json_dumps):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.mobile_tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        mock_json_dumps.return_value = "{'a': 'b'}"
        generic_tool.save()
        mock_json_dumps.assert_called_with({'name': 'generic_tool', 'welcome_message': 'welcome'})
        try:
            os.remove('generic_tool.json')
        except:
            pass


    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')           
    def test_mobileTool_openFileWithToolParameters_realData(
                    self, mock_serialdev, mock_readAll, mock_cartesian):
        
        # Preparing for the test
        try:
            os.remove('generic_tool.json')
        except:
            pass
        
        with open('generic_tool.json', 'w') as f:
            f.write(json.dumps({'a': 'b'}))
        
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.mobile_tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        
        # Test
        result_data_dict = generic_tool.openFileWithToolParameters('generic_tool.json')
        self.assertEqual(result_data_dict, {'a': 'b'})
        self.assertEqual(generic_tool.tool_data, {'a': 'b', 'name': 'generic_tool', 'welcome_message': 'welcome'})
        
        # Cleaning up after the test
        try:
            os.remove('generic_tool.json')
        except:
            pass


    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test__mobile_tool__getDockingPointByToolName(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.mobile_tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        generic_tool.rack.overwriteSlot(1,0)
        # Providing calibration data
        generic_tool.rack.updateCalibratedRackCenter(240, 70, 600)
        x, y, z = generic_tool.getDockingPointByToolName()
        self.assertEqual(x, 240)
        self.assertEqual(y, 70)
        self.assertEqual(z, 600+generic_tool.rack.z_working_height)


    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test__mobile_tool__returnTool(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        ar.returnToolToCoord = mock.MagicMock()
        generic_tool = tools.mobile_tool.getToolAtCoord(robot=ar, 
                x=50, y=66, z=450, z_init=0, speed_xy=2000, speed_z=3000, 
                welcome_message='welcome', tool_name='generic_tool')
        generic_tool.rack.overwriteSlot(1,0)
        # Mimicking tool coordinates load
        generic_tool.rack.updateCalibratedRackCenter(50, 66, 450)

        generic_tool.returnTool()
        
        # TODO: After finishing the data system, provide proper test
        # Test called with.
        ar.returnToolToCoord.assert_called()
        
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test__mobile_tool__returnToolToCoord(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        ar.returnToolToCoord = mock.MagicMock()
        generic_tool = tools.mobile_tool.getToolAtCoord(robot=ar, 
                x=50, y=66, z=450, z_init=0, speed_xy=2000, speed_z=3000, 
                welcome_message='welcome', tool_name='generic_tool')
        generic_tool.rack.overwriteSlot(1,0)
        
        generic_tool.returnToolToCoord(50, 66, 450, z_init=0, speed_xy=None, speed_z=None)
        
        ar.returnToolToCoord.assert_called_with(50, 66, 450, z_init=0, speed_xy=None, speed_z=None)



# ======================================================================================
# mobile_touch_probe class
# ======================================================================================

    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test__mobile_touch_probe__init__(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Arnie's mobile touch probe/nRev. 1.01, 11/27/2019"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.mobile_touch_probe(ar, 'COM3')
        mock_readAll.assert_called()
        self.assertEqual(generic_tool.actual_welcome_message, 
                "Arnie's mobile touch probe/nRev. 1.01, 11/27/2019")
        mock_cartesian.assert_called()
        mock_serialdev.assert_called()
        mock_serialdev.assert_called_with('COM3', 115200, timeout=0.1)


    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test_mobile_touch_probe__getTool(self, 
                mock_serialdev, mock_readAll, mock_cartesian):
        """
        If coordinates are not matched, then library for some reason
        not loading json file, and using probably slot calibration data instead.
        """
        
        with open('mobile_touch_probe_rack.json', 'r') as f:
            saved_dict = json.loads(f.read())
        x, y, z = saved_dict['position']

        config = configparser.ConfigParser()
        config_path = 'configs/mobile_touch_probe_rack.ini'
        config.read(config_path)            
        z_working_height = float(config['geometry']['z_working_height'])
        z_height = float(config['geometry']['z_box_height'])
        z_pickup = z - z_working_height
        
        # Setting mocks        
        mock_readAll.return_value = "Arnie's mobile touch probe/nRev. 1.01, 11/27/2019"
        
        # Initializing
        ar = cartesian.arnie('COM1', 'COM2')
        ar.getToolAtCoord = mock.MagicMock()
        serial_device = llc.serial_device('COM3')
        generic_tool = tools.mobile_touch_probe.getTool(robot=ar)
        
        # Testing
        ar.getToolAtCoord.assert_called_with(x, y, z_pickup, z_init=0, speed_xy=None, speed_z=None)
        

    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test__mobile_touch_probe__returnTool(self, 
                mock_serialdev, mock_readAll, mock_cartesian):

        with open('mobile_touch_probe_rack.json', 'r') as f:
            saved_dict = json.loads(f.read())
        x, y, z = saved_dict['position']

        config = configparser.ConfigParser()
        config_path = 'configs/mobile_touch_probe_rack.ini'
        config.read(config_path)            
        z_working_height = float(config['geometry']['z_working_height'])
        z_height = float(config['geometry']['z_box_height'])
        z_pickup = z - z_working_height
        
        # Setting mocks        
        mock_readAll.return_value = "Arnie's mobile touch probe/nRev. 1.01, 11/27/2019"
        
        # Initializing
        ar = cartesian.arnie('COM1', 'COM2')
        ar.getToolAtCoord = mock.MagicMock()
        serial_device = llc.serial_device('COM3')
        mobile_touch_probe = tools.mobile_touch_probe.getTool(robot=ar)
        
        mobile_touch_probe.returnTool()
        
        
        # Testing
        ar.getToolAtCoord.assert_called_with(x, y, z_pickup, z_init=0, speed_xy=None, speed_z=None)
        ar.returnToolToCoord.assert_called_with(x, y, z_pickup, z_init=0, speed_xy=None, speed_z=None)


# ======================================================================================
# stationary_touch_probe class
# ======================================================================================


    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test__stationary_touch_probe__init__(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Arnie's stationary touch probe/nRev. 1.01, 11/27/2019"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.stationary_touch_probe(ar, 'COM3')
        mock_readAll.assert_called()
        self.assertEqual(generic_tool.actual_welcome_message, 
                "Arnie's stationary touch probe/nRev. 1.01, 11/27/2019")
        mock_cartesian.assert_called()
        mock_serialdev.assert_called()
        mock_serialdev.assert_called_with('COM3', 115200, timeout=0.1)


    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')  
    def test_obtainSlotCenter(self, mock_serialdev, mock_readAll, mock_cartesian):        
        mock_readAll.return_value = "Arnie's stationary touch probe/nRev. 1.01, 11/27/2019"
        ar = cartesian.arnie('COM1', 'COM2')
        stp = tools.stationary_touch_probe(ar, 'COM3')
        slot_center = stp.rack.getSavedSlotCenter()
        self.assertGreater(slot_center[0], 80)
        self.assertLess(slot_center[0], 100)
        self.assertGreater(slot_center[1], 50)
        self.assertLess(slot_center[1], 80)
        self.assertGreater(slot_center[2], 500)
        self.assertLess(slot_center[2], 700)

    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')  
    def test_STP_obtainCalibrationPoints(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Arnie's stationary touch probe/nRev. 1.01, 11/27/2019"
        ar = cartesian.arnie('COM1', 'COM2')
        stp = tools.stationary_touch_probe(ar, 'COM3')
        x, y, z, opposite_x, orthogonal_y, raise_height = stp.rack.getSimpleCalibrationPoints()

        
        self.assertGreater(x, 70)
        self.assertLess(x, 100)
        self.assertGreater(y, 60)
        self.assertLess(y, 80)
        self.assertGreater(z, 480)
        self.assertLess(z, 510)
        self.assertGreater(opposite_x, 16+1+1)
        self.assertLess(opposite_x, 30)
        self.assertGreater(orthogonal_y, (16+1)/2.0)
        self.assertLess(orthogonal_y, 110)
        self.assertGreater(raise_height, 1)
        self.assertLess(raise_height, 100)
    

# ======================================================================================
# pipettor class
# ======================================================================================

# TODO: Those functions are probably blocked by homing
# TODO: Mock homing somehow

    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    @mock.patch('tools.pipettor.home')
    def test__pipettor__init__(self, mock_home, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Servo"
        ar = cartesian.arnie('COM1', 'COM2')        
        p1000 = tools.pipettor(robot=ar, com_port_number='COM3', tool_name='p1000_tool')
        mock_readAll.assert_called()
        self.assertEqual(p1000.actual_welcome_message, 
                "Servo")
        mock_cartesian.assert_called()
        mock_serialdev.assert_called()
        mock_serialdev.assert_called_with('COM3', 115200, timeout=0.1)
        mock_home.assert_called()


    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    @mock.patch('tools.pipettor.home')
    def test__pipettor__getTool(self, 
                mock_home, mock_serialdev, mock_readAll, mock_cartesian):
        """
        If coordinates are not matched, then library for some reason
        not loading json file, and using probably slot calibration data instead.
        """
        
        with open('p1000_tool_rack.json', 'r') as f:
            saved_dict = json.loads(f.read())
        x, y, z = saved_dict['position']

        config = configparser.ConfigParser()
        config_path = 'configs/pipette_rack.ini'
        config.read(config_path)            
        z_working_height = float(config['geometry']['z_working_height'])
        z_height = float(config['geometry']['z_box_height'])
        z_pickup = z - z_working_height
        
        # Setting mocks        
        mock_readAll.return_value = "Servo"
        
        # Initializing
        ar = cartesian.arnie('COM1', 'COM2')
        ar.getToolAtCoord = mock.MagicMock()
        serial_device = llc.serial_device('COM3')
        p1000_tool = tools.pipettor.getTool(robot=ar, tool_name='p1000_tool')
        
        # Testing
        ar.getToolAtCoord.assert_called_with(x, y, z_pickup, z_init=0, speed_xy=None, speed_z=None)



# ======================================================================================
# Touch probe functions
# ======================================================================================







if __name__ == '__main__':
    unittest.main()