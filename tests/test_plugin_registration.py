from sanic import Sanic
from spf import SanicPlugin, SanicPluginsFramework


class TestPlugin(SanicPlugin):
    pass


instance = TestPlugin()


def test_legacy_registration_1():
    app = Sanic('test_legacy_registration_1')
    spf = SanicPluginsFramework(app)
    # legacy style import
    plugin = TestPlugin(app)
    assert plugin == instance


def test_duplicate_registration_1():
    app = Sanic('test_duplicate_registration_1')
    spf = SanicPluginsFramework(app)
    plug1 = spf.register_plugin(instance)
    exc = None
    try:
        plug2 = spf.register_plugin(instance)
        assert not plug2
    except Exception as e:
        exc = e
    assert isinstance(exc, ValueError)

