"""LIFX Emulator Application

Standalone CLI and HTTP management API for the LIFX Emulator.
"""

from importlib.metadata import version as get_version

__version__ = get_version("lifx-emulator")

__all__ = ["__version__"]
