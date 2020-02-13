from edelweiss_data import __version__, API, QueryExpression as Q
import pytest

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

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
        backoff_factor=backoff_factor,
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
    # we manually request the /ready endpoint up to 8 times with backoff before
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
