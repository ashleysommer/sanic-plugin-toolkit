import pytest
from sanic import Sanic
from spf import SanicPluginsFramework

@pytest.fixture
def app(request):
    return Sanic(request.node.name)

@pytest.fixture
def spf(request):
    a = app(request)
    return SanicPluginsFramework(a)
