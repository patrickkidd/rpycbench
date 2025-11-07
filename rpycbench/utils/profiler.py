"""RPyC connection profiler and wrapper"""

import rpyc
from rpyc.core import netref
import time
from typing import Any, Optional
from contextlib import contextmanager

from rpycbench.utils.telemetry import get_telemetry


class ProfiledNetRef:
    """Wrapper around RPyC netref that tracks accesses"""

    def __init__(self, netref_obj: Any, telemetry_inst, netref_id: int):
        object.__setattr__(self, '_netref_obj', netref_obj)
        object.__setattr__(self, '_telemetry', telemetry_inst)
        object.__setattr__(self, '_netref_id', netref_id)

    def __getattr__(self, name):
        if name.startswith('_'):
            return object.__getattribute__(self, name)

        telemetry = object.__getattribute__(self, '_telemetry')
        netref_obj = object.__getattribute__(self, '_netref_obj')
        netref_id = object.__getattribute__(self, '_netref_id')

        call_id = telemetry.start_call(
            method_name=f"getattr({name})",
            call_type='getattr',
            is_netref=True,
            netref_id=netref_id,
        )

        try:
            result = getattr(netref_obj, name)

            result_is_netref = isinstance(result, netref.BaseNetref)
            result_netref_id = None

            if result_is_netref:
                result_netref_id = telemetry.register_netref(result, created_by_call_id=call_id)
                result = ProfiledNetRef(result, telemetry, result_netref_id)

            telemetry.end_call(call_id, result_is_netref, result_netref_id)
            return result

        except Exception as e:
            telemetry.end_call(call_id, exception=e)
            raise

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        telemetry = object.__getattribute__(self, '_telemetry')
        netref_obj = object.__getattribute__(self, '_netref_obj')
        netref_id = object.__getattribute__(self, '_netref_id')

        call_id = telemetry.start_call(
            method_name=f"setattr({name})",
            call_type='setattr',
            is_netref=True,
            netref_id=netref_id,
        )

        try:
            setattr(netref_obj, name, value)
            telemetry.end_call(call_id)
        except Exception as e:
            telemetry.end_call(call_id, exception=e)
            raise

    def __call__(self, *args, **kwargs):
        telemetry = object.__getattribute__(self, '_telemetry')
        netref_obj = object.__getattribute__(self, '_netref_obj')
        netref_id = object.__getattribute__(self, '_netref_id')

        call_id = telemetry.start_call(
            method_name="__call__",
            call_type='call',
            is_netref=True,
            netref_id=netref_id,
        )

        try:
            result = netref_obj(*args, **kwargs)

            result_is_netref = isinstance(result, netref.BaseNetref)
            result_netref_id = None

            if result_is_netref:
                result_netref_id = telemetry.register_netref(result, created_by_call_id=call_id)
                result = ProfiledNetRef(result, telemetry, result_netref_id)

            telemetry.end_call(call_id, result_is_netref, result_netref_id)
            return result

        except Exception as e:
            telemetry.end_call(call_id, exception=e)
            raise

    def __repr__(self):
        netref_obj = object.__getattribute__(self, '_netref_obj')
        netref_id = object.__getattribute__(self, '_netref_id')
        return f"<ProfiledNetRef #{netref_id} wrapping {repr(netref_obj)}>"


class ProfiledConnection:
    """
    Wrapper around RPyC connection that profiles all remote calls

    This intercepts all remote method calls and tracks:
    - Number of network round trips
    - Netref creation and usage
    - Call stacks and nesting depth
    - Performance of individual calls
    """

    def __init__(
        self,
        connection: rpyc.Connection,
        telemetry_inst=None,
        auto_print_on_slow: bool = True,
        auto_print_on_deep: bool = True,
    ):
        self._connection = connection
        self._telemetry = telemetry_inst or get_telemetry()
        self._auto_print_on_slow = auto_print_on_slow
        self._auto_print_on_deep = auto_print_on_deep
        self._root_netref_id = None

    @property
    def root(self):
        """Get profiled root object"""
        if self._root_netref_id is None:
            root_obj = self._connection.root
            self._root_netref_id = self._telemetry.register_netref(root_obj)

        return ProfiledNetRef(
            self._connection.root,
            self._telemetry,
            self._root_netref_id
        )

    def close(self):
        """Close connection and print telemetry summary"""
        self._connection.close()

    @property
    def telemetry(self):
        """Get telemetry instance"""
        return self._telemetry

    def __getattr__(self, name):
        """Proxy other attributes to underlying connection"""
        return getattr(self._connection, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def create_profiled_connection(
    host: str = 'localhost',
    port: int = 18812,
    telemetry_inst=None,
    auto_print_on_slow: bool = False,
    auto_print_on_deep: bool = False,
    **rpyc_config
) -> ProfiledConnection:
    """
    Create a profiled RPyC connection

    Args:
        host: Server host
        port: Server port
        telemetry_inst: Custom telemetry instance (uses global if None)
        auto_print_on_slow: Automatically print stack on slow calls
        auto_print_on_deep: Automatically print stack on deep recursion
        **rpyc_config: Additional RPyC connection config

    Returns:
        ProfiledConnection instance
    """
    config = {
        'allow_public_attrs': True,
        'allow_pickle': True,
        'sync_request_timeout': 30,
    }
    config.update(rpyc_config)

    conn = rpyc.connect(host, port, config=config)

    return ProfiledConnection(
        conn,
        telemetry_inst=telemetry_inst,
        auto_print_on_slow=auto_print_on_slow,
        auto_print_on_deep=auto_print_on_deep,
    )


@contextmanager
def profile_rpyc_calls(
    connection: rpyc.Connection,
    print_summary: bool = True,
    **telemetry_kwargs
):
    """
    Context manager for profiling RPyC calls

    Example:
        conn = rpyc.connect('localhost', 18812)
        with profile_rpyc_calls(conn) as profiled_conn:
            profiled_conn.root.some_method()
        # Telemetry summary printed automatically
    """
    from rpycbench.utils.telemetry import RPyCTelemetry

    telemetry = RPyCTelemetry(enabled=True, **telemetry_kwargs)
    profiled_conn = ProfiledConnection(connection, telemetry_inst=telemetry)

    try:
        yield profiled_conn
    finally:
        if print_summary:
            telemetry.print_summary()
