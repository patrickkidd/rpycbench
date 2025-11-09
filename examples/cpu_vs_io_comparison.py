"""
CPU-bound vs I/O-bound Workload Comparison

This example demonstrates the performance difference between CPU-bound and I/O-bound
workloads under concurrent load, and how server mode (threaded vs forking) affects each.

Key Concepts Demonstrated:
1. GIL Impact: CPU-bound work suffers in threaded mode due to Python's GIL
2. Forking Benefit: CPU-bound work scales well with forking (each process has own GIL)
3. I/O Behavior: I/O-bound work performs similarly in both modes (GIL released during I/O)
4. Memory Trade-off: Forking uses more memory but enables true parallelism

Run this to understand when to use threaded vs forking mode for your RPyC server.
"""

import hashlib
import time
import rpyc
from rpycbench.core.benchmark import ConcurrentBenchmark
from rpycbench.servers.rpyc_servers import RPyCServer


class CPUBoundService(rpyc.Service):
    """Server that does CPU-intensive work (hash computation)"""

    def exposed_cpu_work(self, iterations=100000):
        """
        CPU-intensive task: repeated hash computation
        This demonstrates work that keeps the CPU busy
        """
        result = b"start"
        for i in range(iterations):
            result = hashlib.sha256(result).digest()
        return result.hex()[:16]


class IOBoundService(rpyc.Service):
    """Server that does I/O-bound work (simulated database/network)"""

    def exposed_io_work(self, delay=0.01):
        """
        I/O-bound task: simulates database query or network call
        This demonstrates work where server is waiting, not computing
        """
        time.sleep(delay)  # Simulates I/O wait (database, file, network)
        return "data"


def benchmark_workload(service_class, port, mode, num_clients=128):
    """Helper to benchmark a workload with specific server mode"""
    print(f"\n{'='*60}")
    print(f"Testing {service_class.__name__} in {mode.upper()} mode")
    print(f"{'='*60}")

    with RPyCServer(port=port, mode=mode, service=service_class) as server:
        # Determine which method to call based on service type
        if service_class == CPUBoundService:
            request_func = lambda c: c.root.cpu_work()
        else:
            request_func = lambda c: c.root.io_work()

        bench = ConcurrentBenchmark(
            name=f"{service_class.__name__}_{mode}",
            protocol="rpyc",
            server_mode=mode,
            connection_factory=lambda: rpyc.connect('localhost', port),
            request_func=request_func,
            num_clients=num_clients,
            requests_per_client=10
        )

        metrics = bench.run()
        metrics.record_system_metrics()  # Capture CPU and memory usage

        stats = metrics.compute_statistics()

        # Print results
        success_rate = (1 - metrics.failed_requests / metrics.total_requests) * 100
        print(f"\nResults:")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Mean latency: {stats['latency']['mean']*1000:.2f}ms")
        print(f"  P50 latency:  {stats['latency']['median']*1000:.2f}ms")
        print(f"  P99 latency:  {stats['latency']['p99']*1000:.2f}ms")
        print(f"  CPU usage:    {stats['cpu_usage']['mean']:.1f}%")
        print(f"  Memory:       {stats['memory_usage']['mean']/1024/1024:.0f}MB")

        return stats


def main():
    print("""
    CPU vs I/O Workload Comparison
    ===============================

    This benchmark compares CPU-bound and I/O-bound workloads under concurrent load.

    Expected Results:
    -----------------
    CPU-BOUND WORKLOAD:
      - Threaded mode: SLOW (GIL prevents parallel CPU execution)
      - Forking mode:  FAST (each process has own GIL, true parallelism)

    I/O-BOUND WORKLOAD:
      - Threaded mode: GOOD (GIL released during I/O wait)
      - Forking mode:  SIMILAR (no GIL benefit since we're waiting on I/O anyway)

    Testing with {num_clients} concurrent clients...
    """.format(num_clients=128))

    # ===== CPU-BOUND WORKLOAD =====
    print("\n" + "="*70)
    print("PART 1: CPU-BOUND WORKLOAD (Hash Computation)")
    print("="*70)

    cpu_threaded_stats = benchmark_workload(CPUBoundService, 18812, 'threaded')
    cpu_forking_stats = benchmark_workload(CPUBoundService, 18813, 'forking')

    # Compare CPU-bound results
    cpu_improvement = ((cpu_threaded_stats['latency']['mean'] - cpu_forking_stats['latency']['mean'])
                       / cpu_threaded_stats['latency']['mean'] * 100)

    print(f"\nCPU-Bound Summary:")
    print(f"  Threaded: {cpu_threaded_stats['latency']['mean']*1000:.2f}ms avg, "
          f"CPU: {cpu_threaded_stats['cpu_usage']['mean']:.1f}%")
    print(f"  Forking:  {cpu_forking_stats['latency']['mean']*1000:.2f}ms avg, "
          f"CPU: {cpu_forking_stats['cpu_usage']['mean']:.1f}%")
    print(f"  Performance improvement with forking: {cpu_improvement:.1f}%")

    if cpu_improvement > 20:
        print(f"  ✓ EXPECTED: Forking mode is much faster for CPU-bound work")
        print(f"    Reason: Each forked process has its own GIL, enabling true parallelism")
    else:
        print(f"  ⚠ UNEXPECTED: Forking should be significantly faster for CPU-bound work")

    # ===== I/O-BOUND WORKLOAD =====
    print("\n" + "="*70)
    print("PART 2: I/O-BOUND WORKLOAD (Simulated Database/Network)")
    print("="*70)

    io_threaded_stats = benchmark_workload(IOBoundService, 18814, 'threaded')
    io_forking_stats = benchmark_workload(IOBoundService, 18815, 'forking')

    # Compare I/O-bound results
    io_difference = ((io_forking_stats['latency']['mean'] / io_threaded_stats['latency']['mean']) - 1) * 100

    print(f"\nI/O-Bound Summary:")
    print(f"  Threaded: {io_threaded_stats['latency']['mean']*1000:.2f}ms avg, "
          f"CPU: {io_threaded_stats['cpu_usage']['mean']:.1f}%")
    print(f"  Forking:  {io_forking_stats['latency']['mean']*1000:.2f}ms avg, "
          f"CPU: {io_forking_stats['cpu_usage']['mean']:.1f}%")
    print(f"  Difference: {abs(io_difference):.1f}% "
          f"({'forking slower' if io_difference > 0 else 'forking faster'})")

    if abs(io_difference) < 20:
        print(f"  ✓ EXPECTED: Similar performance in both modes for I/O-bound work")
        print(f"    Reason: GIL is released during I/O wait, so threading works fine")
        print(f"    Recommendation: Use threaded mode (lower memory overhead)")
    else:
        print(f"  ⚠ UNEXPECTED: I/O-bound work should have similar performance in both modes")

    # ===== FINAL RECOMMENDATIONS =====
    print("\n" + "="*70)
    print("CONCLUSIONS & RECOMMENDATIONS")
    print("="*70)

    print("\nWhen to use THREADED mode:")
    print("  ✓ I/O-bound workloads (database queries, file I/O, network calls)")
    print("  ✓ Lower memory usage is important")
    print("  ✓ Light CPU processing between I/O operations")

    print("\nWhen to use FORKING mode:")
    print("  ✓ CPU-bound workloads (data processing, encryption, computation)")
    print("  ✓ Need true parallelism across multiple CPU cores")
    print("  ✓ Can afford higher memory usage")

    print("\nHow to identify your workload type:")
    print("  1. Look at CPU usage during concurrent load:")
    print("     - High CPU (>80%) in threaded + poor scaling = CPU-bound (use forking)")
    print("     - Low CPU (<30%) + high latency = I/O-bound (threading is fine)")
    print("  2. Compare P99 vs P50 latency:")
    print("     - P99 >> P50 (>5x) in threaded = GIL contention (try forking)")
    print("  3. Benchmark both modes with your actual workload and compare")


if __name__ == '__main__':
    main()
