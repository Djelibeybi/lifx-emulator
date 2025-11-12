"""LIFX Emulator CLI

Command-line interface and HTTP API server for the LIFX emulator.
"""

from importlib.metadata import version as get_version

__version__ = get_version("lifx-emulator-cli")

__all__ = ["__version__"]
