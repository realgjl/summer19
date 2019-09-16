import os
import shutil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pyramses



def sfc(ram, case, monitor, list_of_gens, weight_of_gens, list_of_td, prepared_folder_address, start_time, end_time, agcTimeStep, breaker, nominal_value, kp, ki):
	"""Secondary Frequency Control (SFC)
	
	Args:
		ram: a simulator instance
		case: load saved test-case
		monitor: a normal generator in the system
		list_of_gens: generators which send their power to the system to restore frequnecy
		weight_of_gens: the weight of power of generators to send to the system
		list_of_td: communication time delay of generators
		prepared_folder_address: the address of generated cur files
		start_time: agc start time
		end_time: agc end time
		agcTimeStep: the time step of controller interfering the system
		breaker: a generator that will disconnect from the system
		nominal_value: nominal frequency (1pμ OR 50Hz OR 60Hz)
		kp (float): p term of PI control
		ki (float): i term of PI control
		
	Generates:
		cur file (f-t curve OR any other self-customized curve), trj files (P-t curve), other trace files
		
	Raises:
		PyRAMSESError: voltages or frequency out of bound
	"""
	kp = float(kp)
	ki = float(ki)
	
	
	# simulation cannot be started => flag = 1
	flag = 0
	try:
		ram.execSim(case,start_time)
	except:  # skip to end simulation & move files
		flag = 1
		pass


	# normal <=> flag = 0:
	if flag == 0:
		# Initialization
		comp_type = ['SYN']
		obs_name = ['Omega']
		errSum = 0.0


		"""
		start of agc
		"""
		for i in np.arange(start_time+agcTimeStep,end_time+1,agcTimeStep):  # ending time will be include the 'end_time' sec
			#print("i = " + str(i))
			actual_frequency = ram.getObs(comp_type, monitor, obs_name)[0] # monitor
			error = nominal_value - actual_frequency
			if abs(error)<=0.000001: #10e-6
				error = 0.0
				errSum = 0.0
			#print("error = " + str(error))

			errSum += error * agcTimeStep
			#print("errSum = " + str(errSum))
			output = float(kp) * float(error) + float(ki) * float(errSum)
			if abs(output)<=0.00001:
				output = 0.0
			# print("output = " + str(output))

			# send measurements to generators in 'list_of_gens'
			gens = zip(list_of_gens, weight_of_gens, list_of_td)
			for gen in gens:
				gensName, gensWeight, gensTd = gen
				command = 'CHGPRM TOR ' + gensName + ' Tm0 ' + str(output*gensWeight) + ' 0'
				#print(str(ram.getSimTime()+0.01)+' '+command)
				gensTd = "{0:.4f}".format(gensTd,4)
				gensTd = float(gensTd)
				# print("line 79: gensTd = " + str(gensTd))
				ram.addDisturb(ram.getSimTime() + gensTd, command)

			# catch errors (voltages or frequency out of bound)
			try:
				ram.contSim(i)
			except:
				print("RAMSES error => break, ready to kill gnuplot")
				break
			
			# unacceptable
			if actual_frequency <= 0.995 or actual_frequency >= 1.005:
				print("t = " + str(i) + "s, actual_frequency=" + str(actual_frequency) + ": not in a range of [0.995, 1.005], will end the simulation")
				ram.contSim(i)  # pause
				break
		"""
		end of agc
		"""
		pass


	kp = "{0:.4f}".format(round(float(kp),4))
	ki = "{0:.4f}".format(round(float(ki),4))
	
	
	# end simulation & move files
	end_simulation(ram, case, flag)
	move_file(prepared_folder_address, breaker, kp, ki, list_of_gens, list_of_td)
	



def end_simulation(ram, case, flag):
	"""end the simulation safety

	Args:
		ram: a simulator instance
		case: saved test-case ('cmd.txt')
		flag (int): determine when to terminate the simulation
	'"""
	# end the simulation without starting simulation & agc
	if flag == 1:
		print("flag = 1: cannot start simulation")

		# kill gnuplot ('$CALL_GP F;')
		os.system("TASKKILL /F /IM gnuplot.exe /T")
		print("kill gnuplot successfully: no-simulation")

		# end simulation and exit
		try:
			ram.endSim()
			print("endSim() successfully: no-simulation")
		except:
			print("skip endSim(): no-simulation")


	# end the simulation normally
	if flag == 0:
		# kill gnuplot
		os.system("TASKKILL /F /IM gnuplot.exe /T")
		print("kill gnuplot successfully")

		# end simulation and exit
		try:
			ram.endSim()
			print("endSim() successfully")
		except:
			print("skip endSim()")


	# make sure the process of simulation and the case is ended
	del(ram)
	del(case)
	print("delete ram & case successfully")




def move_file(prepared_folder_address, breaker, kp, ki, list_of_gens, list_of_td):
	"""move cur file to a prepared folder & delete some files

	Args:
		prepared_folder_address (string): cur file's new folder address
		breaker (string): the name of generator you want to disconnection (e.g.: 'g12')
		kp, ki (float): PI control's parameter
		list_of_td (list): commuication delays
	"""
	# create a folder (that cur files will be moved into)
	try:
		if not os.path.exists(prepared_folder_address):
			os.makedirs(prepared_folder_address)
	except OSError:
		print('Error: Creating floder:' + prepared_folder_address)


	# open, read and re-write contents to another file (in public folder) (cur)
	with open("temp_display.cur", encoding='utf-8') as f00:
		with open("temp_display_.cur", "w", encoding='utf-8') as f01:
			for line in f00:
				if "error" not in line:
					f01.write(line)
	print("re-write cur successfully")


	# copy the file (in public folder) to another prepared folder
	shutil.copy("temp_display_.cur", prepared_folder_address)
	print("copy cur successfully")



	# rename the file in new folder (cur)
	new_address = curAddress(list_of_gens, list_of_td, prepared_folder_address, breaker, kp, ki)
	os.rename(prepared_folder_address + '/temp_display_.cur', new_address)


	# delete cur files
	os.unlink("temp_display.cur")
	os.unlink("temp_display_.cur")
	print("delete temp_display(_).cur successfully")


	# delete other files
	os.unlink("cont.trace")
	os.unlink("disc.trace")
	os.unlink("init.trace")
	print("delete some trace files successfully")




class Gens:
	"""Information of generators
	
	Attributes:
		name: offical name of genrators (string)
		weight: weight of sending power to the system (float, max 4th decimal point)
		delay: time delay between generators 
	"""
	name = ''
	weight = 0
	delay = 0.0

	def __init__(self, n, w, td):
		self.name = n
		self.weight = w
		self.delay = td

	def __cmp__(self, other):
		return cmp(self.delay, other.delay)

	def printGensInfo(self):
		print("Generator %s: weight = %f, delay = %f sec" %(self.name, self.weight, self.delay))




def sortGens(liST):
	'''Sort Generator's information according to the size of delay, and send them into a new list.
	
	Args:
		liST: a list of Class Gens of generators
		
	Returns:
		gens_list: new list of names of generators
		weight_list: new list of weights of generators
		miniTd_list: new list of mini time delays of generators
	'''
	gens_list = []
	weight_list = []
	miniTd_list = []

	liST.sort(key=lambda x: x.delay)
	for i in liST:
		gens_list.append(i.name)
		weight_list.append(i.weight)
		miniTd_list.append(i.delay)

	return(gens_list, weight_list, miniTd_list)




def multipleIncreaseDelay(pcgTd, mini_list_of_td):
	"""increase time delay
	
	Args:
		pcgTd: percentage of mini time delay (>= 0, in %)
		mini_list_of_td: list of mini time delay
		
	Returns:
		td_list: modified list of time delay
	"""
	td_list = []
	for miniTd in mini_list_of_td:
		td = miniTd * pcgTd/100
		td = "{0:.4f}".format(round(float(td),4))
		td_list.append(float(td))
	return(td_list)
	



def curAddress(list_of_gens, list_of_td, prepared_folder_address, breaker, kp, ki):
	"""rename the address of cur file and its name
	
	Args:
		list_of_gens: list of names of generators generating this cur file
		list_of_td: list of time delays of generators generating this cur file
		prepared_folder_address
		breaker: name of breaker generators generating this cur file (string)
		kp: the value of kp generating this cur file
		ki: the value of ki generating this cur file
		
	Returns:
		address: new address of cur file
	"""
	tdText = ""
	address = ""
	i = 0
	while i < len(list_of_gens):
		strTd = "{0:.4f}".format(list_of_td[i],4)
		tdText += '_' + str(list_of_gens[i]) + '-' + strTd + 's'
		i += 1
	address += prepared_folder_address + '/temp_display_' + 'breaker-' + breaker + tdText + '_' + str(kp) + '-' + str(ki) + '.cur'
	return(address)
	



def index_of_value_in_list(target_list, target_value):
	"""find index of target_value in target_list	
	
	Args:
		target_list: a list containing target_value
		target_value: (see above)
	
	Returns:
		index of target_value in its list
	"""
	for i in range(len(target_list)):
		if target_list[i] == target_value:
			return(i)




def chop_curve(input_x_axis, input_y_axis, chop_value):
	"""get a new curve (x>=chop_value)
	
	Args:
		input_x_axis: original data set of x axis
		input_y_axis: original data set of y axis
		chop_value: a value that allows the program cut the curve by x=chop_value
	
	Returns:
		x_old: original data set of x axis (list)
		y_old: original data set of y axis (list)
		x: chopped data set of x axis (list)
		y: chopped data set of y axis (list)
	"""
	# unchopped data
	x_old = input_x_axis.tolist()
	y_old = input_y_axis.tolist()
	
	# index of 300 in its x axis list
	index_of_chop_value = index_of_value_in_list(x_old, chop_value)
	
	# chopped data
	del x_old[0:index_of_chop_value]
	x = x_old
	del y_old[0:index_of_chop_value]
	y = y_old
	
	# unchopped data
	x_old = input_x_axis.tolist()
	y_old = input_y_axis.tolist()
	
	return(x_old, y_old, x, y)
	
	


def rate_of_change(input_x_axis, input_y_axis, start_value_of_x, end_value_of_x, step_x, unit_converter):
	"""find rate of delta_y (example: delta_y per min)
	
	Args:
		input_x_axis: data set of x (list)
		input_y_axis: data set of y (list)
		start_value_of_x: the first value of x you want to compute rate
		end_value_of_x: the last value of x you want to compute rate
		step_x: delta x
		unit_converter: = unit of target/unit of delta_x (example: target unit is in min, unit of delta_x is in sec, unit_converter = 1 min/1 sec = 60)
	
	Returns:
		rate_of_delta_y: rate of change of y according to step_x
	"""
	# filter original data set so the step of x is step_x
	filtered_x = []
	filtered_y = []
	value_of_x = start_value_of_x  # initialize value in list filtered_x
	for i in range(len(input_x_axis)):
		if input_x_axis[i] == value_of_x and value_of_x <= end_value_of_x + step_x:
			filtered_x.append(value_of_x)
			filtered_y.append(input_y_axis[i])
			value_of_x += step_x
	# plt.plot(filtered_x, filtered_y)
	
	# compute delta y
	delta_y = []
	for i in range(1, len(filtered_y)):
		delta_y.append(filtered_y[i] - filtered_y[i-1])
	
	# compute rate of delta y via step_x & unit_converter
	rate_of_delta_y = []
	for i in delta_y:
		rate_of_delta_y.append(i/(step_x/unit_converter))
	return(rate_of_delta_y)
	



def max_rate_of_change(input_x_axis, input_y_axis, start_value_of_x, end_value_of_x, step_x, unit_converter):
	"""round and float max value of rate of change
	
	Args:
		input_x_axis: data set of x (list)
		input_y_axis: data set of y (list)
		start_value_of_x: the first value of x you want to compute rate
		end_value_of_x: the last value of x you want to compute rate
		step_x: delta x
		unit_converter: = unit of target/unit of delta_x (example: target unit is in min, unit of delta_x is in sec, unit_converter = 1 min/1 sec = 60)
	
	Returns:
		max_value: max value of rate of change (float)
	"""
	ramp_rate = rate_of_change(input_x_axis, input_y_axis, start_value_of_x, end_value_of_x, step_x, unit_converter)
	max_value = max(ramp_rate)
	max_value = float("{0:.4f}".format(round(max_value,4)))
	return(max_value)
	
	
	

def curve_of_rate_of_change(name_of_machine, input_x_axis, input_y_axis, start_value_of_x, end_value_of_x, step_x, unit_converter):
	"""draw the curve of rate of change vs time
	
	Args:
		name_of_machine: offcial name of machine (string)
		input_x_axis: data set of x (list)
		input_y_axis: data set of y (list)
		start_value_of_x: the first value of x you want to compute rate
		end_value_of_x: the last value of x you want to compute rate
		step_x: delta x
		unit_converter: = unit of target/unit of delta_x (example: target unit is in min, unit of delta_x is in sec, unit_converter = 1 min/1 sec = 60)
		
	Plots:
		curve of rate of change vs time with suitable size of diagram, label, and grid
	"""
	ramp_rate = rate_of_change(input_x_axis, input_y_axis, start_value_of_x, end_value_of_x, step_x, unit_converter)
	max_rate = max_rate_of_change(input_x_axis, input_y_axis, start_value_of_x, end_value_of_x, step_x, unit_converter)
	
	t = np.arange(start_value_of_x, end_value_of_x + step_x/10, step_x)

	fig = plt.figure(figsize=(20,10))
	str_label = name_of_machine + ": activate power rate (MW/min); Max activate rate = " +  str(max_rate) + "MW/min"
	plt.plot(t, ramp_rate, label=str_label)
	plt.xlabel('t (s)')
	plt.ylabel('power rate (MW/min)')
	plt.legend()
	plt.grid(True)
	



def settling_time(x, y, settling_range, nominal_value):
	"""settling time of a curve (f-t) with a specific settling range & nominal value
	
	Args:
		x: data set of x axis (list)
		y: data set of y axis (list)
		settling_range: positive value; a range that y should in it (-settling_range <= y <= +settling_range).
		nominal_value: target value that y should be OR the end value of y value (MATLAB default)
		
	Returns: settling time (if settled) OR an infinite value (if not settled)
	"""
	settled_time = 999999999999
	for i in range(1,len(y)+1):
		if abs(y[-i]-nominal_value) > settling_range:
			ii = i
			break
	if ii == 1:
		return(settled_time)  # not settled till the end, return infinite value
	else:
		settled_time = "{0:.4f}".format(round(float(x[-ii]),4))
		settled_time = float(settled_time)
		return(settled_time)

