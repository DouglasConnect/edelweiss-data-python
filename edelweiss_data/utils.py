import datetime
import pandas


def decode_utc_datetime(datetime_string: str) -> datetime.datetime:
    # Python ISO format doesn't seem to support seven digits
    # of microseconds that Edelweiss server returns. To be sure,
    # we chop everything after the third digit (this includes the timezone
    # offset but we assume per convention for this to be Z for UTC time)
    datetime_string = datetime_string[:datetime_string.index('.') + 4]
    # Python 3.7 has a nice function to parse iso datetimes but
    # we want to support python 3.6 as well and avoid additional
    # external dependencies for now (this can change once we have a pip
    # package that manages dependencies for us)
    parsed = datetime.datetime.strptime(datetime_string, '%Y-%m-%dT%H:%M:%S.%f')
    parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def encode_aggregation_filters(aggregation_filters):
    aggregation_filters = aggregation_filters or {}
    return [
        {
            'columnName': column_name,
            'buckets': buckets
        }
        for column_name, buckets in aggregation_filters.items()
    ]


def encode_order_by(order_by, ascending):
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


def ensure_compatible_versions(client_version, server_version):
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
