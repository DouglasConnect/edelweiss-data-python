"""Usage:
  edelweiss published list [--column=<name,jsonpath>]...
        [--aggregation-filter=<name,value...>]...
        [--condition=<json>] [--search-anywhere=<search>]...
        [--descriptions] [--schemas] [--metadata]
        [--limit=<limit>] [--offset=<offset>] [--no-latest-only]

Options:
  -h --help          Show this screen

  --column=<name,jsonpath>
        A column name and json path describing columns in the dataframe
        Example: --column='compound,$.Assay.Compounds[*]."Compound Name"'
        Specifiy many times for multiple columns
  --aggregation-filter=<name,value...>
        Limits the fetched datasets to ones where column values fall into one of the selected buckets.
        The following example returns datasets where both organ is either liver or kidney AND species
        is either mouse or elephant:
        Example: --aggregation-filter=organ,liver,kidney --aggregation-filter=species,mouse,elephant
  --condition=<json>
        Returns only rows matching the edelweiss query epxression
        Example: --condition='{"fuzzySearch": [{"systemColumn": ["description"]}, "covid"]}'
  --search-anywhere=<search>
        Returns only rows that contain the search term in one of their text-like columns.
        E.g. --search-anywhere=covid
        Equivalent to --condition='{"searchAnywhere": "covid"}'

  --descriptions     Include dataset descriptions in the response
  --schemas          Include dataset schemas in the response
  --metadata         Include dataset metadata in the response
  --limit=<limit>    The number of rows to return [default: 100]
  --offset=<offset>  The list offset, used for incremental fetching [default: 0]
  --no-latest-only   Disables the latest-only feature, which returns only latest version of each dataset.

"""
from docopt import docopt
import json
from edelweiss_data import QueryExpression

def reduce_query_expressions(query_expressions):
    ret = None
    for qe in query_expressions:
        ret = qe if ret is None else ret if qe is None else ret & qe
    return ret

def run(api, argv, pretty=False):
    args = docopt(__doc__, argv=argv)
    def parse_filter(f):
        split = f.split(',', 1)
        return (split[0], split[1:])

    search_anywheres = [QueryExpression.search_anywhere(s) for s in args['--search-anywhere']]
    condition = QueryExpression.decode(json.loads(args['--condition'])) if args['--condition'] else None
    condition = reduce_query_expressions(search_anywheres + [condition])

    datasets = api.get_raw_datasets(
        columns=[pair.split(',', 1) for pair in args['--column']],
        condition=condition,
        aggregation_filters=dict(map(parse_filter, args['--aggregation-filter'])),
        include_description=args['--descriptions'],
        include_schema=args['--schemas'], include_metadata=args['--metadata'],
        limit=args['--limit'], latest_only=not args['--no-latest-only'])
    print(json.dumps(datasets, indent=2 if pretty else None))
