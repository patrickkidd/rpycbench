#!/usr/bin/env python3
"""
Example: Baseline comparison of RPyC vs HTTP

This runs a simple baseline comparison showing:
- Connection establishment time
- Request/response latency
- Upload/download bandwidth

Results are printed in comparable format.
"""

from rpycbench.benchmarks.suite import BenchmarkSuite


def run_baseline_comparison():
    """Run baseline RPyC vs HTTP comparison"""

    print("BASELINE COMPARISON: RPyC vs HTTP/REST")
    print("=" * 80)
    print("\nThis compares the baseline performance of:")
    print("  - RPyC (threaded server)")
    print("  - HTTP/REST (Flask threaded server)")
    print("\nMetrics measured:")
    print("  - Connection establishment time")
    print("  - Request/response latency")
    print("  - Upload/download bandwidth")
    print("=" * 80)

    # Create suite
    suite = BenchmarkSuite(
        rpyc_host='localhost',
        rpyc_port=18812,
        http_host='localhost',
        http_port=5000,
    )

    # Run baseline benchmarks
    # Using moderate parameters for quick baseline
    results = suite.run_all(
        test_rpyc_threaded=True,
        test_rpyc_forking=False,  # Skip forking for baseline
        test_http=True,
        num_connections=100,       # Connection establishment
        num_requests=1000,         # Latency testing
        num_concurrent_clients=10, # Concurrent load
        requests_per_client=100,
    )

    # Print formatted comparison
    results.print_summary()

    # Export to JSON for programmatic analysis
    with open('baseline_comparison.json', 'w') as f:
        f.write(results.to_json())

    print("\n" + "=" * 80)
    print("Results saved to baseline_comparison.json")
    print("\nTo analyze programmatically:")
    print("  import json")
    print("  data = json.load(open('baseline_comparison.json'))")
    print("  rpyc_latency = data['rpyc_threaded']['latency']['mean']")
    print("  http_latency = data['http_threaded']['latency']['mean']")


def run_quick_baseline():
    """Run a quick baseline with minimal parameters"""

    print("\nQUICK BASELINE (faster, less accurate)")
    print("=" * 80)

    suite = BenchmarkSuite()

    results = suite.run_all(
        test_rpyc_threaded=True,
        test_rpyc_forking=False,
        test_http=True,
        num_connections=20,
        num_requests=100,
        num_concurrent_clients=3,
        requests_per_client=20,
    )

    results.print_summary()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        run_quick_baseline()
    else:
        run_baseline_comparison()
