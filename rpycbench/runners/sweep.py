import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import psutil

from rpycbench.benchmarks.suite import BenchmarkSuite
from rpycbench.analysis.graphs import generate_graphs_from_json


def collectSystemInfo(remote_host: Optional[str] = None) -> Dict[str, Any]:
    info = {}

    if remote_host:
        info['hostname'] = remote_host
        try:
            from rpycbench.remote.executor import RemoteExecutor
            executor = RemoteExecutor(remote_host)

            info['cpu_model'] = executor.execute_command("sysctl -n machdep.cpu.brand_string || lscpu | grep 'Model name' | cut -d: -f2 | xargs")
            info['cpu_cores'] = executor.execute_command("sysctl -n hw.ncpu || nproc")
            info['ram_gb'] = executor.execute_command("sysctl -n hw.memsize | awk '{print $1/1024/1024/1024}' || free -g | awk '/^Mem:/{print $2}'")
            info['os'] = executor.execute_command("uname -s")
            info['kernel'] = executor.execute_command("uname -r")
            info['python_version'] = executor.execute_command("python3 --version")
        except (ImportError, RuntimeError, OSError) as e:
            info['error'] = f"Could not collect remote system info: {e}"
    else:
        info['hostname'] = platform.node()
        info['cpu_model'] = platform.processor() or "Unknown"
        info['cpu_cores'] = psutil.cpu_count(logical=True)
        info['ram_gb'] = round(psutil.virtual_memory().total / (1024**3), 2)
        info['os'] = platform.system()
        info['kernel'] = platform.release()
        info['python_version'] = platform.python_version()

        if platform.system() == 'Darwin':
            try:
                cpu_brand = subprocess.check_output(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    text=True
                ).strip()
                info['cpu_model'] = cpu_brand
            except:
                pass

    return info


def runSweep(
    remote_host: Optional[str],
    output_dir: Path,
    description: str,
    test_rpyc_threaded: bool = True,
    test_rpyc_forking: bool = True,
    test_http: bool = True,
) -> Dict[str, Any]:
    print("\n" + "="*80)
    print("RPYCBENCH PARAMETER SWEEP")
    print("="*80)
    print(f"Output Directory: {output_dir}")
    print(f"Remote Host: {remote_host or 'localhost'}")
    print(f"Description: {description}")
    print("="*80 + "\n")

    output_dir.mkdir(parents=True, exist_ok=True)

    print("Collecting system information...")
    local_info = collectSystemInfo(None)
    print(f"  Local: {local_info['hostname']} - {local_info['cpu_model']}")

    remote_info = None
    if remote_host:
        remote_info = collectSystemInfo(remote_host)
        print(f"  Remote: {remote_info.get('hostname', 'Unknown')} - {remote_info.get('cpu_model', 'Unknown')}")

    print("\nRunning benchmark suite...")
    suite = BenchmarkSuite(
        rpyc_host='localhost',
        rpyc_port=18812,
        http_host='localhost',
        http_port=5000,
        remote_host=remote_host,
    )

    suite.run_all(
        test_rpyc_threaded=test_rpyc_threaded,
        test_rpyc_forking=test_rpyc_forking,
        test_http=test_http,
        num_serial_connections=100,
        num_requests=1000,
        num_parallel_clients=10,
        requests_per_client=100,
    )

    results_dict = suite.results.to_dict()

    sweep_results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'remote_host': remote_host,
        },
        'local_system': local_info,
        'remote_system': remote_info,
        'results': results_dict,
    }

    location_suffix = 'remote' if remote_host else 'local'
    results_file = output_dir / f'results_{location_suffix}.json'

    print(f"\nSaving results to {results_file}")
    with open(results_file, 'w') as f:
        json.dump(sweep_results, f, indent=2)

    return sweep_results


def main():
    parser = argparse.ArgumentParser(
        description='RPyC vs HTTP/REST Parameter Sweep',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--remote-host',
        help='Remote host for network testing (format: user@hostname)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('benchmarks'),
        help='Output directory for results and graphs'
    )
    parser.add_argument(
        '--skip-graphs',
        action='store_true',
        help='Skip graph generation'
    )
    parser.add_argument(
        '--description',
        default='',
        help='Description of test topology (e.g., "Parallels VM on same MacOS host")'
    )
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

    args = parser.parse_args()

    if not args.description:
        if args.remote_host:
            args.description = f"Remote benchmarks on {args.remote_host}"
        else:
            args.description = "Local benchmarks (localhost only)"

    try:
        results = runSweep(
            remote_host=args.remote_host,
            output_dir=args.output_dir,
            description=args.description,
            test_rpyc_threaded=not args.skip_rpyc_threaded,
            test_rpyc_forking=not args.skip_rpyc_forking,
            test_http=not args.skip_http,
        )

        if not args.skip_graphs:
            print("\nGenerating graphs...")
            graphs_dir = args.output_dir / 'graphs'
            graphs_dir.mkdir(parents=True, exist_ok=True)

            location_suffix = 'remote' if args.remote_host else 'local'
            results_file = args.output_dir / f'results_{location_suffix}.json'

            graph_files = generate_graphs_from_json(results_file, graphs_dir)
            print(f"Generated {len(graph_files)} graphs in {graphs_dir}")

        print("\n" + "="*80)
        print("SWEEP COMPLETE")
        print("="*80)
        print(f"Results saved to: {args.output_dir}")
        print("="*80 + "\n")

    except KeyboardInterrupt:
        print("\n\nSweep interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during sweep: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
