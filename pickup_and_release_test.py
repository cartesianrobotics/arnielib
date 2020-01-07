import cartesian
import logging
import param

logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler(filename='arnietest.log')])
logger = logging.getLogger()

ar = cartesian.arnie('COM4')
ar.home()
[x, y, z] = param.getToolDockingPoint('mobile_probe')
probe = ar.getToolAtCoord(x, y, z, 200)
ar.returnToolToCoord(x, y, z, 200)
ar.close()