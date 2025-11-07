"""HTTP/REST server implementations for benchmarking"""

from flask import Flask, request, jsonify, send_file
import threading
import time
import io


class HTTPBenchmarkServer:
    """Flask-based HTTP server for benchmarking"""

    def __init__(self, host='localhost', port=5000, threaded=True):
        self.host = host
        self.port = port
        self.threaded = threaded
        self.app = Flask(__name__)
        self.server_thread = None

        # Disable Flask logging for cleaner benchmark output
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes"""

        @self.app.route('/ping', methods=['GET'])
        def ping():
            """Simple ping endpoint for latency testing"""
            return jsonify({'response': 'pong'})

        @self.app.route('/echo', methods=['POST'])
        def echo():
            """Echo data back for bandwidth testing"""
            data = request.get_data()
            return data

        @self.app.route('/upload', methods=['POST'])
        def upload():
            """Receive data for upload bandwidth testing"""
            data = request.get_data()
            return jsonify({'size': len(data)})

        @self.app.route('/download/<int:size>', methods=['GET'])
        def download(size):
            """Send data for download bandwidth testing"""
            data = b'x' * size
            return send_file(
                io.BytesIO(data),
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name='data.bin'
            )

        @self.app.route('/compute/<int:n>', methods=['GET'])
        def compute(n):
            """Perform computation for testing"""
            result = sum(i * i for i in range(n))
            return jsonify({'result': result})

        @self.app.route('/sleep/<float:duration>', methods=['GET'])
        def sleep_endpoint(duration):
            """Sleep for testing async behavior"""
            time.sleep(duration)
            return jsonify({'duration': duration})

    def start(self):
        """Start the HTTP server"""
        self.server_thread = threading.Thread(
            target=lambda: self.app.run(
                host=self.host,
                port=self.port,
                threaded=self.threaded,
                debug=False,
                use_reloader=False
            ),
            daemon=True
        )
        self.server_thread.start()

        # Give server time to start
        time.sleep(0.5)

    def stop(self):
        """Stop the HTTP server"""
        # Note: Flask doesn't have a clean shutdown method when run in thread
        # In production, you'd use a proper WSGI server like Gunicorn
        pass

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
