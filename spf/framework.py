# -*- coding: utf-8 -*-
import sys
from asyncio import CancelledError
from functools import partial, update_wrapper
from inspect import isawaitable, ismodule
from collections import deque
from distutils.version import LooseVersion
import importlib
import re
from sanic import Sanic, Blueprint, __version__ as sanic_version
from sanic.log import logger
from uuid import uuid1

from spf.config import load_config_file
from spf.context import SanicContext
from spf.plugin import SanicPlugin, PluginRegistration

module = sys.modules[__name__]
module.consts = CONSTS = dict()
CONSTS["APP_CONFIG_INSTANCE_KEY"] = APP_CONFIG_INSTANCE_KEY = "__SPF_INSTANCE"
CONSTS["SPF_LOAD_INI_KEY"] = SPF_LOAD_INI_KEY = "SPF_LOAD_INI"
CONSTS["SPF_INI_FILE_KEY"] = SPF_INI_FILE_KEY = "SPF_INI_FILE"
CONSTS["SANIC_19_12_0"] = SANIC_19_12_0 = LooseVersion("19.12.0")

# Currently installed sanic version in this environment
SANIC_VERSION = LooseVersion(sanic_version)

CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10


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
    __slots__ = ('_running', '_app', '_plugin_names', '_contexts',
                 '_pre_request_middleware', '_post_request_middleware',
                 '_pre_response_middleware', '_post_response_middleware',
                 '_cleanup_middleware', '_loop', '__weakref__')

    def log(self, level, message, reg=None, *args, **kwargs):
        if reg is not None:
            (_, n, _) = reg
            message = "{:s}: {:s}".format(str(n), str(message))
        return logger.log(level, message, *args, **kwargs)

    def debug(self, message, reg=None, *args, **kwargs):
        return self.log(DEBUG, message=message, reg=reg, *args, **kwargs)

    def info(self, message, reg=None, *args, **kwargs):
        return self.log(INFO, message=message, reg=reg, *args, **kwargs)

    def warning(self, message, reg=None, *args, **kwargs):
        return self.log(WARNING, message=message, reg=reg, *args, **kwargs)

    def error(self, message, reg=None, *args, **kwargs):
        return self.log(ERROR, message=message, reg=reg, *args, **kwargs)

    def critical(self, message, reg=None, *args, **kwargs):
        return self.log(CRITICAL, message=message, reg=reg, *args, **kwargs)

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

    def _get_spf_plugin(self, plugin):
        if isinstance(plugin, str):
            if plugin not in self._plugin_names:
                self.warning("Cannot lookup that plugin by its name.")
                return None
            name = plugin
        else:
            reg = plugin.find_plugin_registration(self)
            (_, name, _) = reg
        _p_context = self._plugins_context
        try:
            _plugin_reg = _p_context[name]
        except KeyError as k:
            self.warning("Plugin not found!")
            raise k
        return _plugin_reg

    def get_plugin_inst(self, plugin):
        _plugin_reg = self._get_spf_plugin(plugin)
        try:
            inst = _plugin_reg['instance']
        except KeyError:
            self.warning("Plugin is not registered properly")
            inst = None
        return inst

    def get_plugin_assoc(self, plugin):
        _plugin_reg = self._get_spf_plugin(plugin)
        p = _plugin_reg['instance']
        reg = _plugin_reg['reg']
        associated_tuple = p.AssociatedTuple
        return associated_tuple(p, reg)

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
                    plugin = getattr(mod, lower_class)
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
                logger.warning(
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
                               "spf, maybe under a different name?")
        self._plugin_names.add(name)
        shared_context = self.shared_context
        self._contexts[name] = context = SanicContext(
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
    def _register_middleware_helper(m, _spf, plugin, context):
        _spf._plugin_register_middleware(m.middleware, plugin, context,
                                         *m.args, **m.kwargs)

    @staticmethod
    def _register_route_helper(r, _spf, plugin, context, _p_name,
                               _url_prefix):
        # Prepend the plugin URI prefix if available
        uri = _url_prefix + r.uri if _url_prefix else r.uri
        uri = uri[1:] if uri.startswith('//') else uri
        # attach the plugin name to the handler so that it can be
        # prefixed properly in the router
        _app = _spf._app
        if isinstance(_app, Blueprint):
            # blueprint always handles adding __blueprintname__
            # So we identify ourselves here a different way.
            handler_name = r.handler.__name__
            r.handler.__name__ = "{}.{}".format(_p_name, handler_name)
            _spf._plugin_register_bp_route(
                r.handler, plugin, context, uri, *r.args, **r.kwargs)
        else:
            # app is not a blueprint, but we use the __blueprintname__
            # property to store the plugin name
            r.handler.__blueprintname__ = _p_name
            _spf._plugin_register_app_route(
                r.handler, plugin, context, uri, *r.args, **r.kwargs)

    @staticmethod
    def _register_websocket_route_helper(w, _spf, plugin, context, _p_name,
                                         _url_prefix):
        # Prepend the plugin URI prefix if available
        uri = _url_prefix + w.uri if _url_prefix else w.uri
        uri = uri[1:] if uri.startswith('//') else uri
        # attach the plugin name to the handler so that it can be
        # prefixed properly in the router
        _app = _spf._app
        if isinstance(_app, Blueprint):
            # blueprint always handles adding __blueprintname__
            # So we identify ourselves here a different way.
            handler_name = w.handler.__name__
            w.handler.__name__ = "{}.{}".format(_p_name, handler_name)
            _spf._plugin_register_bp_websocket_route(
                w.handler, plugin, context, uri, *w.args, **w.kwargs)
        else:
            # app is not a blueprint, but we use the __blueprintname__
            # property to store the plugin name
            w.handler.__blueprintname__ = _p_name
            _spf._plugin_register_app_websocket_route(
                w.handler, plugin, context, uri, *w.args, **w.kwargs)

    @staticmethod
    def _register_static_helper(s, _spf, plugin, context, _p_name,
                                _url_prefix):
        # attach the plugin name to the static route so that it can be
        # prefixed properly in the router
        name = s.kwargs.pop('name', 'static')
        if not name.startswith(_p_name + '.'):
            name = '{}.{}'.format(_p_name, name)
        # Prepend the plugin URI prefix if available
        uri = _url_prefix + s.uri if _url_prefix else s.uri
        uri = uri[1:] if uri.startswith('//') else uri
        _spf._plugin_register_static(uri, s.file_or_dir, plugin,
                                     context, *s.args, name=name,
                                     **s.kwargs)

    @staticmethod
    def _register_helper(plugin, context, *args, _spf=None, _plugin_name=None,
                         _url_prefix=None, **kwargs):
        error_str = "Plugin must be initialised using the " \
                    "Sanic Plugins Framework."
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
        [_spf._register_route_helper(r, _spf, plugin, context, _plugin_name,
                                     _url_prefix)
         for r in plugin._routes]

        # Websocket routes
        [_spf._register_websocket_route_helper(w, _spf, plugin, context,
                                               _plugin_name, _url_prefix)
         for w in plugin._ws]

        # Static routes
        [_spf._register_static_helper(s, _spf, plugin, context, _plugin_name,
                                      _url_prefix)
         for s in plugin._static]

        # Middleware
        [_spf._register_middleware_helper(m, _spf, plugin, context)
         for m in plugin._middlewares]

        # Exceptions
        for e in plugin._exceptions:
            _spf._plugin_register_exception(
                e.handler, plugin, context, *e.exceptions, **e.kwargs)

        # Listeners
        for event, listeners in plugin._listeners.items():
            for listener in listeners:
                if isinstance(listener, tuple):
                    listener, kwargs = listener
                _spf._plugin_register_listener(
                    event, listener, plugin, context, **kwargs)

        # # this should only ever run once!
        plugin.registrations.add(reg)
        plugin.on_registered(context, reg, *args, **kwargs)

        return reg

    def _plugin_register_app_route(self, r_handler, plugin, context, uri,
                                   *args, with_context=False, **kwargs):
        if with_context:
            bp = r_handler.__blueprintname__
            r_handler = update_wrapper(partial(r_handler, context=context),
                                       r_handler)
            r_handler.__blueprintname__ = bp
        if SANIC_19_12_0 <= SANIC_VERSION:
            names, r_handler = self._app.route(uri, *args, **kwargs)(r_handler)
        else:
            r_handler = self._app.route(uri, *args, **kwargs)(r_handler)
        return r_handler

    def _plugin_register_bp_route(self, r_handler, plugin, context, uri, *args,
                                  with_context=False, **kwargs):
        bp = self._app
        if with_context:
            r_handler = update_wrapper(partial(r_handler, context=context),
                                       r_handler)
            # __blueprintname__ gets added in the register() routine
        # When app is a blueprint, it doesn't register right away, it happens
        # in the blueprint.register() routine.
        r_handler = bp.route(uri, *args, **kwargs)(r_handler)
        return r_handler

    def _plugin_register_app_websocket_route(self, w_handler, plugin, context,
                                             uri, *args, with_context=False,
                                             **kwargs):
        if with_context:
            bp = w_handler.__blueprintname__
            w_handler = update_wrapper(partial(w_handler, context=context),
                                       w_handler)
            w_handler.__blueprintname__ = bp
        if SANIC_19_12_0 <= SANIC_VERSION:
            names, w_handler = self._app.websocket(uri, *args, **kwargs)(
                w_handler)
        else:
            w_handler = self._app.websocket(uri, *args, **kwargs)(w_handler)
        return w_handler

    def _plugin_register_bp_websocket_route(self, w_handler, plugin, context,
                                            uri, *args, with_context=False,
                                            **kwargs):
        bp = self._app
        if with_context:
            w_handler = update_wrapper(partial(w_handler, context=context),
                                       w_handler)
            # __blueprintname__ gets added in the register() routine
        # When app is a blueprint, it doesn't register right away, it happens
        # in the blueprint.register() routine.
        w_handler = bp.websocket(uri, *args, **kwargs)(w_handler)
        return w_handler

    def _plugin_register_static(self, uri, file_or_dir, plugin, context,
                                *args, **kwargs):
        return self._app.static(uri, file_or_dir, *args, **kwargs)

    def _plugin_register_exception(self, handler, plugin, context, *exceptions,
                                   with_context=False, **kwargs):
        if with_context:
            handler = update_wrapper(partial(handler, context=context),
                                     handler)
        return self._app.exception(*exceptions)(handler)

    def _plugin_register_middleware(self, middleware, plugin, context, *args,
                                    priority=5, relative=None, attach_to=None,
                                    with_context=False, **kwargs):
        assert isinstance(priority, int), "Priority must be an integer!"
        assert 0 <= priority <= 9,\
            "Priority must be between 0 and 9 (inclusive), " \
            "0 is highest priority, 9 is lowest."
        assert isinstance(plugin, SanicPlugin), \
            "Plugin middleware only works with a plugin from SPF."
        if len(args) > 0 and isinstance(args[0], str) and attach_to is None:
            # for backwards/sideways compatibility with Sanic,
            # the first arg is interpreted as 'attach_to'
            attach_to = args[0]
        if with_context:
            middleware = update_wrapper(partial(middleware, context=context),
                                        middleware)
        if attach_to is None or attach_to == "request":
            insert_order =\
                len(self._pre_request_middleware) + \
                len(self._post_request_middleware)
            priority_middleware = (priority, insert_order, middleware)
            if relative is None or relative == 'pre':
                # plugin request middleware default to pre-app middleware
                self._pre_request_middleware.append(priority_middleware)
            else:  # post
                assert relative == "post",\
                    "A request middleware must have relative = pre or post"
                self._post_request_middleware.append(priority_middleware)
        elif attach_to == "cleanup":
            insert_order = len(self._cleanup_middleware)
            priority_middleware = (priority, insert_order, middleware)
            assert relative is None, \
                "A cleanup middleware cannot have relative pre or post"
            self._cleanup_middleware.append(priority_middleware)
        else:  # response
            assert attach_to == "response",\
                "A middleware kind must be either request or response."
            insert_order = \
                len(self._post_response_middleware) + \
                len(self._pre_response_middleware)
            # so they are sorted backwards
            priority_middleware = (0-priority, 0.0-insert_order, middleware)
            if relative is None or relative == 'post':
                # plugin response middleware default to post-app middleware
                self._post_response_middleware.append(priority_middleware)
            else:  # pre
                assert relative == "pre",\
                    "A response middleware must have relative = pre or post"
                self._pre_response_middleware.append(priority_middleware)
        return middleware

    def _plugin_register_listener(self, event, listener, plugin, context,
                                  *args, with_context=False, **kwargs):
        if with_context:
            listener = update_wrapper(partial(listener, context=context),
                                      listener)
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
            logger.error("Context {:s} does not exist!")
            return None
        return _context

    def get_from_context(self, item, context=None):
        context = context or 'shared'
        try:
            _context = self._contexts[context]
        except KeyError:
            logger.warning(
                "Context {:s} does not exist! Falling back to shared context"
                .format(context))
            _context = self._contexts['shared']
        return _context.__getitem__(item)

    def create_temporary_request_context(self, request):
        request_hash = id(request)
        new_ctx = SanicContext(self, None, {'id': 'shared request contexts'})
        shared_context = self.shared_context
        shared_request = shared_context.get('request', False)
        if not shared_request:
            shared_context['request'] = shared_request = new_ctx
        shared_request[request_hash] =\
            SanicContext(self, None,
                         {'request': request,
                          'id': "shared request context for request {}"
                          .format(id(request))})
        for name, _p in self._plugins_context.items():
            if not (isinstance(_p, SanicContext) and 'instance' in _p
                    and isinstance(_p['instance'], SanicPlugin)):
                continue
            if not('context' in _p and
                   isinstance(_p['context'], SanicContext)):
                continue
            _p_context = _p['context']
            if 'request' not in _p_context:
                _p_context['request'] = p_request = SanicContext(
                    self, None, {'id': 'private request contexts'})
            else:
                p_request = _p_context.request
            p_request[request_hash] =\
                SanicContext(self, None, {'request': request, 'id':
                             "private request context for {} on request {}"
                                          .format(name, id(request))})

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
            if not (isinstance(_p, SanicContext) and 'instance' in _p
                    and isinstance(_p['instance'], SanicPlugin)):
                continue
            if not ('context' in _p and
                    isinstance(_p['context'], SanicContext)):
                continue
            _p_context = _p['context']
            try:
                _p_request = _p_context['request']
                del _p_request[request_hash]
                if len(_p_request) < 1:
                    del _p_context['request']
            except KeyError:
                pass

    async def _handle_request(self, real_handle, request, write_callback,
                              stream_callback):
        cancelled = False
        try:
            _ = await real_handle(request, write_callback,
                                  stream_callback)
        except CancelledError as ce:
            # We still want to run cleanup middleware, even if cancelled
            cancelled = ce
        except BaseException as be:
            logger.error("SPF caught an error that should have been caught"
                         " by Sanic response handler.")
            logger.error(str(be))
            raise
        finally:
            # noinspection PyUnusedLocal
            _ = await self._run_cleanup_middleware(request)  # noqa: F841
            if cancelled:
                raise cancelled

    def wrap_handle_request(self, app):
        orig_handle_request = app.handle_request
        return update_wrapper(partial(
            self._handle_request, orig_handle_request), self._handle_request)

    async def _run_request_middleware_18_12(self, request):
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

    async def _run_request_middleware_19_12(self, request, request_name=None):
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
        app = self._app
        named_middleware = app.named_request_middleware.get(request_name,
                                                            deque())
        applicable_middleware = app.request_middleware + named_middleware
        if applicable_middleware:
            for middleware in applicable_middleware:
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

    async def _run_response_middleware_18_12(self, request, response):
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
        return response

    async def _run_response_middleware_19_12(self, request, response,
                                             request_name=None):
        if self._pre_response_middleware:
            for (_pri, _ins, middleware) in self._pre_response_middleware:
                _response = middleware(request, response)
                if isawaitable(_response):
                    _response = await _response
                if _response:
                    response = _response
                    break
        app = self._app
        named_middleware = app.named_response_middleware.get(request_name,
                                                             deque())
        applicable_middleware = app.response_middleware + named_middleware
        if applicable_middleware:
            for middleware in applicable_middleware:
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
        return response

    async def _run_cleanup_middleware(self, request):
        if self._cleanup_middleware:
            for (_pri, _ins, middleware) in self._cleanup_middleware:
                response = middleware(request)
                if isawaitable(response):
                    response = await response
                if response:
                    return response
        self.delete_temporary_request_context(request)
        return None

    def _on_server_start(self, app, loop):
        if not isinstance(self._app, Blueprint):
            assert self._app == app,\
                    "Sanic Plugins Framework is not assigned to the correct " \
                    "Sanic App!"
        if self._running:
            # during testing, this will be called _many_ times.
            return  # Ignore if this is already called.
        self._loop = loop

        self._running = True
        # sort and freeze these
        self._pre_request_middleware = \
            tuple(sorted(self._pre_request_middleware))
        self._post_request_middleware = \
            tuple(sorted(self._post_request_middleware))
        self._pre_response_middleware = \
            tuple(sorted(self._pre_response_middleware))
        self._post_response_middleware = \
            tuple(sorted(self._post_response_middleware))
        self._cleanup_middleware = \
            tuple(sorted(self._cleanup_middleware))

    def _patch_app(self, app):
        # monkey patch the app!
        app.handle_request = self.wrap_handle_request(app)
        if SANIC_19_12_0 <= SANIC_VERSION:
            app._run_request_middleware = self._run_request_middleware_19_12
            app._run_response_middleware = self._run_response_middleware_19_12
        else:
            app._run_request_middleware = self._run_request_middleware_18_12
            app._run_response_middleware = self._run_response_middleware_18_12
        app.config[APP_CONFIG_INSTANCE_KEY] = self

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
            _spf.delete_temporary_request_context(request)

        def bp_register(bp_self, orig_register, app, options):
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
        bp.register = update_wrapper(partial(bp_register, bp, bp.register),
                                     bp.register)
        setattr(bp, APP_CONFIG_INSTANCE_KEY, self)

    @classmethod
    def _recreate(cls, app):
        self = super(SanicPluginsFramework, cls).__new__(cls)
        self._running = False
        self._app = app
        self._loop = None
        self._plugin_names = set()
        # these deques get replaced with frozen tuples at runtime
        self._pre_request_middleware = deque()
        self._post_request_middleware = deque()
        self._pre_response_middleware = deque()
        self._post_response_middleware = deque()
        self._cleanup_middleware = deque()
        self._contexts = SanicContext(self, None)
        self._contexts['shared'] = SanicContext(self, None, {'app': app})
        self._contexts['_plugins'] = SanicContext(self, None, {'spf': self})
        return self

    def __new__(cls, app, *args, **kwargs):
        assert app, "SPF must be given a valid Sanic App to work with."
        assert isinstance(app, Sanic) or isinstance(app, Blueprint),\
            "SPF only works with Sanic Apps or Blueprints. " \
            "Please pass in an app instance to the SPF constructor."
        # An app _must_ only have one spf instance associated with it.
        # If there is already one registered on the app, return that one.
        try:
            instance = app.config[APP_CONFIG_INSTANCE_KEY]
            assert isinstance(instance, cls),\
                "This app is already registered to a different type of " \
                "Sanic Plugins Framework!"
            return instance
        except AttributeError:  # app must then be a blueprint
            try:
                instance = getattr(app, APP_CONFIG_INSTANCE_KEY)
                assert isinstance(instance, cls),\
                    "This Blueprint is already registered to a different " \
                    "type of Sanic Plugins Framework!"
                return instance
            except AttributeError:
                pass
        except KeyError:
            pass
        self = cls._recreate(app)
        if isinstance(app, Blueprint):
            bp = app
            self._patch_blueprint(bp)
            bp.listener('after_server_start')(self._on_server_start)
        else:
            self._patch_app(app)
            app.listener('after_server_start')(self._on_server_start)
        config = getattr(app, 'config', None)
        if config:
            load_ini = config.get(SPF_LOAD_INI_KEY, True)
            if load_ini:
                ini_file = config.get(SPF_INI_FILE_KEY, 'spf.ini')
                try:
                    load_config_file(self, app, ini_file)
                except FileNotFoundError:
                    pass
        return self

    def __init__(self, *args, **kwargs):
        args = list(args)  # tuple is not mutable. Change it to a list.
        if len(args) > 0:
            args.pop(0)  # remove 'app' arg
        assert self._app and self._contexts,\
            "Sanic Plugin Framework was not initialized correctly."
        assert len(args) < 1, \
            "Unexpected arguments passed to the Sanic Plugins Framework."
        assert len(kwargs) < 1, \
            "Unexpected keyword arguments passed to the SanicPluginsFramework."
        super(SanicPluginsFramework, self).__init__(*args, **kwargs)

    def __getstate__(self):
        if self._running:
            raise RuntimeError(
                "Cannot call __getstate__ on an SPF app that is "
                "already running.")
        state_dict = {}
        for s in SanicPluginsFramework.__slots__:
            if s in ('_running', '_loop'):
                continue
            state_dict[s] = getattr(self, s)
        return state_dict

    def __setstate__(self, state):
        running = getattr(self, '_running', False)
        if running:
            raise RuntimeError(
                "Cannot call __setstate__ on an SPF app that is "
                "already running.")
        for s, v in state.items():
            if s in ('_running', '_loop'):
                continue
            if s == "__weakref__":
                if v is None:
                    continue
                else:
                    raise NotImplementedError("Setting weakrefs on SPF")
            setattr(self, s, v)

    def __reduce__(self):
        if self._running:
            raise RuntimeError(
                "Cannot pickle a SPF App after it has started running!")
        state_dict = self.__getstate__()
        app = state_dict.pop("_app")
        return SanicPluginsFramework._recreate, (app,), state_dict
