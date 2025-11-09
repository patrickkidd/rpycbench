#!/usr/bin/env python3
"""
Example script demonstrating autobench profiling

This script can be run directly or with autobench:
    python examples/autobench_example.py  # No profiling
    python -m rpycbench.autobench examples/autobench_example.py  # With profiling
"""

import rpyc.utils.classic
import sys

try:
    from rpycbench import mark
except ImportError:
    class mark:
        @staticmethod
        def start(name): pass
        @staticmethod
        def end(): pass
        @staticmethod
        def section(name):
            from contextlib import contextmanager
            @contextmanager
            def noop():
                yield
            return noop()


def main():
    print("Connecting to RPyC server...")
    print("(Make sure you have an RPyC classic server running: python -m rpyc.utils.classic)")

    try:
        with mark.section("Establishing connection"):
            conn = rpyc.utils.classic.connect('localhost', 18812)

        print("Connected! Making some calls...")

        with mark.section("Multiple ping calls"):
            for i in range(5):
                conn.root.ping()
            print("  Completed 5 pings")

        with mark.section("Accessing remote modules"):
            remote_os = conn.modules.os
            cwd = remote_os.getcwd()
            print(f"  Remote CWD: {cwd}")

        with mark.section("Nested remote calls"):
            remote_sys = conn.modules.sys
            version = remote_sys.version
            print(f"  Remote Python: {version[:20]}...")

        conn.close()
        print("\nDone!")

    except ConnectionRefusedError:
        print("\nError: Could not connect to RPyC server.")
        print("Start a classic server first:")
        print("  python -m rpyc.utils.classic")
        sys.exit(1)


if __name__ == '__main__':
    main()
