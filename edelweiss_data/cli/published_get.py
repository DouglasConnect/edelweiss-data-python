"""Usage:
  edelweiss published get <id> [<version>] [--simple] [--drop=<key]...

Options:
  -h --help      Show this screen

  --simple       Equivalant to --drop=metadata --drop=description --drop=schema
  --drop=<key>   Do not print the specified key

"""
from docopt import docopt
import json
from edelweiss_data import QueryExpression

def run(api, argv, pretty=False):
    args = docopt(__doc__, argv=argv)
    version = int(args['<version>']) if args['<version>'] is not None else None
    dataset = api.get_published_dataset(args['<id>'], version).encode()
    if args['--simple'] or 'metadata' in args['--drop']:
        del dataset['metadata']
    if args['--simple'] or 'schema' in args['--drop']:
        del dataset['schema']
    if args['--simple'] or 'description' in args['--drop']:
        del dataset['description']

    print(json.dumps(dataset, indent=2 if pretty else None))
