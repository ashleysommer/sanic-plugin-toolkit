from sanic import Sanic
from sanic.response import text

from spf.plugin import SanicPluginsFramework
from my_plugin import my_plugin
from logging import DEBUG

app = Sanic(__name__)
spf = SanicPluginsFramework(app)
my_plugin = spf.register_plugin(my_plugin)


@app.route('/')
def index(request):
    return text("hello world")

if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True)
