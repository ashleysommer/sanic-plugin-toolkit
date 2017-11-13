# -*- coding: utf-8 -*-
from functools import partial, update_wrapper
from inspect import isawaitable, ismodule
from queue import PriorityQueue
import importlib
import logging
import re
from sanic import Sanic, Blueprint
from uuid import uuid1
from spf.context import ContextDict
from spf.plugin import SanicPlugin, PluginRegistration


def to_snake_case(name):
    """
    Simple helper function.
    Changes PascalCase, camelCase, and CAPS_CASE to snake_case.
    :param name: variable name to convert
    :type name: str
    :return: the name of the variable, converted to snake_case
    :rtype: str
    """
    s1 = to_snake_case.first_cap_re.sub(r'\1_\2', name)
    return to_snake_case.all_cap_re.sub(r'\1_\2', s1).lower()


to_snake_case.first_cap_re = re.compile('(.)([A-Z][a-z]+)')
to_snake_case.all_cap_re = re.compile('([a-z0-9])([A-Z])')


class SanicPluginsFramework(object):
    __slots__ = ('_running', '_logger', '_app', '_plugin_names', '_contexts',
                 '_pre_request_middleware', '_post_request_middleware',
                 '_pre_response_middleware', '_post_response_middleware',
                 '_loop', '__weakref__')

    def log(self, level, message, reg=None, *args, **kwargs):
        if reg is not None:
            (_, n, _) = reg
            message = "{:s}: {:s}".format(str(n), str(message))
        return self._logger.log(level, message, *args, **kwargs)

    def url_for(self, view_name, *args, reg=None, **kwargs):
        if reg is not None:
            (spf, name, url_prefix) = reg
            view_name = "{}.{}".format(name, view_name)
        app = self._app
        if app is None:
            return None
        if isinstance(app, Blueprint):
            view_name = "{}.{}".format(app.name, view_name)
        return app.url_for(view_name, *args, **kwargs)

    def get_plugin(self, plugin):
        reg = plugin.find_plugin_registration(self)
        (_, name, _) = reg
        _p_context = self._plugins_context
        try:
            _plugin_reg = _p_context[name]
        except KeyError as k:
            self.log(logging.WARNING, "Plugin not found!")
            raise k
        try:
            inst = _plugin_reg['instance']
        except KeyError:
            self.log(logging.WARNING, "Plugin is not registered properly")
            inst = None
        return inst

    def register_plugin(self, plugin, *args, name=None, skip_reg=False,
                        **kwargs):
        assert not self._running, "Cannot add, remove, or change plugins " \
                                  "after the App has started serving."
        assert plugin, "Plugin must be a valid type! Do not pass in `None` " \
                       "or `False`"

        if isinstance(plugin, type):
            # We got passed in a Class. That's ok, we can handle this!
            module_name = getattr(plugin, '__module__')
            class_name = getattr(plugin, '__name__')
            lower_class = to_snake_case(class_name)
            try:
                mod = importlib.import_module(module_name)
                try:
                    plugin = mod.getattr(lower_class)
                except AttributeError:
                    plugin = mod  # try the module-based resolution next
            except ImportError:
                raise

        if ismodule(plugin):
            # We got passed in a module. That's ok, we can handle this!
            try:  # look for '.instance' on the module
                plugin = getattr(plugin, 'instance')
                assert plugin is not None
            except (AttributeError, AssertionError):
                # now look for the same name,
                # like my_module.my_module on the module.
                try:
                    plugin_module_name = getattr(plugin, '__name__')
                    assert plugin_module_name and len(plugin_module_name) > 0
                    plugin_module_name = plugin_module_name.split('.')[-1]
                    plugin = getattr(plugin, plugin_module_name)
                    assert plugin is not None
                except (AttributeError, AssertionError):
                    raise RuntimeError(
                        "Cannot import this module as a Sanic Plugin.")

        assert isinstance(plugin, SanicPlugin),\
            "Plugin must be derived from SanicPlugin"
        if name is None:
            try:
                name = str(plugin.__class__.__name__)
                assert name is not None
            except (AttributeError, AssertionError, ValueError, KeyError):
                self._logger.warning(
                    "Cannot determine a name for {}, using UUID."
                    .format(repr(plugin)))
                name = str(uuid1(None, None))
        assert isinstance(name, str), \
            "Plugin name must be a python unicode string!"

        associated_tuple = plugin.AssociatedTuple

        if name in self._plugin_names:  # we're already registered on this SPF
            reg = plugin.find_plugin_registration(self)
            assoc = associated_tuple(plugin, reg)
            raise ValueError(
                "Plugin {:s} is already registered!".format(name), assoc)
        if plugin.is_registered_on_framework(self):
            raise RuntimeError("Plugin already shows it is registered to this "
                               "spf.")
        self._plugin_names.add(name)
        shared_context = self.shared_context
        self._contexts[name] = context = ContextDict(
            self, shared_context, {'shared': shared_context})
        _p_context = self._plugins_context
        _plugin_reg = _p_context.get(name, None)
        if _plugin_reg is None:
            _p_context[name] = _plugin_reg = _p_context.create_child_context()
        _plugin_reg['name'] = name
        _plugin_reg['context'] = context
        if skip_reg:
            dummy_reg = PluginRegistration(spf=self, plugin_name=name,
                                           url_prefix=None)
            context['log'] = partial(self.log, reg=dummy_reg)
            context['url_for'] = partial(self.url_for, reg=dummy_reg)
            plugin.registrations.add(dummy_reg)
            # This indicates the plugin is not registered on the app
            _plugin_reg['instance'] = None
            _plugin_reg['reg'] = None
            return associated_tuple(plugin, dummy_reg)
        if _plugin_reg.get('instance', False):
            raise RuntimeError("The plugin we are trying to register already "
                               "has a known instance!")
        reg = self._register_helper(plugin, context, *args, _spf=self,
                                    _plugin_name=name, **kwargs)
        _plugin_reg['instance'] = plugin
        _plugin_reg['reg'] = reg
        return associated_tuple(plugin, reg)

    @staticmethod
    def _register_helper(plugin, context, *args, _spf=None, _plugin_name=None,
                         _url_prefix=None, **kwargs):
        error_str = "Plugin must be initialised using the " \
                    "Sanic Plugins Framework"
        assert _spf is not None, error_str
        assert _plugin_name is not None, error_str
        _app = _spf._app
        assert _app is not None, error_str

        reg = PluginRegistration(spf=_spf, plugin_name=_plugin_name,
                                 url_prefix=_url_prefix)
        context['log'] = partial(_spf.log, reg=reg)
        context['url_for'] = partial(_spf.url_for, reg=reg)
        continue_flag = plugin.on_before_registered(context, *args, **kwargs)
        if continue_flag is False:
            return plugin

        # Routes
        for r in plugin._routes:
            # attach the plugin name to the handler so that it can be
            # prefixed properly in the router
            if isinstance(_app, Blueprint):
                # blueprint always handles adding __blueprintname__
                # So we identify ourselves here a different way.
                handler_name = r.handler.__name__
                r.handler.__name__ = "{}.{}".format(_plugin_name, handler_name)
            else:
                r.handler.__blueprintname__ = _plugin_name
            # Prepend the plugin URI prefix if available
            uri = _url_prefix + r.uri if _url_prefix else r.uri
            _spf._plugin_register_route(
                r.handler, plugin, context,
                uri[1:] if uri.startswith('//') else uri, *r.args, **r.kwargs)

        # Middleware
        for m in plugin._middlewares:
            _spf._plugin_register_middleware(
                m.middleware, plugin, context, *m.args, **m.kwargs)

        # Exceptions
        for e in plugin._exceptions:
            _spf._plugin_register_exception(
                e.handler, plugin, context, *e.exceptions, **e.kwargs)

        # Listeners
        for event, listeners in plugin._listeners.items():
            for listener in listeners:
                _spf._plugin_register_listener(event, listener, plugin)

        # # this should only ever run once!
        plugin.registrations.add(reg)
        plugin.on_registered(context, reg, *args, **kwargs)

        return reg

    def _plugin_register_route(self, handler, plugin, context, uri, *args,
                               with_context=False, **kwargs):
        if with_context:
            h_name = handler.__name__
            try:
                bp = handler.__blueprintname__
            except AttributeError:
                bp = False
            handler = partial(handler, context=context)
            handler.__name__ = h_name
            if bp:
                handler.__blueprintname__ = bp
        return self._app.route(uri, *args, **kwargs)(handler)

    def _plugin_register_exception(self, handler, plugin, context, *exceptions,
                                   with_context=False, **kwargs):
        if with_context:
            handler = partial(handler, context=context)
        return self._app.exception(*exceptions)(handler)

    def _plugin_register_middleware(self, middleware, plugin, context, *args,
                                    priority=5, relative=None, attach_to=None,
                                    with_context=False, **kwargs):
        assert isinstance(priority, int), "Priority must be an integer!"
        assert 0 <= priority <= 9,\
            "Priority must be between 0 and 9 (inclusive), " \
            "0 is highest priority, 9 is least."
        assert isinstance(plugin, SanicPlugin), \
            "Plugin middleware only works with a plugin from SPF."
        if len(args) > 0 and isinstance(args[0], str) and attach_to is None:
            # for backwards/sideways compatibility with Sanic,
            # the first arg is interpreted as 'attach_to'
            attach_to = args[0]
        if with_context:
            middleware = partial(middleware, context=context)
        if attach_to is None or attach_to == "request":
            insert_order =\
                self._pre_request_middleware.qsize() + \
                self._post_request_middleware.qsize()
            priority_middleware = (priority, insert_order, middleware)
            if relative is None or relative == 'pre':
                # plugin request middleware default to pre-app middleware
                self._pre_request_middleware.put_nowait(priority_middleware)
            else:  # post
                assert relative == "post",\
                    "A request middleware must have relative = pre or post"
                self._post_request_middleware.put_nowait(priority_middleware)
        else:  # response
            assert attach_to == "response",\
                "A middleware kind must be either request or response."
            insert_order = \
                self._post_response_middleware.qsize() + \
                self._pre_response_middleware.qsize()
            # so they are sorted backwards
            priority_middleware = (0-priority, 0.0-insert_order, middleware)
            if relative is None or relative == 'post':
                # plugin response middleware default to post-app middleware
                self._post_response_middleware.put_nowait(priority_middleware)
            else:  # pre
                assert relative == "pre",\
                    "A response middleware must have relative = pre or post"
                self._pre_response_middleware.put_nowait(priority_middleware)
        return middleware

    def _plugin_register_listener(self, event, listener, plugin):
        return self._app.listener(event)(listener)

    @property
    def _plugins_context(self):
        try:
            return self._contexts['_plugins']
        except (AttributeError, KeyError):
            raise RuntimeError("SPF does not have a valid plugins context!")

    @property
    def shared_context(self):
        try:
            return self._contexts['shared']
        except (AttributeError, KeyError):
            raise RuntimeError("SPF does not have a valid shared context!")

    def get_context(self, context=None):
        context = context or 'shared'
        try:
            _context = self._contexts[context]
        except KeyError:
            self._logger.error("Context {:s} does not exist!")
            return None
        return _context

    def get_from_context(self, item, context=None):
        context = context or 'shared'
        try:
            _context = self._contexts[context]
        except KeyError:
            self._logger.warning(
                "Context {:s} does not exist! Falling back to shared context"
                .format(context))
            _context = self._contexts['shared']
        return _context.__getitem__(item)

    def create_temporary_request_context(self, request):
        request_hash = id(request)
        new_ctx = ContextDict(self, None, {})
        shared_context = self.shared_context
        shared_request = shared_context.get('request', False)
        if not shared_request:
            shared_context['request'] = shared_request = new_ctx
        shared_request[request_hash] =\
            ContextDict(self, None, {'request': request})
        for name, _p in self._plugins_context.items():
            if isinstance(_p, ContextDict) and 'instance' in _p \
                    and isinstance(_p['instance'], SanicPlugin):
                if 'context' in _p and isinstance(_p['context'], ContextDict):
                    _p_context = _p['context']
                    p_request = _p_context.get('request', False)
                    if not p_request:
                        _p_context['request'] = p_request = ContextDict(
                            self, None, {})
                    p_request[request_hash] =\
                        ContextDict(self, None, {'request': request})

    def delete_temporary_request_context(self, request):
        request_hash = id(request)
        shared_context = self.shared_context
        try:
            _shared_request = shared_context['request']
            del _shared_request[request_hash]
            if len(_shared_request) < 1:
                del shared_context['request']
        except KeyError:
            pass
        for name, _p in self._plugins_context.items():
            if isinstance(_p, ContextDict) and 'instance' in _p \
                    and isinstance(_p['instance'], SanicPlugin):
                if 'context' in _p and isinstance(_p['context'], ContextDict):
                    _p_context = _p['context']
                    try:
                        _p_request = _p['context']['request']
                        del _p_request[request_hash]
                        if len(_p_request) < 1:
                            del _p_context['request']
                    except KeyError:
                        pass

    async def _run_request_middleware(self, request):
        assert self._running,\
            "App must be running before you can run middleware!"
        self.create_temporary_request_context(request)
        if self._pre_request_middleware:
            for (_pri, _ins, middleware) in self._pre_request_middleware:
                response = middleware(request)
                if isawaitable(response):
                    response = await response
                if response:
                    return response
        if self._app.request_middleware:
            for middleware in self._app.request_middleware:
                response = middleware(request)
                if isawaitable(response):
                    response = await response
                if response:
                    return response
        if self._post_request_middleware:
            for (_pri, _ins, middleware) in self._post_request_middleware:
                response = middleware(request)
                if isawaitable(response):
                    response = await response
                if response:
                    return response
        return None

    async def _run_response_middleware(self, request, response):
        if self._pre_response_middleware:
            for (_pri, _ins, middleware) in self._pre_response_middleware:
                _response = middleware(request, response)
                if isawaitable(_response):
                    _response = await _response
                if _response:
                    response = _response
                    break
        if self._app.response_middleware:
            for middleware in self._app.response_middleware:
                _response = middleware(request, response)
                if isawaitable(_response):
                    _response = await _response
                if _response:
                    response = _response
                    break
        if self._post_response_middleware:
            for (_pri, _ins, middleware) in self._post_response_middleware:
                _response = middleware(request, response)
                if isawaitable(_response):
                    _response = await _response
                if _response:
                    response = _response
                    break
        self.delete_temporary_request_context(request)
        return response

    def _on_before_server_start(self, app, loop=None):
        if not isinstance(self._app, Blueprint):
            assert self._app == app,\
                    "Sanic Plugins Framework is not assigned to the correct " \
                    "Sanic App!"
        assert loop,\
            "Sanic server did not give us a loop to use! " \
            "Check for app updates, you might out of date."
        self._loop = loop
        if self._running:
            # during testing, this will be called _many_ times.
            return  # Ignore if this is already called.
        self._running = True
        # sort and freeze these
        self._pre_request_middleware = \
            tuple(self._pre_request_middleware.get()
                  for _ in range(self._pre_request_middleware.qsize()))
        self._post_request_middleware = \
            tuple(self._post_request_middleware.get()
                  for _ in range(self._post_request_middleware.qsize()))
        self._pre_response_middleware = \
            tuple(self._pre_response_middleware.get()
                  for _ in range(self._pre_response_middleware.qsize()))
        self._post_response_middleware = \
            tuple(self._post_response_middleware.get()
                  for _ in range(self._post_response_middleware.qsize()))

    def _patch_app(self, app):
        # monkey patch the app!
        app._run_request_middleware = self._run_request_middleware
        app._run_response_middleware = self._run_response_middleware
        app.listener('before_server_start')(self._on_before_server_start)
        app.config['__SPF_INSTANCE'] = self

    def _patch_blueprint(self, bp):
        # monkey patch the blueprint!
        # Caveat! We cannot take over the sanic middleware runner when
        # app is a blueprint. We will do this a different way.
        _spf = self

        async def run_bp_pre_request_mw(request):
            nonlocal _spf
            _spf.create_temporary_request_context(request)
            if _spf._pre_request_middleware:
                for (_pri, _ins, middleware) in _spf._pre_request_middleware:
                    response = middleware(request)
                    if isawaitable(response):
                        response = await response
                    if response:
                        return response

        async def run_bp_post_request_mw(request):
            nonlocal _spf
            if _spf._post_request_middleware:
                for (_pri, _ins, middleware) in _spf._post_request_middleware:
                    response = middleware(request)
                    if isawaitable(response):
                        response = await response
                    if response:
                        return response

        async def run_bp_pre_response_mw(request, response):
            nonlocal _spf
            if _spf._pre_response_middleware:
                for (_pri, _ins, middleware) in _spf._pre_response_middleware:
                    _response = middleware(request, response)
                    if isawaitable(_response):
                        _response = await _response
                    if _response:
                        response = _response
                        break

        async def run_bp_post_response_mw(request, response):
            nonlocal _spf
            if _spf._post_response_middleware:
                for (_pri, _ins, middleware) in _spf._post_response_middleware:
                    _response = middleware(request, response)
                    if isawaitable(_response):
                        _response = await _response
                    if _response:
                        response = _response
                        break
            _spf.delete_temporary_request_context()

        orig_register = bp.register

        def bp_register(bp_self, app, options):
            nonlocal orig_register
            from sanic.blueprints import FutureMiddleware as BPFutureMW
            pre_request = BPFutureMW(run_bp_pre_request_mw, args=(),
                                     kwargs={'attach_to': 'request'})
            post_request = BPFutureMW(run_bp_post_request_mw, args=(),
                                      kwargs={'attach_to': 'request'})
            pre_response = BPFutureMW(run_bp_pre_response_mw, args=(),
                                      kwargs={'attach_to': 'response'})
            post_response = BPFutureMW(run_bp_post_response_mw, args=(),
                                       kwargs={'attach_to': 'response'})
            # this order is very important. Don't change it. It is correct.
            bp_self.middlewares.insert(0, post_response)
            bp_self.middlewares.insert(0, pre_request)
            bp_self.middlewares.append(post_request)
            bp_self.middlewares.append(pre_response)

            orig_register(app, options)
        bp.register = update_wrapper(partial(bp_register, bp), orig_register)
        setattr(bp, '__SPF_INSTANCE', self)
        bp.listener('before_server_start')(self._on_before_server_start)

    def __new__(cls, app, *args, **kwargs):
        assert app, "SPF must be given a valid Sanic App to work with."
        assert isinstance(app, Sanic) or isinstance(app, Blueprint),\
            "SPF only works with Sanic Apps or Blueprints. " \
            "Please pass in an app instance to the SPF constructor."
        # An app _must_ only have one spf instance associated with it.
        # If there is already one registered on the app, return that one.
        try:
            instance = app.config['__SPF_INSTANCE']
            assert isinstance(instance, cls),\
                "This app is already registered to a different type of " \
                "Sanic Plugins Framework!"
            return instance
        except AttributeError:  # app must then be a blueprint
            try:
                instance = getattr(app, '__SPF_INSTANCE')
                assert isinstance(instance, cls),\
                    "This Blueprint is already registered to a different " \
                    "type of Sanic Plugins Framework!"
                return instance
            except AttributeError:
                pass
        except KeyError:
            pass
        self = super(SanicPluginsFramework, cls).__new__(cls)
        self._running = False
        self._app = app
        self._logger = logging.getLogger(__name__)
        self._plugin_names = set()
        # these PQs get replaced with frozen tuples at runtime
        self._pre_request_middleware = PriorityQueue()
        self._post_request_middleware = PriorityQueue()
        self._pre_response_middleware = PriorityQueue()
        self._post_response_middleware = PriorityQueue()
        self._contexts = ContextDict(self, None)
        self._contexts['shared'] = ContextDict(self, None, {'app': app})
        self._contexts['_plugins'] = ContextDict(self, None, {'spf': self})
        if isinstance(app, Blueprint):
            self._patch_blueprint(app)
        else:
            self._patch_app(app)
        return self

    def __init__(self, *args, **kwargs):
        args = list(args)  # tuple is not mutable. Change it to a list.
        if len(args) > 0:
            args.pop(0)  # remove 'app' arg
        assert self._app and self._contexts,\
            "Sanic Plugin Framework as not initialized correctly."
        assert len(args) < 1, \
            "Unexpected arguments passed to the Sanic Plugins Framework."
        assert len(kwargs) < 1, \
            "Unexpected keyword arguments passed to the SanicPluginsFramework."
        super(SanicPluginsFramework, self).__init__(*args, **kwargs)
