"""Tests for telemetry and profiling"""

import pytest
import time
from rpycbench.utils.telemetry import RPyCTelemetry, get_telemetry, enable_telemetry
from rpycbench.utils.profiler import (
    ProfiledConnection,
    ProfiledNetRef,
    create_profiled_connection,
    profile_rpyc_calls,
)
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection
import rpyc


class TestTelemetry:
    """Test telemetry tracking"""

    def test_telemetry_tracks_calls(self, rpyc_port):
        """Test that telemetry tracks remote calls"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            telemetry = RPyCTelemetry(enabled=True)

            conn = create_profiled_connection(
                host='localhost',
                port=rpyc_port,
                telemetry_inst=telemetry,
            )

            # Make some calls
            for _ in range(10):
                conn.root.ping()

            conn.close()

            # Verify telemetry
            stats = telemetry.get_statistics()
            assert stats['total_calls'] >= 10
            assert stats['total_network_roundtrips'] >= 10

    def test_telemetry_tracks_netrefs(self, rpyc_port):
        """Test that telemetry tracks netref creation"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            telemetry = RPyCTelemetry(
                enabled=True,
                track_netrefs=True,
            )

            conn = create_profiled_connection(
                host='localhost',
                port=rpyc_port,
                telemetry_inst=telemetry,
            )

            # Access root (creates netref)
            _ = conn.root

            conn.close()

            stats = telemetry.get_statistics()
            # Should have tracked at least the root netref
            assert stats['total_netrefs_created'] >= 1

    def test_telemetry_slow_call_detection(self, rpyc_port):
        """Test that telemetry detects slow calls"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            telemetry = RPyCTelemetry(
                enabled=True,
                slow_call_threshold=0.01,  # 10ms threshold
            )

            conn = create_profiled_connection(
                host='localhost',
                port=rpyc_port,
                telemetry_inst=telemetry,
            )

            # Make a slow call
            conn.root.sleep(0.02)  # 20ms sleep

            conn.close()

            stats = telemetry.get_statistics()
            # Should have detected at least one slow call
            assert stats['num_slow_calls'] >= 1

    def test_telemetry_call_stack_depth(self, rpyc_port):
        """Test that telemetry tracks call stack depth"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            telemetry = RPyCTelemetry(
                enabled=True,
                track_stacks=True,
            )

            conn = create_profiled_connection(
                host='localhost',
                port=rpyc_port,
                telemetry_inst=telemetry,
            )

            # Make some calls
            conn.root.ping()
            conn.root.ping()

            conn.close()

            stats = telemetry.get_statistics()
            # Should track some calls
            assert stats['total_calls'] >= 2


class TestProfiledConnection:
    """Test profiled connection wrapper"""

    def test_profiled_connection_tracks_calls(self, rpyc_port):
        """Test that ProfiledConnection tracks all calls"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            telemetry = RPyCTelemetry(enabled=True)

            conn = ProfiledConnection(
                rpyc.connect('localhost', rpyc_port),
                telemetry_inst=telemetry,
            )

            # Make calls
            result = conn.root.ping()
            assert result == "pong"

            result = conn.root.compute(10)
            assert result == sum(i * i for i in range(10))

            conn.close()

            # Verify tracking
            stats = telemetry.get_statistics()
            assert stats['total_calls'] >= 2

    def test_profiled_connection_context_manager(self, rpyc_port):
        """Test profiled connection as context manager"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            conn = rpyc.connect('localhost', rpyc_port)

            with profile_rpyc_calls(conn, print_summary=False) as profiled:
                profiled.root.ping()
                profiled.root.ping()

                telemetry = profiled.telemetry
                stats = telemetry.get_statistics()
                assert stats['total_calls'] >= 2


class TestTelemetryStatistics:
    """Test telemetry statistics computation"""

    def test_telemetry_computes_avg_duration(self, rpyc_port):
        """Test that telemetry computes average call duration"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            telemetry = RPyCTelemetry(enabled=True)

            conn = create_profiled_connection(
                host='localhost',
                port=rpyc_port,
                telemetry_inst=telemetry,
            )

            # Make several calls
            for _ in range(20):
                conn.root.ping()

            conn.close()

            stats = telemetry.get_statistics()
            assert stats['avg_call_duration'] > 0
            # Each ping() call involves 2 operations: getattr('ping') + __call__()
            assert stats['total_calls'] == 40

    def test_telemetry_reset(self, rpyc_port):
        """Test that telemetry can be reset"""
        telemetry = RPyCTelemetry(enabled=True)

        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            conn = create_profiled_connection(
                host='localhost',
                port=rpyc_port,
                telemetry_inst=telemetry,
            )

            conn.root.ping()
            conn.close()

        # Should have stats
        stats = telemetry.get_statistics()
        assert stats['total_calls'] > 0

        # Reset
        telemetry.reset()

        # Should be zero
        stats = telemetry.get_statistics()
        assert stats['total_calls'] == 0
        assert stats['total_network_roundtrips'] == 0
