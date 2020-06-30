import unittest
import tools
import os
import json
import mock
import cartesian
import low_level_comm as llc
import configparser
import racks
import calibration


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

    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test__getStalagmyteCoord(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.mobile_tool.getToolAtCoord(robot=ar, 
                x=50, y=66, z=450, z_init=0, speed_xy=2000, speed_z=3000, 
                welcome_message='welcome', tool_name='generic_tool')
        
        # A tool only gets stalagmyte coordinates after its calibration procedure.
        # The coordinates are not saved, as every time the tool is picked up, 
        # the coordinates will be slightly different (as this is the point)
        # Calibration function calls tool.setStalagmyteCoord(center_x, center_y, z)
        # at the end.
        generic_tool.setStalagmyteCoord(200, 100, 500)
        x, y, z = generic_tool.getStalagmyteCoord()
        self.assertEqual(x, 200)
        self.assertEqual(y, 100)
        self.assertEqual(z, 500)
        


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
# Mobile gripper tool
# ======================================================================================

    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    def test__mobile_gripper__init__(self, mock_serialdev, mock_readAll, mock_cartesian):
        mock_readAll.return_value = "mobile gripper"
        ar = cartesian.arnie('COM1', 'COM2')        
        gr = tools.mobile_gripper(robot=ar, com_port_number='COM3', tool_name='mobile_gripper')
        mock_readAll.assert_called()
        self.assertEqual(gr.actual_welcome_message, 
                "mobile gripper")
        mock_cartesian.assert_called()
        mock_serialdev.assert_called()
        mock_serialdev.assert_called_with('COM3', 115200, timeout=0.1)

    
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial') 
    @mock.patch('tools.racks.rack')
    def test__mobile_gripper__grabRack__mockRack(self, 
            mock_rack, mock_serialdev, mock_readAll, mock_cartesian):
        # Defining all mock values and parameters for gripper
        mock_readAll.return_value = "mobile gripper"
        ar = cartesian.arnie('COM1', 'COM2')        
        gr = tools.mobile_gripper(robot=ar, com_port_number='COM3', tool_name='mobile_gripper')
        gr.operateGripper = mock.MagicMock()
        gr.getToRackCenter = mock.MagicMock()
        # Mocking rack functions and outputs:
        mock_rack.getGrippingOpenDiam.return_value = 90
        mock_rack.getGrippingHeight.return_value = 550
        mock_rack.getGrippingCloseDiam.return_value = 80
        mock_rack.getHeightBelowGripper.return_value = 20
        
        # Calling function to see if errors appear
        gr.grabRack(mock_rack)
        # Checking gripper instance parameters changed
        self.assertEqual(gr.sample, mock_rack)
        self.assertEqual(gr.gripper_has_something, True)
        self.assertEqual(gr.added_z_length, 20)
        # Testing correctness of the default settings
        param_dict = gr.grabRack(mock_rack, test=True)
        self.assertEqual(param_dict['open_diam'], 90)
        self.assertEqual(param_dict['close_diam'], 80)
        self.assertEqual(param_dict['z_grab'], 550)
        self.assertEqual(param_dict['z_retract'], 550)
        param_dict = gr.grabRack(mock_rack, man_open_diam=95, test=True)
        self.assertEqual(param_dict['open_diam'], 95)
        param_dict = gr.grabRack(mock_rack, man_close_diam=85, test=True)
        self.assertEqual(param_dict['close_diam'], 85)
        param_dict = gr.grabRack(mock_rack, extra_retraction_dz=10, test=True)
        self.assertEqual(param_dict['z_retract'], 540)
        
        
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')
    def test__mobile_gripper__grabRack(self, 
            mock_serialdev, mock_readAll, mock_cartesian):
        # Same as above, but using a real rack object
        
        # Defining all mock values and parameters for gripper
        mock_readAll.return_value = "mobile gripper"
        ar = cartesian.arnie('COM1', 'COM2')        
        gr = tools.mobile_gripper(robot=ar, com_port_number='COM3', tool_name='mobile_gripper')
        gr.operateGripper = mock.MagicMock()
        gr.getToRackCenter = mock.MagicMock()
        
        # Emulating tool calibration
        gr.setStalagmyteCoord(x=210, y=95, z=530)
        
        # Initializing a test rack
        r = racks.stackable(rack_name="p1000_1_test", 
            rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        r.updateCenter(x=100, y=200, z=550, x_btm_touch=90, y_btm_touch=66, z_btm_touch=500)
        #r.z_working_height = 0
        r.setGrippingProperties(open_diam=90, grip_diam=80, z_relative_to_top=10, gripper=gr)
        
        self.assertEqual(gr.getStalagmyteCoord()[2], 530)
        self.assertEqual(r.rack_data['pos_stalagmyte'][2], 500)
        self.assertEqual(r.calcRackCenterFullCalibration(gr)[2], 550-8-500+530)
        self.assertEqual(r.getGrippingHeight(gr), 550-8-500+530+10)
        
        # Calling function to see if errors appear
        param_dict = gr.grabRack(r, test=True)
        # Checking gripper instance parameters changed
        self.assertEqual(gr.sample, r)
        self.assertEqual(gr.gripper_has_something, True)
        self.assertEqual(gr.added_z_length, 86)
        # Testing correctness of the default settings
        self.assertEqual(r.rack_data['position'][2], 550)
        self.assertEqual(r.getCalibratedRackCenter()[2], 550)
        self.assertEqual(r.z_working_height, -8)
        self.assertEqual(gr.getStalagmyteCoord()[2], 530-86)
        self.assertEqual(param_dict['open_diam'], 90)
        self.assertEqual(param_dict['close_diam'], 80)
        self.assertEqual(param_dict['z_grab'], 582)
        self.assertEqual(param_dict['z_retract'], 582-86)

        # Z calculations:
        # z_grab = z_rack_full_calibrated + z_relative_to_top
        # z_relative_to_top = 10
        # z_rack_full_calibrated = z_calibrated_rack_center + z_working_height - tp_stal_z + tool_stal_z
        # z_working_height = -8
        # z_calibrated_rack_center = 550 (used updateCenter function)
        # tp_stal_z = 500 (used updateCenter function)
        # tool_stal_z = 530
        # z_rack_full_calibrated = 550 - 8 - 500 + 530 = 572
        # z_grab = 572 + 10 = 582

    def test__mobile_gripper__placeRack(self):
        
        gripped_rack = racks.stackable(rack_name='RackThatCannotBeNamed', rack_type='test_rack')
        dest_rack = racks.stackable(rack_name='BottomRackThatCannotBeNamed', rack_type='test_rack')
        dest_rack.updateCenter(600, 300, 550, 90, 66, 500)
        dest_rack.overwriteSlot(1, 3)
        
        cartesian.arnie = mock.MagicMock()
        tools.llc.serial_device.readAll = mock.MagicMock()
        tools.llc.serial_device.readAll.return_value = "mobile gripper"
        tools.llc.serial.Serial = mock.MagicMock()

        ar = cartesian.arnie('COM1', 'COM2')
        gr = tools.mobile_gripper(robot=ar, com_port_number='COM3', tool_name='mobile_gripper')
        gr.operateGripper = mock.MagicMock()
        gr.getToRackCenter = mock.MagicMock()
        gr.setStalagmyteCoord(x=210, y=95, z=430)
        gripped_rack.setGrippingProperties(90, 80, 10, gripper=gr)
        dest_rack.setGrippingProperties(90, 80, 10, gripper=gr)
        
        gr.sample = gripped_rack
        
        placed_rack_object, param_dict = gr.placeRack(dest_rack, test=True)
        
        self.assertEqual(gr.getStalagmyteCoord()[2], 430)
        self.assertEqual(dest_rack.calcRackCenterFullCalibration(tool=gr), 
                         (600+210-90, 300+95-66, 550+430-500))
        self.assertEqual(gripped_rack, placed_rack_object)
        self.assertEqual(param_dict['destination_coord'][0], 600+210-90)
        self.assertEqual(param_dict['destination_coord'][1], 300+95-66)
        self.assertEqual(param_dict['destination_coord'][2], 550+430-500)
        self.assertEqual(param_dict['rack_heigth'], 100)
        self.assertEqual(param_dict['z_final_absolute'], 480)
        self.assertEqual(param_dict['open_diam'], 90)
        
        
    
    def test__plate_gripper__grabAndPlaceStackable(self):
        cartesian.arnie = mock.MagicMock()
        tools.llc.serial_device.readAll = mock.MagicMock()
        tools.llc.serial_device.readAll.return_value = "mobile gripper"
        tools.llc.serial.Serial = mock.MagicMock()
        
        ar = cartesian.arnie('COM1', 'COM2')
        gr = tools.mobile_gripper(robot=ar, com_port_number='COM3', tool_name='mobile_gripper')
        gr.operateGripper = mock.MagicMock()
        gr.getToRackCenter = mock.MagicMock()
        
        s1 = racks.stackable(rack_name='RackThatCannotBeNamed-1', rack_type='test_rack')
        s1.overwriteSlot(1, 3)
        s2 = racks.stackable(rack_name='RackThatCannotBeNamed-2', rack_type='test_rack')
        s3 = racks.stackable(rack_name='RackThatCannotBeNamed-3', rack_type='test_rack')
        s3.overwriteSlot(2, 4)
        
        s1.rack_data['position'] = [400, 200, 500]
        s1.rack_data['pos_stalagmyte'] = [200, 100, 400]
        s3.rack_data['position'] = [800, 330, 300]
        s3.rack_data['pos_stalagmyte'] = [200, 100, 400]
        gr.setStalagmyteCoord(x=210, y=95, z=530)
        s2.max_height = 100
        s2.setGrippingProperties(90, 80, 10, gripper=gr)
        
        s1.placeItemOnTop(s2)
        
        self.assertEqual(s2.getCalibratedRackCenter(), (400, 200, 400))
        self.assertEqual(s2.rack_data['pos_stalagmyte'], [200, 100, 400])
        self.assertEqual(s2.getStalagmyteCalibration(), (200, 100, 400))
        self.assertEqual(s2.rack_data['n_x'], 1)
        self.assertEqual(s2.rack_data['n_y'], 3)
        
        param_dict = gr.grabRack(s2, test=True)
        
        # Bottom rack shall now has no top rack:
        self.assertEqual(s1.getTopItem(), None)
        # Rack is in the gripper
        self.assertEqual(gr.sample, s2)
        self.assertEqual(gr.gripper_has_something, True)
        self.assertEqual(gr.added_z_length, 90)
        # Grabbing parameters
        self.assertEqual(param_dict['z_grab'], 400-0-400+530+10)
        
        # Placing to the new rack
        placed_rack_object, param_dict = gr.placeRack(s3, test=True)
        # Checking that gripper has nothing left
        self.assertEqual(gr.sample, None)
        self.assertEqual(gr.gripper_has_something, False)
        self.assertEqual(gr.added_z_length, 0)
        # Updated rack parameters:
        self.assertEqual(s2.getCalibratedRackCenter(), (800, 330, 200))
        self.assertEqual(s2.getStalagmyteCalibration(), (200, 100, 400))
        self.assertEqual(s3.getTopItem(), s2)
        self.assertEqual(s2.bottom_item, s3)
        self.assertEqual(s2.rack_data['n_x'], 2)
        self.assertEqual(s2.rack_data['n_y'], 4)

    
    def test__plate_gripper__test__plate_gripper__grabAndPlaceStackable_SameSpot(self):
        cartesian.arnie = mock.MagicMock()
        tools.llc.serial_device.readAll = mock.MagicMock()
        tools.llc.serial_device.readAll.return_value = "mobile gripper"
        tools.llc.serial.Serial = mock.MagicMock()
        
        ar = cartesian.arnie('COM1', 'COM2')
        gr = tools.mobile_gripper(robot=ar, com_port_number='COM3', tool_name='mobile_gripper')
        gr.operateGripper = mock.MagicMock()
        gr.getToRackCenter = mock.MagicMock()
        
        s1 = racks.stackable(rack_name='RackThatCannotBeNamed-1', rack_type='test_rack')
        s1.overwriteSlot(1, 3)
        s2 = racks.stackable(rack_name='RackThatCannotBeNamed-2', rack_type='test_rack')
        
        s1.rack_data['position'] = [400, 200, 500]
        s1.rack_data['pos_stalagmyte'] = [200, 100, 400]
        gr.setStalagmyteCoord(x=210, y=95, z=530)
        s2.max_height = 100
        s2.setGrippingProperties(90, 80, 10, gripper=gr)
        
        s1.placeItemOnTop(s2)
        gr.grabRack(s2)
        
        gr.robot.move.assert_has_calls([mock.call(z=400-400+530+10)])
        
        gr.placeRack(s1)
        
        gr.robot.move.assert_has_calls([mock.call(z=400-400+530+10)])


    def test__plate_gripper__grabRack__open_close_diameters(self):
        cartesian.arnie = mock.MagicMock()
        tools.llc.serial_device.readAll = mock.MagicMock()
        tools.llc.serial_device.readAll.return_value = "mobile gripper"
        tools.llc.serial.Serial = mock.MagicMock()
        
        ar = cartesian.arnie('COM1', 'COM2')
        gr = tools.mobile_gripper(robot=ar, com_port_number='COM3', tool_name='mobile_gripper')
        gr.operateGripper = mock.MagicMock()
        gr.getToRackCenter = mock.MagicMock()
        gr.setStalagmyteCoord(x=210, y=95, z=530)
        
        gr.toDiameter = mock.MagicMock()

        s1 = racks.stackable(rack_name='RackThatCannotBeNamed-1', rack_type='test_rack')
        s1.rack_data['position'] = [400, 200, 500]
        s1.rack_data['pos_stalagmyte'] = [200, 100, 400]
        s1.setGrippingProperties(90, 80, 10, gripper=gr)
        
        gr.grabRack(s1)
        
        gr.toDiameter.assert_has_calls([mock.call(diameter=90, powerdown=False), 
                                        mock.call(diameter=80, powerdown=False)])
        

        

# ======================================================================================
# Touch probe functions
# ======================================================================================


    def test__findWall__step_back_length_used(self):
        tools.touch_probe = mock.MagicMock()
        tools.approachUntilTouch = mock.MagicMock()
        tp = tools.touch_probe()
        tp.robot.axisToCoordinates.return_value = [90, 0, 0]
        tp.step_dict = {
                0: {'step_fwd': 3, 'speed_xy_fwd': 1000, 'speed_z_fwd':2000,
                    'step_back': 3, 'speed_xy_back': 1000, 'speed_z_back':2000},
                1: {'step_fwd': 0.2, 'speed_xy_fwd': 200, 'speed_z_fwd':1000,
                    'step_back': 1, 'speed_xy_back': 500, 'speed_z_back':1000},
                2: {'step_fwd': 0.05, 'speed_xy_fwd': 25, 'speed_z_fwd':500,
                    'step_back': 0.2, 'speed_xy_back': 50, 'speed_z_back':500},
            }
        
        tools.findWall(probe=tp, axis='x', direction=1)
        tp.robot.axisToCoordinates.assert_called_with(axis='x', value=-3)
        tools.findWall(probe=tp, axis='x', direction=1, step_back_length=-3)
        tp.robot.axisToCoordinates.assert_called_with(axis='x', value=3)
        

    @mock.patch('tools.llc')
    def test__touch_probe__findWall__step_back_length_used(self, mock_llc):
        cartesian.arnie = mock.MagicMock()
        
        ar = cartesian.arnie()
        ar.axisToCoordinates.return_value = [90, 0, 0]
        
        tp = tools.stationary_touch_probe(robot=ar)
        tp.step_dict = {
                0: {'step_fwd': 3, 'speed_xy_fwd': 1000, 'speed_z_fwd':2000,
                    'step_back': 3, 'speed_xy_back': 1000, 'speed_z_back':2000},
                1: {'step_fwd': 0.2, 'speed_xy_fwd': 200, 'speed_z_fwd':1000,
                    'step_back': 1, 'speed_xy_back': 500, 'speed_z_back':1000},
                2: {'step_fwd': 0.05, 'speed_xy_fwd': 25, 'speed_z_fwd':500,
                    'step_back': 0.2, 'speed_xy_back': 50, 'speed_z_back':500},
            }
        
        tp.findWall(axis='x', direction=1)
        tp.robot.axisToCoordinates.assert_called_with(axis='x', value=-3)
        tp.findWall(axis='x', direction=1, step_back_length=-3)
        tp.robot.axisToCoordinates.assert_called_with(axis='x', value=3)


if __name__ == '__main__':
    unittest.main()