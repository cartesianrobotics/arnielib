"""
TODO:
1. Make commands interruptable.
2. Make a function for specifying tools. 
3. Save tools in a file. 
4. Make a function for swapping tools. 
7. Make better serialization.
8. Turn on the probe when connecting.
9. Automatic unstucking for the stalactite.
"""
	
import serial
import time
import math
import json
import re
import os 
from copy import deepcopy
from datetime import datetime
from shutil import copyfile

import sys
import glob

robots = []

safe_height = 5900

uninitialized_slot = {
	"LT": [-1, -1], 
	"LB": [-1, -1], 
	"RT": [-1, -1], 
	"RB": [-1, -1], 
	"floor_z": -1
}

def log(text):
	log_file = open("log.txt", "a")
	log_file.write(text)
	log_file.write("\n")
	log_file.close()

def message_log(port, text, read_or_write):
	log_file = open("message_log.txt", "a")
	log_file.write(port + " " + read_or_write + " " + text)
	log_file.write("\n")
	log_file.close()
	
def log_value(name, value, axis):
	log(name + ' ' + axis + ' ' + str(value))

def axis_index(axis):
	result = axis.upper()
	axes = ["X", "Y", "Z"]
	if result not in axes:
		print("ERROR: wrond axis provided: " + axis)
		return -1
	else:
		result = axes.index(result)
		return result

def serial_ports():
	""" Lists serial port names

		:raises EnvironmentError:
			On unsupported or unknown platforms
		:returns:
			A list of the serial ports available on the system
	"""
	if sys.platform.startswith('win'):
		ports = ['COM%s' % (i + 1) for i in range(256)]
	elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
		# this excludes your current terminal "/dev/tty"
		ports = glob.glob('/dev/tty[A-Za-z]*')
	elif sys.platform.startswith('darwin'):
		ports = glob.glob('/dev/tty.*')
	else:
		raise EnvironmentError('Unsupported platform')

	result = []
	for port in ports:
		try:
			s = serial.Serial(port)
			s.close()
			result.append(port)
		except (OSError, serial.SerialException):
			pass
	return result
	
class serial_device():
	"""
	Parent class, handling basic communication with a device, 
	be it an Arnie robot, or a tool or something else
	"""
	
	def __init__(self, port_name, baudrate=115200, timeout=0.1, eol="\r"):
		
		"""
		Initializes a devise to communicate through the serial port
		(which is now most likely a USB emulation of a serial port)
		
		Inputs:
			port_name 
				The name of the port through which a robot or a tool is going to communicate.
			baudrate
				Speed of communication. For USB 115200 is good. Lower if communication becomes bad.
			timeout
				How long to wait (in seconds) for a device to respond before returning an error
				0.1 seconds is default.
			eol
				character to pass at the end of a line when sending something to the device.
				Default is '\r'
		"""
		
		self.eol=eol
		self.recent_message = ""

		self.openSerialPort(port_name, baudrate, timeout)
	
	
	def openSerialPort(self, port_name="", baudrate=115200, timeout=0.1):
		"""
		Opens serial port
		"""
		# Trying to use specifically provided port_name
		# Otherwise using whatever internal number instance may already have.
		if port_name != "":
			com_port = port_name
			self.port_name = port_name
		else:
			com_port = self.port_name
		# Make sure port is closed
		self.close()
		# Opening robot instance
		self.port = serial.Serial(com_port, baudrate, timeout=timeout)
		# Cleaning input buffer from hello message
		self.port.flushInput()
		
		while True:
			msg = self.readAll()
			if msg != "":
				print("Msg: " + msg)
				break
				
		self.recent_message = msg
		
	def close(self):
		"""
		Will try to close Arnie port if it is open
		"""
		if self in robots:
			robots.remove(self)
		
		try:
			self.port.close()
		except:
			pass
		
	def write(self, expression, eol=None):
		"""
		Sending an expression to a device. Expression is in str format.
		Proper end of line will be sent. If eol specified here, it will be sent
		Otherwise the one specified during initialization will be sent.
		"""
		# Cleaning input buffer (so the buffer will contain only response of a device 
		# to the command send within this function)
		self.port.flushInput()
		# Strip all EOL characters for consistency
		expression = expression.strip()
		if eol:
			eol_to_send = eol
		else:
			eol_to_send = self.eol
		# Add end of line
		expression = expression + eol_to_send
		# Encode to binary
		expr_enc = expression.encode()
		
		message_log(self.port_name, expression, "write")
		# Writing to robot
		self.port.write(expr_enc)
		
		
	# TODO: Inline this function so that people don't circumvent logging by using this function. 
	def read(self, number_of_bytes=1):
		"""
		Same functionality as Serial.read()
		"""
		return self.port.read(number_of_bytes).decode("utf-8")
	
	def readAll(self, timeout=0.1):
		"""
		Function will wait until everything that the device send is read
		"""
		# Give time for device to respond
		time.sleep(timeout)
		# Wait forever for device to return something
		message=self.read()
		#message=''
		# Continue reading until device output buffer is empty
		while self.port.inWaiting():
			message += self.read()
		
		message_log(self.port_name, message, "read")
		return message

	def writeAndWait(self, expression, eol=None, confirm_message='ok\n'):
		"""
		Function will write an expression to the device and wait for the proper response.
		
		Use this function to make the devise perform a physical operation and
		make sure program continues after the operation is physically completed.
		
		Function will return an output message
		"""
		
		self.idle = False
		self.write(expression, eol)
		
		full_message = ""
		while True:
			message = self.readAll()
			if message != "":
				print("MESSAGE: " + repr(message))
				full_message += message
				if re.search(pattern="ok\n", string=full_message):
					self.recent_message = full_message
					break

class tool(serial_device):
	def promote(self, position):
		
		"""
		To initialize, provide position_tuple in the form (x, y, z). 
		Those are coordinates at which the tool can be found on a base
		
		To establish connection with a tool, call openSerialPort()
		
		To send a command, use write()
		
		To read all buffer, use readAll()
		"""
		self.type = "none"
		self.position = position
		
class mobile_touch_probe(tool):
	def promote(self):
		self.type = "mobile_probe"
	
	def isTouched(self):
		self.write('d')
		response = self.readAll()
		print("Mobile touch probe response: " + response)
		return bool(int(re.split(pattern='/r/n', string=response)[0]))
	
class stationary_touch_probe(tool):
	def promote(self):
		self.type = "stationary_probe"
	
	def isTouched(self):
		self.write('d')
		response = self.readAll()
		print("Stationary touch probe response: " + response)
		return bool(int(re.split(pattern='/r/n', string=response)[0]))
		
GenCenter = lambda xmin, xmax: xmin + (xmax - xmin)/2.0
GenCenterXYZ = lambda xmin, xmax, ymin, ymax, zmin, zmax: (
	GenCenter(xmin, xmax), 
	GenCenter(ymin, ymax),
	GenCenter(zmin, zmax),
)
		
class arnie(serial_device):
	def promote(self, speed_x=15000, speed_y=15000, speed_z=15000):
		self.calibrated = False
		self.speed = [speed_x, speed_y, speed_z]
		self.slot_tools = []
		
	def home(self, axes='ZXY'):
		"""
		Home one of the axes, X, Y or Z.
		Axis 
			axis to home
				x - home X axis
				y - home Y axis
				z - home Z axis
		"""
		for axis in axes:
			axis = axis.upper()
			if axis != 'X' and axis != 'Y' and axis != 'Z' and axis != 'XYZ':
				print ('Wrong axis specified. Please specify x, y or z. You specified: '+axis)
			else:
				self.writeAndWait('G28 '+axis)
	
	
	def moveAxis(self, axis, destination, speed=None):
		if destination == 0:
			return 
		
		axis=axis.upper()
		if speed == None:
			speed = self.speed[axis_index(axis)]
		speed_cmd = 'F' + str(speed)
		full_cmd = 'G0 ' + axis + str(destination) + ' ' + speed_cmd
		
		try:
			self.writeAndWait(full_cmd)
		except:
			pass
		return 
		
		# This was a failed attempt to make commands interruptable.
		if axis == "X":
			coordinate_i = 0
		elif axis == "Y":
			coordinate_i = 1
		elif axis == "Z":
			coordinate_i = 2
		else:
			print("ERROR: Unknown axis.")
			return
		
		pos = self.getPosition()
		if pos[coordinate_i] == destination:
			return
		elif destination > pos[coordinate_i]:
			direction = 1
		else:
			direction = -1
			
		distance = abs(pos[coordinate_i] - destination)
		next_step = pos[coordinate_i]
		
		while distance > 0:
			next_step += direction
			distance -= 1
			cmd = 'G0 ' + axis + str(next_step) + ' ' + speed_cmd			
			self.writeAndWait(cmd)

		
	def moveXY(self, x, y, speed=None):
		if speed == None:
			speed = self.speed[axis_index("X")]
		full_cmd = 'G0 X' + str(x) + ' Y' + str(y) + ' F' + str(speed)
		try:
			self.writeAndWait(full_cmd)
		except:
			pass
	
	
	def move(self, x=0, y=0, z=0, z_first=True, speed_xy=None, speed_z=None):
		"""
		Move robot to an absolute coordinates.
		
		Spefify z_first = True if you want Z to move first; otherwise x an y will move first.
		"""
		if speed_xy == None:
			speed_xy = self.speed[axis_index("X")]
		if speed_z == None:
			speed_z = self.speed[axis_index("Z")]
		
		# Each of the functions attempting to move an axis to the coordinate. 
		# If something goes wrong, like coordinate not specified, command is ignored
		# and the next one is attempted.
		if z_first:
			self.moveAxis('Z', z, speed_z)
			self.moveAxis('X', x, speed_xy)
			self.moveAxis('Y', y, speed_xy)
		else:
			self.moveAxis('X', x, speed_xy)
			self.moveAxis('Y', y, speed_xy)
			self.moveAxis('Z', z, speed_z)
	
	def moveDelta(self, dx=None, dy=None, dz=None, z_first=True, speed_xy=None, speed_z=None):
		"""
		Moves the robot arbitrarily to the current position
		"""
		# Getting current absolute position
		x, y, z = self.getPosition()
		
		# Assigning zero movement to coordinates which are not provided
		if dx is None:
			dx = 0
		if dy is None:
			dy = 0
		if dz is None:
			dz = 0
			
		# Calculating new absolute position for Arnie
		new_x = x + dx
		new_y = y + dy
		new_z = z + dz
		
		# Moving Arnie
		self.move(new_x, new_y, new_z, z_first=z_first, speed_xy=speed_xy, speed_z=speed_z)
	
	def openTool(self):
		"""Docker opens to accept a tool"""
		self.write('M280 P1 S10')
		time.sleep(1.5)
		
	def closeTool(self):
		"""Docker closes, fixing a tool in place"""
		self.write('M280 P1 S80')
		time.sleep(1.5)
	
	def getPosition(self):
		# TODO: Fix this.
		self.writeAndWait("M114")
		msg = self.recent_message
		msg_list = re.split(pattern=' ', string=msg)
		x_str = msg_list[0]
		y_str = msg_list[1]
		z_str = msg_list[2]
		#print (x_str, y_str, z_str)
		x = float(re.split(pattern="\:", string=x_str)[1])
		y = float(re.split(pattern="\:", string=y_str)[1])
		z = float(re.split(pattern="\:", string=z_str)[1])
		return x, y, z
	
		
	def approachToolPosition(self, x, y, z, speed_xy=None, speed_z=None):
		"""
		Moves robot to specified coordinates, where the tool is expected to be.
		Alternatively, moves robot WITH a tool to its empty slot
		Coordinates for both operations should be the same.
		Thif function will not engage docker, as one need to make sure the tool is at the right position
		"""
		
		self.move(x, y, z, z_first=False, speed_xy=speed_xy, speed_z=speed_z)
	
	def approachToolAtSlot(self, tool_at_slot, speed_xy=None, speed_z=None):
		"""
		Moves robot towards the tool, which object is passed in "tool_at_slot". 
		Same as "approachToolPosition", but using the object of tool_at_slot class
		"""
		x, y, z = tool_at_slot.getCenterCoordinates()
		self.move(x, y, z, z_first=False, speed_xy=speed_xy, speed_z=speed_z)
	
	
	def get_tool(self, tool, speed_xy=None, speed_z=None):
		"""
		Engages with a tool, using tool instance for guidance
		"""
		# Make sure docker is open
		self.openTool()
		x, y, z = tool.getToolCoordinates()
		self.approachToolPosition(x, y, z)
		
		# Attempting to initialize the tool
		attempt_successful = self.softInitToolAttempt(tool, total_attempts=2)
		if not attempt_successful:
			attempt_successful = self.hardInitToolAttempt(tool, total_attempts=3)
		if attempt_successful:
			# Locking tool
			self.closeTool()
			# Moving back up
			self.move(z=0, speed_z=speed_z)
		else:
			self.openTool()
			print("Failed to pickup tool. Program stopped.")
			
	
	def return_tool(self, tool):
		"""
		Returns tool back on its place.
		The place is provided either with tool instance, or simply as position_tuple (x, y, z)
		"""
		dest = tool.position
		self.home("Z")
		self.move(x=dest[0], y=dest[1])
		self.move(z=dest[2])
		self.openTool()
		self.home("Z")
		

	def softInitToolAttempt(self, tool, total_attempts=4, wait_time=2, current_attempt=0):
		# Attempt to initialize tool several times without robot movement
		# Waiting before attempt, so electronics has time to connect
		time.sleep(wait_time)
		try:
			tool.openSerialPort()
			attempt_successful=1
		except:
			print("Tool initialization failed, attempting again")
			if total_attempts > current_attempt:
				attempt_successful=0
				current_attempt += 1
				attempt_successful = self.softInitToolAttempt(
					tool=tool,
					total_attempts=total_attempts, 
					wait_time=wait_time, 
					current_attempt=current_attempt)
			else:
				attempt_successful = 0
				print('Tool initialization failed after '+str(current_attempt)+' attempts')
		return attempt_successful
	
	
	def hardInitToolAttempt(self, tool, total_attempts=3, current_attempt=0):
		# Attempt to re-connect to the tool. 
		# To be used after failed initialization
		self.openTool()
		# Moving Arnie up and down for an attempt to physically reconnect
		self.moveDelta(dz=-300)
		self.moveDelta(dz=300)
		
		attempt_successful = self.softInitToolAttempt(tool, total_attempts=1)
		if not attempt_successful and total_attempts > current_attempt:
			current_attempt += 1
			attempt_successful = 0
			attempt_successful = self.hardInitToolAttempt(
				tool=tool, total_attempts=total_attempts, current_attempt=current_attempt)
		elif not attempt_successful and total_attempts <= current_attempt:
			print("Repeated tool pickup failed after "+str(current_attempt)+" attempts")
			attempt_successful = 0
		return attempt_successful

def move_delta_mm(robot, dx=0, dy=0, dz=0):
	if abs(dx) > 0.001 and robot.params["units_in_mm"][0] == -1:
		print("ERROR: X axis units are not calibrated.")
		return
	if abs(dy) > 0.001 and robot.params["units_in_mm"][1] == -1:
		print("ERROR: Y axis units are not calibrated.")
		return
	if abs(dz) > 0.001 and robot.params["units_in_mm"][2] == -1:
		print("ERROR: Z axis units are not calibrated.")
		return
		
	robot.moveDelta(dx=dx * robot.params["units_in_mm"][0], dy=dy * robot.params["units_in_mm"][1], dz=dz * robot.params["units_in_mm"][2])

def find_wall(robot, axis, direction, name="unknown"):
	# direction should be either 1 or -1
	if direction != 1 and direction != -1:
		print("ERROR: invalid direction.")
		print(direction)
		return
	
	if axis == "Z": 
		approach_step_1 = 45.0 # CONSTANT
		approach_step_2 = 5.0
	else:
		approach_step_1 = 10.0 # CONSTANT
		approach_step_2 = 3.0
	
	
	ApproachUntilTouch(robot, robot.current_tool, axis, direction * approach_step_1) # CONSTANT
	retract_until_no_touch(robot, robot.current_tool, axis, -direction * approach_step_2) # CONSTANT
	wall_coord = ApproachUntilTouch(robot, robot.current_tool, axis, direction * 0.5) # CONSTANT
	result = wall_coord[axis_index(axis)]
	step_back = [0, 0, 0]
	if axis == "Z": 
		step_back_length = 30 # CONSTANT
	else:
		step_back_length = 5 # CONSTANT
	step_back[axis_index(axis)] = -direction * step_back_length
	robot.moveDelta(dx=step_back[0], dy=step_back[1], dz=step_back[2])
	log_value(name, result, axis)
	return result

# This function is for testing calibration precision. The probe should touch the screw.
def touch_left_top(robot, n_x, n_y):
	if not robot.calibrated:
		print("ERROR: The robot is not calibrated.")
		return
	target = robot.params['slots'][n_x][n_y]['LT']
	robot.move(z=safe_height)
	robot.move(x=target[0], y=target[1])
	find_wall(robot, "Z", 1, "left_top_screw_" + str(n_x) + "_" + str(n_y))
	robot.move(z=safe_height)

def calibrate_stationary_probe_rack(robot, x_n, y_n):
	center_xy = calc_slot_center(robot, x_n, y_n)
	floor_z = robot.params["slots"][x_n][y_n]["floor_z"]
	center_z = floor_z - 105 * robot.params["units_in_mm"][2]
	rack_circle = calibrate_circle(robot, [center_xy[0], center_xy[1], center_z])
	robot.current_tool.position[0] = rack_circle[0]
	robot.current_tool.position[1] = rack_circle[1]
	length_screw_mm = 35 
	robot.current_tool.position[2] = floor_z - (60 - length_screw_mm) * robot.params["units_in_mm"][2]
	
def check_floor_calibration(robot):
	w_n = robot.params["width_n"]
	h_n = robot.params["height_n"]
	
	for col_i in range(w_n):
		for row_i in range(h_n):
			goto_slot_lt(robot, col_i, row_i)
			goto_slot_lb(robot, col_i, row_i)
			goto_slot_rb(robot, col_i, row_i)
			goto_slot_rt(robot, col_i, row_i)

def calibrate_circle(robot, approx_center):
	robot.move(z=approx_center[2] - 100)
	robot.move(x=approx_center[0], y=approx_center[1])
	robot.move(z=approx_center[2])

	x_pos = find_wall(robot, "X", 1, "calibrate_circle-x_pos")
	x_neg = find_wall(robot, "X", -1, "calibrate_circle-x_neg")
	
	center_x = (x_pos + x_neg) / 2
	robot.move(x=center_x)
	
	y_pos = find_wall(robot, "Y", 1, "calibrate_circle-y_pos")
	y_neg = find_wall(robot, "Y", -1, "calibrate_circle-y_neg")
	
	radius_1 = (y_pos - y_neg) / 2
	center_y = (y_pos + y_neg) / 2
	robot.move(y=center_y)
	
	
	x_pos = find_wall(robot, "X", 1, "calibrate_circle-x_pos2")
	x_neg = find_wall(robot, "X", -1, "calibrate_circle-x_neg2")
	radius_2 = (x_pos - x_neg) / 2
	
	radius = (radius_1 + radius_2) / 2
	
	return center_x, center_y, radius

def calibrate_slot(robot, n_x, n_y):
	calibration_start_time = time.time()

	approx_const = 0.9

	robot.move(z=safe_height)
	go_to_slot_center_calibration(robot, n_x, n_y)
	z_max = find_wall(robot, "Z", 1, "calibrate_slot-center" + str(n_x) + "_" + str(n_y))
	robot.move(z=z_max - 30)
	
	inner_slot_w = robot.params['slot_width'] - robot.params['plank_width']
	inner_slot_h = robot.params['slot_height'] - robot.params['flower_height']
	
	current_slot = deepcopy(uninitialized_slot)	
	current_slot["floor_z"] = z_max
	
	robot.moveDelta(dx= -inner_slot_w * approx_const / 2, dy= -inner_slot_h * approx_const / 2)
	current_slot['LT'][0] = find_wall(robot, "X", -1, "calibrate_slot-LT" + str(n_x) + "_" + str(n_y)) - robot.params['plank_width'] / 2
	current_slot['LT'][1] = find_wall(robot, "Y", -1, "calibrate_slot-LT" + str(n_x) + "_" + str(n_y)) - robot.params['flower_height'] / 2
	
	robot.moveDelta(dy= inner_slot_h * approx_const)
	current_slot['LB'][0] = find_wall(robot, "X", -1, "calibrate_slot-LB" + str(n_x) + "_" + str(n_y)) - robot.params['plank_width'] / 2
	current_slot['LB'][1] = find_wall(robot, "Y", 1, "calibrate_slot-LB" + str(n_x) + "_" + str(n_y)) + robot.params['flower_height'] / 2
	
	robot.moveDelta(dx= inner_slot_w * approx_const)
	current_slot['RT'][0] = find_wall(robot, "X", 1, "calibrate_slot-RT" + str(n_x) + "_" + str(n_y)) + robot.params['plank_width'] / 2
	current_slot['RT'][1] = find_wall(robot, "Y", 1, "calibrate_slot-RT" + str(n_x) + "_" + str(n_y)) - robot.params['flower_height'] / 2
	
	robot.moveDelta(dy= -inner_slot_h * approx_const)
	current_slot['RB'][0] = find_wall(robot, "X", 1, "calibrate_slot-RB" + str(n_x) + "_" + str(n_y)) + robot.params['plank_width'] / 2
	current_slot['RB'][1] = find_wall(robot, "Y", -1, "calibrate_slot-RB" + str(n_x) + "_" + str(n_y)) + robot.params['flower_height'] / 2
	
	robot.move(z=safe_height)
	
	robot.params['slots'][n_x][n_y] = current_slot
	
	calibration_end_time = time.time()
	print("Slot calibration time: ")
	print(calibration_end_time - calibration_start_time)

def calc_slot_center(robot, n_x, n_y):
	slot = robot.params["slots"][n_x][n_y]
	return [(slot['LT'][0] + slot['RB'][0]) / 2, (slot['LT'][1] + slot['RB'][1]) / 2]

def goto_slot_center(robot, n_x, n_y):
	slot = robot.params["slots"][n_x][n_y]
	center = [(slot['LT'][0] + slot['RB'][0]) / 2, (slot['LT'][1] + slot['RB'][1]) / 2]
	robot.move(x = center[0], y = center[1])

def goto_slot_lt(robot, n_x, n_y):
	slot = robot.params["slots"][n_x][n_y]
	robot.move(x = slot['LT'][0], y = slot['LT'][1])
	
def goto_slot_lb(robot, n_x, n_y):
	slot = robot.params["slots"][n_x][n_y]
	robot.move(x = slot['LB'][0], y = slot['LB'][1])
	
def goto_slot_rt(robot, n_x, n_y):
	slot = robot.params["slots"][n_x][n_y]
	robot.move(x = slot['RT'][0], y = slot['RT'][1])
	
def goto_slot_rb(robot, n_x, n_y):
	slot = robot.params["slots"][n_x][n_y]
	robot.move(x = slot['RB'][0], y = slot['RB'][1])
	
def ziggurat_calibration(robot):
	if not robot.calibrated:
		print("ERROR: The robot is not calibrated. Use calibrate(robot) first.")
		return
	
	def find_next_step(axis, expected_width):
		initial_wall = find_wall(robot, axis, 1, "ziggurat_calibration-find_next_step")
		while True:
			# TODO: Make a rough approimaion of units in mm by z axis and express this 60 in 10 mm times that.
			robot.moveDelta(dz=-60)
			next_wall = find_wall(robot, axis, 1, "ziggurat_calibration-find_next_step")
			if next_wall - initial_wall > expected_width * 0.8:
				return next_wall
	
	n_steps = 3
	dxs = []
	dys = []
	dzs = []
	
	robot.move(z=5400)
	goto_slot_lt(robot, 0, 3)
	robot.move(z=safe_height)
	robot.moveDelta(dy=robot.params['slot_height'] / 2)
	
	old_x = find_wall(robot, "X", 1, "ziggurat_calibration-x1")
	old_z = find_wall(robot, "Z", 1, "ziggurat_calibration-z11")
	
	for step_i in range(n_steps):
		new_x = find_next_step("X", 10 * robot.params['units_in_mm'][0])
		new_z = find_wall(robot, "Z", 1, "ziggurat_calibration-z" + str(step_i) + "1")
		if step_i == n_steps - 1:
			dxs.append((new_x - old_x) / 2)
		else: 
			dxs.append(new_x - old_x)
		dzs.append(old_z - new_z)
		old_x = new_x
		old_z = new_z
	
	robot.move(z=5400)
	goto_slot_lt(robot, 0, 3)
	robot.move(z=safe_height)
	robot.moveDelta(dx=robot.params['slot_width'] / 2)
	
	old_y = find_wall(robot, "Y", 1, "ziggurat_calibration-y1")
	old_z = find_wall(robot, "Z", 1, "ziggurat_calibration-z12")
	
	for step_i in range(n_steps):
		new_y = find_next_step("Y", 10 * robot.params['units_in_mm'][0])
		new_z = find_wall(robot, "Z", 1, "ziggurat_calibration-z" + str(step_i) + "2")
		dys.append(new_y - old_y)
		dzs.append(old_z - new_z)
		old_y = new_y
		old_z = new_z
	
	robot.params['units_in_mm'][0] = sum(dxs) / len(dxs) / 10
	robot.params['units_in_mm'][1] = sum(dys) / len(dys) / 10
	robot.params['units_in_mm'][2] = sum(dzs) / len(dzs) / 10

	print(robot.params['units_in_mm'])
	print(dxs)
	print(dys)
	print(dzs)

def update_floor(robot):
	if os.path.exists("floor.json"):
		time_str = str(datetime.now()).replace(":", "_")
		copyfile("floor.json", time_str + "floor.json")
	file = open('floor.json', 'w')
	file.write(json.dumps(robot.params))
	file.close()

def calibrate(robot):
	calibration_start_time = time.time()
	
	slot_width_mm = 150
	slot_height_mm = 110
	
	expected_slot_width = 278
	expected_slot_height = 172
	approx_const = 0.9
	
	n_slots_width = 6
	n_slots_height = 4
	robot.params = {
		'width_n': n_slots_width,
		'height_n': n_slots_height,
		'slots': [[0 for j in range(n_slots_height)] for i in range(n_slots_width)],
		'slot_width': -1,
		'slot_height': -1,
		'plank_width': -1,
		'flower_height': -1,
		'units_in_mm': [-1.0, -1.0, -1.0]
	}

	robot.home()
	robot.min = robot.getPosition()
	robot.max = [0, 0, 0]
	
	if robot.current_tool.type == "none": 
		ports = serial_ports()
		if len(ports) == 0:
			print("ERROR: No tool connected.")
			return
		
		robot.current_tool = touch_probe([0, 0, 0], ports[0])
		robot.current_tool.openSerialPort()
		# TODO: Make sure it's a probe.
	
	robot.move(z=5900)
	robot.max[2] = find_wall(robot, "Z", 1, "calibrate-0-0-floor")
	
	robot.move(z=robot.max[2] - 30)
	robot.move(y = 100) # CONSTANT
	first_plank_left_y = find_wall(robot, "X", 1, "calibrate-first_plank_left")
	robot.move(z=safe_height)
	robot.moveDelta(dx=50)
	
	robot.move(z=robot.max[2] - 30)
	pos = robot.getPosition()
	
	slot_wall_x_down = find_wall(robot, "X", -1, "calibrate-first_slot_down")
	robot.moveDelta(dx=expected_slot_width * approx_const)
	slot_wall_x_up = find_wall(robot, "X", 1, "calibrate-first_slot_up")
	slot_wall_y_down = find_wall(robot, "Y", -1, "calibrate-first_slot_down")
	robot.moveDelta(dy=expected_slot_height * approx_const)
	slot_wall_y_up = find_wall(robot, "Y", 1, "calibrate-first_slot_up")
	
	first_center = [(slot_wall_x_down + slot_wall_x_up) / 2, (slot_wall_y_down + slot_wall_y_up) / 2]
	log_value("calibrate-first_center_approx", first_center[0], "X")
	log_value("calibrate-first_center_approx", first_center[1], "Y")
	
	robot.move(z=safe_height)
	robot.moveDelta(dy=70)
	robot.move(z=robot.max[2] - 30)
	tmp_y_measurement = find_wall(robot, "Y", -1, "calibrate-flower_top")	

	plank_width = slot_wall_x_down - first_plank_left_y
	flower_height = tmp_y_measurement - slot_wall_y_up
	robot.params['plank_width'] = plank_width
	robot.params['flower_height'] = flower_height
	
	robot.first_slot = [slot_wall_x_down, slot_wall_x_up, slot_wall_y_down, slot_wall_y_up, robot.max[2]]
	
	robot.params['slot_width'] = slot_wall_x_up - slot_wall_x_down + plank_width
	robot.params['slot_height'] = slot_wall_y_up - slot_wall_y_down + flower_height
	# TODO: Update it after calibration. 
	
	check_slot_n_y = robot.params['height_n'] - (1 - robot.params['height_n'] % 2)
	last_slot_center_estimate = [slot_wall_x_down + (robot.params['width_n'] - 0.5) * robot.params['slot_width'], slot_wall_y_down + (check_slot_n_y - 0.5) * robot.params['slot_height']]
	log_value("calibrate-last_center_approx1", last_slot_center_estimate[0], "X")
	log_value("calibrate-last_center_approx1", last_slot_center_estimate[1], "Y")
	
	
	robot.move(z=safe_height)
	robot.move(x = last_slot_center_estimate[0], y = last_slot_center_estimate[1])

	find_wall(robot, "Z", 1, "calibrate-last_slot_center")	

	robot.moveDelta(dx= -expected_slot_width * approx_const / 2)
	slot_wall_x_down = find_wall(robot, "X", -1, "calibrate-last_slot_down")
	robot.moveDelta(dx=expected_slot_width * approx_const)
	slot_wall_x_up = find_wall(robot, "X", 1, "calibrate-last_slot_up")
	robot.moveDelta(dy= -expected_slot_height * approx_const / 2)
	slot_wall_y_down = find_wall(robot, "Y", -1, "calibrate-last_slot_down")
	robot.moveDelta(dy=expected_slot_height * approx_const)
	slot_wall_y_up = find_wall(robot, "Y", 1, "calibrate-last_slot_up")
	
	robot.moveDelta(dz=-70)
	
	robot.last_slot = [slot_wall_x_down, slot_wall_x_up, slot_wall_y_down, slot_wall_y_up, robot.getPosition()[2]]

	last_center = [(slot_wall_x_down + slot_wall_x_up) / 2, (slot_wall_y_down + slot_wall_y_up) / 2]
	log_value("calibrate-last_center_approx2", last_center[0], "X")
	log_value("calibrate-last_center_approx2", last_center[1], "Y")
	
	robot.params['units_in_mm'][0] = (last_center[0] - first_center[0]) / ((robot.params['width_n'] - 1) * slot_width_mm)
	robot.params['units_in_mm'][1] = (last_center[1] - first_center[1]) / ((check_slot_n_y - 1) * slot_height_mm)
	
	robot.params['slot_width'] = slot_wall_x_up - slot_wall_x_down + plank_width
	robot.params['slot_height'] = slot_wall_y_up - slot_wall_y_down + flower_height	
	
	for n_x in range(robot.params['width_n']):
		for n_y2 in range(math.floor(robot.params['height_n'] / 2)):
			calibrate_slot(robot, n_x, n_y2 * 2)
			
	robot.calibrated = True
	
	fill_slots(robot)
	ziggurat_calibration(robot)
	
	update_floor(robot)
	
	calibration_end_time = time.time()
	print("Calibration time: ")
	print(calibration_end_time - calibration_start_time)

# TODO: inline this function.
def fill_slots(robot):
	for n_x in range(robot.params['width_n']):
		for n_y2 in range(math.floor(robot.params['height_n'] / 2)):
			robot.params['slots'][n_x][n_y2 * 2 + 1] = deepcopy(uninitialized_slot)
			
			print("row" + str(n_y2 * 2 + 1))
			
			if n_y2 * 2 + 1 < math.floor(robot.params['height_n']):
				robot.params['slots'][n_x][n_y2 * 2 + 1]["LT"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2]["LB"])
				robot.params['slots'][n_x][n_y2 * 2 + 1]["RT"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2]["RB"])
				robot.params['slots'][n_x][n_y2 * 2 + 1]["floor_z"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2]["floor_z"])
				if n_y2 * 2 + 2 < math.floor(robot.params['height_n']) - 1:
					robot.params['slots'][n_x][n_y2 * 2 + 1]["LB"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2 + 2]["LT"])
					robot.params['slots'][n_x][n_y2 * 2 + 1]["RB"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2 + 2]["RT"])
				else:
					robot.params['slots'][n_x][n_y2 * 2 + 1]["LB"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2]["LT"])
					robot.params['slots'][n_x][n_y2 * 2 + 1]["RB"] = deepcopy(robot.params['slots'][n_x][n_y2 * 2]["RT"])
					robot.params['slots'][n_x][n_y2 * 2 + 1]["LB"][1] += robot.params['slot_height']
					robot.params['slots'][n_x][n_y2 * 2 + 1]["RB"][1] += robot.params['slot_height']

def go_to_slot_center_calibration(robot, n_x, n_y):
	if n_x < 0 or n_x >= robot.params['width_n']:
		print("ERROR: Invalid x coordinate: " + str(n_x))
		return
		
	if n_y < 0 or n_y >= robot.params['height_n']:
		print("ERROR: Invalid y coordinate: " + str(n_y))
		return
		
	first_slot_center = [(robot.first_slot[0] + robot.first_slot[1])/2, (robot.first_slot[2] + robot.first_slot[3])/2]
	last_slot_center = [(robot.last_slot[0] + robot.last_slot[1])/2, (robot.last_slot[2] + robot.last_slot[3])/2]
		
	destination_x = first_slot_center[0] + n_x * robot.params['slot_width']
	destination_y = first_slot_center[1] + n_y * robot.params['slot_height']
	
	log_value("go_to_slot_center_calibration-center_approx_" + str(n_x) + "_" + str(n_y), destination_x, "X")
	log_value("go_to_slot_center_calibration-center_approx_" + str(n_x) + "_" + str(n_y), destination_y, "Y")
	
	robot.move(x=destination_x, y=destination_y)

def AxisToCoordinates(axis, value, nonetype=False):
	"""
	Accepts "axis" input as "x", "y", "z" and numerical value.
	Returns tuple (x, y, z), where two of the values are 0, other is "value"
	For example:
		AxisToCoordinates('y', 5)
	returns
		(0, 5, 0)
	"""
	axis = axis.lower()
	if nonetype:
		t = [None, None, None]
	else:
		t = [0, 0, 0]
		
	if axis=='x':
		t[0] = value
	elif axis=='y':
		t[1] = value
	elif axis=='z':
		t[2] = value
	else:
		print("Wrong axis provided: ", axis)
		print("Provide axis x, y or z")
	return t

def retract_until_no_touch(arnie, touch_probe, axis, step):
	delta_coord = AxisToCoordinates(axis, step)
	x, y, z = arnie.getPosition()
	
	if delta_coord != [0, 0, 0] and delta_coord != [None, None, None]:
		while touch_probe.isTouched():
			arnie.moveDelta(dx=delta_coord[0], dy=delta_coord[1], dz=delta_coord[2], speed_xy=1000)
	else:
		print ("Interrupted because wrong axis was provided.")
		return
		
	x, y, z = arnie.getPosition()
	return x, y, z
	
def ApproachUntilTouch(arnie, touch_probe, axis, step):
	"""
	Arnie will move along specified "axis" by "step"
	Provide:
		arnie - instance of Arnie object
		touch_probe - instance of touch_probe object
		axis - string, "x", "y" or "z"
		step - distance to move at every step
	"""
	
	delta_coord = AxisToCoordinates(axis, step)
	x, y, z = arnie.getPosition()
	
	if delta_coord != [0, 0, 0] and delta_coord != [None, None, None]:
		while not touch_probe.isTouched():
			# ApproachUntilTouchoach forward by a tiny step	
			arnie.moveDelta(dx=delta_coord[0], dy=delta_coord[1], dz=delta_coord[2], speed_xy=1000)
	else:
		print ("Interrupted because wrong axis was provided.")
		return
		
	x, y, z = arnie.getPosition()
	
	return x, y, z

def load_floor(robot):
		file = open("floor.json", "r")
		params_string = file.read()
		robot.params = json.loads(params_string)
		file.close()

def connect_tool(port_name, robot=None):
	device = serial_device(port_name)
	msg = device.recent_message
	
	if re.search(pattern="Marlin", string=msg):
		device.__class__ = arnie
		device.promote()
		robot = device

	if re.search(pattern="mobile touch probe", string=msg):
		device.__class__ = tool
		device.promote([0,0,0])
		device.__class__ = mobile_touch_probe
		device.promote()
		mtp = device
		
	if re.search(pattern="stationary touch probe", string=msg):
		device.__class__ = tool
		device.promote([0,0,0])
		device.__class__ = stationary_touch_probe
		device.promote()
		stp = device

	if robot != None:
		if device.__class__ == mobile_touch_probe:
			robot.current_tool = device
		if device.__class__ == stationary_touch_probe:
			robot.slots.append(device)
	
	return device

def connect():
	ports = serial_ports()

	mtp = None
	robot = None
	stp = None
	
	for port_name in ports:
		device = connect_tool(port_name)
		
		if device.__class__ == arnie:
			robot = device
		if device.__class__ == mobile_touch_probe:
			mtp = device
		if device.__class__ == stationary_touch_probe:
			stp = device

	if robot == None:
		print("ERROR: No robot detected.")
		print(ports)
		return
	
	if mtp != None:
		robot.current_tool = mtp
	if stp != None:
		robot.slot_tools.append(stp)
	
	robots.append(robot)
	print("Connected. Homing.")
	time.sleep(1)
	robot.home()
	
	if os.path.exists("floor.json"):
		load_floor(robot)
		robot.calibrated = True
	
		ports = serial_ports()
		if (len(ports) != 0):
			# TODO: Handle other tools too.
			robot.current_tool = touch_probe([0, 0, 0], ports[0])
			robot.current_tool.openSerialPort()
	
	log("Start")
	log(str(datetime.now()))
	
	print("Done.")
	return robot
