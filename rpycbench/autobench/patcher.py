"""Monkey-patching for automatic RPyC connection profiling"""

import sys
import rpyc
from typing import Optional

from rpycbench.utils.profiler import ProfiledConnection
from rpycbench.utils.telemetry import get_telemetry


_original_connect = None
_original_classic_connect = None
_patches_installed = False


def install_patches():
    """Install monkey patches for rpyc.connect and rpyc.utils.classic.connect

    This intercepts connection creation to automatically wrap connections
    with profiling capabilities.
    """
    global _original_connect, _original_classic_connect, _patches_installed

    if _patches_installed:
        return

    import rpyc as rpyc_module
    _original_connect = rpyc_module.connect

    def profiled_connect(*args, **kwargs):
        """Wrapper for rpyc.connect that returns a ProfiledConnection"""
        conn = _original_connect(*args, **kwargs)
        telemetry = get_telemetry()
        return ProfiledConnection(conn, telemetry_inst=telemetry)

    rpyc_module.connect = profiled_connect

    try:
        import rpyc.utils.classic as classic_module
        _original_classic_connect = classic_module.connect

        def profiled_classic_connect(*args, **kwargs):
            """Wrapper for rpyc.utils.classic.connect that returns a ProfiledConnection"""
            conn = _original_classic_connect(*args, **kwargs)
            telemetry = get_telemetry()
            return ProfiledConnection(conn, telemetry_inst=telemetry)

        classic_module.connect = profiled_classic_connect
    except (ImportError, AttributeError):
        pass

    _patches_installed = True


def uninstall_patches():
    """Restore original RPyC connection functions"""
    global _patches_installed

    if not _patches_installed:
        return

    if _original_connect:
        import rpyc as rpyc_module
        rpyc_module.connect = _original_connect

    if _original_classic_connect:
        try:
            import rpyc.utils.classic as classic_module
            classic_module.connect = _original_classic_connect
        except (ImportError, AttributeError):
            pass

    _patches_installed = False


def is_patched() -> bool:
    """Check if patches are currently installed"""
    return _patches_installed
