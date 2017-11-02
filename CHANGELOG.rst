Sanic Plugins Framework
=======================

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
Fix readme, add shields

0.1.0.20171018
--------------
Bump version to trigger travis tests, and initial pypi build

0.1.0.dev1
----------
Initial release, pre-alpha.
Got TOX build working with Python 3.5 and Python 3.6, with pytest tests and flake8
