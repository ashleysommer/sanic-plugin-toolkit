from urllib.parse import urlparse

import pytest

from sanic import Sanic
from sanic.response import text

from sanic_plugin_toolkit import SanicPlugin, SanicPluginRealm


class TestPlugin(SanicPlugin):
    pass


# The following tests are taken directly from Sanic source @ v0.6.0
# and modified to test the SanicPluginsFramework, rather than Sanic


@pytest.mark.parametrize(
    'path,query,expected_url',
    [
        ('/foo', '', 'http://{}:{}/foo'),
        ('/bar/baz', '', 'http://{}:{}/bar/baz'),
        ('/moo/boo', 'arg1=val1', 'http://{}:{}/moo/boo?arg1=val1'),
    ],
)
def test_plugin_ws_url_attributes(realm, path, query, expected_url):
    """Note, this doesn't _really_ test websocket functionality very well."""
    app = realm._app
    test_plugin = TestPlugin()

    async def handler(request):
        return text('OK')

    test_plugin.websocket(path)(handler)
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
