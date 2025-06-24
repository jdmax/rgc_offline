import glob
import json
import yaml


def load_settings():
    '''Load settings from YAML config files'''

    with open('config.yaml') as f:                           # Load settings from YAML files
       config_dict = yaml.load(f, Loader=yaml.FullLoader)
    with open('per_run_overrides.yaml') as f:
       override_dict = yaml.load(f, Loader=yaml.FullLoader)
    return config_dict['settings'], override_dict['options'], override_dict['runs']

def sum_event_stats(settings):

    all_files = glob.glob(f"{settings['proton_data_dir']}/*.txt") \
                + glob.glob(f"{settings['deuteron_data_dir']}/*.txt")
    sum_events = 0
    sum_sweeps = 0

    for eventfile in all_files:
        if 'base' in eventfile or 'current' in eventfile: continue
        print('Parsing file:', eventfile)
        with open(eventfile, 'r') as f:
            for line in f:
                event = json.loads(line)
                sum_events += 1
                sum_sweeps += int(event['sweeps'])

    print("events:", sum_events)
    print("sweeps:", sum_sweeps)

def main():

    settings, options, runs = load_settings()
    sum_event_stats(settings)

if __name__ == '__main__':
    main()