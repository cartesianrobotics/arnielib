from os import listdir
from os.path import isfile, join
from json import loads

for file_name in listdir():
	if  not isfile(file_name):
		continue
		
	if "tools" not in file_name:
		continue
		
	file = open(file_name, "r")
	contents = file.read()
	tools = loads(contents)
	
	for tool in tools:
		if tool["type"] == "plate":
			print(tool["params"])