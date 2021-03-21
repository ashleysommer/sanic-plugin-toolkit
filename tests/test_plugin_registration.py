from sanic import Sanic
from sanic_plugin_toolkit import SanicPlugin, SanicPluginRealm
from sanic_plugin_toolkit.plugin import PluginRegistration, PluginAssociated


class TestPlugin(SanicPlugin):
    pass


instance = TestPlugin()


def test_spf_registration(realm):
    reg = realm.register_plugin(instance)
    assert isinstance(reg, PluginAssociated)
    (plugin, reg) = reg
    assert isinstance(reg, PluginRegistration)
    assert plugin == instance

def test_legacy_registration_1(app):
    # legacy style import
    reg = TestPlugin(app)
    assert isinstance(reg, PluginAssociated)
    (plugin, reg) = reg
    assert isinstance(reg, PluginRegistration)
    assert plugin == instance

def test_legacy_registration_2(app):
    # legacy style import, without declaring sanic_plugin_toolkit first
    reg = TestPlugin(app)
    assert isinstance(reg, PluginAssociated)
    (plugin, reg) = reg
    assert isinstance(reg, PluginRegistration)
    assert plugin == instance

def test_duplicate_registration_1(realm):
    assoc1 = realm.register_plugin(instance)
    exc = None
    try:
        assoc2 = realm.register_plugin(instance)
        assert not assoc2
    except Exception as e:
        exc = e
    assert isinstance(exc, ValueError)
    assert exc.args and len(exc.args) > 1 and exc.args[1] == assoc1

def test_duplicate_legacy_registration():
    app1 = Sanic('test_duplicate_legacy_registration_1')
    app2 = Sanic('test_duplicate_legacy_registration_2')
    # legacy style import
    assoc1 = TestPlugin(app1)
    (plugin1, reg1) = assoc1
    baseline_reg_count = len(plugin1.registrations)
    assoc2 = TestPlugin(app2)
    (plugin2, reg2) = assoc2
    assert len(plugin1.registrations) == baseline_reg_count + 1
    assert plugin1 == plugin2

class TestPlugin2(SanicPlugin):
    pass

test_plugin2 = TestPlugin2()

def test_plugiun_class_registration(realm):
    reg = realm.register_plugin(TestPlugin2)
    assert isinstance(reg, PluginAssociated)
    (plugin, reg) = reg
    assert isinstance(reg, PluginRegistration)
    assert plugin == test_plugin2
