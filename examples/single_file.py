from sanic import Sanic
from spf import SanicPlugin, SanicPluginsFramework
from sanic.response import text

from logging import DEBUG


class MyPlugin(SanicPlugin):
    def on_registered(self):
        c = self.context
        shared = c.shared
        shared.hello_shared = "test2"
        c.hello1 = "test1"
        _a = c.hello1
        _b = c.hello_shared

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
    print(context)
    my_plugin.log(DEBUG, "Hello Middleware")

@instance.route('/test_plugin', with_context=False)
def t1(request):
    c = my_plugin.context
    return text('from plugin!')




app = Sanic(__name__)
mp = MyPlugin(app)
spf = SanicPluginsFramework(app)
my_plugin = spf.register_plugin(mp)


@app.route('/')
def index(request):
    return text("hello world")

if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True)


