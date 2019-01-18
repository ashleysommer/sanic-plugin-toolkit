import pytest
import pickle
from sanic import Sanic
from spf import SanicPluginsFramework
from spf.context import ContextDict


##TODO: Test context stuff



def test_context_pickle():
    app = Sanic()
    spf = SanicPluginsFramework(app)
    context = ContextDict(spf, None)
    child_context = context.create_child_context()
    child_context['t1'] = "hello world"
    p_bytes = pickle.dumps(child_context)
    un_p = pickle.loads(p_bytes)
    # the spf and the parent context are not the same as before, because
    # their state got pickled and unpicked too
    assert un_p._spf != spf
    assert un_p._parent_context != context
    assert un_p['t1'] == "hello world"

def test_context_replace():
    app = Sanic()
    spf = SanicPluginsFramework(app)
    context = ContextDict(spf, None)
    child_context = context.create_child_context()

    context['t1'] = "hello world"
    assert child_context['t1'] == "hello world"
    child_context['t1'] = "goodbye world"
    assert context['t1'] != "goodbye world"
    del(child_context['t1'])
    child_context.replace('t1', 'goodbye world')
    assert context['t1'] == "goodbye world"

def test_context_update():
    app = Sanic()
    spf = SanicPluginsFramework(app)
    context = ContextDict(spf, None)
    child_context = context.create_child_context()

    context['t1'] = "hello world"
    child_context['t2'] = "hello2"
    assert child_context['t1'] == "hello world"
    child_context.update({'t1': "test1", 't2': "test2"})
    assert context['t1'] == "test1"
    assert child_context['t2'] == "test2"
