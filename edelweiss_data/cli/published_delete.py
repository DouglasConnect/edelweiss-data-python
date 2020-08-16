"""Usage:
  edelweiss published delete <id>

Options:
  -h --help      Show this screen

"""
from docopt import docopt
import json

def run(api, argv, pretty=False):
    args = docopt(__doc__, argv=argv)
    dataset = api.get_published_dataset(args['<id>'])
    dataset.delete_all_versions()

    print('ok')
