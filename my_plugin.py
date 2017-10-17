from logging import DEBUG
from spf.plugin import SanicPlugin
from sanic.response import text

class MyPlugin(SanicPlugin):
    pass

my_plugin = MyPlugin()

@my_plugin.middleware(priority=6, with_context=True)
def mw1(request, context):
    context['test1'] = "test"
    print("Hello world")


@my_plugin.middleware(priority=7, with_context=True)
def mw2(request, context):
    assert 'test1' in context and context['test1'] == "test"
    context['test2'] = "testb"
    print("Hello world")


@my_plugin.middleware(priority=8, kind='response', relative='pre', with_context=True)
def mw3(request, response, context):
    assert 'test1' in context and context['test1'] == "test"
    assert 'test2' in context and context['test2'] == "testb"
    print("Hello world")


@my_plugin.middleware(priority=2, with_context=True)
def mw4(request, context):
    print(context)
    my_plugin.log(DEBUG, "Hello Middleware")

@my_plugin.route('/test_plugin', with_context=False)
def t1(request):
    c = my_plugin.context
    return text('from plugin!')
