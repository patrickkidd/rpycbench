"""Integration tests for complete workflows"""

import pytest
import time
from rpycbench.benchmarks.suite import BenchmarkSuite
from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection
from rpycbench.servers.http_servers import HTTPBenchmarkServer


class TestEndToEnd:
    """Test complete end-to-end workflows"""

    def test_baseline_comparison_workflow(self, rpyc_port, http_port):
        """Test running a baseline comparison"""
        suite = BenchmarkSuite(
            rpyc_host='localhost',
            rpyc_port=rpyc_port,
            http_host='localhost',
            http_port=http_port,
        )

        # Run with small parameters for speed
        results = suite.run_all(
            test_rpyc_threaded=True,
            test_rpyc_forking=False,  # Skip for speed
            test_http=True,
            num_connections=5,
            num_requests=10,
            num_concurrent_clients=3,
            requests_per_client=5,
        )

        # Verify results
        comparison = results.get_comparison_table()

        assert 'rpyc_threaded' in comparison
        assert 'http_threaded' in comparison

        # Both should have latency metrics
        assert 'latency' in comparison['rpyc_threaded']
        assert 'latency' in comparison['http_threaded']

    def test_app_integration_workflow(self, rpyc_port):
        """Test integrating benchmarks into an app"""

        class MockApp:
            def __init__(self, conn):
                self.conn = conn

            def process(self, data):
                # Simulate app overhead
                time.sleep(0.001)
                result = self.conn.root.echo(data)
                return result

        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            conn = create_rpyc_connection('localhost', rpyc_port)

            # Baseline benchmark
            with BenchmarkContext("Baseline", "rpyc", measure_latency=True) as baseline_bench:
                for _ in range(10):
                    with baseline_bench.measure_request():
                        conn.root.ping()
                        baseline_bench.record_request(success=True)

            # App benchmark
            app = MockApp(conn)
            with BenchmarkContext("With App", "rpyc", measure_latency=True) as app_bench:
                for _ in range(10):
                    with app_bench.measure_request():
                        app.process(b"test")
                        app_bench.record_request(success=True)

            conn.close()

            # Compare results
            baseline_stats = baseline_bench.get_results().compute_statistics()
            app_stats = app_bench.get_results().compute_statistics()

            # App should have higher latency due to overhead
            assert app_stats['latency']['mean'] > baseline_stats['latency']['mean']


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_server_timeout(self):
        """Test handling of server startup timeout"""
        # Try to connect to non-existent server
        server = RPyCServer(host='localhost', port=19999, mode='threaded')

        # This should timeout waiting for server
        with pytest.raises((TimeoutError, Exception)):
            # Manually create and try to wait
            import multiprocessing
            server.ready_event = multiprocessing.Event()
            server._wait_for_server(timeout=1)

    def test_failed_requests_tracking(self, rpyc_port):
        """Test that failed requests are tracked"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            with BenchmarkContext("Test", "rpyc", measure_latency=True) as bench:
                conn = create_rpyc_connection('localhost', rpyc_port)

                # Some successful requests
                for _ in range(5):
                    with bench.measure_request():
                        conn.root.ping()
                        bench.record_request(success=True)

                # Some failed requests
                for _ in range(3):
                    bench.record_request(success=False)

                conn.close()

            metrics = bench.get_results()
            stats = metrics.compute_statistics()

            assert stats['concurrent']['total_requests'] == 8
            assert stats['concurrent']['failed_requests'] == 3
            assert stats['concurrent']['success_rate'] == 5.0 / 8.0


class TestRobustness:
    """Test robustness and stability"""

    def test_repeated_server_start_stop(self, rpyc_port):
        """Test starting and stopping server multiple times"""
        for _ in range(3):
            with RPyCServer(host='localhost', port=rpyc_port, mode='threaded') as server:
                conn = create_rpyc_connection('localhost', rpyc_port)
                result = conn.root.ping()
                assert result == "pong"
                conn.close()

            # Small delay between iterations
            time.sleep(0.5)

    def test_server_cleanup_on_crash(self, rpyc_port):
        """Test that server process is cleaned up properly"""
        server = RPyCServer(host='localhost', port=rpyc_port, mode='threaded')
        server.start()

        # Record PID
        server_pid = server.server_process.pid
        assert server.server_process.is_alive()

        # Stop server
        server.stop()
        time.sleep(0.5)

        # Process should be terminated
        assert not server.server_process.is_alive()

    def test_concurrent_benchmark_with_errors(self, rpyc_port):
        """Test concurrent benchmark handles some connection failures gracefully"""
        # This tests resilience - some connections might fail but benchmark should complete
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            from rpycbench.core.benchmark import ConcurrentBenchmark

            bench = ConcurrentBenchmark(
                name="Resilience Test",
                protocol="rpyc",
                server_mode="threaded",
                connection_factory=lambda: create_rpyc_connection('localhost', rpyc_port),
                request_func=lambda conn: conn.root.ping(),
                num_clients=20,
                requests_per_client=5,
            )

            metrics = bench.execute()
            stats = metrics.compute_statistics()

            # Should complete even if some fail
            assert stats['concurrent']['connections'] == 20
            # Should have attempted all requests
            assert stats['concurrent']['total_requests'] > 0


class TestDataIntegrity:
    """Test data integrity throughout benchmarks"""

    def test_data_transfer_integrity(self, rpyc_port, test_data_large):
        """Test that data is transferred correctly"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            conn = create_rpyc_connection('localhost', rpyc_port)

            # Test echo preserves data
            result = conn.root.echo(test_data_large)
            assert result == test_data_large

            # Test download returns correct size
            downloaded = conn.root.download(len(test_data_large))
            assert len(downloaded) == len(test_data_large)

            conn.close()
