from os import listdir
from os.path import isfile, join
from json import loads

def print_tool_params(tool_type):
	result = []
	for file_name in listdir():
		if  not isfile(file_name):
			continue
			
		if "tools" not in file_name:
			continue
			
		file = open(file_name, "r")
		contents = file.read()
		file.close()
		tools = loads(contents)
		
		for tool in tools:
			if tool["type"] == tool_type:
				print(tool["params"])
				result.append(tool["params"])
				
	return result
				
def print_floor_params(param_name):
	for file_name in listdir():
		if  not isfile(file_name):
			continue
			
		if "floor" not in file_name:
			continue
		
		file = open(file_name, "r")
		contents = file.read()
		file.close()
		
		print(contents)
		# TODO: The following causes a crash: it can't loads the floor for some reason. 
		# floor = loads(contents)
		# print(floor[param_name])
