import asyncio
from queue import Queue
from sanic.response import json, text, HTTPResponse
from sanic_plugin_toolkit import SanicPlugin, SanicPluginRealm
from unittest.mock import MagicMock

class TestPlugin(SanicPlugin):
    pass

async def stop(app, loop):
    await asyncio.sleep(0.1)
    app.stop()


calledq = Queue()


def set_loop(app, loop):
    loop.add_signal_handler = MagicMock()


def after(app, loop):
    calledq.put(loop.add_signal_handler.called)


def test_register_system_signals(realm):
    """Test if sanic register system signals"""
    app = realm._app
    plugin = TestPlugin()
    @plugin.route("/hello")
    async def hello_route(request):
        return HTTPResponse()

    plugin.listener("after_server_start")(stop)
    plugin.listener("before_server_start")(set_loop)
    plugin.listener("after_server_stop")(after)
    realm.register_plugin(plugin)
    app.run("127.0.0.1", 9999)
    assert calledq.get() is True


def test_dont_register_system_signals(realm):
    """Test if sanic don't register system signals"""
    app = realm._app
    plugin = TestPlugin()
    @plugin.route("/hello")
    async def hello_route(request):
        return HTTPResponse()

    plugin.listener("after_server_start")(stop)
    plugin.listener("before_server_start")(set_loop)
    plugin.listener("after_server_stop")(after)
    realm.register_plugin(plugin)
    app.run("127.0.0.1", 9999, register_sys_signals=False)
    assert calledq.get() is False
