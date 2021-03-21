from sanic import Sanic
from sanic.response import text

from examples import my_plugin


app = Sanic(__name__)


@app.route('/', methods={'GET', 'OPTIONS'})
@my_plugin.decorate(app)
def index(request, context):
    return text("hello world")


if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True, auto_reload=False)
