"""Tests for metrics collection and statistics"""

import pytest
from rpycbench.core.metrics import BenchmarkMetrics, BenchmarkResults
import time


class TestBenchmarkMetrics:
    """Test metrics collection"""

    def test_metrics_creation(self):
        """Test creating metrics object"""
        metrics = BenchmarkMetrics(
            name="Test",
            protocol="rpyc",
            server_mode="threaded",
        )

        assert metrics.name == "Test"
        assert metrics.protocol == "rpyc"
        assert metrics.server_mode == "threaded"

    def test_metrics_add_connection_time(self):
        """Test adding connection times"""
        metrics = BenchmarkMetrics(name="Test", protocol="rpyc")

        for i in range(10):
            metrics.add_connection_time(0.001 * (i + 1))

        stats = metrics.compute_statistics()
        assert 'connection_time' in stats
        assert stats['connection_time']['count'] == 10
        assert stats['connection_time']['mean'] > 0

    def test_metrics_add_latency(self):
        """Test adding latencies"""
        metrics = BenchmarkMetrics(name="Test", protocol="rpyc")

        for i in range(100):
            metrics.add_latency(0.002 * (i + 1))

        stats = metrics.compute_statistics()
        assert 'latency' in stats
        assert stats['latency']['count'] == 100
        assert stats['latency']['mean'] > 0
        assert stats['latency']['median'] > 0
        assert stats['latency']['p95'] > 0
        assert stats['latency']['p99'] > 0

    def test_metrics_add_bandwidth(self):
        """Test adding bandwidth measurements"""
        metrics = BenchmarkMetrics(name="Test", protocol="rpyc")

        # Add upload bandwidth
        for _ in range(10):
            metrics.add_upload_bandwidth(10240, 0.01)  # 10KB in 10ms

        # Add download bandwidth
        for _ in range(10):
            metrics.add_download_bandwidth(10240, 0.01)

        stats = metrics.compute_statistics()
        assert 'upload_bandwidth' in stats
        assert 'download_bandwidth' in stats
        assert stats['upload_bandwidth']['mean'] > 0
        assert stats['download_bandwidth']['mean'] > 0

    def test_metrics_concurrent_tracking(self):
        """Test concurrent connection metrics"""
        metrics = BenchmarkMetrics(name="Test", protocol="rpyc")
        metrics.concurrent_connections = 128
        metrics.total_requests = 1280
        metrics.failed_requests = 10

        stats = metrics.compute_statistics()
        assert 'concurrent' in stats
        assert stats['concurrent']['connections'] == 128
        assert stats['concurrent']['total_requests'] == 1280
        assert stats['concurrent']['failed_requests'] == 10
        assert 0 < stats['concurrent']['success_rate'] < 1

    def test_metrics_duration_tracking(self):
        """Test duration tracking"""
        metrics = BenchmarkMetrics(name="Test", protocol="rpyc")

        metrics.start()
        time.sleep(0.1)
        metrics.end()

        duration = metrics.get_duration()
        assert duration is not None
        assert duration >= 0.1


class TestBenchmarkResults:
    """Test results aggregation"""

    def test_results_add_multiple_metrics(self):
        """Test adding multiple benchmark results"""
        results = BenchmarkResults()

        # Add RPyC metrics
        rpyc_metrics = BenchmarkMetrics(
            name="RPyC Test",
            protocol="rpyc",
            server_mode="threaded"
        )
        rpyc_metrics.add_latency(0.001)
        rpyc_metrics.add_latency(0.002)
        results.add_result(rpyc_metrics)

        # Add HTTP metrics
        http_metrics = BenchmarkMetrics(
            name="HTTP Test",
            protocol="http",
            server_mode="threaded"
        )
        http_metrics.add_latency(0.003)
        http_metrics.add_latency(0.004)
        results.add_result(http_metrics)

        # Get comparison
        comparison = results.get_comparison_table()

        assert 'rpyc_threaded' in comparison
        assert 'http_threaded' in comparison

    def test_results_to_json(self):
        """Test exporting results to JSON"""
        results = BenchmarkResults()

        metrics = BenchmarkMetrics(name="Test", protocol="rpyc")
        metrics.add_latency(0.001)
        results.add_result(metrics)

        json_str = results.to_json()
        assert isinstance(json_str, str)
        assert 'rpyc' in json_str

    def test_results_to_dict(self):
        """Test exporting results to dictionary"""
        results = BenchmarkResults()

        metrics = BenchmarkMetrics(name="Test", protocol="rpyc", server_mode="threaded")
        metrics.add_latency(0.001)
        results.add_result(metrics)

        data = results.to_dict()
        assert isinstance(data, dict)
        assert 'rpyc_threaded' in data


class TestStatisticsComputation:
    """Test statistical calculations"""

    def test_percentile_calculation(self):
        """Test percentile computation"""
        metrics = BenchmarkMetrics(name="Test", protocol="rpyc")

        # Add 100 measurements
        for i in range(100):
            metrics.add_latency(i * 0.001)  # 0ms to 99ms

        stats = metrics.compute_statistics()

        # P95 should be around 95th value
        assert 0.090 < stats['latency']['p95'] < 0.098

        # P99 should be around 99th value
        assert 0.095 < stats['latency']['p99'] <= 0.099

    def test_standard_deviation(self):
        """Test standard deviation calculation"""
        metrics = BenchmarkMetrics(name="Test", protocol="rpyc")

        # Add measurements with known distribution
        for _ in range(50):
            metrics.add_latency(0.001)  # 1ms
        for _ in range(50):
            metrics.add_latency(0.003)  # 3ms

        stats = metrics.compute_statistics()

        # Mean should be 2ms
        assert 0.0019 < stats['latency']['mean'] < 0.0021

        # Should have some standard deviation
        assert stats['latency']['stdev'] > 0

    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        metrics = BenchmarkMetrics(name="Test", protocol="rpyc")

        metrics.total_requests = 100
        metrics.failed_requests = 5

        stats = metrics.compute_statistics()

        assert stats['concurrent']['success_rate'] == 0.95

    def test_empty_metrics(self):
        """Test handling of empty metrics"""
        metrics = BenchmarkMetrics(name="Test", protocol="rpyc")

        stats = metrics.compute_statistics()

        # Should not crash, should have basic info
        assert stats['name'] == "Test"
        assert stats['protocol'] == "rpyc"
