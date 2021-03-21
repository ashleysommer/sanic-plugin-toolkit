from urllib.parse import urlparse
from sanic import Sanic
from sanic.response import text
from sanic_plugin_toolkit import SanicPluginRealm, SanicPlugin
from sanic_plugin_toolkit.plugins import contextualize
import pytest

from sanic_plugin_toolkit.context import HierDict

def test_contextualize_plugin_route(realm):
    app = realm._app
    ctx = realm.register_plugin(contextualize)

    async def handler(request, context):
        assert isinstance(context, HierDict)
        shared = context.get('shared', None)
        assert shared is not None
        shared_request = shared.get('request', None)
        assert shared_request is not None
        shared_request_ctx = shared_request.get(id(request), None)
        assert shared_request_ctx is not None
        assert isinstance(shared_request_ctx, HierDict)
        r2 = shared_request_ctx.get('request', None)
        assert r2 is not None
        assert r2 == request

        priv_request = context.get('request', None)
        assert priv_request is not None
        priv_request_ctx = priv_request.get(id(request), None)
        assert priv_request_ctx is not None
        assert isinstance(priv_request_ctx, HierDict)
        r3 = priv_request_ctx.get('request', None)
        assert r3 is not None
        assert r3 == request
        assert priv_request_ctx != shared_request_ctx
        return text('OK')

    ctx.route('/')(handler)

    request, response = app._test_manager.test_client.get('/')
    assert response.text == "OK"

def test_contextualize_plugin_middleware(realm):
    app = realm._app
    ctx = realm.register_plugin(contextualize)

    @ctx.middleware(attach_to='request')
    async def mw1(request, context):
        assert isinstance(context, HierDict)
        shared = context.get('shared', None)
        shared_request = shared.get('request', None)
        assert shared_request is not None
        shared_request_ctx = shared_request.get(id(request), None)
        assert shared_request_ctx is not None
        shared_request_ctx['middleware_ran'] = True

    @ctx.route('/')
    async def handler(request, context):
        assert isinstance(context, HierDict)
        shared = context.get('shared', None)
        shared_request = shared.get('request', None)
        shared_request_ctx = shared_request.get(id(request), None)
        middleware_ran = shared_request_ctx.get('middleware_ran', False)
        assert middleware_ran
        return text('OK')

    request, response = app._test_manager.test_client.get('/')
    assert response.text == "OK"
