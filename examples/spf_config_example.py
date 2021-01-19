from sanic import Sanic
from sanic.response import text
from sanic_plugin_toolkit import SanicPluginRealm
from sanic_plugin_toolkit.plugins.contextualize import instance as contextualize

app = Sanic(__name__)
app.config['STK_LOAD_INI'] = True
app.config['STK_INI_FILE'] = 'example_stk.ini'
realm = SanicPluginRealm(app)

# We can get the assoc object from SPF, it is already registered
contextualize = realm.get_plugin_assoc('Contextualize')


@contextualize.middleware
def middle3(request, context):
    shared = context.shared
    r = shared.request
    r.test = "true"


@contextualize.middleware(priority=7)
def middle4(request, context):
    shared = context.shared
    r = shared.request
    _ = r.test


@contextualize.route('/1/<args>')
def index2(request, args, context):
    shared = context.shared
    _ = shared.request
    return text("hello world")


if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True, auto_reload=False)
