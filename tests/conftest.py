import pytest
from sanic import Sanic
from sanic_plugin_toolkit import SanicPluginRealm

def app_with_name(name):
    return Sanic(name)

@pytest.fixture
def app(request):
    return app_with_name(request.node.name)

@pytest.fixture
def realm(request):
    a = app_with_name(request.node.name)
    return SanicPluginRealm(a)
