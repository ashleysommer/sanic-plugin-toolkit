from sanic import Sanic
from sanic.response import text
from spf import SanicPluginsFramework
from examples import my_plugin
from examples import my_blueprint

app = Sanic(__name__)
# mp = MyPlugin(app)  //Legacy registration example
spf = SanicPluginsFramework(my_blueprint.api_v1)

spf.register_plugin(my_plugin)

app.blueprint(my_blueprint.api_v1)

@app.route('/')
def index(request):
    return text("hello world")


if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True)
