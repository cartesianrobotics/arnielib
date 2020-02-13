import unittest
import tools
import os
import json
import mock
import cartesian

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
    
    
    @mock.patch('builtins.open')
    @mock.patch('tools.json.loads')
    @mock.patch('cartesian.arnie')
    @mock.patch('tools.llc.serial_device.readAll')
    @mock.patch('tools.llc.serial.Serial')   
    def test_openFileWithToolParameters(self, 
            mock_serialdev, mock_readAll, mock_cartesian, mock_json_loads, mock_open):
        
        mock_json_loads.return_value = {'a': 'b'}
        mock_readAll.return_value = "Welcome returned from the device"
        ar = cartesian.arnie('COM1', 'COM2')
        generic_tool = tools.tool(ar, 'COM3', tool_name='generic_tool', welcome_message='welcome')
        result_data_dict = generic_tool.openFileWithToolParameters('somepath.json')
        
        mock_open.assert_called_with('somepath.json', 'r')
        #self.assertEqual(result_data_dict, {'a': 'b'})


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

if __name__ == '__main__':
    unittest.main()