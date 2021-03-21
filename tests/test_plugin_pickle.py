import pickle
from sanic.response import text
from sanic.exceptions import NotFound
from sanic_plugin_toolkit import SanicPlugin


class TestPlugin(SanicPlugin):
    pass


instance = test_plugin = TestPlugin()

@test_plugin.route('/t1')
def t1(request):
    return text("t1")

@test_plugin.exception(NotFound)
def not_found(request):
    return text("404")

def test_plugin_pickle_unpickle(realm):
    app = realm._app
    p1 = pickle.dumps(test_plugin)
    p2 = pickle.loads(p1)
    realm.register_plugin(p2)
    client = app._test_manager.test_client
    resp = client.get('/t1')
    assert resp[1].text == 't1'


