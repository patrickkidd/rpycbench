"""Autonomous benchmark runner"""

import argparse
import json
import sys
from pathlib import Path

from rpycbench.benchmarks.suite import BenchmarkSuite


def main():
    """Main entry point for autonomous benchmark runner"""

    parser = argparse.ArgumentParser(
        description="RPyC vs HTTP/REST Benchmark Suite",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Server configuration
    parser.add_argument(
        '--rpyc-host',
        default='localhost',
        help='RPyC server host'
    )
    parser.add_argument(
        '--rpyc-port',
        type=int,
        default=18812,
        help='RPyC server port'
    )
    parser.add_argument(
        '--http-host',
        default='localhost',
        help='HTTP server host'
    )
    parser.add_argument(
        '--http-port',
        type=int,
        default=5000,
        help='HTTP server port'
    )

    # Test selection
    parser.add_argument(
        '--skip-rpyc-threaded',
        action='store_true',
        help='Skip RPyC threaded server tests'
    )
    parser.add_argument(
        '--skip-rpyc-forking',
        action='store_true',
        help='Skip RPyC forking server tests'
    )
    parser.add_argument(
        '--skip-http',
        action='store_true',
        help='Skip HTTP server tests'
    )

    # Benchmark parameters
    parser.add_argument(
        '--num-serial-connections',
        type=int,
        default=100,
        help='Sample size: number of serial connections created one-at-a-time to measure average connection establishment time'
    )
    parser.add_argument(
        '--num-requests',
        type=int,
        default=1000,
        help='Number of requests for latency benchmark'
    )
    parser.add_argument(
        '--num-parallel-clients',
        type=int,
        default=10,
        help='Number of parallel clients (simultaneous connections to measure performance under load)'
    )
    parser.add_argument(
        '--requests-per-client',
        type=int,
        default=100,
        help='Number of requests per parallel client'
    )

    # Binary transfer benchmark
    parser.add_argument(
        '--test-binary-transfer',
        action='store_true',
        help='Enable binary file transfer benchmarks'
    )
    parser.add_argument(
        '--binary-file-sizes',
        type=int,
        nargs='+',
        default=None,
        help='File sizes in bytes (default: 1572864 134217728 524288000)'
    )
    parser.add_argument(
        '--binary-chunk-size',
        type=int,
        default=None,
        help='Chunk size in bytes for chunked transfers (default: 65536)'
    )
    parser.add_argument(
        '--binary-iterations',
        type=int,
        default=3,
        help='Number of iterations per binary transfer test'
    )

    # Output options
    parser.add_argument(
        '--output',
        '-o',
        help='Output file for JSON results'
    )
    parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        help='Suppress summary output'
    )

    args = parser.parse_args()

    # Create and run benchmark suite
    suite = BenchmarkSuite(
        rpyc_host=args.rpyc_host,
        rpyc_port=args.rpyc_port,
        http_host=args.http_host,
        http_port=args.http_port,
    )

    try:
        results = suite.run_all(
            test_rpyc_threaded=not args.skip_rpyc_threaded,
            test_rpyc_forking=not args.skip_rpyc_forking,
            test_http=not args.skip_http,
            num_serial_connections=args.num_serial_connections,
            num_requests=args.num_requests,
            num_parallel_clients=args.num_parallel_clients,
            requests_per_client=args.requests_per_client,
            test_binary_transfer=args.test_binary_transfer,
            binary_file_sizes=args.binary_file_sizes,
            binary_chunk_size=args.binary_chunk_size,
            binary_iterations=args.binary_iterations,
        )

        # Print summary
        if not args.quiet:
            results.print_summary()

        # Save JSON output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                f.write(results.to_json())

            print(f"\nResults saved to: {output_path}")

        return 0

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        return 130
    except Exception as e:
        print(f"\nError running benchmarks: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
