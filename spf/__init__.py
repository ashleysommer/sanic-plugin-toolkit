# -*- coding: latin-1 -*-
# this is ascii, no unicode in this document
from .framework import SanicPluginsFramework
from .plugin import SanicPlugin

__version__ = '0.6.4.dev20181101'
__all__ = ["SanicPlugin", "SanicPluginsFramework", "__version__"]
