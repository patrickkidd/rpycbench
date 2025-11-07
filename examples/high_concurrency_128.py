#!/usr/bin/env python3
"""
Example: High concurrency benchmark with 128 parallel connections

Demonstrates:
- 128 parallel client connections from single process
- Server in separate process (no GIL interference)
- Per-connection metrics tracking
- Testing different server modes (threaded vs forking)
"""

from rpycbench.benchmarks.suite import BenchmarkSuite
from rpycbench.core.benchmark import ConcurrentBenchmark
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection
from rpycbench.servers.http_servers import HTTPBenchmarkServer, create_http_session


def test_high_concurrency_rpyc():
    """Test RPyC with 128 concurrent connections"""

    print("=" * 80)
    print("RPYC HIGH CONCURRENCY TEST: 128 Parallel Connections")
    print("=" * 80)

    modes = ['threaded', 'forking']

    for mode in modes:
        print(f"\n[Testing RPyC {mode.upper()} server]")
        print("-" * 80)

        # Start server in separate process (GIL-free)
        with RPyCServer(host='localhost', port=18812, mode=mode):

            # Create benchmark with 128 clients
            bench = ConcurrentBenchmark(
                name=f"RPyC {mode} - 128 clients",
                protocol="rpyc",
                server_mode=mode,
                connection_factory=lambda: create_rpyc_connection('localhost', 18812),
                request_func=lambda conn: conn.root.ping(),
                num_clients=128,
                requests_per_client=50,
                track_per_connection=True,  # Track individual connections
            )

            metrics = bench.execute()
            stats = metrics.compute_statistics()

            # Print results
            print(f"\nResults for {mode} mode:")
            print(f"  Total requests: {stats['concurrent']['total_requests']}")
            print(f"  Failed requests: {stats['concurrent']['failed_requests']}")
            print(f"  Success rate: {stats['concurrent']['success_rate']*100:.2f}%")
            print(f"  Mean latency: {stats['latency']['mean']*1000:.2f}ms")
            print(f"  Median latency: {stats['latency']['median']*1000:.2f}ms")
            print(f"  P95 latency: {stats['latency']['p95']*1000:.2f}ms")
            print(f"  P99 latency: {stats['latency']['p99']*1000:.2f}ms")

            # Per-connection analysis
            per_conn = bench.get_per_connection_metrics()
            if per_conn:
                avg_conn_time = sum(c['connection_time'] for c in per_conn) / len(per_conn)
                print(f"  Avg connection time: {avg_conn_time*1000:.2f}ms")

                # Find slowest connection
                slowest = max(per_conn, key=lambda c: c.get('total_duration', 0))
                print(f"  Slowest client #{slowest['client_id']}: {slowest['total_duration']:.2f}s")


def test_high_concurrency_http():
    """Test HTTP with 128 concurrent connections"""

    print("\n\n" + "=" * 80)
    print("HTTP HIGH CONCURRENCY TEST: 128 Parallel Connections")
    print("=" * 80)

    # Start HTTP server in separate process
    with HTTPBenchmarkServer(host='localhost', port=5000, threaded=True):

        # Create benchmark with 128 clients
        bench = ConcurrentBenchmark(
            name="HTTP threaded - 128 clients",
            protocol="http",
            server_mode="threaded",
            connection_factory=lambda: create_http_session(),
            request_func=lambda session: session.get('http://localhost:5000/ping'),
            num_clients=128,
            requests_per_client=50,
            track_per_connection=True,
        )

        metrics = bench.execute()
        stats = metrics.compute_statistics()

        # Print results
        print(f"\nResults:")
        print(f"  Total requests: {stats['concurrent']['total_requests']}")
        print(f"  Failed requests: {stats['concurrent']['failed_requests']}")
        print(f"  Success rate: {stats['concurrent']['success_rate']*100:.2f}%")
        print(f"  Mean latency: {stats['latency']['mean']*1000:.2f}ms")
        print(f"  Median latency: {stats['latency']['median']*1000:.2f}ms")
        print(f"  P95 latency: {stats['latency']['p95']*1000:.2f}ms")
        print(f"  P99 latency: {stats['latency']['p99']*1000:.2f}ms")


def compare_server_modes():
    """Compare different server modes under high load"""

    print("\n\n" + "=" * 80)
    print("SERVER MODE COMPARISON UNDER HIGH LOAD")
    print("=" * 80)

    results = {}

    for mode in ['threaded', 'forking']:
        print(f"\n[Benchmarking RPyC {mode.upper()}]")

        with RPyCServer(host='localhost', port=18812, mode=mode):
            bench = ConcurrentBenchmark(
                name=f"RPyC {mode}",
                protocol="rpyc",
                server_mode=mode,
                connection_factory=lambda: create_rpyc_connection('localhost', 18812),
                request_func=lambda conn: conn.root.ping(),
                num_clients=128,
                requests_per_client=100,
            )

            metrics = bench.execute()
            results[mode] = metrics.compute_statistics()

    # Compare results
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)

    for mode, stats in results.items():
        print(f"\n{mode.upper()}:")
        print(f"  Mean latency: {stats['latency']['mean']*1000:.2f}ms")
        print(f"  P95 latency: {stats['latency']['p95']*1000:.2f}ms")
        print(f"  Success rate: {stats['concurrent']['success_rate']*100:.2f}%")

    # Calculate speedup
    if 'threaded' in results and 'forking' in results:
        threaded_lat = results['threaded']['latency']['mean']
        forking_lat = results['forking']['latency']['mean']

        if threaded_lat < forking_lat:
            speedup = forking_lat / threaded_lat
            print(f"\nThreaded is {speedup:.2f}x faster than forking")
        else:
            speedup = threaded_lat / forking_lat
            print(f"\nForking is {speedup:.2f}x faster than threaded")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == '--rpyc':
            test_high_concurrency_rpyc()
        elif sys.argv[1] == '--http':
            test_high_concurrency_http()
        elif sys.argv[1] == '--compare':
            compare_server_modes()
    else:
        # Run all tests
        test_high_concurrency_rpyc()
        test_high_concurrency_http()
        compare_server_modes()
