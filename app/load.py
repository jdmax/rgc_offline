import h5py


def main():
    """Read all data files and save in more efficient HDF5 format"""

    self.included = glob.glob(f"{self.parent.settings['proton_data_dir']}/*.txt") \
                     + glob.glob(f"{self.parent.settings['deuteron_data_dir']}/*.txt")


    for eventfile in self.included:
        print('Parsing file:', eventfile)
        with open(eventfile, 'r') as f:
            for line in f:
                event = json.loads(line)
                s = event['stop_time']
                line_stoptime = datetime.datetime.strptime(s[:26], '%Y-%m-%d %H:%M:%S.%f')
                #utcstamp = str(event['stop_stamp'])
                utcstamp = event['stop_stamp']
                if self.start < line_stoptime < self.end and 'pol' in event:
                    self.all[utcstamp] = event    # full dictionary from datafile
                    self.all[utcstamp]['stop_time'] = line_stoptime    # full dictionary from datafile


if __name__ == '__main__':
    main()
