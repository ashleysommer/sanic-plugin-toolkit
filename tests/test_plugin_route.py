from urllib.parse import urlparse

import pytest

from sanic import Sanic
from sanic.response import text

from sanic_plugin_toolkit import SanicPlugin, SanicPluginRealm
from sanic_plugin_toolkit.context import HierDict, SanicContext


class TestPlugin(SanicPlugin):
    pass


@pytest.mark.parametrize(
    'path,query,expected_url',
    [
        ('/foo', '', 'http://{}:{}/foo'),
        ('/bar/baz', '', 'http://{}:{}/bar/baz'),
        ('/moo/boo', 'arg1=val1', 'http://{}:{}/moo/boo?arg1=val1'),
    ],
)
def test_plugin_url_attributes(realm, path, query, expected_url):
    app = realm._app
    test_plugin = TestPlugin()

    async def handler(request):
        return text('OK')

    test_plugin.route(path)(handler)

    realm.register_plugin(test_plugin)
    test_client = app._test_manager.test_client
    request, response = test_client.get(path + '?{}'.format(query))
    try:
        # Sanic 20.3.0 and above
        p = test_client.port
        h = test_client.host
    except AttributeError:
        p = 0
        h = "127.0.0.1"

    assert request.url == expected_url.format(h, str(p))

    parsed = urlparse(request.url)

    assert parsed.scheme == request.scheme
    assert parsed.path == request.path
    assert parsed.query == request.query_string
    assert parsed.netloc == request.host


def test_plugin_route_context(realm):
    app = realm._app
    test_plugin = TestPlugin()

    async def handler(request, context):
        assert isinstance(context, HierDict)
        shared = context.get('shared', None)
        assert shared is not None
        shared_request = shared.get('request', None)
        assert shared_request is not None
        req_id = id(request)
        shared_request = shared_request.get(req_id, None)
        assert shared_request is not None
        assert isinstance(shared_request, HierDict)
        r2 = shared_request.get('request', None)
        assert r2 is not None
        assert r2 == request

        priv_request = context.get('request', None)
        assert priv_request is not None
        priv_request = priv_request.get(req_id, None)
        assert priv_request is not None
        assert isinstance(priv_request, HierDict)
        r3 = priv_request.get('request', None)
        assert r3 is not None
        assert r3 == request
        priv_request2 = context.for_request(request)
        assert priv_request2 is priv_request
        assert priv_request != shared_request
        return text('OK')

    test_plugin.route('/', with_context=True)(handler)

    realm.register_plugin(test_plugin)
    request, response = app._test_manager.test_client.get('/')
    assert response.text == "OK"
