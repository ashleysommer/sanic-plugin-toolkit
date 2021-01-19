Sanic Plugin Toolkit
====================

0.99.1
------
- Project Renamed to Sanic Plugin Toolkit
  - Module is renamed from spf to sanic_plugin_toolkit (fixes #16)
- Changed to PEP517/518 project, with pyproject.toml and Poetry
  - removed setup.py, setup.cfg, environment.yml, tox.ini

0.9.4.post2
-----------
- Pinned this series of SPF to maximum Sanic v20.12.x, this series will not work on Sanic 21.x

  - A new version of SanicPluginsFramework is in development that will work on Sanic 21.x
  - It will have a new module name to avoid the conflict with the other `spf` library on Pip.
  - It will be a PEP 517/518 project, with pyproject.toml and Poetry orchestration.
  - New features in Sanic 21.x will necessitate some big changes in SanicPluginsFramework (this is a good thing!)


0.9.4.post1
-----------
- Add ``setuptools`` as a specific requirement to this project.

  - It is needed for the entrypoints-based plugin auto-discovery feature
  - ``setuptools`` is not always included in a python distribution, so we cannot assume it will be there
  - Pinned to ``>40.0`` for now, but will likely change when we migrate to a Poetry/PEP517-based project


0.9.4
-----------
- If the Sanic server emits a "before_server_start" event, use this to initialize SPF, instead of the
  "after_server_start" event.

  - This solves a potential race-condition introduced in SPF v0.8.2, when this was reversed.
- Changed the RuntimeError thrown in that circumstance to a Sanic ``ServerError``

  - This may make the error easier to catch and filter. Also may change what the end-user sees when this occurs.


0.9.3
-----------
- Fixed calling routes on a SPF-enabled Sanic app using asgi_client before the app is started.
- Clarified error message generated when a SPF-enabled route is called before the Sanic server is booted.
- Fixed test breakages for Sanic 20.3 and 20.6 releases
- Updated testing packages in requirements-dev
- Updated Travis and TOX to include python 3.8 tests


0.9.2
-----------
- Added a convenience feature on SanicContext class to get the request-context for a given request
- Added correct licence file to LICENSE.txt

  - Existing one was accidentally a copy of the old Sanic-CORS licence file
  - Renamed from LICENSE to LICENSE.txt


0.9.1
-----------
- Fixed a problem with error reporting when a plugin is not yet registered on the SPF


0.9.0
-----------
- Released 0.9.0 with Sanic 19.12LTS compatibility
- Minimum supported sanic version is 18.12LTS


0.9.0.b1
-----------
- New minimum supported sanic version is 18.12LTS
- Fixed bugs with Sanic 19.12LTS
- Fixed registering plugin routes on blueprints
- Tested more on blueprints
- Added python3.7 tests to tox, and travis
- Max supported sanic version for this release series is unknown for now.


0.8.2.post1
-----------
- Explicitly set max Sanic version supported to 19.6.3
- This is the last SPF version to support Sanic v0.8.3

  - (please update to 18.12 or greater if you are still on 0.8.3)


0.8.2
-----
- Change all usages of "before_server_start" to "after_server_start"

  - The logic is basically the same, and this ensures compatibility with external servers, like ASGI mode, and using gunicorn runner, etc.


0.8.1
-----
- Plugin names in the config file are now case insensitive
- Plugin names exported using entrypoints are now case insensitive

0.8.0
-----
- Added support for a spf config file

  - This is in the python configparser format, it is like an INI file.
  - See the config file example in /examples/ for how to use it.

- Added ability to get a plugin assoc object from SPF, simply by asking for the plugin name.

  - This is to facilitate pulling the assoc object from when a plugin was registered via the config file

- A new way of advertising sanic plugins using setup.py entrypoints is defined.

  - We use it in this project to advertise the 'Contextualize' plugin.

- Fixed some example files.

0.7.0
-----
- Added a new type of middleware called "cleanup" middleware

  - It Runs after response middleware, whether response is generated or not, and even if there was errors.
- Moved the request-context removal process to run in the "cleanup" middleware step, because sometimes Response middleware is not run, eg. if Response is None (like in the case of a Websocket route), then Response Middleware will never fire.
- Cleanup middleware can be used to do per-request cleanup to prevent memory leaks.

0.6.7
-----
- A critical fix for plugin-private-request contexts. They were always overwriting the shared request context when they were created.
- Added new 'id' field inside the private request context container and the shared request context container, to tell them apart when they are used.
- Added a new test for this exact issue.

0.6.6
-----
- No 1.0 yet, there are more features planed before we call SPF ready for 1.0.
- Add more tests, and start filling in some missing test coverage
- Fix a couple of bugs already uncovered by filling in coverage.

  - Notably, fix an issue that was preventing the plugin static file helper from working.


0.6.5
-----
- Changed the versioning scheme to not include ".devN" suffixes. This was preventing SPF from being installed using ``pipenv``

  - This is in preparation for a 1.0.0 release, to coincide with the Sanic 2018.12 release.


0.6.4.dev20181101
-----------------
- Made changes in order for SPF, and Sanic Plugins to be pickled
- This fixes the ability for SPF-enabled Sanic Apps to use ``workers=`` on Windows, to allow multiprocessing.

  - Added ``__setstate__``, ``__getstate__``, and ``__reduce__`` methods to all SPF classes
  - Change usages of PriorityQueue to collections.deque (PriorityQueue cannot be pickled because it is a synchronous class)
  - Changed the "name" part of all namedtuples to be the same name as the attribute key on the module they are declared in. This is necessary in order to be able to de-pickle a namedtuple object.

    - This *may* be a breaking change?

  - No longer store our own logger, because they cannot be picked. Just use the global logger provided by ``sanic.log.logger``


0.6.3.dev20180717
-----------------
- Added listener functions to contextualize plugin,
- added a new example for using sqlalchemy with contextualize plugin
- Misc fixes


0.6.2.dev20180617
-----------------
- SanicPluginsFramework now comes with its own built-in plugin (one of possibly more to come)
- The Contextualize plugin offers the shared context and enhanced middleware functions of SanicPluginsFramework, to regular Sanic users.
- You no longer need to be writing a plugin in order to access features provided by SPF.
- Bump version


0.6.1.dev20180616
-----------------
- Fix flake problem inhibiting tox tests on travis from passing.


0.6.0.dev20180616
-----------------
- Added long-awaited feature:

  - add Plugin Websocket routes
  - and add Plugin Static routes

- This more-or-less completes the feature line-up for SanicPluginsFramework.
- Testing is not in place for these features yet.
- Bump version to 0.6.0.dev20180616


0.5.2.dev20180201
-----------------
- Changed tox runner os env from ``precise`` to ``trusty``.
- Pin pytest to 3.3.2 due to a major release bug in 3.4.0.


0.5.1.dev20180201
-----------------
- Removed uvloop and ujson from requirements. These break on Windows.
- Sanic requires these, but deals with the incompatibility on windows itself.
- Also ensure requirements.txt is included in the wheel package.
- Added python 3.7 to supported python versions.


0.5.0.dev20171225
-----------------
- Merry Christmas!
- Sanic version 0.7.0 has been out for a couple of weeks now. It is now our minimum required version.
- Fixed a bug related to deleting shared context when app is a Blueprint. Thanks @huangxinping!


0.4.5.dev20171113
-----------------
- Fixed error in plugin.log helper. It now calls the correct context .log function.


0.4.4.dev20171107
-----------------
- Bump to version 0.4.4 because 0.4.3 broke, and PyPI wouldn't let me re-upload it with the same version.


0.4.3.dev20171107
-----------------
- Fixed ContextDict to no longer be derived from ``dict``, while at the same time act more like a dictionary.
- Added ability for the request context to hold more than one request at once. Use ``id(request)`` to get the correct request context from the request-specific context dict.


0.4.2.dev20171106
-----------------
- Added a new namedtuple that represents a plugin registration association.
- It is simply a tuple of the plugin instance, and a matching PluginRegistration.

  - This is needed in the Sanic-Restplus port.

- Allow plugins to choose their own PluginAssociated class.


0.4.1.dev20171103
-----------------
- Ensure each SPF registers only one 'before_server_start' listener, no matter how many time the SPF is used, and how many plugins are registered on the SPF.
- Added a test to ensure logging works, when got the function from the context object.


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
