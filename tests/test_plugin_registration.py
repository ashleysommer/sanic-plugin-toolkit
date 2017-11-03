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

def test_legacy_registration_2():
    app = Sanic('test_legacy_registration_2')
    # legacy style import, without declaring spf first
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
    assert exc.args and len(exc.args) > 1 and exc.args[1] == plug1

def test_duplicate_legacy_registration():
    app1 = Sanic('test_duplicate_legacy_registration_1')
    app2 = Sanic('test_duplicate_legacy_registration_2')
    # legacy style import
    plugin1 = TestPlugin(app1)
    baseline_reg_count = len(plugin1.registrations)
    plugin2 = TestPlugin(app2)
    assert len(plugin1.registrations) == baseline_reg_count + 1
    assert plugin1 == plugin2