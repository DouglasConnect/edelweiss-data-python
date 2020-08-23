"""Usage:
  edelweiss inprogress publish <id> <changelog>

Options:
  -h --help      Show this screen

"""
from docopt import docopt
import json

def run(api, argv, compact=False):
    args = docopt(__doc__, argv=argv)
    dataset = api.get_in_progress_dataset(args['<id>'])
    dataset = dataset.publish(args['<changelog>'])

    print(json.dumps(dataset.encode(), indent=None if compact else 2))
