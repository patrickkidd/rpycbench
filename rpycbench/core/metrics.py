"""Metrics collection and reporting for benchmarks"""

import time
import psutil
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from statistics import mean, median, stdev
import json


@dataclass
class BenchmarkMetrics:
    """Container for benchmark metrics"""

    name: str
    protocol: str  # 'rpyc' or 'http'
    server_mode: Optional[str] = None  # 'threaded', 'forking', etc.

    # Connection metrics
    connection_times: List[float] = field(default_factory=list)

    # Latency metrics (round-trip time)
    latencies: List[float] = field(default_factory=list)

    # Bandwidth metrics (bytes/second)
    upload_bandwidth: List[float] = field(default_factory=list)
    download_bandwidth: List[float] = field(default_factory=list)

    # Concurrent connection metrics
    concurrent_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0

    # System resource metrics
    cpu_usage: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)

    # Timing
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_connection_time(self, duration: float):
        """Record connection establishment time"""
        self.connection_times.append(duration)

    def add_latency(self, duration: float):
        """Record request/response latency"""
        self.latencies.append(duration)

    def add_upload_bandwidth(self, bytes_sent: int, duration: float):
        """Record upload bandwidth"""
        if duration > 0:
            self.upload_bandwidth.append(bytes_sent / duration)

    def add_download_bandwidth(self, bytes_received: int, duration: float):
        """Record download bandwidth"""
        if duration > 0:
            self.download_bandwidth.append(bytes_received / duration)

    def record_system_metrics(self):
        """Record current system resource usage"""
        self.cpu_usage.append(psutil.cpu_percent(interval=0.1))
        self.memory_usage.append(psutil.virtual_memory().percent)

    def start(self):
        """Mark benchmark start"""
        self.start_time = time.time()

    def end(self):
        """Mark benchmark end"""
        self.end_time = time.time()

    def get_duration(self) -> Optional[float]:
        """Get total benchmark duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def compute_statistics(self) -> Dict[str, Any]:
        """Compute statistical summaries of collected metrics"""
        stats = {
            'name': self.name,
            'protocol': self.protocol,
            'server_mode': self.server_mode,
            'duration': self.get_duration(),
        }

        # Connection time statistics
        if self.connection_times:
            stats['connection_time'] = {
                'mean': mean(self.connection_times),
                'median': median(self.connection_times),
                'min': min(self.connection_times),
                'max': max(self.connection_times),
                'stdev': stdev(self.connection_times) if len(self.connection_times) > 1 else 0,
                'count': len(self.connection_times),
            }

        # Latency statistics
        if self.latencies:
            stats['latency'] = {
                'mean': mean(self.latencies),
                'median': median(self.latencies),
                'min': min(self.latencies),
                'max': max(self.latencies),
                'stdev': stdev(self.latencies) if len(self.latencies) > 1 else 0,
                'p95': self._percentile(self.latencies, 95),
                'p99': self._percentile(self.latencies, 99),
                'count': len(self.latencies),
            }

        # Upload bandwidth statistics
        if self.upload_bandwidth:
            stats['upload_bandwidth'] = {
                'mean': mean(self.upload_bandwidth),
                'median': median(self.upload_bandwidth),
                'min': min(self.upload_bandwidth),
                'max': max(self.upload_bandwidth),
                'stdev': stdev(self.upload_bandwidth) if len(self.upload_bandwidth) > 1 else 0,
            }

        # Download bandwidth statistics
        if self.download_bandwidth:
            stats['download_bandwidth'] = {
                'mean': mean(self.download_bandwidth),
                'median': median(self.download_bandwidth),
                'min': min(self.download_bandwidth),
                'max': max(self.download_bandwidth),
                'stdev': stdev(self.download_bandwidth) if len(self.download_bandwidth) > 1 else 0,
            }

        # Concurrent connection statistics
        stats['concurrent'] = {
            'connections': self.concurrent_connections,
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (self.total_requests - self.failed_requests) / self.total_requests
                           if self.total_requests > 0 else 0,
        }

        # System resource statistics
        if self.cpu_usage:
            stats['cpu_usage'] = {
                'mean': mean(self.cpu_usage),
                'max': max(self.cpu_usage),
            }

        if self.memory_usage:
            stats['memory_usage'] = {
                'mean': mean(self.memory_usage),
                'max': max(self.memory_usage),
            }

        # Add metadata
        stats['metadata'] = self.metadata

        return stats

    @staticmethod
    def _percentile(data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


@dataclass
class BenchmarkResults:
    """Collection of benchmark results for comparison"""

    results: List[BenchmarkMetrics] = field(default_factory=list)

    def add_result(self, metrics: BenchmarkMetrics):
        """Add benchmark result"""
        self.results.append(metrics)

    def get_comparison_table(self) -> Dict[str, Any]:
        """Generate comparison table of all results"""
        comparison = {}

        for metrics in self.results:
            key = f"{metrics.protocol}"
            if metrics.server_mode:
                key += f"_{metrics.server_mode}"

            comparison[key] = metrics.compute_statistics()

        return comparison

    def to_json(self) -> str:
        """Export results as JSON"""
        return json.dumps(self.get_comparison_table(), indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Export results as dictionary"""
        return self.get_comparison_table()

    def print_summary(self):
        """Print a human-readable summary"""
        comparison = self.get_comparison_table()

        print("\n" + "="*80)
        print("BENCHMARK RESULTS SUMMARY")
        print("="*80 + "\n")

        for protocol, stats in comparison.items():
            print(f"\n{protocol.upper()}")
            print("-" * 40)

            if 'duration' in stats and stats['duration'] is not None:
                print(f"  Total Duration: {stats['duration']:.2f}s")

            if 'connection_time' in stats:
                ct = stats['connection_time']
                print(f"  Connection Time: {ct['mean']*1000:.2f}ms (±{ct['stdev']*1000:.2f}ms)")

            if 'latency' in stats:
                lat = stats['latency']
                print(f"  Latency Mean: {lat['mean']*1000:.2f}ms (±{lat['stdev']*1000:.2f}ms)")
                print(f"  Latency Median: {lat['median']*1000:.2f}ms")
                print(f"  Latency P95: {lat['p95']*1000:.2f}ms")
                print(f"  Latency P99: {lat['p99']*1000:.2f}ms")

            if 'upload_bandwidth' in stats:
                ub = stats['upload_bandwidth']
                print(f"  Upload Bandwidth: {ub['mean']/1024/1024:.2f} MB/s")

            if 'download_bandwidth' in stats:
                db = stats['download_bandwidth']
                print(f"  Download Bandwidth: {db['mean']/1024/1024:.2f} MB/s")

            if 'concurrent' in stats:
                conc = stats['concurrent']
                print(f"  Concurrent Connections: {conc['connections']}")
                print(f"  Total Requests: {conc['total_requests']}")
                print(f"  Success Rate: {conc['success_rate']*100:.2f}%")

            if 'cpu_usage' in stats:
                cpu = stats['cpu_usage']
                print(f"  CPU Usage: {cpu['mean']:.1f}% (max: {cpu['max']:.1f}%)")

            if 'memory_usage' in stats:
                mem = stats['memory_usage']
                print(f"  Memory Usage: {mem['mean']:.1f}% (max: {mem['max']:.1f}%)")

        print("\n" + "="*80 + "\n")
