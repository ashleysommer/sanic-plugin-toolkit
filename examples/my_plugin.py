from sanic_plugin_toolkit.plugin import SanicPlugin
from sanic.response import text
from logging import DEBUG

class MyPlugin(SanicPlugin):
    def on_before_registered(self, context, *args, **kwargs):
        shared = context.shared
        print("Before Registered")

    def on_registered(self, context, reg, *args, **kwargs):
        shared = context.shared
        print("After Registered")
        shared.hello_shared = "test2"
        context.hello1 = "test1"
        _a = context.hello1
        _b = context.hello_shared

    def __init__(self, *args, **kwargs):
        super(MyPlugin, self).__init__(*args, **kwargs)


my_plugin = instance = MyPlugin()

@my_plugin.middleware(priority=6, with_context=True)
def mw1(request, context):
    context['test1'] = "testa"
    print("Hello world")


@my_plugin.middleware(priority=7, with_context=True)
def mw2(request, context):
    assert 'test1' in context and context['test1'] == "testa"
    context['test2'] = "testb"
    print("Hello world")


@my_plugin.middleware(priority=8, attach_to='response', relative='pre',
                      with_context=True)
def mw3(request, response, context):
    assert 'test1' in context and context['test1'] == "testa"
    assert 'test2' in context and context['test2'] == "testb"
    print("Hello world")


@my_plugin.middleware(priority=2, with_context=True)
def mw4(request, context):
    print(context)
    log = context.log
    # logging example!
    log(DEBUG, "Hello Middleware")

@my_plugin.route('/test_plugin', with_context=True)
def t1(request, context):
    print(context)
    return text('from plugin!')

def decorate(app, *args, **kwargs):
    return my_plugin.decorate(app, *args, with_context=True,
                              run_middleware=True, **kwargs)


__all__ = ["my_plugin", "decorate"]

