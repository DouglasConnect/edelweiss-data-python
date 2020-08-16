"""Usage:
  edelweiss inprogress get <id>

Options:
  -h --help      Show this screen

"""
from docopt import docopt
import json

def run(api, argv, pretty=False):
    args = docopt(__doc__, argv=argv)
    dataset = api.get_in_progress_dataset(args['<id>'])

    print(json.dumps(dataset.encode(), indent=2 if pretty else None))
