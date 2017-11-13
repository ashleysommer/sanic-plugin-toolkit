# -*- coding: utf-8 -*-
from collections import namedtuple, defaultdict
from functools import update_wrapper
from inspect import isawaitable
from queue import PriorityQueue
import importlib
import logging
from sanic import Sanic, Blueprint


FutureMiddleware = namedtuple('Middleware', ['middleware', 'args', 'kwargs'])
FutureRoute = namedtuple('Route', ['handler', 'uri', 'args', 'kwargs'])
FutureException = namedtuple('Exception', ['handler', 'exceptions', 'kwargs'])
PluginRegistration = namedtuple('Registration',
                                ['spf', 'plugin_name', 'url_prefix'])
PluginAssociated = namedtuple('Associated', ['plugin', 'reg'])


class SanicPlugin(object):
    __slots__ = ('registrations', '_routes',
                 '_middlewares', '_exceptions', '_listeners', '_initialized',
                 '__weakref__')

    AssociatedTuple = PluginAssociated

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

    def on_before_registered(self, context, *args, **kwargs):
        pass

    def on_registered(self, context, reg, *args, **kwargs):
        pass

    def find_plugin_registration(self, spf):
        if isinstance(spf, PluginRegistration):
            return spf
        for reg in self.registrations:
            (s, n, u) = reg
            if s is not None and s == spf:
                return reg
        return KeyError("Not found")

    def first_plugin_context(self):
        """Returns the context is associated with the first app this plugin was
         registered on"""
        # Note, because registrations are stored in a set, its not _really_
        # the first one, but whichever one it sees first in the set.
        first_spf_reg = next(iter(self.registrations))
        return self.get_context_from_spf(first_spf_reg)

    def get_context_from_spf(self, spf):
        rt_err = RuntimeError(
            "Cannot use the plugin's Context before it is "
            "registered.")
        if isinstance(spf, PluginRegistration):
            reg = spf
        else:
            reg = self.find_plugin_registration(spf)
        (s, n, u) = reg
        try:
            return s.get_context(n)
        except KeyError as k:
            raise k
        except AttributeError:
            raise rt_err

    def get_app_from_spf_context(self, spf):
        if isinstance(spf, PluginRegistration):
            reg = spf
        else:
            reg = self.find_plugin_registration(spf)
        context = self.get_context_from_spf(reg)
        return context.app

    def spf_resolve_url_for(self, spf, view_name, *args, **kwargs):
        reg = self.find_plugin_registration(spf)
        (spf, name, url_prefix) = reg
        app = self.get_app_from_spf_context(reg)
        if app is None:
            return None
        if isinstance(app, Blueprint):
            self.warning("Cannot use url_for when plugin is registered "
                         "on a Blueprint. Use `app.url_for` instead.")
            return None
        constructed_name = "{}.{}".format(name, view_name)
        return app.url_for(constructed_name, *args, **kwargs)

    def log(self, spf, level, message, *args, **kwargs):
        reg = self.find_plugin_registration(spf)
        context = self.get_context_from_spf(reg)
        return context.log(level, message, *args, reg=self, **kwargs)

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
    def decorate(cls, app, *args, run_middleware=False, with_context=False,
                 **kwargs):
        """
        This is a decorator that can be used to apply this plugin to a specific
        route/view on your app, rather than the whole app.
        :param app:
        :type app: Sanic | Blueprint
        :param args:
        :type args: tuple(Any)
        :param kwargs:
        :param kwargs: dict(Any)
        :return: the decorated route/view
        :rtype: fn
        """
        from spf.framework import SanicPluginsFramework
        spf = SanicPluginsFramework(app)  # get the singleton from the app
        try:
            assoc = spf.register_plugin(cls, skip_reg=True)
        except ValueError as e:
            # this is normal, if this plugin has been registered previously
            assert e.args and len(e.args) > 1
            assoc = e.args[1]
        (plugin, reg) = assoc
        inst = spf.get_plugin(plugin)  # plugin may not actually be registered
        regd = True if inst else None
        if regd is True:
            run_middleware = False
        req_middleware = PriorityQueue()
        resp_middleware = PriorityQueue()
        # registered might be True, False or None at this point
        if run_middleware:
            for i, m in enumerate(plugin._middlewares):
                attach_to = m.kwargs.pop('attach_to', 'request')
                priority = m.kwargs.pop('priority', 5)
                with_context = m.kwargs.pop('with_context', False)
                handler = m.middleware
                if attach_to == 'response':
                    relative = m.kwargs.pop('relative', 'post')
                    if relative == "pre":
                        mw = (0, 0 - priority, 0 - i, handler,
                              with_context, m.args, m.kwargs)
                    else:  # relative = "post"
                        mw = (1, 0 - priority, 0 - i, handler,
                              with_context, m.args, m.kwargs)
                    resp_middleware.put_nowait(mw)
                else:  # attach_to = "request"
                    relative = m.kwargs.pop('relative', 'pre')
                    if relative == "post":
                        mw = (1, priority, i, m.middleware, with_context,
                              m.args, m.kwargs)
                    else:  # relative = "pre"
                        mw = (0, priority, i, m.middleware, with_context,
                              m.args, m.kwargs)
                    req_middleware.put_nowait(mw)

        req_middleware = tuple(req_middleware.get()
                               for _ in range(req_middleware.qsize()))
        resp_middleware = tuple(resp_middleware.get()
                                for _ in range(resp_middleware.qsize()))

        def _decorator(f):
            nonlocal spf, plugin, regd, run_middleware, with_context
            nonlocal req_middleware, resp_middleware, args, kwargs

            async def wrapper(request, *a, **kw):
                nonlocal spf, plugin, regd, run_middleware, with_context
                nonlocal req_middleware, resp_middleware, f, args, kwargs
                # the plugin was not registered on the app, it might be now
                if regd is None:
                    _inst = spf.get_plugin(plugin)
                    regd = _inst is not None

                context = plugin.get_context_from_spf(spf)
                if run_middleware and not regd and len(req_middleware) > 0:
                    for (_a, _p, _i, handler, with_context, args, kwargs) \
                            in req_middleware:
                        if with_context:
                            resp = handler(request, *args, context=context,
                                           **kwargs)
                        else:
                            resp = handler(request, *args, **kwargs)
                        if isawaitable(resp):
                            resp = await resp
                        if resp:
                            return

                response = await plugin.route_wrapper(
                    f, request, context, a, kw, *args,
                    with_context=with_context, **kwargs)
                if isawaitable(response):
                    response = await response
                if run_middleware and not regd and len(resp_middleware) > 0:
                    for (_a, _p, _i, handler, with_context, args, kwargs) \
                            in resp_middleware:
                        if with_context:
                            _resp = handler(request, response, *args,
                                            context=context, **kwargs)
                        else:
                            _resp = handler(request, response, *args, **kwargs)
                        if isawaitable(_resp):
                            _resp = await _resp
                        if _resp:
                            response = _resp
                            break
                return response

            return update_wrapper(wrapper, f)
        return _decorator

    async def route_wrapper(self, route, request, context, request_args,
                            request_kw, *decorator_args, with_context=None,
                            **decorator_kw):
        """This is the function that is called when a route is decorated with
           your plugin decorator. Context will normally be None, but the user
           can pass use_context=True so the route will get the plugin
           context
        """
        # by default, do nothing, just run the wrapped function
        if with_context:
            resp = route(request, context, *request_args, **request_kw)
        else:
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
            from spf.framework import SanicPluginsFramework
            spf = SanicPluginsFramework(app)
            # catch cases like when the module is "__main__" or
            # "__call__" or "__init__"
            if mod_name.startswith("__"):
                # In this case, we cannot use the module to register the
                # plugin. Try to use the class method.
                assoc = spf.register_plugin(cls, *args, **kwargs)
            else:
                assoc = spf.register_plugin(mod, *args, **kwargs)
            return assoc
        self = super(SanicPlugin, cls).__new__(cls)
        try:
            self._initialized  # initialized may be True or Unknown
        except AttributeError:
            self._initialized = False
        return self

    def is_registered_on_framework(self, check_spf):
        for reg in self.registrations:
            (spf, name, url) = reg
            if spf is not None and spf == check_spf:
                return True
        return False

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
        self.registrations = set()
        self._initialized = True
