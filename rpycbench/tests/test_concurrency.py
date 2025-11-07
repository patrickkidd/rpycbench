"""Tests for high concurrency and parallel connections"""

import pytest
import time
from rpycbench.core.benchmark import ConcurrentBenchmark
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection
from rpycbench.servers.http_servers import HTTPBenchmarkServer, create_http_session


class TestHighConcurrency:
    """Test 128+ concurrent connections"""

    def test_128_concurrent_rpyc_connections(self, rpyc_port):
        """Test 128 parallel RPyC connections"""
        with RPyCServer(host="localhost", port=rpyc_port, mode="threaded"):
            bench = ConcurrentBenchmark(
                name="128 Concurrent",
                protocol="rpyc",
                server_mode="threaded",
                connection_factory=lambda: create_rpyc_connection(
                    "localhost", rpyc_port
                ),
                request_func=lambda conn: conn.root.ping(),
                num_clients=128,
                requests_per_client=10,
                track_per_connection=True,
            )

            start_time = time.time()
            metrics = bench.execute()
            duration = time.time() - start_time

            stats = metrics.compute_statistics()

            # Verify all clients completed
            assert stats["concurrent"]["connections"] == 128
            assert stats["concurrent"]["total_requests"] == 128 * 10
            assert stats["concurrent"]["success_rate"] > 0.95  # Allow some failures

            # Verify per-connection metrics
            per_conn = bench.get_per_connection_metrics()
            assert len(per_conn) == 128

            # Each connection should have metrics
            for conn_metrics in per_conn:
                assert "client_id" in conn_metrics
                assert "connection_time" in conn_metrics
                assert "total_requests" in conn_metrics
                assert "latencies" in conn_metrics

            print(f"\n128 clients completed in {duration:.2f}s")
            print(f"Success rate: {stats['concurrent']['success_rate']*100:.1f}%")

    def test_concurrent_connections_different_sizes(self, rpyc_port):
        """Test different concurrency levels"""
        with RPyCServer(host="localhost", port=rpyc_port, mode="threaded"):
            for num_clients in [10, 50, 100]:
                bench = ConcurrentBenchmark(
                    name=f"{num_clients} Concurrent",
                    protocol="rpyc",
                    server_mode="threaded",
                    connection_factory=lambda: create_rpyc_connection(
                        "localhost", rpyc_port
                    ),
                    request_func=lambda conn: conn.root.ping(),
                    num_clients=num_clients,
                    requests_per_client=5,
                )

                metrics = bench.execute()
                stats = metrics.compute_statistics()

                assert stats["concurrent"]["connections"] == num_clients
                assert stats["concurrent"]["total_requests"] == num_clients * 5

    def test_128_concurrent_http_connections(self, http_port):
        """Test 128 parallel HTTP connections"""
        with HTTPBenchmarkServer(host="localhost", port=http_port):
            bench = ConcurrentBenchmark(
                name="128 Concurrent HTTP",
                protocol="http",
                server_mode="threaded",
                connection_factory=lambda: create_http_session(),
                request_func=lambda session: session.get(
                    f"http://localhost:{http_port}/ping"
                ),
                num_clients=128,
                requests_per_client=10,
                track_per_connection=True,
            )

            metrics = bench.execute()
            stats = metrics.compute_statistics()

            assert stats["concurrent"]["connections"] == 128
            assert stats["concurrent"]["success_rate"] > 0.95


class TestPerConnectionMetrics:
    """Test per-connection metrics tracking"""

    def test_per_connection_tracking_enabled(self, rpyc_port):
        """Test per-connection metrics are collected when enabled"""
        with RPyCServer(host="localhost", port=rpyc_port, mode="threaded"):
            bench = ConcurrentBenchmark(
                name="Per Connection Test",
                protocol="rpyc",
                server_mode="threaded",
                connection_factory=lambda: create_rpyc_connection(
                    "localhost", rpyc_port
                ),
                request_func=lambda conn: conn.root.ping(),
                num_clients=10,
                requests_per_client=5,
                track_per_connection=True,
            )

            metrics = bench.execute()
            per_conn = bench.get_per_connection_metrics()

            # Should have metrics for each connection
            assert len(per_conn) == 10

            for i, conn_metrics in enumerate(per_conn):
                assert conn_metrics["client_id"] == i
                assert conn_metrics["total_requests"] > 0
                assert len(conn_metrics["latencies"]) > 0
                assert "connection_time" in conn_metrics
                assert "total_duration" in conn_metrics

    def test_per_connection_tracking_disabled(self, rpyc_port):
        """Test per-connection metrics not collected when disabled"""
        with RPyCServer(host="localhost", port=rpyc_port, mode="threaded"):
            bench = ConcurrentBenchmark(
                name="No Per Connection",
                protocol="rpyc",
                server_mode="threaded",
                connection_factory=lambda: create_rpyc_connection(
                    "localhost", rpyc_port
                ),
                request_func=lambda conn: conn.root.ping(),
                num_clients=10,
                requests_per_client=5,
                track_per_connection=False,
            )

            metrics = bench.execute()
            per_conn = bench.get_per_connection_metrics()

            # Should be empty
            assert len(per_conn) == 0

    def test_slowest_connection_identification(self, rpyc_port):
        """Test ability to identify slowest connection"""
        with RPyCServer(host="localhost", port=rpyc_port, mode="threaded"):
            bench = ConcurrentBenchmark(
                name="Slowest Test",
                protocol="rpyc",
                server_mode="threaded",
                connection_factory=lambda: create_rpyc_connection(
                    "localhost", rpyc_port
                ),
                request_func=lambda conn: conn.root.ping(),
                num_clients=20,
                requests_per_client=10,
                track_per_connection=True,
            )

            metrics = bench.execute()
            per_conn = bench.get_per_connection_metrics()

            # Find slowest connection
            slowest = max(per_conn, key=lambda c: c.get("total_duration", 0))

            assert "client_id" in slowest
            assert slowest["total_duration"] > 0
            print(
                f"\nSlowest client: #{slowest['client_id']} took {slowest['total_duration']:.3f}s"
            )


class TestServerModeComparison:
    """Test comparing different server modes under load"""

    def test_compare_threaded_vs_forking(self, rpyc_port):
        """Test threaded vs forking server under same load"""
        results = {}

        for mode in ["threaded", "forking"]:
            with RPyCServer(host="localhost", port=rpyc_port, mode=mode):
                bench = ConcurrentBenchmark(
                    name=f"Compare {mode}",
                    protocol="rpyc",
                    server_mode=mode,
                    connection_factory=lambda: create_rpyc_connection(
                        "localhost", rpyc_port
                    ),
                    request_func=lambda conn: conn.root.ping(),
                    num_clients=50,
                    requests_per_client=10,
                )

                metrics = bench.execute()
                results[mode] = metrics.compute_statistics()

        # Both should complete successfully
        assert results["threaded"]["concurrent"]["success_rate"] > 0.9
        assert results["forking"]["concurrent"]["success_rate"] > 0.9

        # Both should have similar total requests
        assert results["threaded"]["concurrent"]["total_requests"] == 500
        assert results["forking"]["concurrent"]["total_requests"] == 500

        print(
            f"\nThreaded latency: {results['threaded']['latency']['mean']*1000:.2f}ms"
        )
        print(f"Forking latency: {results['forking']['latency']['mean']*1000:.2f}ms")
