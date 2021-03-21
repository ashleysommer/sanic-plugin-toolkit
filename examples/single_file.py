import pickle

from sanic import Sanic
from sanic_plugin_toolkit import SanicPlugin, SanicPluginRealm
from sanic.response import text

from logging import DEBUG


class MyPlugin(SanicPlugin):
    def on_registered(self, context, reg, *args, **kwargs):
        shared = context.shared
        shared.hello_shared = "test2"
        context.hello1 = "test1"
        _a = context.hello1
        _b = context.hello_shared

    def __init__(self, *args, **kwargs):
        super(MyPlugin, self).__init__(*args, **kwargs)


instance = MyPlugin()

@instance.middleware(priority=6, with_context=True)
def mw1(request, context):
    context['test1'] = "test"
    print("Hello world")


@instance.middleware(priority=7, with_context=True)
def mw2(request, context):
    assert 'test1' in context and context['test1'] == "test"
    context['test2'] = "testb"
    print("Hello world")


@instance.middleware(priority=8, attach_to='response', relative='pre',
                     with_context=True)
def mw3(request, response, context):
    assert 'test1' in context and context['test1'] == "test"
    assert 'test2' in context and context['test2'] == "testb"
    print("Hello world")


@instance.middleware(priority=2, with_context=True)
def mw4(request, context):
    log = context.log
    print(context)
    log(DEBUG, "Hello Middleware")

@instance.route('/test_plugin', with_context=False)
def t1(request):
    return text('from plugin!')


app = Sanic(__name__)
mp = MyPlugin(app)
realm = SanicPluginRealm(app)
try:
    assoc_reg = realm.register_plugin(MyPlugin)  # already registered! (line 57)
except ValueError as ve:
    assoc_reg = ve.args[1]

@app.route('/')
def index(request):
    return text("hello world")

if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True, workers=2, auto_reload=False)


