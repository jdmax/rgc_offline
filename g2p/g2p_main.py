#!/usr/bin/python

from __future__ import print_function
import re,datetime,pprint,sys, shelve
from g2p_classes import *
from g2p_functions import *
from g2p_global import *
from optparse import OptionParser
import multiprocessing

	
def main():
	
	'''Offline g2p polarization analysis'''
	
	pols = open("pols_v_time.txt","w")
	runsout = open("pol_v_run.txt","w")
	
	###  Parse command line arguments  #######
	#parser = OptionParser();  # in global now
#	parser.add_option("-s", "--start", dest="start_time", default='02/01/12 00:00',\
#					   help="Start analysis from this time. Format: 'MM/DD/YY hh:mm'")
#	parser.add_option("-S", "--stop", dest="stop_time", default='06/01/12 00:00',\
#					   help="Stop analysis at this time. Format: 'MM/DD/YY hh:mm'")
	parser.add_option("-m", "--multi", dest="multi", default=1,\
					   help="Number of processes to spawn")
	#parser.add_option("-r", "--runs", action="store_true",dest="runs", default=False,\
	#				   help="Use run start, stop file? Overrides time options")					   
	parser.add_option("-T", "--TE", action="store_true", dest="make_te", default=False,\
					   help="Redo offline TEs from list files")
	(options, args) = parser.parse_args()
	#################################
		
	#if options.runs:
	runfile = open(input_path+"/run_times.txt", "r")
	for line in runfile:
		(run,start,stop) = line.split() 
		r = Run(run,start,stop)	# make runs objects
		runs[r.run] = r
			
#	else:	Taking out running by time for now; just use run by run number.
#		try:
#			start_time = get_time(options.start_time)  # get unixtime
#			stop_time = get_time(options.stop_time)
#		except AttributeError:
#			print("Try date format again!  'MM/DD/YY hh:mm'")
#		ranges["times"] = (start_time,stop_time)
		
	print('Reading Baselines')	
	fill_base()   # fills all baselines to dict baselines keyed on unixtime
	print('Baselines Read')
	
	if options.make_te or not 'tes' in te_shelf: 	# if asked for, or if the shelf is empty, run the te maker, otherwise get from shelf
		tesummary = open("te_summary.txt","w")
		materials.update(fill_materials(material_file))  # read materials table and return dict of material objects keyed on id #
		tes.update(fill_tes(te_file))     # read te table and return dict of te objects keyed on id #
			
		for id,te in sorted(tes.items()):
			if te.empty: continue # skip empty tes
			offline_te(te)  # perform offline TE for each
			materials[te.material].add_te(te)  # associate te with its material

		for mat in materials: # average tes for each material together
			materials[mat].avg_tes(tesummary)

		te_shelf['tes'] = tes
		te_shelf['mats'] = materials	
		te_shelf.close()
		tesummary.close()
	else:
		tes.update(te_shelf['tes'])
		materials.update(te_shelf['mats'])
		te_shelf.close()
	
	#for mat in materials: # make dict of materials keyed on start time to allow sorting
	#	mat_start[mat] = 	materials[mat].start		
		#pprint.pprint(materials[mat].__dict__)
	
	curfile = open(input_path+"/curA","r")  # temporary, eventually should average A and B	
	print("Reading beam currents to memory")
	currents.update(fill_currents(curfile))	# put all currents per second in currents dict keyed by time

	annfile = open(input_path+"/anneal_table.txt","r") 
	print("Reading anneals to memory")
	anneals.update(fill_anneals(annfile))
	anneal_times.extend(sorted(anneals.keys()))

	#temp_range = (0,9999999)
	temp_range = (0,15000)
	#temp_range = (6100,6200)
	#temp_range = (2800,3000)
	

	for run in sorted(runs):	
		if not (temp_range[0] < run < temp_range[1]): 
			continue		
		good_run = run_anal(run)      # perform offline analysis on all events in the run
		if not good_run: 
			continue 
		print(run,runs[run].material,runs[run].avg_off_pol,runs[run].avg_on_pol,runs[run].dose,runs[run].dose_sum,file=runsout)
		
if __name__=='__main__':
	main()
