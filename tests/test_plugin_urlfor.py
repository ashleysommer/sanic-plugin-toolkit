from sanic.response import text, redirect
from spf import SanicPlugin


class TestPlugin(SanicPlugin):
    pass


instance = test_plugin = TestPlugin()

@test_plugin.route('/t1')
def t1(request):
    return text("t1")

@test_plugin.route('/t2', with_context=True)
def t2(request, context):
    app = context.app
    url_for = context.url_for
    t1 = url_for('t1')
    return redirect(t1)

def test_plugin_urlfor_1(spf):
    app = spf._app
    spf.register_plugin(test_plugin)
    client = app.test_client
    resp = client.get('/t2')
    assert resp[1].text == 't1'


