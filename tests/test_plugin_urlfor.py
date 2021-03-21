from sanic.response import redirect, text

from sanic_plugin_toolkit import SanicPlugin


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
    if isinstance(t1, (list, tuple, set)):
        t1 = t1[0]  # On a blueprint, redirect to the first app's one
    return redirect(t1)


def test_plugin_urlfor_1(realm):
    app = realm._app
    realm.register_plugin(test_plugin)
    client = app._test_manager.test_client
    resp = client.get('/t2')
    assert resp[1].text == 't1'


def test_plugin_urlfor_2(realm_bp):
    realm, app = realm_bp
    bp = realm._app
    realm.register_plugin(test_plugin)
    app.blueprint(bp)
    client = app._test_manager.test_client
    resp = client.get("/blueprint/t2")
    assert resp[1].text == 't1'
