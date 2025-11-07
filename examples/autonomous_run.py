#!/usr/bin/env python3
"""Example: Running benchmarks autonomously"""

from rpycbench.benchmarks.suite import BenchmarkSuite


def main():
    # Create benchmark suite with custom configuration
    suite = BenchmarkSuite(
        rpyc_host='localhost',
        rpyc_port=18812,
        http_host='localhost',
        http_port=5000,
    )

    # Run all benchmarks
    results = suite.run_all(
        test_rpyc_threaded=True,
        test_rpyc_forking=True,
        test_http=True,
        num_connections=50,
        num_requests=500,
        num_concurrent_clients=5,
        requests_per_client=50,
    )

    # Print summary
    results.print_summary()

    # Save results to JSON
    with open('benchmark_results.json', 'w') as f:
        f.write(results.to_json())

    print("\nResults saved to benchmark_results.json")


if __name__ == '__main__':
    main()
