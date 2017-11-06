Sanic Plugins Framework
=======================

|Build Status| |Latest Version| |Supported Python versions| |License|

Welcome to the Sanic Plugins Framework README file.

The Sanic Plugins Framework (SPF) is a lightweight python library aimed at making it as simple as possible to build
plugins for the Sanic Async HTTP Server.

The SPF provides a `SanicPlugin` python base object that your plugin can build upon. It is set up with all of the basic
functionality that the majority of Sanic Plugins will need.

A SPF Sanic Plugin is implemented in a similar way to Sanic Blueprints. You can use convenience decorators to set up all
of the routes, middleware, exception handlers, and listeners your plugin uses in the same way you would a blueprint,
and any Application developer can import your plugin and register it into their application.

The Sanic Plugins Framework is more than just a Blueprints-like system for Plugins. It provides an enhanced middleware
system, and manages Context objects.

The Enhanced Middleware System
------------------------------

The Middleware system in the Sanic Plugins Framework both builds upon and extends the native Sanic middleware system.
Rather than simply having two middleware queues ('request', and 'response'), the middleware system in SPF uses four
queues.

- Request-Pre: These middleware run *before* the application's own request middleware.
- Request-Post: These middleware run *after* the application's own request middleware.
- Response-Pre: These middleware run *before* the application's own response middleware.
- Response-Post: These middleware run *after* the application's own response middleware.

So as a plugin developer you can choose whether you need your middleware to be executed before or after the
application's own middleware.

You can also assign a priority to each of your plugin's middleware so you can more precisely control the order in which
your middleware is executed, especially when the application is using multiple plugins.

The Context Object Manager
--------------------------

One feature that many find missing from Sanic is a context object. SPF provides multiple context objects that can be
used for different purposes.

- A shared context: All plugins registered in the SPF have access to a shared, persistent context object, which anyone can read and write to.
- A per-request context: All plugins get access to a shared temporary context object anyone can read and write to that is created at the start of a request, and deleted when a request is completed.
- A per-plugin context: All plugins get their own private persistent context object that only that plugin can read and write to.
- A per-plugin per-request context: All plugins get a temporary context object that is created at the start of a request, and deleted when a request is completed.


Installation
------------

Install the extension with using pip, or easy\_install.

.. code:: bash

    $ pip install -U sanic-plugins-framework

Usage
-----

A simple plugin written using the Sanic Plugins Framework will look like this:

.. code:: python

    # Source: my_plugin.py
    from spf import SanicPlugin
    from sanic.response import text

    class MyPlugin(SanicPlugin):
        def __init__(self, *args, **kwargs):
            super(MyPlugin, self).__init__(*args, **kwargs)
            # do pre-registration plugin init here.
            # Note, context objects are not accessible here.

        def on_registered(self, context, reg, *args, **kwargs):
            # do post-registration plugin init here
            # We have access to our context and the shared context now.
            context.my_private_var = "Private variable"
            shared = c.shared
            shared.my_shared_var = "Shared variable"

    my_plugin = MyPlugin()

    # You don't need to add any parameters to @middleware, for default behaviour
    # This is completely compatible with native Sanic middleware behaviour
    @my_plugin.middleware
    def my_middleware(request)
        h = request.headers
        #Do request middleware things here

    #You can tune the middleware priority, and add a context param like this
    #Priority must be between 0 and 9 (inclusive). 0 is highest priority, 9 the lowest.
    #If you don't specify an 'attach_to' parameter, it is a 'request' middleware
    @my_plugin.middleware(priority=6, with_context=True)
    def my_middleware2(request, context):
        context['test1'] = "test"
        print("Hello world")

    #Add attach_to='response' to make this a response middleware
    @my_plugin.middleware(attach_to='response', with_context=True)
    def my_middleware3(request, response, context):
        # Do response middleware here
        return response

    #Add relative='pre' to make this a response middleware run _before_ the
    #application's own response middleware
    @my_plugin.middleware(attach_to='response', relative='pre', with_context=True)
    def my_middleware4(request, response, context):
        # Do response middleware here
        return response

    #Add your plugin routes here. You can even choose to have your context passed in to the route.
    @my_plugin.route('/test_plugin', with_context=True)
    def t1(request, context):
        words = context['test1']
        return text('from plugin! {}'.format(words))


The Application developer can use your plugin in their code like this:

.. code:: python

    # Source: app.py
    from sanic import Sanic
    from spf import SanicPluginFramework
    from sanic.response import text
    import my_plugin

    app = Sanic(__name__)
    spf = SanicPluginFramework(app)
    spf.register_plugin(my_plugin)

    # ... rest of user app here

Or if the developer prefers to do it the old way, (the Flask way), they can still do it like this:

.. code:: python

    # Source: app.py
    from sanic import Sanic
    from sanic.response import text
    from my_plugin import MyPlugin

    app = Sanic(__name__)
    # this magically returns your previously initialized instance
    # from your plugin module, if it is named `my_plugin` or `instance`.
    reg = MyPlugin(app)

    # ... rest of user app here

Contributing
------------

Questions, comments or improvements? Please create an issue on
`Github <https://github.com/ashleysommer/sanicpluginsframework>`__

Credits
-------

Ashley Sommer `ashleysommer@gmail.com <ashleysommer@gmail.com>`__


.. |Build Status| image:: https://api.travis-ci.org/ashleysommer/sanicpluginsframework.svg?branch=master
   :target: https://travis-ci.org/ashleysommer/sanicpluginsframework

.. |Latest Version| image:: https://img.shields.io/pypi/v/Sanic-Plugins-Framework.svg
   :target: https://pypi.python.org/pypi/Sanic-Plugins-Framework/

.. |Supported Python versions| image:: https://img.shields.io/pypi/pyversions/Sanic-Plugins-Framework.svg
   :target: https://img.shields.io/pypi/pyversions/Sanic-Plugins-Framework.svg

.. |License| image:: http://img.shields.io/:license-mit-blue.svg
   :target: https://pypi.python.org/pypi/Sanic-Plugins-Framework/
