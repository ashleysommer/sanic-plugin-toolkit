from spf.plugin import SanicPlugin
from sanic.response import text
from logging import DEBUG

class MyPlugin(SanicPlugin):
    def on_before_registered(self, *args, **kwargs):
        c = self.context
        shared = c.shared
        print("Before Registered")

    def on_registered(self, *args, **kwargs):
        c = self.context
        shared = c.shared
        print("After Registered")
        shared.hello_shared = "test2"
        c.hello1 = "test1"
        _a = c.hello1
        _b = c.hello_shared

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
    # logging example!
    my_plugin.log(DEBUG, "Hello Middleware")

@my_plugin.route('/test_plugin', with_context=False)
def t1(request):
    c = my_plugin.context
    return text('from plugin!')

def decorate(app, *args, **kwargs):
    return my_plugin.decorate(app, *args, with_context=True,
                              run_middleware=True, **kwargs)


__all__ = ["my_plugin", "decorate"]

