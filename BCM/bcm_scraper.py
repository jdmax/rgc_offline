import glob
from dateutil import parser

def main():

    files = glob.glob('BCM/*/*/RUN#*')
    dict ={}
    out = open('../BCM_all.txt', 'w')

    for file in files:
        print('Reading', file)
        with open(file, 'r') as f:
            for line in f:
                if 'time' in line or '?' in line: continue
                entries = line.split(',')
                date_time = parser.parse(entries[0])
                current = entries[8].rstrip()

                dict[date_time] = current

    for date in sorted(list(dict.keys()), reverse=False):
        current = dict[date]
        out.write(f'{date.strftime("%m/%d/%Y %H:%M:%S")},{current}\n')
    out.close()

if __name__ == '__main__':
    main()