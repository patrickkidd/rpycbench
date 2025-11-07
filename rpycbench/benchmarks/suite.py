"""Comprehensive benchmark suite comparing RPyC and HTTP"""

from rpycbench.core.benchmark import (
    ConnectionBenchmark,
    LatencyBenchmark,
    BandwidthBenchmark,
    BinaryTransferBenchmark,
    ConcurrentBenchmark,
)
from rpycbench.core.metrics import BenchmarkResults
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection
from rpycbench.servers.http_servers import HTTPBenchmarkServer, create_http_session
import requests
import time


class BenchmarkSuite:
    """Complete benchmark suite for RPyC vs HTTP comparison"""

    def __init__(
        self,
        rpyc_host='localhost',
        rpyc_port=18812,
        http_host='localhost',
        http_port=5000,
    ):
        self.rpyc_host = rpyc_host
        self.rpyc_port = rpyc_port
        self.http_host = http_host
        self.http_port = http_port
        self.http_base_url = f"http://{http_host}:{http_port}"

        self.results = BenchmarkResults()

    def run_all(
        self,
        test_rpyc_threaded=True,
        test_rpyc_forking=True,
        test_http=True,
        num_serial_connections=100,
        num_requests=1000,
        num_parallel_clients=10,
        requests_per_client=100,
        test_binary_transfer=False,
        binary_file_sizes=None,
        binary_chunk_size=None,
        binary_iterations=3,
    ):
        """Run all benchmarks"""

        print("Starting Benchmark Suite...")
        print("=" * 80)

        # Test RPyC Threaded Server
        if test_rpyc_threaded:
            print("\n[1/3] Testing RPyC Threaded Server...")
            with RPyCServer(self.rpyc_host, self.rpyc_port, mode='threaded') as server:
                self._run_rpyc_benchmarks(
                    'threaded',
                    num_serial_connections,
                    num_requests,
                    num_parallel_clients,
                    requests_per_client,
                    test_binary_transfer,
                    binary_file_sizes,
                    binary_chunk_size,
                    binary_iterations,
                )

        # Test RPyC Forking Server
        if test_rpyc_forking:
            print("\n[2/3] Testing RPyC Forking Server...")
            with RPyCServer(self.rpyc_host, self.rpyc_port, mode='forking') as server:
                self._run_rpyc_benchmarks(
                    'forking',
                    num_serial_connections,
                    num_requests,
                    num_parallel_clients,
                    requests_per_client,
                    test_binary_transfer,
                    binary_file_sizes,
                    binary_chunk_size,
                    binary_iterations,
                )

        # Test HTTP Server
        if test_http:
            print("\n[3/3] Testing HTTP/REST Server...")
            with HTTPBenchmarkServer(self.http_host, self.http_port, threaded=True) as server:
                self._run_http_benchmarks(
                    num_serial_connections,
                    num_requests,
                    num_parallel_clients,
                    requests_per_client,
                    test_binary_transfer,
                    binary_file_sizes,
                    binary_chunk_size,
                    binary_iterations,
                )

        print("\n" + "=" * 80)
        print("All benchmarks complete!")

        return self.results

    def _run_rpyc_benchmarks(
        self,
        server_mode,
        num_serial_connections,
        num_requests,
        num_parallel_clients,
        requests_per_client,
        test_binary_transfer,
        binary_file_sizes,
        binary_chunk_size,
        binary_iterations,
    ):
        """Run all benchmarks for RPyC"""

        # Connection Benchmark
        print(f"  - Connection benchmark ({num_serial_connections} serial connections)...")
        conn_bench = ConnectionBenchmark(
            name=f"RPyC Connection ({server_mode})",
            protocol="rpyc",
            server_mode=server_mode,
            connection_factory=lambda: create_rpyc_connection(self.rpyc_host, self.rpyc_port),
            num_connections=num_serial_connections,
        )
        metrics = conn_bench.execute()
        self.results.add_result(metrics)

        # Latency Benchmark
        print(f"  - Latency benchmark ({num_requests} requests)...")
        lat_bench = LatencyBenchmark(
            name=f"RPyC Latency ({server_mode})",
            protocol="rpyc",
            server_mode=server_mode,
            connection_factory=lambda: create_rpyc_connection(self.rpyc_host, self.rpyc_port),
            request_func=lambda conn: conn.root.ping(),
            num_requests=num_requests,
        )
        metrics = lat_bench.execute()
        self.results.add_result(metrics)

        # Bandwidth Benchmark
        print(f"  - Bandwidth benchmark...")
        bw_bench = BandwidthBenchmark(
            name=f"RPyC Bandwidth ({server_mode})",
            protocol="rpyc",
            server_mode=server_mode,
            connection_factory=lambda: create_rpyc_connection(self.rpyc_host, self.rpyc_port),
            upload_func=lambda conn, data: conn.root.upload(data),
            download_func=lambda conn, size: conn.root.download(size),
            data_sizes=[1024, 10240, 102400, 1048576],
            iterations=10,
        )
        metrics = bw_bench.execute()
        self.results.add_result(metrics)

        # Binary Transfer Benchmark
        if test_binary_transfer:
            print(f"  - Binary transfer benchmark...")
            bin_bench = BinaryTransferBenchmark(
                name=f"RPyC Binary Transfer ({server_mode})",
                protocol="rpyc",
                server_mode=server_mode,
                connection_factory=lambda: create_rpyc_connection(self.rpyc_host, self.rpyc_port),
                upload_func=lambda conn, data: conn.root.upload_file(data),
                download_func=lambda conn, size: conn.root.download_file(size),
                upload_chunked_func=lambda conn, chunks: conn.root.upload_file_chunked(chunks),
                download_chunked_func=lambda conn, size, chunk_size: conn.root.download_file_chunked(size, chunk_size),
                file_sizes=binary_file_sizes,
                chunk_size=binary_chunk_size,
                iterations=binary_iterations,
            )
            metrics = bin_bench.execute()
            self.results.add_result(metrics)

        # Concurrent Benchmark
        print(f"  - Concurrent benchmark ({num_parallel_clients} parallel clients)...")
        conc_bench = ConcurrentBenchmark(
            name=f"RPyC Concurrent ({server_mode})",
            protocol="rpyc",
            server_mode=server_mode,
            connection_factory=lambda: create_rpyc_connection(self.rpyc_host, self.rpyc_port),
            request_func=lambda conn: conn.root.ping(),
            num_clients=num_parallel_clients,
            requests_per_client=requests_per_client,
            track_per_connection=False,  # Disable for suite (enable manually if needed)
        )
        metrics = conc_bench.execute()
        self.results.add_result(metrics)

    def _run_http_benchmarks(
        self,
        num_serial_connections,
        num_requests,
        num_parallel_clients,
        requests_per_client,
        test_binary_transfer,
        binary_file_sizes,
        binary_chunk_size,
        binary_iterations,
    ):
        """Run all benchmarks for HTTP"""

        # Connection Benchmark
        print(f"  - Connection benchmark ({num_serial_connections} serial connections)...")
        conn_bench = ConnectionBenchmark(
            name="HTTP Connection",
            protocol="http",
            server_mode="threaded",
            connection_factory=lambda: create_http_session(),
            num_connections=num_serial_connections,
        )
        metrics = conn_bench.execute()
        self.results.add_result(metrics)

        # Latency Benchmark
        print(f"  - Latency benchmark ({num_requests} requests)...")
        lat_bench = LatencyBenchmark(
            name="HTTP Latency",
            protocol="http",
            server_mode="threaded",
            connection_factory=lambda: create_http_session(),
            request_func=lambda session: session.get(f"{self.http_base_url}/ping"),
            num_requests=num_requests,
        )
        metrics = lat_bench.execute()
        self.results.add_result(metrics)

        # Bandwidth Benchmark
        print(f"  - Bandwidth benchmark...")
        bw_bench = BandwidthBenchmark(
            name="HTTP Bandwidth",
            protocol="http",
            server_mode="threaded",
            connection_factory=lambda: create_http_session(),
            upload_func=lambda session, data: session.post(f"{self.http_base_url}/upload", data=data),
            download_func=lambda session, size: session.get(f"{self.http_base_url}/download/{size}").content,
            data_sizes=[1024, 10240, 102400, 1048576],
            iterations=10,
        )
        metrics = bw_bench.execute()
        self.results.add_result(metrics)

        # Binary Transfer Benchmark
        if test_binary_transfer:
            print(f"  - Binary transfer benchmark...")
            bin_bench = BinaryTransferBenchmark(
                name="HTTP Binary Transfer",
                protocol="http",
                server_mode="threaded",
                connection_factory=lambda: create_http_session(),
                upload_func=lambda session, data: session.post(f"{self.http_base_url}/upload-file", data=data),
                download_func=lambda session, size: session.get(f"{self.http_base_url}/download-file/{size}").content,
                upload_chunked_func=lambda session, chunks: session.post(
                    f"{self.http_base_url}/upload-file-chunked",
                    json={'chunks': [chunk.hex() for chunk in chunks]}
                ),
                download_chunked_func=lambda session, size, chunk_size: [
                    bytes.fromhex(chunk) for chunk in
                    session.get(f"{self.http_base_url}/download-file-chunked/{size}/{chunk_size}").json()['chunks']
                ],
                file_sizes=binary_file_sizes,
                chunk_size=binary_chunk_size,
                iterations=binary_iterations,
            )
            metrics = bin_bench.execute()
            self.results.add_result(metrics)

        # Concurrent Benchmark
        print(f"  - Concurrent benchmark ({num_parallel_clients} parallel clients)...")
        conc_bench = ConcurrentBenchmark(
            name="HTTP Concurrent",
            protocol="http",
            server_mode="threaded",
            connection_factory=lambda: create_http_session(),
            request_func=lambda session: session.get(f"{self.http_base_url}/ping"),
            num_clients=num_parallel_clients,
            requests_per_client=requests_per_client,
            track_per_connection=False,  # Disable for suite (enable manually if needed)
        )
        metrics = conc_bench.execute()
        self.results.add_result(metrics)
