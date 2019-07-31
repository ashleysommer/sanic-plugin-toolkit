# -*- coding: utf-8 -*-
from collections import namedtuple
from spf import SanicPlugin
from spf.plugin import FutureRoute, FutureWebsocket, FutureMiddleware

ContextualizeAssociatedTuple = namedtuple('ContextualizeAssociatedTuple',
                                          ['plugin', 'reg'])


class ContextualizeAssociated(ContextualizeAssociatedTuple):
    __slots__ = ()

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
        kwargs['with_context'] = True  # This is the whole point of this plugin
        plugin = self.plugin
        reg = self.reg

        if len(args) == 1 and callable(args[0]):
            middle_f = args[0]
            return plugin._add_new_middleware(reg, middle_f, **kwargs)

        def wrapper(middle_f):
            nonlocal plugin, reg
            nonlocal args, kwargs
            return plugin._add_new_middleware(reg, middle_f, *args, **kwargs)
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
                               "arguments.")
        kwargs.setdefault('methods', frozenset({'GET'}))
        kwargs.setdefault('host', None)
        kwargs.setdefault('strict_slashes', False)
        kwargs.setdefault('stream', False)
        kwargs.setdefault('name', None)
        kwargs['with_context'] = True  # This is the whole point of this plugin
        plugin = self.plugin
        reg = self.reg

        def wrapper(handler_f):
            nonlocal plugin, reg
            nonlocal uri, args, kwargs
            return plugin._add_new_route(reg, uri, handler_f, *args, **kwargs)
        return wrapper

    def listener(self, event, *args, **kwargs):
        """Create a listener from a decorated function.
        :param event: Event to listen to.
        :type event: str
        :param args: captures all of the positional arguments passed in
        :type args: tuple(Any)
        :param kwargs: captures the keyword arguments passed in
        :type kwargs: dict(Any)
        :return: The function to use as the listener
        :rtype: fn
        """
        if len(args) == 1 and callable(args[0]):
            raise RuntimeError("Cannot use the @listener decorator without "
                               "arguments")
        kwargs['with_context'] = True  # This is the whole point of this plugin
        plugin = self.plugin
        reg = self.reg

        def wrapper(listener_f):
            nonlocal plugin, reg
            nonlocal event, args, kwargs
            return plugin._add_new_listener(reg, event, listener_f, *args,
                                            **kwargs)
        return wrapper

    def websocket(self, uri, *args, **kwargs):
        """Create a websocket route from a decorated function
        :param uri: endpoint at which the socket endpoint will be accessible.
        :type uri: str
        :param args: captures all of the positional arguments passed in
        :type args: tuple(Any)
        :param kwargs: captures the keyword arguments passed in
        :type kwargs: dict(Any)
        :return: The exception function to use as the decorator
        :rtype: fn
        """

        kwargs.setdefault('host', None)
        kwargs.setdefault('strict_slashes', None)
        kwargs.setdefault('subprotocols', None)
        kwargs.setdefault('name', None)
        kwargs['with_context'] = True  # This is the whole point of this plugin
        plugin = self.plugin
        reg = self.reg

        def wrapper(handler_f):
            nonlocal plugin, reg
            nonlocal uri, args, kwargs
            return plugin._add_new_ws_route(reg, uri, handler_f,
                                            *args, **kwargs)
        return wrapper


class Contextualize(SanicPlugin):
    __slots__ = ()

    AssociatedTuple = ContextualizeAssociated

    def _add_new_middleware(self, reg, middle_f, *args, **kwargs):
        # A user should never call this directly.
        # it should be called only by the AssociatedTuple
        assert reg in self.registrations
        (spf, p_name, url_prefix) = reg
        context = self.get_context_from_spf(reg)
        # This is how we add a new middleware _after_ the plugin is registered
        m = FutureMiddleware(middle_f, args, kwargs)
        spf._register_middleware_helper(m, spf, self, context)
        return middle_f

    def _add_new_route(self, reg, uri, handler_f, *args, **kwargs):
        # A user should never call this directly.
        # it should be called only by the AssociatedTuple
        assert reg in self.registrations
        (spf, p_name, url_prefix) = reg
        context = self.get_context_from_spf(reg)
        # This is how we add a new route _after_ the plugin is registered
        r = FutureRoute(handler_f, uri, args, kwargs)
        spf._register_route_helper(r, spf, self, context, p_name, url_prefix)
        return handler_f

    def _add_new_listener(self, reg, event, listener_f, *args, **kwargs):
        # A user should never call this directly.
        # it should be called only by the AssociatedTuple
        assert reg in self.registrations
        (spf, p_name, url_prefix) = reg
        context = self.get_context_from_spf(reg)
        # This is how we add a new listener _after_ the plugin is registered
        spf._plugin_register_listener(event, listener_f, self, context,
                                      *args, **kwargs)
        return listener_f

    def _add_new_ws_route(self, reg, uri, handler_f, *args, **kwargs):
        # A user should never call this directly.
        # it should be called only by the AssociatedTuple
        assert reg in self.registrations
        (spf, p_name, url_prefix) = reg
        context = self.get_context_from_spf(reg)
        # This is how we add a new route _after_ the plugin is registered
        w = FutureWebsocket(handler_f, uri, args, kwargs)
        spf._register_websocket_route_helper(w, spf, self, context, p_name,
                                             url_prefix)
        return handler_f

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
        kwargs['with_context'] = True  # This is the whole point of this plugin
        if len(args) == 1 and callable(args[0]):
            middle_f = args[0]
            return super(Contextualize, self).middleware(middle_f, **kwargs)

        def wrapper(middle_f):
            nonlocal self, args, kwargs
            return super(Contextualize, self).middleware(
                *args, **kwargs)(middle_f)
        return wrapper

    # Decorator
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
                               "arguments.")
        kwargs.setdefault('methods', frozenset({'GET'}))
        kwargs.setdefault('host', None)
        kwargs.setdefault('strict_slashes', False)
        kwargs.setdefault('stream', False)
        kwargs.setdefault('name', None)
        kwargs['with_context'] = True  # This is the whole point of this plugin

        def wrapper(handler_f):
            nonlocal self, uri, args, kwargs
            return super(Contextualize, self).route(
                uri, *args, **kwargs)(handler_f)
        return wrapper

    # Decorator
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
        kwargs['with_context'] = True  # This is the whole point of this plugin

        def wrapper(listener_f):
            nonlocal self, event, args, kwargs
            return super(Contextualize, self).listener(
                event, *args, **kwargs)(listener_f)
        return wrapper

    def websocket(self, uri, *args, **kwargs):
        """Create a websocket route from a decorated function
        :param uri: endpoint at which the socket endpoint will be accessible.
        :type uri: str
        :param args: captures all of the positional arguments passed in
        :type args: tuple(Any)
        :param kwargs: captures the keyword arguments passed in
        :type kwargs: dict(Any)
        :return: The exception function to use as the decorator
        :rtype: fn
        """

        kwargs.setdefault('host', None)
        kwargs.setdefault('strict_slashes', None)
        kwargs.setdefault('subprotocols', None)
        kwargs.setdefault('name', None)
        kwargs['with_context'] = True  # This is the whole point of this plugin

        def wrapper(handler_f):
            nonlocal self, uri, args, kwargs
            return super(Contextualize, self).websocket(
                uri, *args, **kwargs)(handler_f)
        return wrapper

    def __init__(self, *args, **kwargs):
        super(Contextualize, self).__init__(*args, **kwargs)


instance = contextualize = Contextualize()
