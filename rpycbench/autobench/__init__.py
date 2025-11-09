"""Automatic RPyC profiling for user applications

This module provides automatic profiling capabilities by monkey-patching
RPyC connection creation to transparently inject telemetry tracking.
"""

from rpycbench.autobench.patcher import install_patches, uninstall_patches

__all__ = ['install_patches', 'uninstall_patches']
