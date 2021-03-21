from sanic import Sanic
from sanic.response import text
from sanic_plugin_toolkit import SanicPluginRealm
from examples import my_plugin
from examples import my_blueprint

app = Sanic(__name__)
# mp = MyPlugin(app)  //Legacy registration example
realm = SanicPluginRealm(my_blueprint.api_v1)

realm.register_plugin(my_plugin)

app.blueprint(my_blueprint.api_v1)

@app.route('/')
def index(request):
    return text("hello world")


if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True, auto_reload=False)
