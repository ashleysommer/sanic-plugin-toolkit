Sanic Plugins Framework
=======================

0.4.1.dev20171103
-----------------
Ensure each SPF registers only one 'before_server_start' listener, no matter how many time the SPF is used, and
how many plugins are registered on the SPF.

Added a test to ensure logging works, when got the function from the context object.


0.4.0.dev20171103
-----------------
Some big architecture changes.

Split plugin and framework into separate files.

We no longer assume the plugin is going to be registered onto only one app/blueprint.

The plugin can be registered many times, onto many different SPF instances, on different apps.

This means we can no longer easily get a known context object directly from the plugin instance, now the context object
must be provided by the SPF that is registered on the given app. We also need to pass around the context object a bit
more than we did before. While this change makes the whole framework more complicated, it now actually feels cleaner.

This _should_ be enough to get Sanic-Cors ported over to SPF.

Added some tests.

Fixed some tests.


0.3.3.dev20171102
-----------------
Fixed bug in getting the plugin context object, when using the view/route decorator feature.

Got decorator-level middleware working. It runs the middleware on a per-view basis if the Plugin is not registered
on the app or blueprint, when decorating a view with a plugin.


0.3.2.dev20171102
-----------------
First pass cut at implementing a view-specific plugin, using a view decorator.

This is very handy for when you don't want to register a plugin on the whole application (or blueprint),
rather you just want the plugin to run on specific select views/routes. The main driver for this function is for
porting Sanic-CORS plugin to use sanic-plugins-framework, but it will be useful for may other plugins too.


0.3.1.dev20171102
-----------------
Fixed a bug when getting the spf singleton from a Blueprint

This fixed Legacy-style plugin registration when using blueprints.


0.3.0.dev20171102
-----------------
Plugins can now be applied to Blueprints! This is a game changer!

A new url_for function for the plugin! This is a handy thing when you need it.

Added a new section in the examples in the readme.

Bug fixes.


0.2.0.dev20171102
-----------------
Added a on_before_register hook for plugins, this is called when the plugin gets registered, but _before_ all of
the Plugin's routes, middleware, tasks, and exception handlers are evaluated. This allows the Plugin Author to
dynamically build routes and middleware at runtime based on the passed in configuration.

Added changelog.


0.1.0.dev20171101
-----------------
More features!

SPF can only be instantiated once per App now. If you try to create a new SPF for a given app, it will give you back the existing one.

Plugins can now be registered into SPF by using the plugin's module, and also by passing in the Class name of the plugin. Its very smart.

Plugins can use the legacy method to register themselves on an app. Like ``sample_plugin = SamplePlugin(app)`` it will work correctly.

More tests!

FLAKE8 now runs on build, and _passes_!

Misc Bug fixes.


0.1.0.20171018-1 (.post1)
-------------------------
Fix readme, add shields to readme


0.1.0.20171018
--------------
Bump version to trigger travis tests, and initial pypi build


0.1.0.dev1
----------
Initial release, pre-alpha.
Got TOX build working with Python 3.5 and Python 3.6, with pytest tests and flake8
