from collections import namedtuple, defaultdict
from functools import partial
from inspect import isawaitable
from queue import PriorityQueue
import logging
from sanic import Sanic
from uuid import uuid1

FutureMiddleware = namedtuple('Middleware', ['middleware', 'args', 'kwargs'])
FutureRoute = namedtuple('Route', ['handler', 'uri', 'args', 'kwargs'])
FutureException = namedtuple('Exception', ['handler', 'args', 'kwargs'])

class ContextDict(dict):
    __slots__ = ('_spf', '_parent_context')

    def create_child_context(self):
        return ContextDict(self._spf, self)

    def __repr__(self):
        _dict_repr = super(ContextDict, self).__repr__()
        return "ContextDict({:s})".format(_dict_repr)

    def __getitem__(self, item):
        try:
            return super(ContextDict, self).__getitem__(item)
        except KeyError as e:
            parents_searched = [self,]
            parent = self._parent_context
            while parent:
                try:
                    return super(ContextDict, parent).__getitem__(item)
                except KeyError as e:
                    parents_searched.append(parent)
                    # noinspection PyProtectedMember
                    next_parent = parent._parent_context
                    if next_parent in parents_searched:
                        raise RuntimeError("Recursive ContextDict found!")
                    parent = next_parent
            raise e

    def __new__(cls, spf, parent, *args, **kwargs):
        self = super(ContextDict, cls).__new__(cls, *args, **kwargs)
        if parent is not None:
            assert isinstance(parent, ContextDict), "Parent context must be a valid initialised ContextDict"
            self._parent_context = parent
        else:
            self._parent_context = None
        self._spf = spf
        return self

    def __init__(self, *args, **kwargs):
        args = list(args)
        _ = args.pop(0)  # remove spf
        _ = args.pop(0)  # remove parent
        super(ContextDict, self).__init__(*args, **kwargs)


class SanicPlugin(object):
    # Decorator
    def middleware(self, *args, **kwargs):
        """Decorate and register middleware
        Unlike app.middleware, this _cannot_ be called as @plugin.middleware without args.
        """
        kwargs.setdefault('priority', 5)
        kwargs.setdefault('relative', None)
        kwargs.setdefault('kind', None)
        kwargs.setdefault('with_context', False)
        def f(middleware):
            self._middlewares.append(FutureMiddleware(middleware, args=args, kwargs=kwargs))
            return middleware
        return f

    def listener(self, event, *args, **kwargs):
        """Create a listener from a decorated function.

        :param event: Event to listen to.
        """
        def f(listener):
            self._listeners[event].append(listener)
            return listener
        return f

    def route(self, uri, *args, **kwargs):
        """Create a blueprint route from a decorated function.

        :param uri: endpoint at which the route will be accessible.
        :param methods: list of acceptable HTTP methods.
        """
        kwargs.setdefault('methods', frozenset({'GET'}))
        kwargs.setdefault('host', None)
        kwargs.setdefault('strict_slashes', False)
        kwargs.setdefault('stream', False)
        # TODO: sanic 0.6.1 will have 'name' on a route
        ##kwargs.setdefault('name', None)

        def decorator(handler):
            route = FutureRoute(handler, uri, args, kwargs)
            self._routes.append(route)
            return handler
        return decorator

    def register(self, *args, _app=None, _spf=None, _plugin_name=None, _url_prefix=None, **kwargs):
        error_str = "This plugin must be initialised using the Sanic Plugins Framework"
        assert _spf is not None, error_str
        assert _app is not None, error_str
        assert _plugin_name is not None, error_str
        self.app = _app
        self._spf = _spf
        self._plugin_name = _plugin_name
        self._url_prefix = _url_prefix
        # Routes
        for r in self._routes:
            # attach the plugin name to the handler so that it can be
            # prefixed properly in the router
            r.handler.__blueprintname__ = self._plugin_name
            # Prepend the plugin URI prefix if available
            uri = _url_prefix + r.uri if _url_prefix else r.uri
            self._spf._plugin_register_route(r.handler, self, uri[1:] if uri.startswith('//') else uri,
                                             *r.args, **r.kwargs)

        #middlewares
        for m in self._middlewares:
            self._spf._plugin_register_middleware(m.middleware, self, *m.args, **m.kwargs)

        #exceptions
        for e in self._exceptions:
            self._spf._plugin_register_exception(e.handler, self, *e.args, **e.kwargs)

        #listeners
        for event, listeners in self._listeners.items():
            for listener in listeners:
                self._spf._plugin_register_listener(event, listener, self)

    @property
    def context(self):
        try:
            return self._spf.get_context(self._plugin_name)
        except (AttributeError, KeyError) as e:
            raise e

    def log(self, level, message, *args, **kwargs):
        return self._spf.log(level, message, *args, plugin=self, **kwargs)

    def __init__(self, *args, **kwargs):
        super(SanicPlugin, self).__init__(*args, **kwargs)
        self.app = None
        self._routes = []
        self._middlewares = []
        self._exceptions = []
        self._listeners = defaultdict(list)
        self._spf = None
        self._plugin_name = None


class SanicPluginsFramework(object):
    __slots__ = ('_running', '_logger', '_app', '_plugin_names', '_contexts', '_pre_request_middleware',
                 '_post_request_middleware', '_pre_response_middleware', '_post_response_middleware',
                 '_loop')

    def log(self, level, message, *args, plugin=None, **kwargs):
        if plugin is not None:
            message = "{:s}: {:s}".format(str(plugin._plugin_name), str(message))
        return self._logger.log(level, message, *args, **kwargs)

    def register_plugin(self, plugin, *args, name=None, **kwargs):
        assert not self._running, "Cannot add, remove, or change plugins after the App has started serving."
        assert plugin, "Plugin must be a valid type! Do not pass in None or False"
        assert isinstance(plugin, SanicPlugin), "Plugin must be derived from SanicPlugin"
        if name is None:
            try:
                name = str(plugin.__class__.__name__)
                assert name is not None
            except (AttributeError, AssertionError, ValueError, KeyError):
                self._logger.warning("Cannot determine a name for {}, using UUID.".format(repr(plugin)))
                name = str(uuid1(None, None))
        assert isinstance(name, str), "Plugin name must be a python unicode string!"
        if name in self._plugin_names:
            raise RuntimeError("Plugin {:s} is already registered!".format(name))
        self._plugin_names.add(name)
        app = self._app
        self._contexts[name] = context = self._contexts.create_child_context()
        plugin_instance = plugin.register(*args, _app=app, _spf=self, _plugin_name=name, **kwargs)
        _plugins = self._plugins
        _plugins[name] = _plugin_dict = _plugins.create_child_context()
        _plugin_dict['name'] = name
        _plugin_dict['instance'] = plugin_instance
        _plugin_dict['context'] = context
        return plugin_instance

    def _plugin_register_route(self, handler, plugin, uri, *args, with_context=False, **kwargs):
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

    def _plugin_register_exception(self, handler, plugin, *args, with_context=False, **kwargs):
        if with_context:
            handler = partial(handler, context=plugin.context)
        return self._app.exception(*args, **kwargs)(handler)


    def _plugin_register_middleware(self, middleware, plugin, priority, relative=None, kind=None, with_context=False):
        assert isinstance(priority, int), "Priority must be an integer! No floats!"
        assert 0 <= priority <= 9, "Priority must be between 0 and 9 (inclusive), 0 is highest priority, 9 is least."
        assert isinstance(plugin, SanicPlugin), "Plugin middleware only works with a plugin derived from SanicPlugin."
        if with_context:
            middleware = partial(middleware, context=plugin.context)
        priority_middleware = (priority, middleware)
        if kind is None or kind == "request":
            if relative is None or relative == 'pre':  # plugin request middleware default to pre-app middleware
                self._pre_request_middleware.put_nowait(priority_middleware)
            else:  # post
                self._post_request_middleware.put_nowait(priority_middleware)
        else:  # response
            assert kind == "response", "A middleware kind must be either request or response."
            if relative is None or relative == 'post':  # plugin response middleware default to post-app middleware
                self._post_response_middleware.put_nowait(priority_middleware)
            else:  # pre
                self._pre_response_middleware.put_nowait(priority_middleware)
        return middleware

    def _plugin_register_listener(self, event, listener, plugin):
        return self._app.listener(event)(listener)

    @property
    def _plugins(self):
        try:
            return self._contexts['_plugins']
        except (AttributeError, KeyError):
            raise RuntimeError("Sanic Plugins Framework does not have a valid plugins context!")

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
            self._logger.warning("Context {:s} does not exist! Falling back to shared context".format(context))
            _context = self._contexts['shared']
        return _context.__getitem__(item)

    async def _run_request_middleware(self, request):
        assert self._running, "App must be running before you can run middleware!"
        if self._pre_request_middleware:
            for (pri, middleware) in self._pre_request_middleware:
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
            for (pri, middleware) in self._post_request_middleware:
                response = middleware(request)
                if isawaitable(response):
                    response = await response
                if response:
                    return response
        return None

    async def _run_response_middleware(self, request, response):
        if self._pre_response_middleware:
            for (pri, middleware) in self._pre_response_middleware:
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
            for (pri, middleware) in self._post_response_middleware:
                _response = middleware(request, response)
                if isawaitable(_response):
                    _response = await _response
                if _response:
                    response = _response
                    break
        return response

    def _on_before_server_start(self, app, loop=None):
        assert self._app == app, "Sanic Plugins Framework is not assigned to the correct Sanic App!"
        assert loop, "Sanic server did not give us a loop to use! Check for app updates, you might out of date."
        self._loop = loop
        self._running = True
        # sort and freeze these
        self._pre_request_middleware = tuple(self._pre_request_middleware.get()
                                             for _ in range(self._pre_request_middleware.qsize()))
        self._post_request_middleware = tuple(self._post_request_middleware.get()
                                              for _ in range(self._post_request_middleware.qsize()))
        self._pre_response_middleware = tuple(self._pre_response_middleware.get()
                                              for _ in range(self._pre_response_middleware.qsize()))
        self._post_response_middleware = tuple(self._post_response_middleware.get()
                                               for _ in range(self._post_response_middleware.qsize()))
        return False

    def __new__(cls, app):
        assert app, "Sanic Plugins Framework must be given a valid Sanic App to work with."
        assert isinstance(app, Sanic), "Sanic Plugins Framework only works with Sanic Apps." \
                                       "Please pass in an app instance to the SanicPluginsFramework constructor."
        self = super(SanicPluginsFramework, cls).__new__(cls)
        self._running = False
        self._app = app
        self._logger = logging.getLogger(__name__)
        self._plugin_names = set()
        self._pre_request_middleware = PriorityQueue()  # these get replaced with frozen tuples at runtime
        self._post_request_middleware = PriorityQueue()
        self._pre_response_middleware = PriorityQueue()
        self._post_response_middleware = PriorityQueue()
        self._contexts = ContextDict(self, None)
        self._contexts['shared'] = _shared = self._contexts.create_child_context()
        self._contexts['_plugins'] = _plugins = self._contexts.create_child_context()
        _plugins['spf'] = self
        _shared['app'] = app
        # monkey patch the app!
        app._run_request_middleware = self._run_request_middleware
        app._run_response_middleware = self._run_response_middleware
        return self

    def __init__(self, *args, **kwargs):
        args = list(args)
        _ = args.pop(0)  # remove app
        assert self._app, "Sanic Plugin Framework as not initialized correctly."
        self._app.listener('before_server_start')(self._on_before_server_start)
        super(SanicPluginsFramework, self).__init__(*args, **kwargs)
