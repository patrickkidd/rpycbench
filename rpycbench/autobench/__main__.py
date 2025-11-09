"""Command-line interface for automatic RPyC profiling

Usage:
    python -m rpycbench.autobench script.py [script args...]
    python -m rpycbench.autobench -m module [module args...]

This will automatically profile all RPyC connections created in your script
without requiring any code modifications.
"""

import sys
import os
import argparse
import atexit
import runpy
from pathlib import Path

from rpycbench.utils.telemetry import enable_telemetry, get_telemetry
from rpycbench.utils.markers import get_marker_manager
from rpycbench.autobench.patcher import install_patches


def print_summary():
    """Print telemetry and marker summary on exit"""
    telemetry = get_telemetry()
    marker_manager = get_marker_manager()

    print("\n")
    telemetry.print_summary()
    marker_manager.print_markers()


def main():
    parser = argparse.ArgumentParser(
        prog="python -m rpycbench.autobench",
        description="Automatically profile RPyC calls in your application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m rpycbench.autobench myapp.py
  python -m rpycbench.autobench myapp.py --host localhost --port 18861
  python -m rpycbench.autobench -m mymodule

The script will run with automatic RPyC profiling enabled. A summary will
be printed when the script exits.

For more control, use markers in your code:
  from rpycbench import mark

  with mark.section("Critical operation"):
      # Your code here
      pass
        """
    )

    parser.add_argument(
        'script',
        help='Python script to profile (or module name with -m)'
    )

    parser.add_argument(
        'script_args',
        nargs='*',
        help='Arguments to pass to the script'
    )

    parser.add_argument(
        '-m',
        '--module',
        action='store_true',
        help='Run script as a module (like python -m)'
    )

    parser.add_argument(
        '--slow-threshold',
        type=float,
        default=0.1,
        help='Threshold in seconds for slow call reporting (default: 0.1)'
    )

    parser.add_argument(
        '--deep-stack-threshold',
        type=int,
        default=5,
        help='Threshold for deep stack reporting (default: 5)'
    )

    parser.add_argument(
        '--no-netrefs',
        action='store_true',
        help='Disable netref tracking'
    )

    parser.add_argument(
        '--no-stacks',
        action='store_true',
        help='Disable call stack tracking'
    )

    args = parser.parse_args()

    # Enable telemetry with configured options
    telemetry = enable_telemetry(
        track_netrefs=not args.no_netrefs,
        track_stacks=not args.no_stacks,
        slow_call_threshold=args.slow_threshold,
        deep_stack_threshold=args.deep_stack_threshold,
    )

    # Enable marker tracking
    marker_manager = get_marker_manager()
    marker_manager.enable()

    # Install monkey patches BEFORE importing user code
    install_patches()

    # Register summary printer on exit
    atexit.register(print_summary)

    # Prepare sys.argv for the user script
    if args.module:
        # Module mode: python -m rpycbench.autobench -m mymodule [args...]
        sys.argv = [args.script] + args.script_args
        try:
            runpy.run_module(args.script, run_name='__main__', alter_sys=True)
        except SystemExit:
            pass
    else:
        # Script mode: python -m rpycbench.autobench script.py [args...]
        script_path = Path(args.script).resolve()

        if not script_path.exists():
            print(f"Error: Script not found: {script_path}", file=sys.stderr)
            sys.exit(1)

        # Modify sys.argv to look like the script was run directly
        sys.argv = [str(script_path)] + args.script_args

        # Add script directory to path so imports work
        script_dir = str(script_path.parent)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)

        # Run the script
        try:
            runpy.run_path(str(script_path), run_name='__main__')
        except SystemExit:
            pass


if __name__ == '__main__':
    main()
