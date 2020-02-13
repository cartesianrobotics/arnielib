import unittest
import mock
from mock import patch
import low_level_comm

class tool_test_case(unittest.TestCase):
    
    @patch('low_level_comm.serial_device.readAll')
    @patch('low_level_comm.serial.Serial')
    def test__init__(self, mock_serial, mock_readAll):
        mock_readAll.return_value = "Welcome returned from the device"
        dev = low_level_comm.serial_device(port_name='COM1')
        self.assertEqual(dev.port_name, 'COM1')
        dev.readAll.assert_called()
    
    @patch('low_level_comm.serial_device.readAll')
    @patch('low_level_comm.serial.Serial')
    def test__init__2(self, mock_serial, mock_readAll):
        mock_readAll.return_value = 'Message'
        
        dev = low_level_comm.serial_device(port_name='COM1')
        mock_serial.assert_called()
        mock_serial.assert_called_with('COM1', 115200, timeout=0.1)

    @patch('low_level_comm.serial')
    def test__init__3(self, mock_serial):
        
        with patch.object(low_level_comm.serial_device, 'readAll', return_value='Message') as mock_readAll:
            dev = low_level_comm.serial_device(port_name='COM1')
        mock_readAll.assert_called()
        self.assertEqual(dev.actual_welcome_message, 'Message')

    
if __name__ == '__main__':
    unittest.main()