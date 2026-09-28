"""PyPI launcher for the Audioreconstructor native ONNX executable."""
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version("audioreconstructor")
except PackageNotFoundError:  # running from a source tree without an installed dist
    __version__ = "0.0.0+source"
