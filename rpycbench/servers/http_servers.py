"""HTTP/REST server implementations for benchmarking"""

from flask import Flask, request, jsonify, send_file
import multiprocessing
import socket
import time
import io
import signal
import sys


def _run_http_server(host, port, threaded, ready_event):
    """
    HTTP server process target function.
    Runs in a separate process to isolate from client GIL.
    """
    # Ignore keyboard interrupt in server process
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # Disable Flask logging
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    try:
        app = Flask(__name__)

        # Setup routes
        @app.route('/ping', methods=['GET'])
        def ping():
            return jsonify({'response': 'pong'})

        @app.route('/echo', methods=['POST'])
        def echo():
            data = request.get_data()
            return data

        @app.route('/upload', methods=['POST'])
        def upload():
            data = request.get_data()
            return jsonify({'size': len(data)})

        @app.route('/download/<int:size>', methods=['GET'])
        def download(size):
            data = b'x' * size
            return send_file(
                io.BytesIO(data),
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name='data.bin'
            )

        @app.route('/compute/<int:n>', methods=['GET'])
        def compute(n):
            result = sum(i * i for i in range(n))
            return jsonify({'result': result})

        @app.route('/sleep/<float:duration>', methods=['GET'])
        def sleep_endpoint(duration):
            time.sleep(duration)
            return jsonify({'duration': duration})

        # Signal ready
        ready_event.set()

        # Start server (blocks)
        app.run(
            host=host,
            port=port,
            threaded=threaded,
            debug=False,
            use_reloader=False
        )

    except Exception as e:
        print(f"HTTP Server error: {e}", file=sys.stderr)
        ready_event.set()


class HTTPBenchmarkServer:
    """
    Flask-based HTTP server for benchmarking.

    Runs server in a separate process to isolate from client GIL.
    Server lifecycle is managed by the parent process.
    """

    def __init__(self, host='localhost', port=5000, threaded=True):
        self.host = host
        self.port = port
        self.threaded = threaded
        self.server_process = None
        self.ready_event = None

    def _wait_for_server(self, timeout=10):
        """Wait for server to be ready to accept connections"""
        # First wait for the ready event
        if not self.ready_event.wait(timeout=timeout):
            raise TimeoutError(f"HTTP server did not signal ready within {timeout}s")

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

        raise TimeoutError(f"HTTP server not accepting connections after {timeout}s")

    def start(self):
        """Start the HTTP server in a separate process"""
        # Create event for signaling server readiness
        self.ready_event = multiprocessing.Event()

        # Create and start server process
        self.server_process = multiprocessing.Process(
            target=_run_http_server,
            args=(self.host, self.port, self.threaded, self.ready_event),
            daemon=True,
        )
        self.server_process.start()

        # Wait for server to be ready
        self._wait_for_server()

    def stop(self):
        """Stop the HTTP server"""
        if self.server_process and self.server_process.is_alive():
            # Terminate the process
            self.server_process.terminate()

            # Wait for clean shutdown (with timeout)
            self.server_process.join(timeout=5)

            # Force kill if still alive
            if self.server_process.is_alive():
                self.server_process.kill()
                self.server_process.join()

        self.server_process = None
        self.ready_event = None

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
        return False


def create_http_session():
    """Create HTTP session for benchmarking"""
    import requests
    session = requests.Session()
    # Keep-alive connection
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=100,
        max_retries=3
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
