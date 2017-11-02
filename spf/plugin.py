# -*- coding: utf-8 -*-
from collections import namedtuple, defaultdict
from functools import partial, update_wrapper
from inspect import isawaitable, ismodule
from queue import PriorityQueue
import importlib
import logging
import re
from sanic import Sanic, Blueprint
from uuid import uuid1
from spf.context import ContextDict


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

FutureMiddleware = namedtuple('Middleware', ['middleware', 'args', 'kwargs'])
FutureRoute = namedtuple('Route', ['handler', 'uri', 'args', 'kwargs'])
FutureException = namedtuple('Exception', ['handler', 'exceptions', 'kwargs'])


class SanicPlugin(object):
    __slots__ = ('_spf', '_plugin_name', '_url_prefix', '_routes',
                 '_middlewares', '_exceptions', '_listeners', '_initialized',
                 '__weakref__')

    # Decorator
    def middleware(self, *args, **kwargs):
        """Decorate and register middleware
        :param args: captures all of the positional arguments passed in
        :type args: tuple(Any)
        :param kwargs: captures the keyword arguments passed in
        :type kwargs: dict(Any)
        :return: The middleware function to use as the decorator
        :rtype: fn
        """
        kwargs.setdefault('priority', 5)
        kwargs.setdefault('relative', None)
        kwargs.setdefault('attach_to', None)
        kwargs.setdefault('with_context', False)
        if len(args) == 1 and callable(args[0]):
            middle_f = args[0]
            self._middlewares.append(
                FutureMiddleware(middle_f, args=tuple(), kwargs=kwargs))
            return middle_f

        def wrapper(middleware_f):
            self._middlewares.append(
                FutureMiddleware(middleware_f, args=args, kwargs=kwargs))
            return middleware_f
        return wrapper

    def exception(self, *args, **kwargs):
        """Decorate and register an exception handler
        :param args: captures all of the positional arguments passed in
        :type args: tuple(Any)
        :param kwargs: captures the keyword arguments passed in
        :type kwargs: dict(Any)
        :return: The exception function to use as the decorator
        :rtype: fn
        """
        if len(args) == 1 and callable(args[0]):
            if isinstance(args[0], type) and issubclass(args[0], Exception):
                pass
            else:
                raise RuntimeError("Cannot use the @exception decorator "
                                   "without arguments")

        def wrapper(handler_f):
            self._exceptions.append(FutureException(handler_f,
                                                    exceptions=args,
                                                    kwargs=kwargs))
            return handler_f
        return wrapper

    def listener(self, event, *args, **kwargs):
        """Create a listener from a decorated function.
        :param event: Event to listen to.
        :type event: str
        :param args: captures all of the positional arguments passed in
        :type args: tuple(Any)
        :param kwargs: captures the keyword arguments passed in
        :type kwargs: dict(Any)
        :return: The exception function to use as the listener
        :rtype: fn
        """
        if len(args) == 1 and callable(args[0]):
            raise RuntimeError("Cannot use the @listener decorator without "
                               "arguments")

        def wrapper(listener_f):
            self._listeners[event].append(listener_f)
            return listener_f
        return wrapper

    def route(self, uri, *args, **kwargs):
        """Create a plugin route from a decorated function.
        :param uri: endpoint at which the route will be accessible.
        :type uri: str
        :param args: captures all of the positional arguments passed in
        :type args: tuple(Any)
        :param kwargs: captures the keyword arguments passed in
        :type kwargs: dict(Any)
        :return: The exception function to use as the decorator
        :rtype: fn
        """
        if len(args) == 0 and callable(uri):
            raise RuntimeError("Cannot use the @route decorator without "
                               "arguments")
        kwargs.setdefault('methods', frozenset({'GET'}))
        kwargs.setdefault('host', None)
        kwargs.setdefault('strict_slashes', False)
        kwargs.setdefault('stream', False)
        # TODO: sanic 0.6.1 (0.7?) will have 'name' on a route
        # #kwargs.setdefault('name', None)

        def wrapper(handler_f):
            self._routes.append(FutureRoute(handler_f, uri, args, kwargs))
            return handler_f
        return wrapper

    def on_before_registered(self, *args, **kwargs):
        pass

    def on_registered(self, *args, **kwargs):
        pass

    @property
    def app(self):
        if self._spf is None:
            return None
        return self._spf._app

    @property
    def context(self):
        try:
            return self._spf.get_context(self._plugin_name)
        except KeyError as k:
            raise k
        except AttributeError:
            raise RuntimeError("Cannot use the plugin's Context before it is "
                               "registered.")

    def url_for(self, view_name, *args, **kwargs):
        app = self.app
        if app is None:
            return None
        if isinstance(app, Blueprint):
            self.warning("Cannot use url_for when plugin is registered "
                         "on a Blueprint. Use `app.url_for` instead.")
            return None
        constructed_name = "{}.{}".format(self._plugin_name, view_name)
        return app.url_for(constructed_name, *args, **kwargs)

    def log(self, level, message, *args, **kwargs):
        return self._spf.log(level, message, *args, plugin=self, **kwargs)

    def debug(self, message, *args, **kwargs):
        return self.log(logging.DEBUG, message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        return self.log(logging.INFO, message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        return self.log(logging.WARNING, message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        return self.log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        return self.log(logging.CRITICAL, message, *args, **kwargs)

    @classmethod
    def decorate(cls, app, *args, run_middleware=True, with_context=False,
                 **kwargs):
        """
        This is a decorator that can be used to apply this plugin to a specific
        route/view on your app, rather than the whole app.
        :param app:
        :param args:
        :param kwargs:
        :return: the decorated route/view
        """
        spf = SanicPluginsFramework(app)  # get the singleton from the app
        try:
            plugin = spf.register_plugin(cls, skip_reg=True)
        except ValueError as e:
            # this is normal, if this plugin has been registered previously
            assert e.args and len(e.args) > 1
            plugin = e.args[1]

        def _decorator(f):
            nonlocal run_middleware, with_context, args, kwargs

            async def wrapper(request, *a, **kw):
                nonlocal run_middleware, with_context, f, args, kwargs
                if run_middleware:
                    # do request middleware
                    raise NotImplementedError("Middlware on decorated views "
                                              "is not yet implemented.")
                c = plugin.context if with_context else None
                resp = await plugin.route_wrapper(f, request, a, kw, *args,
                                                  context=c, **kwargs)
                if run_middleware:
                    # do response middleware
                    raise NotImplementedError("Middlware on decorated views "
                                              "is not yet implemented.")
                return resp

            return update_wrapper(wrapper, f)
        return _decorator

    async def route_wrapper(self, route, request, request_args, request_kw,
                            *decorator_args, context=None, **decorator_kw):
        """This is the function that is called when a route is decorated with
           your plugin decorator. Context will normally be None, but the user
           can pass use_context=True so the route will get the plugin
           context
        """
        # by default, do nothing, just run the wrapped function
        resp = route(request, *request_args, **request_kw)
        if isawaitable(resp):
            resp = await resp
        return resp

    def __new__(cls, *args, **kwargs):
        # making a bold assumption here.
        # Assuming that if a sanic plugin is initialized using
        # `MyPlugin(app)`, then the user is attempting to do a legacy plugin
        # instantiation.
        if args and len(args) > 0 and \
                (isinstance(args[0], Sanic) or isinstance(args[0], Blueprint)):
            app = args[0]
            try:
                mod_name = cls.__module__
                mod = importlib.import_module(mod_name)
                assert mod
            except (ImportError, AssertionError):
                raise RuntimeError(
                    "Failed attempting a legacy plugin instantiation. "
                    "Cannot find the module this plugin belongs to.")
            # Get the spf singleton from this app
            spf = SanicPluginsFramework(app)
            # catch cases like when the module is "__main__" or
            # "__call__" or "__init__"
            if mod_name.startswith("__"):
                # In this case, we cannot use the module to register the
                # plugin. Try to use the class method.
                return spf.register_plugin(cls, *args, **kwargs)
            else:
                return spf.register_plugin(mod, *args, **kwargs)
        self = super(SanicPlugin, cls).__new__(cls)
        self._initialized = False
        return self

    def __init__(self, *args, **kwargs):
        # Sometimes __init__ can be called twice.
        # Ignore it on subsequent times
        if self._initialized:
            return
        assert len(args) < 1,\
            "Unexpected arguments passed to this Sanic Plugins."
        assert len(kwargs) < 1,\
            "Unexpected keyword arguments passed to this Sanic Plugins."
        super(SanicPlugin, self).__init__(*args, **kwargs)
        self._routes = []
        self._middlewares = []
        self._exceptions = []
        self._listeners = defaultdict(list)
        self._spf = None
        self._plugin_name = None
        self._url_prefix = None
        self._initialized = True


class SanicPluginsFramework(object):
    __slots__ = ('_running', '_logger', '_app', '_plugin_names', '_contexts',
                 '_pre_request_middleware', '_post_request_middleware',
                 '_pre_response_middleware', '_post_response_middleware',
                 '_loop', '__weakref__')

    def log(self, level, message, *args, plugin=None, **kwargs):
        if plugin is not None:
            message = "{:s}: {:s}".format(str(plugin._plugin_name),
                                          str(message))
        return self._logger.log(level, message, *args, **kwargs)

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

        if name in self._plugin_names:
            raise ValueError(
                "Plugin {:s} is already registered!".format(name), plugin)
        self._plugin_names.add(name)
        shared_context = self.shared_context
        self._contexts[name] = context = ContextDict(
            self, shared_context, {'shared': shared_context})
        _p_context = self._plugins_context
        _p_context[name] = _plugin_dict = _p_context.create_child_context()
        _plugin_dict['name'] = name
        _plugin_dict['context'] = context
        if skip_reg:
            return plugin
        plugin = self._register_helper(plugin, *args, _spf=self,
                                       _plugin_name=name, **kwargs)
        _plugin_dict['instance'] = plugin
        return plugin

    @staticmethod
    def _register_helper(plugin, *args, _spf=None,
                         _plugin_name=None, _url_prefix=None, **kwargs):
        error_str = "Plugin must be initialised using the " \
                    "Sanic Plugins Framework"
        assert _spf is not None, error_str
        assert _plugin_name is not None, error_str
        _app = _spf._app
        assert _app is not None, error_str
        plugin._spf = _spf
        plugin._plugin_name = _plugin_name
        plugin._url_prefix = _url_prefix
        continue_flag = plugin.on_before_registered(*args, **kwargs)
        if continue_flag is False:
            return plugin
        # this should only ever run once!
        # replace it with the `pass` function above.
        plugin.on_before_registered = \
            partial(SanicPlugin.on_before_registered, plugin)

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
                r.handler.__blueprintname__ = plugin._plugin_name
            # Prepend the plugin URI prefix if available
            uri = _url_prefix + r.uri if _url_prefix else r.uri
            _spf._plugin_register_route(
                r.handler, plugin, uri[1:] if uri.startswith('//') else uri,
                *r.args, **r.kwargs)

        # Middleware
        for m in plugin._middlewares:
            _spf._plugin_register_middleware(
                m.middleware, plugin, *m.args, **m.kwargs)

        # Exceptions
        for e in plugin._exceptions:
            _spf._plugin_register_exception(
                e.handler, plugin, *e.exceptions, **e.kwargs)

        # Listeners
        for event, listeners in plugin._listeners.items():
            for listener in listeners:
                _spf._plugin_register_listener(event, listener, plugin)

        # this should only ever run once!
        plugin.on_registered(*args, **kwargs)
        # replace it with the `pass` function above.
        plugin.on_registered = partial(SanicPlugin.on_registered, plugin)
        return plugin

    def _plugin_register_route(self, handler, plugin, uri, *args,
                               with_context=False, **kwargs):
        if with_context:
            h_name = handler.__name__
            try:
                bp = handler.__blueprintname__
            except AttributeError:
                bp = False
            handler = partial(handler, context=plugin.context)
            handler.__name__ = h_name
            if bp:
                handler.__blueprintname__ = bp
        return self._app.route(uri, *args, **kwargs)(handler)

    def _plugin_register_exception(self, handler, plugin, *exceptions,
                                   with_context=False, **kwargs):
        if with_context:
            handler = partial(handler, context=plugin.context)
        return self._app.exception(*exceptions)(handler)

    def _plugin_register_middleware(self, middleware, plugin, *args,
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
            middleware = partial(middleware, context=plugin.context)
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
        new_ctx = ContextDict(self, None, {'request': request})
        shared_context = self.shared_context
        shared_context['request'] = new_ctx
        for name, _p in self._plugins_context.items():
            if isinstance(_p, ContextDict) and 'instance' in _p \
                    and isinstance(_p['instance'], SanicPlugin):
                if 'context' in _p and isinstance(_p['context'], ContextDict):
                    _p_context = _p['context']
                    _p_context['request'] = ContextDict(self, None,
                                                        {'request': request})

    def delete_temporary_request_context(self):
        shared_context = self.shared_context
        try:
            del shared_context['request']
        except KeyError:
            pass
        for name, _p in self._plugins_context.items():
            if isinstance(_p, ContextDict) and 'instance' in _p \
                    and isinstance(_p['instance'], SanicPlugin):
                if 'context' in _p and isinstance(_p['context'], ContextDict):
                    try:
                        del _p['context']['request']
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
        self.delete_temporary_request_context()
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
        self._app.listener('before_server_start')(self._on_before_server_start)
        assert len(args) < 1, \
            "Unexpected arguments passed to the Sanic Plugins Framework."
        assert len(kwargs) < 1, \
            "Unexpected keyword arguments passed to the SanicPluginsFramework."
        super(SanicPluginsFramework, self).__init__(*args, **kwargs)
