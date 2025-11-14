from importlib.metadata import version

from configator.core import load_config

__maintainer__ = "kthy"
__version__ = version("configator")

__all__ = ["__maintainer__", "__version__", "load_config"]
