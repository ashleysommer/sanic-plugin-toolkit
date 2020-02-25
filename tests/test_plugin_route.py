from urllib.parse import urlparse
from sanic import Sanic
from sanic.response import text
from sanic.testing import HOST, PORT
from spf import SanicPluginsFramework, SanicPlugin
import pytest

from spf.context import HierDict, SanicContext


class TestPlugin(SanicPlugin):
    pass


# The following tests are taken directly from Sanic source @ v0.6.0
# and modified to test the SanicPluginsFramework, rather than Sanic

@pytest.mark.parametrize(
    'path,query,expected_url', [
        ('/foo', '', 'http://{}:{}/foo'),
        ('/bar/baz', '', 'http://{}:{}/bar/baz'),
        ('/moo/boo', 'arg1=val1', 'http://{}:{}/moo/boo?arg1=val1')
    ])
def test_plugin_url_attributes(spf, path, query, expected_url):
    app = spf._app
    test_plugin = TestPlugin()

    async def handler(request):
        return text('OK')

    test_plugin.route(path)(handler)

    spf.register_plugin(test_plugin)
    request, response = app.test_client.get(path + '?{}'.format(query))
    assert request.url == expected_url.format(HOST, PORT)

    parsed = urlparse(request.url)

    assert parsed.scheme == request.scheme
    assert parsed.path == request.path
    assert parsed.query == request.query_string
    assert parsed.netloc == request.host

def test_plugin_route_context(spf):
    app = spf._app
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

    spf.register_plugin(test_plugin)
    request, response = app.test_client.get('/')
    assert response.text == "OK"