"""Usage:
  edelweiss inprogress update <id>
            [--name=<name>]
            [--csv=<filename> | --from=<dataset-id>]
            [--metadata=<json> | --metadata-file=<filename.json>]
            [--schema=<json> | --schema-file=<filename.json> | --infer-schema]
            [--description=<text> | --description-file=<filename.md> ]

Update an in-progress dataset

Options:
  -h --help          Show this screen

  --name=<name>
        Name of the dataset.

  --csv=<csv>
        Path to a csv file to upload e.g. --csv=./data.csv
  --from=<dataset-id> 
        Copy data from an existing data source

  --metadata=<json>
        Metadata to attach to this dataset
  --metadata-file=<filename.json>
        File containing metadata to attach to this datast

  --description=<text>
        Description to attach to this dataset.
  --description-file=<filename.md>
        File containing a description of this dataset in markdown or plain text.

  --schema=<json>
        Schema definition of this dataset
  --schema-file=<filename.json>
        File containing the schema definition of this dataset
  --infer-schema
        Let the server infer the schema
"""
from docopt import docopt
import json
import os
from edelweiss_data import Schema

def run(api, argv, pretty=False):
    args = docopt(__doc__, argv=argv)

    dataset = api.get_in_progress_dataset(args['<id>'])

    source = api.get_published_dataset(args['--from']) if args['--from'] else None

    if args['--metadata']:
        metadata = json.loads(args['--metadata'])
    elif args['--metadata-file']:
        with open(args['--metadata-file']) as fh:
            metadata = json.load(fh)
    else:
        metadata = None

    if args['--schema']:
        schema = Schema.decode(json.loads(args['--schema']))
    elif args['--schema-file']:
        with open(args['--schema-file']) as fh:
            schema = Schema.decode(json.load(fh))
    else:
        schema = None

    if args['--description']:
        description = args['--description']
    elif args['--description-file']:
        with open(args['--description-file']) as fh:
            description = fh.read()
    else:
        description = None

    name = args['--name'] if args['--name'] else None

    if args['--csv']:
        with open(args['--csv']) as fh:
            dataset.upload_data(fh)

    if metadata or schema or description or source or name:
        dataset.update(
                metadata=metadata,
                schema=schema,
                description=description,
                data_source=source,
                name=name
            )

    if args['--infer-schema']:
        dataset.infer_schema()

    print(json.dumps(dataset.encode(), indent=2 if pretty else None))

