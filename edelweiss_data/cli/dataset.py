"""Usage:
  edelweiss dataset get <id> [<version>]

Options:
  -h --help          Show this screen
"""
from docopt import docopt
import json

def run(api, argv, pretty=False):
    args = docopt(__doc__, argv=argv)
    if args['get']:
        version = int(args['<version>']) if args['<version>'] is not None else None
        dataset = api.get_published_dataset(args['<id>'], version)
        print(json.dumps(dataset.encode(), indent=2 if pretty else None))
