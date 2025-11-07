#!/usr/bin/env python3
"""Quick test to verify the benchmark suite works"""

from rpycbench.benchmarks.suite import BenchmarkSuite


def main():
    print("Running quick test with minimal parameters...")
    print()

    suite = BenchmarkSuite()

    # Run with very small parameters for quick testing
    results = suite.run_all(
        test_rpyc_threaded=True,
        test_rpyc_forking=False,  # Skip forking for speed
        test_http=True,
        num_serial_connections=10,
        num_requests=50,
        num_parallel_clients=3,
        requests_per_client=10,
    )

    results.print_summary()

    print("\n✓ Benchmark suite is working correctly!")


if __name__ == '__main__':
    main()
