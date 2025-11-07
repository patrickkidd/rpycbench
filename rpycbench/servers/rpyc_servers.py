"""RPyC server implementations for benchmarking"""

import rpyc
from rpyc.utils.server import ThreadedServer, ForkingServer, OneShotServer
import multiprocessing
import socket
import time
import signal
import sys


class BenchmarkService(rpyc.Service):
    """RPyC service for benchmarking"""

    def exposed_ping(self):
        """Simple ping method for latency testing"""
        return "pong"

    def exposed_echo(self, data):
        """Echo data back for bandwidth testing"""
        return data

    def exposed_upload(self, data):
        """Receive data for upload bandwidth testing"""
        return len(data)

    def exposed_download(self, size):
        """Send data for download bandwidth testing"""
        return b'x' * size

    def exposed_compute(self, n):
        """Perform computation for testing"""
        result = sum(i * i for i in range(n))
        return result

    def exposed_sleep(self, duration):
        """Sleep for testing async behavior"""
        time.sleep(duration)
        return duration


def _run_rpyc_server(host, port, mode, ready_event):
    """
    Server process target function.
    Runs in a separate process to isolate from client GIL.
    """
    # Ignore keyboard interrupt in server process
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    protocol_config = {
        'allow_public_attrs': True,
        'allow_pickle': True,
        'sync_request_timeout': 30,
    }

    try:
        if mode == 'threaded':
            server = ThreadedServer(
                BenchmarkService,
                hostname=host,
                port=port,
                protocol_config=protocol_config,
            )
        elif mode == 'forking':
            server = ForkingServer(
                BenchmarkService,
                hostname=host,
                port=port,
                protocol_config=protocol_config,
            )
        elif mode == 'oneshot':
            server = OneShotServer(
                BenchmarkService,
                hostname=host,
                port=port,
                protocol_config=protocol_config,
            )
        else:
            raise ValueError(f"Unknown server mode: {mode}")

        # Signal that server is ready
        ready_event.set()

        # Start server (blocks until closed)
        server.start()

    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        ready_event.set()  # Signal even on error to unblock parent


class RPyCServer:
    """
    Wrapper for RPyC servers with lifecycle management.

    Runs server in a separate process to isolate from client GIL.
    Server lifecycle is managed by the parent process.
    """

    def __init__(self, host='localhost', port=18812, mode='threaded', auto_register=False):
        self.host = host
        self.port = port
        self.mode = mode
        self.auto_register = auto_register
        self.server_process = None
        self.ready_event = None

    def _wait_for_server(self, timeout=10):
        """Wait for server to be ready to accept connections"""
        # First wait for the ready event
        if not self.ready_event.wait(timeout=timeout):
            raise TimeoutError(f"Server did not signal ready within {timeout}s")

        # Then verify we can actually connect
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((self.host, self.port))
                sock.close()
                return True
            except (socket.error, ConnectionRefusedError):
                time.sleep(0.1)

        raise TimeoutError(f"Server not accepting connections after {timeout}s")

    def start(self):
        """Start the RPyC server in a separate process"""
        # Create event for signaling server readiness
        self.ready_event = multiprocessing.Event()

        # Create and start server process
        self.server_process = multiprocessing.Process(
            target=_run_rpyc_server,
            args=(self.host, self.port, self.mode, self.ready_event),
            daemon=True,
        )
        self.server_process.start()

        # Wait for server to be ready
        self._wait_for_server()

    def stop(self):
        """Stop the RPyC server"""
        if self.server_process and self.server_process.is_alive():
            # Terminate the process
            self.server_process.terminate()

            # Wait for clean shutdown (with timeout)
            self.server_process.join(timeout=5)

            # Force kill if still alive
            if self.server_process.is_alive():
                self.server_process.kill()
                self.server_process.join()

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
        return False


def create_rpyc_connection(host='localhost', port=18812, timeout=5):
    """Create RPyC connection for benchmarking"""
    return rpyc.connect(
        host,
        port,
        config={
            'allow_public_attrs': True,
            'allow_pickle': True,
            'sync_request_timeout': timeout,
        }
    )
