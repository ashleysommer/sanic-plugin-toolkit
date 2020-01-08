# -*- coding: latin-1 -*-
# this is ascii, no unicode in this document
from .framework import SanicPluginsFramework
from .plugin import SanicPlugin

__version__ = '0.8.2.post1'
__all__ = ["SanicPlugin", "SanicPluginsFramework", "__version__"]
