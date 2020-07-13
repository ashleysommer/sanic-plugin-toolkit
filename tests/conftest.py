import pytest
from sanic import Sanic
from spf import SanicPluginsFramework

def app_with_name(name):
    return Sanic(name)

@pytest.fixture
def app(request):
    return app_with_name(request.node.name)

@pytest.fixture
def spf(request):
    a = app_with_name(request.node.name)
    return SanicPluginsFramework(a)
