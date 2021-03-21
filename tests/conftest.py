import pytest
import pytest_asyncio

from sanic import Blueprint, Sanic
from sanic_testing import TestManager

from sanic_plugin_toolkit import SanicPluginRealm


def app_with_name(name):
    return Sanic(name)


@pytest.fixture
def app(request):
    return app_with_name(request.node.name)


@pytest.fixture
def realm(request):
    a = app_with_name(request.node.name)
    manager = TestManager(a)
    return SanicPluginRealm(a)


@pytest.fixture
def realm_bp(request):
    a = app_with_name(request.node.name)
    b = Blueprint("TestBP", "blueprint")
    realm = SanicPluginRealm(b)
    manager = TestManager(a)
    return realm, a
