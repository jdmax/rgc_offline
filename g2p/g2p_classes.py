#!/usr/bin/python

from __future__ import print_function
import re,datetime,pprint
from g2p_global import *
from math import *


class Baseline():
	'''Data object for baselines.  Just has array of 500 numbers (the baseline signal) and a unixtime to identify.'''
	
	def __init__(self,line):
		'''When passed line from basefile, fills baseline object'''
		
		fields = line.split(',')		
		self.unixtime = int(fields[0])	
		self.base = [float(x) for x in fields[1:501]]
		
class Event():
	'''Data object for target events'''
	
	def __init__(self,line,key):
		'''When passed line from eventfile, fills object. Also needs key from file to be passed'''
		#key = ["EventNum","Polarization","Area","CalConst","Baseline","QMeterNum","QMeterName","MagCurrent","EIPFreq","HPFreq","uWaveFreq","uWavePower","FMAmplitude","FMOffset","ScanSweeps","ScanSteps","ScanFreq","RFFreq","RFMod","RFPower","YaleGain","DCLevel","He3Press","He3Temp","He4Temp","He4Press","SepFlow","MainFlow","MagLevel","NoseLevel","RFVolts","LN2Level","VacPress","Comment","TopChip","BottomChip","CarbonGlass","Collector"]
		key = key.rstrip('\n').split(',')
		fields = line.rstrip('\n').split(',')
		
		for name, entry in zip(key,fields):  # fill object using key names as variable names
			#print(name, entry)
			if not entry:					
				self.__dict__[name] = None	
			elif "QMeterName" in name or "Position" in name: 						# keep as string
				self.__dict__[name] = entry
			elif ("EventNum" in name) or ("Baseline" in name):  # use integer
				self.__dict__[name] = int(entry)
			else:											# use float
				if "NaN" in entry:
					self.__dict__[name] = 0
				try:	
					self.__dict__[name] = float(entry)		
				except ValueError:
					print(entry)
		try:
			if 'Top' in self.QMeterName:
				self.pos = 'top'
			elif 'Bot' in self.QMeterName:
				self.pos = 'bot'	
			else:
				self.pos = "none"	
		except TypeError:
			self.pos = "None"
		
		self.unixtime = int(self.EventNum)
		self.OfflinePolarization = 0
		self.OfflineArea = 0
		self.OfflineCC = 0
		self.d_charge = 0
		self.d_time = 0
		self.dose = 0
		self.total_dose = 0
		self.dose_anneal = 0 # dose since last anneal
		self.avg_curr = 0
		self.material = None
		self.keep = True
		self.time_range = (0,0)
		
	def add_raw(self,raw_line):
		'''Adds sweep to event object usin line from raw file'''
		fields = raw_line.split(',')		
		if (self.unixtime != int(fields[0])): print("unixtime doesn't match sweep!", self.unixtime,fields[0], type(self.unixtime),type(fields[0]))		
		self.sweep = [float(x) for x in fields[1:501]]
		if not self.sweep and self.Polarization: print ("Error setting sweep from raw line, online pol good", self.Polarization)

class Material():
	'''Data object for all data on a given material'''
		
	def __init__(self,line):
		'''Initialize Mat object with line from Mat log'''
		
		fields = line.rstrip("\n").split("\t")
		#pprint.pprint(fields)
		self.id = int(fields[0])
		self.config = fields[1]
		self.cup = fields[3]   # top or bot
		self.start = get_time_cl(fields[5])
		self.stop = get_time_cl(fields[6])
		self.tes = []
		self.runs = []
		self.dose = 0
		self.dose_since_anneal = 0
		self.run_dose = {}
		self.field = self.config[:3] #field in T
				
	def add_te(self,t):
		'''Adds TE to this material object, when passed TE object'''
		self.tes.append(t)
		
	#def add_anneal(self,a):
	#	'''adds anneal to this material object, when passed anneal object'''
	#	self.anneals.append(self,a)	
	
	def avg_tes(self,tesummary):
		'''Average CC from the TEs for this material, print a material summary file (filehandle to print to passed as argument)'''
		avg_cc = 0
		sum_sq = 0
		#print(self.id,len(self.tes))
		for te in self.tes:
			avg_cc += te.cc
			sum_sq += te.cc**2
		avg_cc /= len(self.tes)
		std_cc = sqrt(abs(sum_sq/len(self.tes) - avg_cc**2))
		
		self.cc = avg_cc
		self.cc_std = std_cc	
		# print sumary file at some point
		print("Material",self.id,"from",self.start,"to",self.stop,"in cup",self.cup,file=tesummary)
		print("\t","Average CC:",self.cc,"+-",self.cc_std,file=tesummary)
		print("\t","All CCs:",file=tesummary)
		for te in self.tes:
			print("\t\t","TE",te.id,te.cc,file=tesummary)
		print("")

class Anneal():
	'''Data object for anneal'''
	
	def __init__(self,line):
		'''init anneal when passed a line from the anneal log'''
		
		fields = line.split()
		self.id = fields[0]
		self.starttime = get_time_cl(fields[1]+" "+ fields[2])
		self.stoptime = get_time_cl(fields[1]+" "+ fields[3])
		self.time = (self.starttime+self.stoptime)/2		
		# average of start and stop times

		


			
class TE():
	'''Data object for a TE measurement'''
	
	def __init__(self,line,cup):
		'''Initialize TE object with line from TE log, takes line and index of te in single line (0 or 1)'''
		# line needs start and end time for entire procedure, start and end time for points taken as measurement, number and cup of material
		
		self.time = 0 # will be set to time of last te point
		fields = line.split()
		subs = fields[0].split(',')  # take into account multiple TEs per line, pick only the one we want based on cup variable
		if cup>len(subs)-1: return
		for ind,sub in enumerate(subs):
			if not ind==cup: continue
			#print(sub,ind,cup)
			self.id = sub	
			mats = fields[3].split(',')
			self.material = int(mats[ind])
			if ind==0: self.online_cc = fields[6]
			if ind==1: self.online_cc = fields[7]
		if '2.5' in materials[self.material].field:
			self.field = 2.5016
		else:
			self.field = 5.0033
		#print(materials[self.material].field,self.field)
		self.empty = False
		return
		
	def add_points(self):
		'''Using file from directory given, tries to associate all TE events numbers with this TE'''
		
		filename = te_path+"/te_"+self.id+".txt"
		self.points = []		
		try:
			file = open(filename,"r")
			for line in file:
				line = line.rstrip("\n")
				self.points.append(int(line))
			return
			
		except IOError:
			self.empty = True  # if there is no te_final file, mark this te as empty for now
			pass
		
		

class Run():
	'''Run object has information on run. self.run is the run number'''
	def __init__(self,run,start,stop):		
		self.run = int(run)
		self.start = int(start)
		self.stop = int(stop)
		self.material = 0
		self.dose = 0
		self.dose_sum = 0   # total dose on this material at run end
		self.avg_on_pol = 0
		self.avg_off_pol = 0
		self.events = []
		
		
		
		
timeoffset = 0
date_regex = re.compile(r'(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})')

def get_time_cl(string):
	'''get time from input string'''	
	try:
		(month,day,year,hour,minute) = date_regex.search(string).groups()
	except AttributeError:
		print(string, "doesn't match!")
	dt = datetime.datetime(int(year),int(month),int(day),int(hour),int(minute))
	unixtime = str(int(dt.strftime("%s")))
	return int(unixtime)
