"""Core benchmark framework with context managers"""

import time
import threading
import multiprocessing
from abc import ABC, abstractmethod
from typing import Callable, Optional, Any, Dict
from contextlib import contextmanager
import concurrent.futures

from rpycbench.core.metrics import BenchmarkMetrics, BenchmarkResults


class BenchmarkBase(ABC):
    """Base class for all benchmarks"""

    def __init__(self, name: str, protocol: str, server_mode: Optional[str] = None):
        self.name = name
        self.protocol = protocol
        self.server_mode = server_mode
        self.metrics = BenchmarkMetrics(
            name=name,
            protocol=protocol,
            server_mode=server_mode
        )

    @abstractmethod
    def setup(self):
        """Setup benchmark resources"""
        pass

    @abstractmethod
    def run(self):
        """Run the benchmark"""
        pass

    @abstractmethod
    def teardown(self):
        """Cleanup benchmark resources"""
        pass

    def execute(self) -> BenchmarkMetrics:
        """Execute full benchmark lifecycle"""
        try:
            self.setup()
            self.metrics.start()
            self.run()
            self.metrics.end()
        finally:
            self.teardown()
        return self.metrics


class BenchmarkContext:
    """Context manager for benchmarking that can be integrated into user apps"""

    def __init__(
        self,
        name: str,
        protocol: str,
        server_mode: Optional[str] = None,
        measure_connection: bool = False,
        measure_latency: bool = True,
        measure_bandwidth: bool = False,
        measure_system: bool = True,
    ):
        self.name = name
        self.protocol = protocol
        self.server_mode = server_mode
        self.metrics = BenchmarkMetrics(
            name=name,
            protocol=protocol,
            server_mode=server_mode
        )

        self.measure_connection = measure_connection
        self.measure_latency = measure_latency
        self.measure_bandwidth = measure_bandwidth
        self.measure_system = measure_system

        self._start_time = None
        self._connection_start = None
        self._request_start = None
        self._bytes_sent = 0
        self._bytes_received = 0

    def __enter__(self):
        """Enter benchmark context"""
        self.metrics.start()
        if self.measure_system:
            self.metrics.record_system_metrics()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit benchmark context"""
        self.metrics.end()
        if self.measure_system:
            self.metrics.record_system_metrics()
        return False

    @contextmanager
    def measure_connection_time(self):
        """Context manager to measure connection establishment time"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            if self.measure_connection:
                self.metrics.add_connection_time(duration)

    @contextmanager
    def measure_request(self, bytes_sent: int = 0, bytes_received: int = 0):
        """Context manager to measure request latency and bandwidth"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start

            if self.measure_latency:
                self.metrics.add_latency(duration)

            if self.measure_bandwidth:
                if bytes_sent > 0:
                    self.metrics.add_upload_bandwidth(bytes_sent, duration)
                if bytes_received > 0:
                    self.metrics.add_download_bandwidth(bytes_received, duration)

    def record_request(self, success: bool = True):
        """Record a request completion"""
        self.metrics.total_requests += 1
        if not success:
            self.metrics.failed_requests += 1

    def get_results(self) -> BenchmarkMetrics:
        """Get benchmark results"""
        return self.metrics


class ConnectionBenchmark(BenchmarkBase):
    """Benchmark for measuring connection establishment time"""

    def __init__(
        self,
        name: str,
        protocol: str,
        server_mode: Optional[str],
        connection_factory: Callable[[], Any],
        num_connections: int = 100,
    ):
        super().__init__(name, protocol, server_mode)
        self.connection_factory = connection_factory
        self.num_connections = num_connections
        self.connections = []

    def setup(self):
        """Setup benchmark"""
        pass

    def run(self):
        """Run connection benchmark"""
        for _ in range(self.num_connections):
            start = time.time()
            try:
                conn = self.connection_factory()
                duration = time.time() - start
                self.metrics.add_connection_time(duration)
                self.connections.append(conn)
            except Exception as e:
                self.metrics.metadata['errors'] = self.metrics.metadata.get('errors', [])
                self.metrics.metadata['errors'].append(str(e))

    def teardown(self):
        """Cleanup connections"""
        for conn in self.connections:
            try:
                if hasattr(conn, 'close'):
                    conn.close()
            except:
                pass


class LatencyBenchmark(BenchmarkBase):
    """Benchmark for measuring request/response latency"""

    def __init__(
        self,
        name: str,
        protocol: str,
        server_mode: Optional[str],
        connection_factory: Callable[[], Any],
        request_func: Callable[[Any], Any],
        num_requests: int = 1000,
        warmup_requests: int = 10,
    ):
        super().__init__(name, protocol, server_mode)
        self.connection_factory = connection_factory
        self.request_func = request_func
        self.num_requests = num_requests
        self.warmup_requests = warmup_requests
        self.connection = None

    def setup(self):
        """Setup connection and warmup"""
        self.connection = self.connection_factory()

        # Warmup
        for _ in range(self.warmup_requests):
            try:
                self.request_func(self.connection)
            except:
                pass

    def run(self):
        """Run latency benchmark"""
        for _ in range(self.num_requests):
            start = time.time()
            try:
                self.request_func(self.connection)
                duration = time.time() - start
                self.metrics.add_latency(duration)
                self.metrics.total_requests += 1
            except Exception as e:
                self.metrics.failed_requests += 1
                self.metrics.metadata['errors'] = self.metrics.metadata.get('errors', [])
                self.metrics.metadata['errors'].append(str(e))

    def teardown(self):
        """Cleanup connection"""
        if self.connection and hasattr(self.connection, 'close'):
            try:
                self.connection.close()
            except:
                pass


class BandwidthBenchmark(BenchmarkBase):
    """Benchmark for measuring data transfer bandwidth"""

    def __init__(
        self,
        name: str,
        protocol: str,
        server_mode: Optional[str],
        connection_factory: Callable[[], Any],
        upload_func: Callable[[Any, bytes], Any],
        download_func: Callable[[Any, int], bytes],
        data_sizes: list = None,
        iterations: int = 10,
    ):
        super().__init__(name, protocol, server_mode)
        self.connection_factory = connection_factory
        self.upload_func = upload_func
        self.download_func = download_func
        self.data_sizes = data_sizes or [1024, 10240, 102400, 1048576]  # 1KB to 1MB
        self.iterations = iterations
        self.connection = None

    def setup(self):
        """Setup connection"""
        self.connection = self.connection_factory()

    def run(self):
        """Run bandwidth benchmark"""
        for size in self.data_sizes:
            data = b'x' * size

            # Test upload bandwidth
            for _ in range(self.iterations):
                start = time.time()
                try:
                    self.upload_func(self.connection, data)
                    duration = time.time() - start
                    self.metrics.add_upload_bandwidth(size, duration)
                except Exception as e:
                    self.metrics.metadata['errors'] = self.metrics.metadata.get('errors', [])
                    self.metrics.metadata['errors'].append(f"Upload error: {str(e)}")

            # Test download bandwidth
            for _ in range(self.iterations):
                start = time.time()
                try:
                    received = self.download_func(self.connection, size)
                    duration = time.time() - start
                    self.metrics.add_download_bandwidth(len(received) if received else size, duration)
                except Exception as e:
                    self.metrics.metadata['errors'] = self.metrics.metadata.get('errors', [])
                    self.metrics.metadata['errors'].append(f"Download error: {str(e)}")

    def teardown(self):
        """Cleanup connection"""
        if self.connection and hasattr(self.connection, 'close'):
            try:
                self.connection.close()
            except:
                pass


class ConcurrentBenchmark(BenchmarkBase):
    """
    Benchmark for measuring concurrent client performance.

    Supports high concurrency (e.g., 128+ connections) with per-connection
    metrics tracking. Each client connection runs in its own thread within
    the client process.
    """

    def __init__(
        self,
        name: str,
        protocol: str,
        server_mode: Optional[str],
        connection_factory: Callable[[], Any],
        request_func: Callable[[Any], Any],
        num_clients: int = 128,  # Default to 128 for high concurrency
        requests_per_client: int = 100,
        max_workers: Optional[int] = None,
        track_per_connection: bool = False,  # Track individual connection metrics
    ):
        super().__init__(name, protocol, server_mode)
        self.connection_factory = connection_factory
        self.request_func = request_func
        self.num_clients = num_clients
        self.requests_per_client = requests_per_client
        self.max_workers = max_workers or min(num_clients, 128)  # Cap thread pool
        self.track_per_connection = track_per_connection
        self.metrics.concurrent_connections = num_clients

        # Per-connection tracking
        self.per_connection_metrics = [] if track_per_connection else None

    def setup(self):
        """Setup benchmark"""
        pass

    def _client_worker(self, client_id: int) -> Dict[str, Any]:
        """
        Worker function for each concurrent client.

        Each worker establishes its own connection and tracks its metrics.
        Runs in a separate thread within the client process.
        """
        client_metrics = {
            'client_id': client_id,
            'latencies': [],
            'total_requests': 0,
            'failed_requests': 0,
            'start_time': time.time(),
        }

        try:
            # Establish connection
            conn_start = time.time()
            connection = self.connection_factory()
            conn_duration = time.time() - conn_start
            client_metrics['connection_time'] = conn_duration

            # Make requests
            for req_num in range(self.requests_per_client):
                start = time.time()
                try:
                    self.request_func(connection)
                    duration = time.time() - start
                    client_metrics['latencies'].append(duration)
                    client_metrics['total_requests'] += 1
                except Exception as e:
                    client_metrics['failed_requests'] += 1
                    if self.track_per_connection:
                        if 'errors' not in client_metrics:
                            client_metrics['errors'] = []
                        client_metrics['errors'].append(f"Request {req_num}: {str(e)}")

            # Cleanup
            if hasattr(connection, 'close'):
                connection.close()

        except Exception as e:
            client_metrics['connection_error'] = str(e)

        client_metrics['end_time'] = time.time()
        client_metrics['total_duration'] = client_metrics['end_time'] - client_metrics['start_time']

        return client_metrics

    def run(self):
        """
        Run concurrent benchmark with all clients in parallel.

        Creates num_clients threads, each establishing its own connection
        and making requests independently. Tracks aggregate and per-connection
        metrics.
        """
        print(f"  Starting {self.num_clients} concurrent clients...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self._client_worker, i)
                for i in range(self.num_clients)
            ]

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()

                    # Store per-connection metrics if tracking
                    if self.track_per_connection:
                        self.per_connection_metrics.append(result)

                    # Aggregate metrics
                    if 'connection_time' in result:
                        self.metrics.add_connection_time(result['connection_time'])

                    for latency in result.get('latencies', []):
                        self.metrics.add_latency(latency)

                    self.metrics.total_requests += result['total_requests']
                    self.metrics.failed_requests += result['failed_requests']

                    completed += 1
                    if completed % 10 == 0:
                        print(f"    {completed}/{self.num_clients} clients completed...")

                except Exception as e:
                    self.metrics.failed_requests += self.requests_per_client
                    self.metrics.metadata['errors'] = self.metrics.metadata.get('errors', [])
                    self.metrics.metadata['errors'].append(str(e))
                    completed += 1

        print(f"  All {self.num_clients} clients completed")

        # Store per-connection summary if tracking
        if self.track_per_connection:
            self.metrics.metadata['per_connection_count'] = len(self.per_connection_metrics)
            self.metrics.metadata['per_connection_available'] = True

    def teardown(self):
        """Cleanup benchmark"""
        pass

    def get_per_connection_metrics(self) -> List[Dict[str, Any]]:
        """Get per-connection metrics if tracking is enabled"""
        if not self.track_per_connection:
            return []
        return self.per_connection_metrics
