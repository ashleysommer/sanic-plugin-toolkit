from sanic import Sanic
from sanic.exceptions import InvalidUsage, NotFound, ServerError
from sanic.handlers import ErrorHandler
from sanic.response import text
from sanic_testing import TestManager

from sanic_plugin_toolkit import SanicPlugin, SanicPluginRealm


class TestPlugin(SanicPlugin):
    pass


# The following tests are taken directly from Sanic source @ v0.6.0
# and modified to test the SanicPlugin, rather than Sanic

exception_handler_app = Sanic('test_exception_handler')
test_manager = TestManager(exception_handler_app)
realm = SanicPluginRealm(exception_handler_app)
test_plugin = TestPlugin()


@test_plugin.route('/1')
def handler_1(request):
    raise InvalidUsage("OK")


@test_plugin.route('/2')
def handler_2(request):
    raise ServerError("OK")


@test_plugin.route('/3')
def handler_3(request):
    raise NotFound("OK")


@test_plugin.route('/4')
def handler_4(request):
    # noinspection PyUnresolvedReferences
    foo = bar  # noqa -- F821 undefined name 'bar' is done to throw exception
    return text(foo)


@test_plugin.route('/5')
def handler_5(request):
    class CustomServerError(ServerError):
        pass

    raise CustomServerError('Custom server error')


@test_plugin.route('/6/<arg:int>')
def handler_6(request, arg):
    try:
        foo = 1 / arg
    except Exception as e:
        raise e from ValueError("{}".format(arg))
    return text(foo)


@test_plugin.exception(NotFound, ServerError)
def handler_exception(request, exception):
    return text("OK")


realm.register_plugin(test_plugin)


def test_invalid_usage_exception_handler():
    request, response = test_manager.test_client.get('/1')
    assert response.status == 400


def test_server_error_exception_handler():
    request, response = test_manager.test_client.get('/2')
    assert response.status == 200
    assert response.text == 'OK'


def test_not_found_exception_handler():
    request, response = test_manager.test_client.get('/3')
    assert response.status == 200


def test_text_exception__handler():
    request, response = test_manager.test_client.get('/random')
    assert response.status == 200
    assert response.text == 'OK'


def test_html_traceback_output_in_debug_mode():
    request, response = test_manager.test_client.get('/4', debug=True)
    assert response.status == 500
    html = str(response.body)

    assert ('response = handler(request, *args, **kwargs)' in html) or (
        'response = handler(request, **kwargs)' in html
    )
    assert 'handler_4' in html
    assert 'foo = bar' in html

    try:
        summary_start = html.index("<div class=\"summary\">")
        summary_start += 21
        summary_end = html.index("</div>", summary_start)
    except ValueError:
        # Sanic 20.3 and later uses a cut down HTML5 spec,
        # see here: https://stackoverflow.com/a/25749523
        summary_start = html.index("<div class=summary>")
        summary_start += 19
        summary_end = html.index("</code>", summary_start)
    summary_text = html[summary_start:summary_end]
    summary_text = (
        summary_text.replace("  ", " ")
        .replace("\n", "")
        .replace('\\n', "")
        .replace('\t', "")
        .replace('\\t', "")
        .replace('\\\'', '\'')
        .replace("<b>", "")
        .replace("</b>", "")
        .replace("<p>", "")
        .replace("</p>", "")
        .replace("<code>", "")
        .replace("</code>", "")
        .replace("  ", " ")
    )
    assert "NameError: name \'bar\' is not defined" in summary_text
    assert "while handling path /4" in summary_text


def test_inherited_exception_handler():
    request, response = test_manager.test_client.get('/5')
    assert response.status == 200


def test_chained_exception_handler():
    request, response = test_manager.test_client.get('/6/0', debug=True)
    assert response.status == 500

    html = str(response.body)

    assert ('response = handler(request, *args, **kwargs)' in html) or (
        'response = handler(request, **kwargs)' in html
    )
    assert 'handler_6' in html
    assert 'foo = 1 / arg' in html
    assert 'ValueError' in html
    assert 'The above exception was the direct cause' in html

    try:
        summary_start = html.index("<div class=\"summary\">")
        summary_start += 21
        summary_end = html.index("</div>", summary_start)
    except ValueError:
        # Sanic 20.3 and later uses a cut down HTML5 spec,
        # see here: https://stackoverflow.com/a/25749523
        summary_start = html.index("<div class=summary>")
        summary_start += 19
        summary_end = html.index("</code>", summary_start)
    summary_text = html[summary_start:summary_end]
    summary_text = (
        summary_text.replace("  ", " ")
        .replace("\n", "")
        .replace('\\n', "")
        .replace('\t', "")
        .replace('\\t', "")
        .replace('\\\'', '\'')
        .replace("<b>", "")
        .replace("</b>", "")
        .replace("<p>", "")
        .replace("</p>", "")
        .replace("<code>", "")
        .replace("</code>", "")
        .replace("  ", " ")
    )
    assert "ZeroDivisionError: division by zero " in summary_text
    assert "while handling path /6/0" in summary_text


def test_exception_handler_lookup():
    class CustomError(Exception):
        pass

    class CustomServerError(ServerError):
        pass

    def custom_error_handler():
        pass

    def server_error_handler():
        pass

    def import_error_handler():
        pass

    try:
        ModuleNotFoundError
    except:

        class ModuleNotFoundError(ImportError):
            pass

    try:
        handler = ErrorHandler()
    except TypeError:
        handler = ErrorHandler("auto")
    handler.add(ImportError, import_error_handler)
    handler.add(CustomError, custom_error_handler)
    handler.add(ServerError, server_error_handler)

    assert handler.lookup(ImportError()) == import_error_handler
    assert handler.lookup(ModuleNotFoundError()) == import_error_handler
    assert handler.lookup(CustomError()) == custom_error_handler
    assert handler.lookup(ServerError('Error')) == server_error_handler
    assert handler.lookup(CustomServerError('Error')) == server_error_handler

    # once again to ensure there is no caching bug
    assert handler.lookup(ImportError()) == import_error_handler
    assert handler.lookup(ModuleNotFoundError()) == import_error_handler
    assert handler.lookup(CustomError()) == custom_error_handler
    assert handler.lookup(ServerError('Error')) == server_error_handler
    assert handler.lookup(CustomServerError('Error')) == server_error_handler
