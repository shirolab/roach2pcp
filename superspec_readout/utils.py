#just some utility functions


def read_config():
	new_dict = {}
	with open('config.txt','r') as f:
		for line in f:
			splitline = line.split()
			new_dict[splitline[0]] = splitline[1]
	return new_dict
