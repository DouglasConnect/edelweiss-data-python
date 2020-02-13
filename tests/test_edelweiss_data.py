from edelweiss_data import __version__, API, QueryExpression as Q
import pytest

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import filecmp
import json
import os

# Helper for retrying requests
def requests_retry_session(
    retries=3,
    backoff_factor=0.1,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor, # backoff_factor is used as (backoff_factor * 2**retry_number) seconds
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

@pytest.fixture
def api():
    edelweiss_api_url = 'http://localhost:8000'
    # The edelweiss server or the database may not be up yet so
    # we manually request the /ready endpoint up to 5 times with backoff before
    # we try to initialize the API
    response = requests_retry_session(retries=5).get('{}/ready'.format(edelweiss_api_url))
    response.raise_for_status()

    api = API(edelweiss_api_url)
    api.authenticate(development=True)
    return api

def test_version():
    assert __version__ == '0.2.4'

def test_connection(api):
    assert True

def create_dataset_and_check_data_using_files(api, metadata, datasetname, input_filename, output_filename, output_schema_filename, expected_filename, expected_schema_filename):
    with open (input_filename) as f:
        dataset: PublishedDataset = api.create_published_dataset_from_csv_file(datasetname, f, metadata)
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    with open (output_filename, 'w') as f:
        data = dataset.get_raw_data()
        json.dump(data, f, indent=2, sort_keys=True)
    assert filecmp.cmp(expected_filename, output_filename)
    with open (output_schema_filename, 'w') as f:
        data = dataset.schema.encode()
        json.dump(data, f, indent=2, sort_keys=True)
    assert filecmp.cmp(expected_schema_filename, output_schema_filename)

def create_dataset_and_check_data(api, metadata, datasetname, input_filename, expected_filename, expected_schema_filename):
    with open (input_filename) as f:
        dataset: PublishedDataset = api.create_published_dataset_from_csv_file(datasetname, f, metadata)
    data = dataset.get_raw_data()
    with open (expected_filename, 'r') as f:
        expected = json.load(f)
    assert data == expected
    data = dataset.schema.encode()
    with open (expected_schema_filename, 'r') as f:
        expected = json.load(f)
    assert data == expected

def test_roundtrip(api):
    metadata = {"category": "alpha", "number": 42.0}
    create_dataset_and_check_data(api, metadata, "small1", "tests/files/small1.csv", "tests/files/small1.expected-data.json", "tests/files/small1.expected-schema.json")

def test_dataset_selector(api):
    datasets_filter = Q.search_anywhere("small1")
    datasets = api.get_published_datasets(condition=datasets_filter)
    # Do a very simple assert for now that just checks if we got back a single row
    assert datasets.shape == (1,1)
