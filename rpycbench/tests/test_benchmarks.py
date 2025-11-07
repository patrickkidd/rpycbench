"""Tests for benchmark implementations"""

import pytest
import time
from rpycbench.core.benchmark import (
    ConnectionBenchmark,
    LatencyBenchmark,
    BandwidthBenchmark,
    ConcurrentBenchmark,
    BenchmarkContext,
)
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection
from rpycbench.servers.http_servers import HTTPBenchmarkServer, create_http_session


class TestConnectionBenchmark:
    """Test connection establishment benchmarking"""

    def test_rpyc_connection_benchmark(self, rpyc_port):
        """Test RPyC connection benchmark"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            bench = ConnectionBenchmark(
                name="Test Connection",
                protocol="rpyc",
                server_mode="threaded",
                connection_factory=lambda: create_rpyc_connection('localhost', rpyc_port),
                num_connections=10,
            )

            metrics = bench.execute()
            stats = metrics.compute_statistics()

            assert 'connection_time' in stats
            assert stats['connection_time']['count'] == 10
            assert stats['connection_time']['mean'] > 0
            assert stats['connection_time']['min'] > 0

    def test_http_connection_benchmark(self, http_port):
        """Test HTTP connection benchmark"""
        with HTTPBenchmarkServer(host='localhost', port=http_port):
            bench = ConnectionBenchmark(
                name="Test Connection",
                protocol="http",
                server_mode="threaded",
                connection_factory=lambda: create_http_session(),
                num_connections=10,
            )

            metrics = bench.execute()
            stats = metrics.compute_statistics()

            assert 'connection_time' in stats
            assert stats['connection_time']['count'] == 10


class TestLatencyBenchmark:
    """Test latency benchmarking"""

    def test_rpyc_latency_benchmark(self, rpyc_port):
        """Test RPyC latency measurement"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            bench = LatencyBenchmark(
                name="Test Latency",
                protocol="rpyc",
                server_mode="threaded",
                connection_factory=lambda: create_rpyc_connection('localhost', rpyc_port),
                request_func=lambda conn: conn.root.ping(),
                num_requests=50,
                warmup_requests=5,
            )

            metrics = bench.execute()
            stats = metrics.compute_statistics()

            assert 'latency' in stats
            assert stats['latency']['count'] == 50
            assert stats['latency']['mean'] > 0
            assert stats['latency']['median'] > 0
            assert stats['latency']['p95'] > 0
            assert stats['latency']['p99'] > 0
            assert stats['latency']['min'] > 0
            assert stats['latency']['max'] > 0

    def test_http_latency_benchmark(self, http_port):
        """Test HTTP latency measurement"""
        with HTTPBenchmarkServer(host='localhost', port=http_port):
            bench = LatencyBenchmark(
                name="Test Latency",
                protocol="http",
                server_mode="threaded",
                connection_factory=lambda: create_http_session(),
                request_func=lambda session: session.get(f'http://localhost:{http_port}/ping'),
                num_requests=50,
            )

            metrics = bench.execute()
            stats = metrics.compute_statistics()

            assert 'latency' in stats
            assert stats['latency']['count'] == 50


class TestBandwidthBenchmark:
    """Test bandwidth benchmarking"""

    def test_rpyc_bandwidth_benchmark(self, rpyc_port, test_data_small):
        """Test RPyC bandwidth measurement"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            bench = BandwidthBenchmark(
                name="Test Bandwidth",
                protocol="rpyc",
                server_mode="threaded",
                connection_factory=lambda: create_rpyc_connection('localhost', rpyc_port),
                upload_func=lambda conn, data: conn.root.upload(data),
                download_func=lambda conn, size: conn.root.download(size),
                data_sizes=[1024, 10240],
                iterations=5,
            )

            metrics = bench.execute()
            stats = metrics.compute_statistics()

            assert 'upload_bandwidth' in stats
            assert 'download_bandwidth' in stats
            assert stats['upload_bandwidth']['mean'] > 0
            assert stats['download_bandwidth']['mean'] > 0

    def test_http_bandwidth_benchmark(self, http_port):
        """Test HTTP bandwidth measurement"""
        with HTTPBenchmarkServer(host='localhost', port=http_port):
            bench = BandwidthBenchmark(
                name="Test Bandwidth",
                protocol="http",
                server_mode="threaded",
                connection_factory=lambda: create_http_session(),
                upload_func=lambda session, data: session.post(f'http://localhost:{http_port}/upload', data=data),
                download_func=lambda session, size: session.get(f'http://localhost:{http_port}/download/{size}').content,
                data_sizes=[1024, 10240],
                iterations=5,
            )

            metrics = bench.execute()
            stats = metrics.compute_statistics()

            assert 'upload_bandwidth' in stats
            assert 'download_bandwidth' in stats


class TestBenchmarkContext:
    """Test context manager for custom benchmarking"""

    def test_benchmark_context_basic(self, rpyc_port):
        """Test basic context manager usage"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            with BenchmarkContext(
                name="Test",
                protocol="rpyc",
                measure_latency=True,
                measure_connection=True,
            ) as bench:
                conn = create_rpyc_connection('localhost', rpyc_port)

                with bench.measure_connection_time():
                    pass  # Connection already established

                for _ in range(10):
                    with bench.measure_request():
                        conn.root.ping()
                        bench.record_request(success=True)

                conn.close()

            metrics = bench.get_results()
            stats = metrics.compute_statistics()

            assert 'latency' in stats
            assert stats['latency']['count'] == 10
            assert stats['concurrent']['total_requests'] == 10

    def test_benchmark_context_bandwidth(self, rpyc_port, test_data_small):
        """Test bandwidth measurement with context manager"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            with BenchmarkContext(
                name="Test",
                protocol="rpyc",
                measure_bandwidth=True,
            ) as bench:
                conn = create_rpyc_connection('localhost', rpyc_port)

                for _ in range(5):
                    with bench.measure_request(bytes_sent=len(test_data_small)):
                        conn.root.upload(test_data_small)
                        bench.record_request(success=True)

                conn.close()

            metrics = bench.get_results()
            stats = metrics.compute_statistics()

            assert 'upload_bandwidth' in stats
            assert stats['upload_bandwidth']['mean'] > 0
