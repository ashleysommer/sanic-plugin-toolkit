import pickle

from sanic import Sanic
from sanic_plugin_toolkit import SanicPlugin, SanicPluginRealm
from sanic.response import text

from logging import DEBUG


class MyPlugin(SanicPlugin):

    def __init__(self, *args, **kwargs):
        super(MyPlugin, self).__init__(*args, **kwargs)


instance = MyPlugin()

@instance.middleware(priority=6, with_context=True, attach_to="cleanup")
def mw1(request, context):
    context['test1'] = "test"
    print("Doing Cleanup!")


app = Sanic(__name__)
realm = SanicPluginRealm(app)
assoc_reg = realm.register_plugin(instance)

@app.route('/')
def index(request):
    return text("hello world")

@app.websocket('/test1')
async def we_test(request, ws):
    print("hi")
    return


if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True, auto_reload=False)


