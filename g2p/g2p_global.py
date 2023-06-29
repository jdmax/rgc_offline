#!/usr/bin/python

import shelve
from optparse import OptionParser

path = '/home/jmaxwell/winhome/Dropbox (Personal)/JLab/NMR/Signal_analysis'
input_path = path+"/input"
data_path = path+'/Log'
te_path = input_path+"/te_final"
material_file = input_path+"/material_table.txt"
te_file = input_path+"/te_table.txt"

current_cut = 4 # nA, any lower, and it counts as off

time_fh = open("pol_v_time.txt","w")
freq_fh = open("freq_vs_dose.txt","w")
anneal_fh = open("anneals_at_dose.txt","w")

all_total_dose = 0
e_per_nc = int(6.241e9)  # electrons per nanocoloumb
cup_area = 3.1415 # assumes 1 cm radius slow raster, cm^2, change in time?	

timeoffset = 0
gpoffset = 14400

bounds = [5,100,400,495]  # bounds of wings for fit (leftstart, leftstop, rightstart, rightstop)

events = {}
baselines = {}	
event_files = {}
runs = {}
mat_start = {}
materials = {}
tes = {}
currents = {}
anneals = {}
anneal_times = []
parser = OptionParser()
reset_top = 0
reset_bottom = 0

te_shelf = shelve.open('teshelf')
