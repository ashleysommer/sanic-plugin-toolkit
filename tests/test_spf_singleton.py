from sanic import Sanic
from spf import SanicPlugin, SanicPluginsFramework


class TestPlugin(SanicPlugin):
    pass


instance = TestPlugin()

def test_spf_singleton_1():
    """
    Registering the framework twice on the same app should return
    an indentical instance of the spf
    :return:
    """
    app = Sanic('test_spf_singleton_1')
    spf = SanicPluginsFramework(app)
    spf.register_plugin(instance)

    spf2 = SanicPluginsFramework(app)
    assert spf == spf2

def test_spf_singleton_2():
    """
    Registering the framework twice, but with different apps should return
    two different spfs
    :return:
    """
    app1 = Sanic('test_spf_singleton_2_1')
    spf1 = SanicPluginsFramework(app1)
    app2 = Sanic('test_spf_singleton_2_1')
    spf1.register_plugin(instance)
    spf2 = SanicPluginsFramework(app2)
    assert spf1 != spf2