from urllib.parse import urlparse
from sanic import Sanic
from sanic.response import text
from sanic.testing import HOST, PORT
from spf import SanicPluginsFramework, SanicPlugin
import pytest


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
