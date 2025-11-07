"""RPyC server implementations for benchmarking"""

import rpyc
from rpyc.utils.server import ThreadedServer, ForkingServer, OneShotServer
import threading
import time


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


class RPyCServer:
    """Wrapper for RPyC servers with lifecycle management"""

    def __init__(self, host='localhost', port=18812, mode='threaded', auto_register=False):
        self.host = host
        self.port = port
        self.mode = mode
        self.auto_register = auto_register
        self.server = None
        self.server_thread = None

    def start(self):
        """Start the RPyC server"""
        if self.mode == 'threaded':
            self.server = ThreadedServer(
                BenchmarkService,
                hostname=self.host,
                port=self.port,
                protocol_config={
                    'allow_public_attrs': True,
                    'allow_pickle': True,
                    'sync_request_timeout': 30,
                }
            )
        elif self.mode == 'forking':
            self.server = ForkingServer(
                BenchmarkService,
                hostname=self.host,
                port=self.port,
                protocol_config={
                    'allow_public_attrs': True,
                    'allow_pickle': True,
                    'sync_request_timeout': 30,
                }
            )
        elif self.mode == 'oneshot':
            self.server = OneShotServer(
                BenchmarkService,
                hostname=self.host,
                port=self.port,
                protocol_config={
                    'allow_public_attrs': True,
                    'allow_pickle': True,
                    'sync_request_timeout': 30,
                }
            )
        else:
            raise ValueError(f"Unknown server mode: {self.mode}")

        # Start server in background thread
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()

        # Give server time to start
        time.sleep(0.5)

    def stop(self):
        """Stop the RPyC server"""
        if self.server:
            self.server.close()
            self.server = None

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
