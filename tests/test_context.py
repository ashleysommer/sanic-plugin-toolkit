import pickle
from sanic_plugin_toolkit.context import SanicContext

def test_context_set_contains_get(realm):
    context = SanicContext(realm, None)
    context.set("t1", "hello world")
    assert "t1" in context
    assert context.get("t1") == "hello world"
    exceptions = []
    try:
        context.set("__weakref__", set())
    except ValueError as e:
        exceptions.append(e)
    finally:
        assert len(exceptions) > 0

def test_context_get_private_from_slots(realm):
    context = SanicContext(realm, None)
    context.set("t1", "hello world")
    d = context.__getattr__('_dict')
    d2 = getattr(context, '_dict')
    assert isinstance(d, dict)
    assert "t1" in d
    assert d == d2

def test_context_items_keys_values(realm):
    context = SanicContext(realm, None)
    context["t1"] = "hello world"
    context["t2"] = "hello 2"
    items = context.items()
    assert len(items) == 2
    keys = context.keys()
    assert len(keys) == 2
    assert "t1" in list(keys)
    vals = context.values()
    assert len(vals) == 2
    assert "hello world" in list(vals)

def test_context_pickle(realm):
    context = SanicContext(realm, None)
    child_context = context.create_child_context()
    child_context['t1'] = "hello world"
    p_bytes = pickle.dumps(child_context)
    un_p = pickle.loads(p_bytes)
    # the sanic_plugin_toolkit and the parent context are not the same as before, because
    # their state got pickled and unpicked too
    assert un_p._stk_realm != realm
    assert un_p._parent_hd != context
    assert un_p['t1'] == "hello world"

def test_context_replace(realm):
    context = SanicContext(realm, None)
    child_context = context.create_child_context()
    context['t1'] = "hello world"
    assert child_context['t1'] == "hello world"
    child_context['t1'] = "goodbye world"
    assert context['t1'] != "goodbye world"
    del(child_context['t1'])
    child_context.replace('t1', 'goodbye world')
    assert context['t1'] == "goodbye world"

def test_context_update(realm):
    context = SanicContext(realm, None)
    child_context = context.create_child_context()
    context['t1'] = "hello world"
    child_context['t2'] = "hello2"
    assert child_context['t1'] == "hello world"
    child_context.update({'t1': "test1", 't2': "test2"})
    assert context['t1'] == "test1"
    assert child_context['t2'] == "test2"

def test_context_del(realm):
    context = SanicContext(realm, None)
    context.set(1, "1")
    context.set(2, "2")
    context.set(3, "3")
    context.set(4, "4")
    del context[1]
    one = context.get(1, None)
    assert one is None
    exceptions = []
    try:
        #TODO: How do you even delete a slice?
        del context[2:4]
    except Exception as e:
        exceptions.append(e)
    finally:
        assert len(exceptions) > 0

def test_context_str(realm):
    context = SanicContext(realm, None)
    context['t1'] = "hello world"
    s1 = str(context)
    assert s1 == "SanicContext({'t1': 'hello world'})"

def test_context_repr(realm):
    context = SanicContext(realm, None)
    context['t1'] = "hello world"
    s1 = repr(context)
    assert s1 == "SanicContext({'t1': 'hello world'})"

def test_recursive_dict(realm):
    context = SanicContext(realm, None)
    context['t1'] = "hello world"
    c2 = context.create_child_context()
    c2['t2'] = "hello 2"
    c3 = c2.create_child_context()
    c3['t3'] = "hello 3"
    context._parent_hd = c3  # This is dodgy, why would anyone do this?
    exceptions = []
    try:
        _ = c2['t4']
    except RuntimeError as e:
        assert len(e.args) > 0
        assert "recursive" in str(e.args[0]).lower()
        exceptions.append(e)
    finally:
        assert len(exceptions) == 1
