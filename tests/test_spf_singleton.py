from sanic import Sanic
from spf import SanicPlugin, SanicPluginsFramework


class TestPlugin(SanicPlugin):
    pass


instance = TestPlugin()

def test_spf_singleton_1():
    app = Sanic('test_spf_singleton_1')
    spf = SanicPluginsFramework(app)
    spf.register_plugin(instance)

    spf2 = SanicPluginsFramework(app)
    assert spf == spf2
