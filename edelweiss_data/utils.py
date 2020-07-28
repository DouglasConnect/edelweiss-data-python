import datetime
import pandas
from typing import Dict, Iterable, Union, List, Optional


def encode_aggregation_filters(aggregation_filters: Dict[str, Iterable[str]]):
    aggregation_filters = aggregation_filters or {}
    return [
        {
            'columnName': column_name,
            'buckets': buckets
        }
        for column_name, buckets in aggregation_filters.items()
    ]


def encode_order_by(order_by: list, ascending: Union[bool, List[bool]]):
    order_by = order_by or []
    if isinstance(ascending, bool):
        ascending = len(order_by) * [ascending]
    elif not (isinstance(ascending, list) and all(isinstance(asc, bool) for asc in ascending)):
        raise ValueError('Argument ascending must be either a boolean or a list of booleans.')
    elif len(ascending) != len(order_by):
        raise ValueError('Argument ascending must be of the same length as order_by.')
    return [
        {
            'expression': expression.encode(),
            'ordering': 'ascending' if ordering else 'descending'
        }
        for expression, ordering in zip(order_by, ascending)
    ]


def decode_aggregations(aggregations):
    buckets = []
    counts = []
    for bucket_name, aggregation in aggregations.items():
        for bucket in aggregation['buckets']:
            buckets.append((bucket_name, bucket['termName']))
            counts.append(bucket['docCount'])
    index = pandas.MultiIndex.from_tuples(buckets, names=['bucket', 'term'])
    return pandas.Series(counts, index=index)


def ensure_compatible_versions(client_version: str, server_version: Optional[str]):
    def parse(version):
        major, minor, patch = version.split('.')
        return int(major), int(minor), int(patch)
    major_client, minor_client, patch_client = parse(client_version)
    major_server, minor_server, patch_server = parse(server_version)
    if major_client != major_server:
        raise ValueError(f'Client API version {client_version} is not compatible with the server API version {server_version}.')
    elif minor_client > minor_server:
        print(f'Python client implements API version {client_version} and may provide features')
        print(f'not supported by the server, which implements API version {server_version}.')
    elif minor_client < minor_server:
        print(f'Python client implements API version {client_version} and does not support all the features')
        print(f'provided by the server, which implements API version {server_version}.')
        print(f'Please update the client to a newer version.')
        raise ValueError(f'Server does not support version {client_version} is not compatible with the API version {server_version}.')
