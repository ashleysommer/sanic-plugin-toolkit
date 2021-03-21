from sanic import Sanic
from sanic.exceptions import NotFound
from sanic.request import Request
from sanic.response import HTTPResponse, text

from sanic_plugin_toolkit import SanicPlugin, SanicPluginRealm


class TestPlugin(SanicPlugin):
    pass


# The following tests are taken directly from Sanic source @ v0.6.0
# and modified to test the SanicPlugin, rather than Sanic

# ------------------------------------------------------------ #
#  GET
# ------------------------------------------------------------ #


def test_middleware_request(realm):
    app = realm._app
    plugin = TestPlugin()

    results = []

    @plugin.middleware
    async def handler(request):
        results.append(request)

    @plugin.route('/')
    async def handler(request):
        return text('OK')

    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get('/')

    assert response.text == 'OK'
    assert type(results[0]) is Request


def test_middleware_response(realm):
    app = realm._app
    plugin = TestPlugin()
    results = []

    @plugin.middleware('request')
    async def process_response(request):
        results.append(request)

    @plugin.middleware('response')
    async def process_response(request, response):
        results.append(request)
        results.append(response)

    @plugin.route('/')
    async def handler(request):
        return text('OK')

    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get('/')

    assert response.text == 'OK'
    assert type(results[0]) is Request
    assert type(results[1]) is Request
    assert isinstance(results[2], HTTPResponse)


def test_middleware_response_exception(realm):
    app = realm._app
    plugin = TestPlugin()
    result = {'status_code': None}

    @plugin.middleware('response')
    async def process_response(reqest, response):
        result['status_code'] = response.status
        return response

    @plugin.exception(NotFound)
    async def error_handler(request, exception):
        return text('OK', exception.status_code)

    @plugin.route('/')
    async def handler(request):
        return text('FAIL')

    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get('/page_not_found')
    assert response.text == 'OK'
    assert result['status_code'] == 404


def test_middleware_override_request(realm):
    app = realm._app
    plugin = TestPlugin()

    @plugin.middleware
    async def halt_request(request):
        return text('OK')

    @plugin.route('/')
    async def handler(request):
        return text('FAIL')

    realm.register_plugin(plugin)
    _, response = app._test_manager.test_client.get('/', gather_request=False)

    assert response.status == 200
    assert response.text == 'OK'


def test_middleware_override_response(realm):
    app = realm._app
    plugin = TestPlugin()

    @plugin.middleware('response')
    async def process_response(request, response):
        return text('OK')

    @plugin.route('/')
    async def handler(request):
        return text('FAIL')

    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get('/')

    assert response.status == 200
    assert response.text == 'OK'


def test_middleware_order(realm):
    app = realm._app
    plugin = TestPlugin()
    order = []

    @plugin.middleware('request')
    async def request1(request):
        order.append(1)

    @plugin.middleware('request')
    async def request2(request):
        order.append(2)

    @plugin.middleware('request')
    async def request3(request):
        order.append(3)

    @plugin.middleware('response')
    async def response1(request, response):
        order.append(6)

    @plugin.middleware('response')
    async def response2(request, response):
        order.append(5)

    @plugin.middleware('response')
    async def response3(request, response):
        order.append(4)

    @plugin.route('/')
    async def handler(request):
        return text('OK')

    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get('/')

    assert response.status == 200
    assert order == [1, 2, 3, 4, 5, 6]
