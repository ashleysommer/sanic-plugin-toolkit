from sanic import Sanic
from sanic_plugin_toolkit import SanicPlugin, SanicPluginRealm


class TestPlugin(SanicPlugin):
    pass


instance = TestPlugin()

def test_spf_singleton_1(realm):
    """
    Registering the toolkit twice on the same app should return
    an indentical instance of the realm
    :return:
    """
    app1 = realm._app
    realm.register_plugin(instance)
    realm2 = SanicPluginRealm(app1)
    assert realm == realm2

def test_spf_singleton_2(realm):
    """
    Registering the toolkit twice, but with different apps should return
    two different spfs
    :return:
    """
    app1 = realm._app
    app2 = Sanic('test_realm_singleton_2_1')
    realm.register_plugin(instance)
    realm2 = SanicPluginRealm(app2)
    assert realm != realm2
