from distutils.version import LooseVersion
from sanic import __version__ as sanic_version
from sanic.response import text
from spf import SanicPlugin
import pytest

SANIC_VERSION = LooseVersion(sanic_version)

if LooseVersion("19.6.3") <= SANIC_VERSION:

    class TestPlugin(SanicPlugin):
        pass


    @pytest.mark.asyncio
    async def test_request_class_regular(spf):
        app = spf._app
        test_plugin = TestPlugin()

        def regular_request(request):
            return text(request.__class__.__name__)
        test_plugin.route("/regular", methods=('GET',))(regular_request)
        spf.register_plugin(test_plugin)

        _, response = await app.asgi_client.get("/regular")
        assert response.body == b"Request"