from sanic import Sanic
from spf import SanicPlugin, SanicPluginsFramework


class TestPlugin(SanicPlugin):
    pass


instance = TestPlugin()

def test_spf_singleton_1(spf):
    """
    Registering the framework twice on the same app should return
    an indentical instance of the spf
    :return:
    """
    app1 = spf._app
    spf.register_plugin(instance)
    spf2 = SanicPluginsFramework(app1)
    assert spf == spf2

def test_spf_singleton_2(spf):
    """
    Registering the framework twice, but with different apps should return
    two different spfs
    :return:
    """
    app1 = spf._app
    app2 = Sanic('test_spf_singleton_2_1')
    spf.register_plugin(instance)
    spf2 = SanicPluginsFramework(app2)
    assert spf != spf2