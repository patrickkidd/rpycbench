#!/usr/bin/env python3
"""Example: Using benchmark context managers in your app"""

from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection
from rpycbench.servers.http_servers import HTTPBenchmarkServer, create_http_session


def example_rpyc_benchmarking():
    """Example of benchmarking RPyC in your application"""

    print("RPyC Benchmarking Example")
    print("-" * 40)

    # Start RPyC server
    with RPyCServer(host='localhost', port=18812, mode='threaded'):

        # Create benchmark context
        with BenchmarkContext(
            name="My App RPyC",
            protocol="rpyc",
            server_mode="threaded",
            measure_connection=True,
            measure_latency=True,
            measure_bandwidth=True,
            measure_system=True,
        ) as bench:

            # Connect to server
            with bench.measure_connection_time():
                conn = create_rpyc_connection('localhost', 18812)

            # Make some requests and measure latency
            for i in range(100):
                with bench.measure_request():
                    result = conn.root.ping()
                    bench.record_request(success=True)

            # Test bandwidth
            test_data = b'x' * 10240  # 10KB
            with bench.measure_request(bytes_sent=len(test_data)):
                conn.root.upload(test_data)
                bench.record_request(success=True)

            conn.close()

        # Get results
        metrics = bench.get_results()
        stats = metrics.compute_statistics()

        print("\nResults:")
        if 'connection_time' in stats:
            print(f"  Connection Time: {stats['connection_time']['mean']*1000:.2f}ms")
        if 'latency' in stats:
            print(f"  Latency (mean): {stats['latency']['mean']*1000:.2f}ms")
            print(f"  Latency (p95): {stats['latency']['p95']*1000:.2f}ms")
        if 'upload_bandwidth' in stats:
            print(f"  Upload Bandwidth: {stats['upload_bandwidth']['mean']/1024/1024:.2f} MB/s")


def example_http_benchmarking():
    """Example of benchmarking HTTP in your application"""

    print("\n\nHTTP Benchmarking Example")
    print("-" * 40)

    # Start HTTP server
    with HTTPBenchmarkServer(host='localhost', port=5000, threaded=True):

        # Create benchmark context
        with BenchmarkContext(
            name="My App HTTP",
            protocol="http",
            measure_connection=True,
            measure_latency=True,
            measure_bandwidth=True,
            measure_system=True,
        ) as bench:

            # Create session
            with bench.measure_connection_time():
                session = create_http_session()

            # Make some requests and measure latency
            for i in range(100):
                with bench.measure_request():
                    response = session.get('http://localhost:5000/ping')
                    bench.record_request(success=response.ok)

            # Test bandwidth
            test_data = b'x' * 10240  # 10KB
            with bench.measure_request(bytes_sent=len(test_data)):
                response = session.post('http://localhost:5000/upload', data=test_data)
                bench.record_request(success=response.ok)

            session.close()

        # Get results
        metrics = bench.get_results()
        stats = metrics.compute_statistics()

        print("\nResults:")
        if 'connection_time' in stats:
            print(f"  Connection Time: {stats['connection_time']['mean']*1000:.2f}ms")
        if 'latency' in stats:
            print(f"  Latency (mean): {stats['latency']['mean']*1000:.2f}ms")
            print(f"  Latency (p95): {stats['latency']['p95']*1000:.2f}ms")
        if 'upload_bandwidth' in stats:
            print(f"  Upload Bandwidth: {stats['upload_bandwidth']['mean']/1024/1024:.2f} MB/s")


if __name__ == '__main__':
    example_rpyc_benchmarking()
    example_http_benchmarking()
