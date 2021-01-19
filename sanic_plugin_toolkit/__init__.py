# -*- coding: latin-1 -*-
# this is ascii, no unicode in this document
from .realm import SanicPluginRealm
from .plugin import SanicPlugin

__version__ = '0.99.1a1'
__all__ = ["SanicPlugin", "SanicPluginRealm", "__version__"]
