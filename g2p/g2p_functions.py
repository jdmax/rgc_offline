#!/usr/bin/python

from __future__ import print_function
import re,datetime,pprint, glob,subprocess
from g2p_classes import *
from g2p_global import *
from scipy import *
from scipy import optimize
import multiprocessing

#data_path = '/home/jdm2z/g2p/target/test'
#timeoffset = 18000 # before dst
#timeoffset = 14400 # after dst
#timeoffset = 0

date_regex = re.compile(r'(\d{2})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2})')

def get_time(string):
	'''get time from input string'''	
	#print(string)
	try:
		(month,day,year,hour,minute) = date_regex.search(string).groups()
	except AttributeError:
		print(string, "doesn't match!")
	year = int(year) + 2000
	dt = datetime.datetime(int(year),int(month),int(day),int(hour),int(minute))
	unixtime = str(int(dt.strftime("%s")))
	return int(unixtime)

	
def fill_base():
	'''Looks through all baseline files and reads them to global baseline dictionary of objects, keyed on unixtime'''

	files = glob.glob(data_path+"/*-base-RawSignal.csv")
	
	for file in files:
		for line in open(file,'r'):			
			b = Baseline(line)
			baselines[b.unixtime] = b
	
def fit_wings(sub_sweep):
	'''4th order fit to wings with scipy'''
	
	data = [(x,y) for x,y in enumerate(sub_sweep) if (bounds[0]<x<bounds[1] or bounds[2]<x<bounds[3])]
	X = array([x for x,y in data])
	Y = array([y for x,y in data])
	
	errfunc = lambda p, x, y: poly(p,x) - y
	
	pi = [0.01, 0.8, 0.01, 0.001,0.00001]  # initial guess
	pf, success = optimize.leastsq(errfunc, pi[:], args=(X,Y))  # perform fit
	
	return pf
	

def poly(p,x):
	'''Third or Fourth order polynomial for fitting'''
	return p[0] + p[1]*x + p[2]*power(x,2) + p[3]*power(x,3)# + p[4]*power(x,4)
	
	
def signal_analysis(sweep,base):
	#########################
	# signal analysis: subtract baseline, fit to wings of this, subtract fit from base_sub, sum final signal

	sub_signal = [x-y for x,y in zip(sweep,base)]				
	final_p = fit_wings(sub_signal)				
	poly_signal = [poly(final_p,x) for x in range(500)]
	final_signal = [x-y for x,y in zip(sub_signal,poly_signal)]
			
	sum = 0 			
	for x in final_signal:	sum+=x	# sum signal
	return sum,sub_signal,poly_signal,final_signal
	


def read_events(start,stop):
	'''Returns a dict keyed on unixtime pointing to event object for all events in the time range given in unixtime'''
	
	# build list of event files, put in dict keyed on unixtime of end
		
	files = glob.glob(data_path+"/*s.csv") 		
	name = re.compile('(\d{4})-(\d{2})-(\d{2})_(\d{2})h(\d{2})m(\d{2})s\.csv')
	eventfiles = {}	
	
	for file in files:
		if not ".csv" in file: continue
		m = name.search(file)
		if m is None: 
			print("No match for the event file regex!")
			continue
		year, month, day, hour, minute, sec = m.groups()
		year = int(year)
		dt = datetime.datetime(int(year),int(month),int(day),int(hour),int(minute),int(sec))
		unixtime = str(int(dt.strftime("%s")))		 
		eventfiles[int(unixtime)] = file			
		
	# pick eventfiles which have data in our range, put in 'selected'
	last = 0
	selected = []
	for time in sorted(eventfiles):		
		if (last<=start<=time) or (last<=stop<=time) or (start<=time<=stop):
			selected.append(time)
		last = time	
			
	# read lines in our range, put them in object dictionary
	events = {}
	event_lines = {}		# read lines from each file to dict keyed on unixtime to match up later
	raw_lines = {}
	
	for unixtime in selected:		
		file = eventfiles[unixtime]
		print("Accessing file",file)
		raw_file = file[:-4]+"-RawSignal.csv"  # corresponding Raw Signal file
	
		f = open(file,'r')
		key = f.readline().rstrip('\n')  #first line is key
		rf = open(raw_file,'r')
				
		for line in f:
			if ',' in line[0:10]: continue  # skip empty lines
			try:
				event_lines[int(line[0:10])] = line
			except ValueError:
				print("Weird Event File line")
		for line in rf:
			if ',' in line[0:10]: continue 
			try:
				raw_lines[int(line[0:10])] = line
			except ValueError:
				print("Weird Raw File line")		
			
	for unixtime in sorted(raw_lines):			
		if start<=int(unixtime)<=stop:					
			try:
				e = Event(event_lines[unixtime].rstrip('\n'),key)
				e.add_raw(raw_lines[unixtime].rstrip('\n'))
				if e.Polarization: events[e.unixtime] = e  # only add to dict if it is a full event
			except KeyError:
				print("Key error",unixtime)		
				
	return events	



def fill_materials(filename):
	'''Read material table to create material objects for each load.  Returns array of material objects.'''
	materials = {}
	tab = open(filename, "r")
	for line in tab:	
		if line.startswith("#"): continue
		m = Material(line)
		materials[m.id] = m
	return materials	

def fill_tes(filename):
	'''Read te table to create te objects for each load.  Returns array of te objects.'''
	tes = {}
	tab = open(filename, "r")
	for line in tab:		
		if line.startswith("#"): continue
		t = TE(line,0)
		t.add_points()
		tes[t.id] = t
		t = TE(line,1)
		try:
			t.add_points()
			tes[t.id] = t
		except AttributeError:
			pass  # this line has only one te entry
	return tes	
	
	
def offline_te(te):
	'''Using list of events in the TE, perform the TE measurement'''
	
	meas = [] #  list of tups: (area,he3,field)
	events = read_events(min(te.points),max(te.points))  # get events range from files
	field = te.field
	print("Fitting events for TE",te.id)
	for point in te.points:
		e = events[point]  
		te.time = point
		try:
			area, sub , poly, final = signal_analysis(e.sweep,baselines[e.Baseline].base)
			#print "Offline:",area,"Online:",e.Area
			meas.append((area,e.He3Temp,field))
		except KeyError:
			print("missing baseline?", e.Baseline , type(e.Baseline))
			
	avg_cc = 0
	avg_te = 0
	sum_sq_cc = 0		
	for area,temp,field in meas:		
		cc,te_pol = te_point(area,temp,field)
		avg_cc += cc
		avg_te += te_pol
		sum_sq_cc += cc*cc
	avg_cc /= len(meas)
	avg_te /= len(meas)
	std_cc = sqrt(abs(sum_sq_cc/len(meas) - avg_cc**2))
	#print("CC:",avg_cc,"STD:",std_cc)
	# print out te summary file here at some point
	te.cc = avg_cc
	
def te_point(area,temp,field):
	'''Calculate one TE point from an area, B field, and temperature, return point cc, polarization'''	
	nuc_magtn=5.05078658e-27 #J/T
	prot_magtn=2.79268  # mu_0
	boltz_const=1.380658e-23 #J/K
	#mag_field=5.0033;	 NOOOOOOOOOOOOOO!!!!!!!
	mag_field = field # T

	tanh_arg=(prot_magtn*nuc_magtn*mag_field)/(boltz_const*temp)
	te_pol=tanh(tanh_arg)*100
	cc=te_pol/area
	return cc,te_pol

def fill_currents(cur):
	currents = {}
	for line in cur:
		fields = line.split()
		key = epics_to_labview_time(int(round(float(fields[0])))) # get time from epics file, convert to lv time
		#currents[key] = float(fields[1])*0.0058824 -1 # conversion to nA
		currents[key] = float(fields[1])#*1000
	return currents

def fill_anneals(ann):
	anneals = {}
	for line in ann:
		a = Anneal(line)
		anneals[a.time] = a
	return anneals
	
def offline_pol(ut,last_time):
	'''does offline polarization summation when passed unixtime, assuming the events and baselines globals have been filled'''
	try:
		if last_time == 0: last_time = ut
		events[ut].d_time = ut - last_time
		events[ut].time_range = (last_time,ut)
		
		events[ut].OfflineArea, sub , poly, final = signal_analysis(events[ut].sweep,baselines[events[ut].Baseline].base)
				
		events[ut].OfflinePolarization = events[ut].OfflineArea* events[ut].OfflineCC
				
		if events[ut].OfflineArea:
			events[ut].keep = True
		else: 	
			events[ut].keep = False
		#print "Offline:",area,"Online:",e.Area
	except KeyError:
		print("missing baseline?", events[ut].Baseline , type(events[ut].Baseline))
		events[ut].keep = False
	#	pass
	

def run_anal(run):
	'''Does offline analysis for each event in a run, returns False if bad run, True if good'''
	(options, args) = parser.parse_args()
	
	events.clear()  # empty events dict 
	events.update(read_events(runs[run].start,runs[run].stop))	# read all events in range, put in events global 

	if not events:
		print("No good events in run", run)
		return False

	last_time = 0
	cur_material = None
	processes = [] # list to store running process objects
	
	for ut in sorted(events):	  # go through events, do final analysis for each
		if not events[ut].Polarization: continue # skip empty events
		if not events[ut].sweep: 
			if events[ut].Polarization: print("Skipped event without sweep",ut)
			continue  #skip events without baselines
		if (not events[ut].Baseline) or (events[ut].Baseline==0) or (events[ut].Baseline==-1):
			print("Skipped event without baseline",ut)
			continue		
		if not cur_material or not materials[cur_material].start < ut < materials[cur_material].stop: # pick material if we need to	
		#	for start,num in sorted(mat_start.items()):
			if cur_material: print("Material changed during run!")
			cur_material = None
			for num in sorted(materials):
				if (materials[num].start < ut < materials[num].stop):
					if (events[ut].pos in materials[num].cup):
						cur_material = num
				if cur_material: break
			if not cur_material: print("event time not in range",ut) 
		events[ut].material = cur_material
		if (not cur_material) or cur_material==0: 
			print("No material selected")
			continue # skip event if it isn't from a material from the table
			
		# Set CC for this event one of two ways: first, average of all for this material; second, closest TE in time	
		#events[ut].OfflineCC = materials[events[ut].material].cc  # set material's cc for this event
		
		prox = 9999999999
		for te in materials[events[ut].material].tes:  # look for closest TE, set it
			if abs(te.time - ut) < prox:
				prox = abs(te.time - ut)
				events[ut].OfflineCC = te.cc
		
		runs[run].events.append(ut)
		runs[run].material = cur_material
		####multiprocessing code####
#		if options.multi>1:		
#			p = multiprocessing.Process(target=offline_pol, args=(ut,last_time))  # make, put process in list
#			
#			if len(processes) < 6: # do no more than 6 processes
#				p.start()
#				processes.append(p)	
#				#print(len(processes))
#			else:
#				q = processes.pop()
#				q.join()
#				p.start()
#				processes.append(p)	
				#print(len(processes))
#		else:
		#####################
		offline_pol(ut,last_time)
		
		last_time = ut	
	if (not runs[run].material) or runs[run].material==0: 
		print("Material for this run not selected correctly", run) 
		return False		
	
	# charge accumulate
	pol_e_sum = 0	# pol*e for charge weighted average	
	opol_e_sum = 0	# online 
	global all_total_dose
	global reset_top
	global reset_bottom
	global anneal_times
	
	for ut in sorted(events):  # looping over events of this run in order
		if not events[ut].keep: continue
		
		# check to see if anneal has occurred, reset counter.
		# anneal_times is ordered list of anneals, and we throw away an entry after it is passed.

		if ut > anneal_times[0]:
			reset_top = 1   # reset flags for each cup
			reset_bottom = 1
			trash = anneal_times.pop(0)
			while ut > anneal_times[0]:
				trash = anneal_times.pop(0)
				print("catching up with anneal",trash)	
		
		if "top" in materials[runs[run].material].cup and reset_top == 1:
			materials[runs[run].material].dose_since_anneal = 0
			reset_top = 0
			print(runs[run].material,ut,materials[runs[run].material].dose,file=anneal_fh)
			#print("reset top anneal")
			
		if "bot" in materials[runs[run].material].cup and reset_bottom == 1:
			materials[runs[run].material].dose_since_anneal = 0
			reset_bottom = 0
			print(runs[run].material,ut,materials[runs[run].material].dose,file=anneal_fh)
			#print("reset bot anneal")
		
		if events[ut].d_time<600:  # need to know if beam went off, this assumes events far apart don't have beam on in between
			#print(events[ut].keep,events[ut].OfflineArea)
			start,stop = events[ut].time_range
			for time in range(start,stop):
				try:
					if currents[time]>current_cut: events[ut].d_charge += currents[time]  # sum nanocoloumb, time = 1 sec
					events[ut]	
				except KeyError:
					pass
		
		# Per event:			
		if (stop-start)>0: events[ut].avg_curr = events[ut].d_charge/(stop-start) # Average current for this event		
		events[ut].dose = events[ut].d_charge*e_per_nc/cup_area # total dose in e/cm^2 for this event
		
		# Per run:
		runs[run].dose +=  events[ut].dose				# summming dose for this run
		events[ut].total_dose = runs[run].dose				# dose on this run at the end of this event
		pol_e_sum +=  events[ut].OfflinePolarization*events[ut].dose  # dose weighted polarization for this run
		if events[ut].Polarization: opol_e_sum +=  events[ut].Polarization*events[ut].dose # same for online
		
		# Per material:
		materials[runs[run].material].dose += events[ut].dose  # dose on this material at end of event
		events[ut].mat_dose = materials[runs[run].material].dose   
		materials[runs[run].material].dose_since_anneal += events[ut].dose # dose on this material since last anneal 
		
		# Per experiment:		
		all_total_dose += events[ut].dose
		
		print(ut,run,runs[run].material,all_total_dose,events[ut].mat_dose, materials[runs[run].material].dose_since_anneal, events[ut].Polarization, events[ut].OfflinePolarization,events[ut].d_charge,events[ut].avg_curr, file=time_fh)
		print(ut,runs[run].material,materials[runs[run].material].dose, materials[runs[run].material].dose_since_anneal, events[ut].Polarization, events[ut].OfflinePolarization,events[ut].uWaveFreq, file=freq_fh)
	
	if runs[run].dose: 
		run_pol = pol_e_sum/runs[run].dose
		run_opol = opol_e_sum/runs[run].dose
	else:
		print("No dose for this run")	
		runs[run].avg_off_pol = "NoDose"
		run_pol=0
		run_opol=0
		
	# Run totals:	
	runs[run].avg_off_pol = run_pol
	runs[run].avg_on_pol = run_opol
	runs[run].dose_sum = materials[runs[run].material].dose
	
	materials[runs[run].material].runs.append(run) 
	materials[runs[run].material].run_dose.update({run:materials[runs[run].material].dose}) 	
	
	return True

def epics_to_labview_time(epicstime):
	'''applies offset to get lv time from epics'''
	# lv time is local time, epics is utc (no dst)
	#timeoffset = 18000 # before dst 
	#timeoffset = 14400 # after dst
	# offset = 14400
	# dst switch at 1331431200
	offset = 0
	#if (epicstime > 1331431200):
	#	offset = 14400
	#else:
	#	offset = 18000
	lvtime = epicstime + offset
	return lvtime
	
	#	if 'times' in run:		
#		for unixtime, e in sorted(events.items()):	
#			if True: print(unixtime, e.Polarization,e.OfflinePolarization, e.QMeterNum,e.material,e.total_dose,file=pols)
		
#	else:
#		print(run,run_pol,total_e,file=pols)		
