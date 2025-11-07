#!/usr/bin/env python3
"""
Example: Integrating benchmarks into your application

This shows how to benchmark both baseline performance (without app overhead)
and actual performance (with your app logic).
"""

from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.core.metrics import BenchmarkResults
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection
import time


# Your application code
class MyApplication:
    """Example application that uses RPyC"""

    def __init__(self, conn):
        self.conn = conn

    def process_data(self, data):
        """Simulate some app processing overhead"""
        # Your app logic here (validation, transformation, etc.)
        time.sleep(0.001)  # Simulate 1ms processing

        # Call RPyC service
        result = self.conn.root.echo(data)

        # More app logic
        time.sleep(0.001)  # Simulate 1ms processing

        return result


def benchmark_baseline(conn, num_requests=100):
    """Benchmark baseline performance without app overhead"""

    with BenchmarkContext(
        name="Baseline (no app overhead)",
        protocol="rpyc",
        server_mode="threaded",
        measure_latency=True,
    ) as bench:

        for _ in range(num_requests):
            with bench.measure_request():
                # Direct call without app logic
                conn.root.ping()
                bench.record_request(success=True)

    return bench.get_results()


def benchmark_with_app(conn, num_requests=100):
    """Benchmark performance with app overhead"""

    app = MyApplication(conn)

    with BenchmarkContext(
        name="With app overhead",
        protocol="rpyc",
        server_mode="threaded",
        measure_latency=True,
    ) as bench:

        test_data = b'test'

        for _ in range(num_requests):
            with bench.measure_request():
                # Call through app (includes app overhead)
                app.process_data(test_data)
                bench.record_request(success=True)

    return bench.get_results()


def main():
    """Run both baseline and app-integrated benchmarks"""

    print("Running Baseline vs Application Overhead Benchmark")
    print("=" * 60)

    # Start server
    with RPyCServer(host='localhost', port=18812, mode='threaded'):
        conn = create_rpyc_connection('localhost', 18812)

        # Run both benchmarks
        baseline_metrics = benchmark_baseline(conn, num_requests=500)
        app_metrics = benchmark_with_app(conn, num_requests=500)

        conn.close()

    # Compare results
    results = BenchmarkResults()
    results.add_result(baseline_metrics)
    results.add_result(app_metrics)

    results.print_summary()

    # Calculate overhead
    baseline_stats = baseline_metrics.compute_statistics()
    app_stats = app_metrics.compute_statistics()

    baseline_latency = baseline_stats['latency']['mean']
    app_latency = app_stats['latency']['mean']
    overhead = app_latency - baseline_latency

    print("\nOverhead Analysis:")
    print("-" * 60)
    print(f"Baseline latency:  {baseline_latency*1000:.2f}ms")
    print(f"App latency:       {app_latency*1000:.2f}ms")
    print(f"App overhead:      {overhead*1000:.2f}ms ({(overhead/baseline_latency)*100:.1f}%)")


if __name__ == '__main__':
    main()
