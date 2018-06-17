from sanic import Sanic
from sanic.response import text
from spf import SanicPluginsFramework
from contextualize import instance as contextualize

app = Sanic(__name__)
spf = SanicPluginsFramework(app)


# You can create a context middlewares _before_ registering the plugin
@contextualize.middleware
def middle1(request, context):
    shared = context.shared
    r = shared.request
    r.hello = "true"


# and with args
@contextualize.middleware(priority=6)
def middle2(request, context):
    shared = context.shared
    r = shared.request
    a_ = r.hello


# You can create a context route _before_ registering the plugin
@contextualize.route('/1')
def index1(request, context):
    shared = context.shared
    _ = shared.request
    return text("hello world")


contextualize = spf.register_plugin(contextualize)


# Or you can create a context route _after_ registering the plugin
@contextualize.middleware
def middle3(request, context):
    shared = context.shared
    r = shared.request
    r.test = "true"


# and with args
@contextualize.middleware(priority=7)
def middle4(request, context):
    shared = context.shared
    r = shared.request
    _ = r.test


# And you can create a context route _after_ registering the plugin
@contextualize.route('/2/<args>')
def index2(request, args, context):
    shared = context.shared
    _ = shared.request
    return text("hello world")


if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True)
