from edelweiss_data import __version__, API, QueryExpression as Q

@pytest.fixture
def api():
    edelweiss_api_url = 'http://localhost:8000'
    api = API(edelweiss_api_url)
    api.authenticate(development=True)
    return api

def test_version():
    assert __version__ == '0.2.4'

def test_connection(api):
    assert True
