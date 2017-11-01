from sanic import Sanic
from sanic.response import text
from spf import SanicPluginsFramework
#from examples.my_plugin import my_plugin
from examples import my_plugin
from examples.my_plugin import MyPlugin
from logging import DEBUG

app = Sanic(__name__)
mp = MyPlugin(app)
spf = SanicPluginsFramework(app)
my_plugin = spf.register_plugin(my_plugin)


@app.route('/')
def index(request):
    return text("hello world")

if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True)
