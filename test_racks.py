import unittest
import racks
import os
import json

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
        self.assertGreater(z - raise_z, z_cntr - p1000.max_height - p1000.dz_clearance)


    def test_calcWellXY_NotCalibrated(self):
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        x, y = p1000.calcWellXY(0, 0)
        #self.assertAlmostEqual(x, 42.694, 1)
        #self.assertAlmostEqual(y, 254.100, 1)
        x, y = p1000.calcWellXY(11, 7)
        #self.assertAlmostEqual(x, 141.695, 1)
        #self.assertAlmostEqual(y, 317.1, 1)
        self.assertTrue(True)
    
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
        p1000 = racks.rack(rack_name="p1000_1", rack_data={'n_x':0, 'n_y':2, 'type': 'p1000_tips'})
        x1, y1 = p1000.calcWellXY(0, 0)
        x2, y2 = p1000.calcWellXY(11, 7)
        self.assertGreater(x2, x1)
        self.assertGreater(y2, y1)
        self.assertAlmostEqual(x2-x1, 11*8.89, 1)
        self.assertAlmostEqual(y2-y1, 7*8.89, 1)
        
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
        
        
if __name__ == '__main__':
    unittest.main()