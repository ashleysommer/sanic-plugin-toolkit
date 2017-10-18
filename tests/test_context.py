from urllib.parse import urlparse
from sanic import Sanic
from sanic.response import text
from sanic.testing import HOST, PORT
from spf import SanicPluginsFramework, SanicPlugin
import pytest


class TestPlugin(SanicPlugin):
    pass

##TODO: Test context stuff
