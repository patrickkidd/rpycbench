"""Tests for server process isolation and lifecycle"""

import pytest
import time
import psutil
import os
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection
from rpycbench.servers.http_servers import HTTPBenchmarkServer, create_http_session


class TestServerProcessIsolation:
    """Test that servers run in separate processes"""

    def test_rpyc_server_separate_process(self, rpyc_port):
        """Test RPyC server runs in a separate process"""
        parent_pid = os.getpid()

        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded') as server:
            # Server should be running in a different process
            assert server.server_process is not None
            assert server.server_process.is_alive()
            assert server.server_process.pid != parent_pid

            # Verify we can connect
            conn = create_rpyc_connection('localhost', rpyc_port)
            result = conn.root.ping()
            assert result == "pong"
            conn.close()

        # Server process should be terminated
        assert not server.server_process.is_alive()

    def test_http_server_separate_process(self, http_port):
        """Test HTTP server runs in a separate process"""
        parent_pid = os.getpid()

        with HTTPBenchmarkServer(host='localhost', port=http_port, threaded=True) as server:
            # Server should be running in a different process
            assert server.server_process is not None
            assert server.server_process.is_alive()
            assert server.server_process.pid != parent_pid

            # Verify we can connect
            session = create_http_session()
            response = session.get(f'http://localhost:{http_port}/ping')
            assert response.status_code == 200
            session.close()

        # Server process should be terminated
        assert not server.server_process.is_alive()

    def test_server_cleanup_on_exception(self, rpyc_port):
        """Test server is cleaned up even if exception occurs"""
        server = RPyCServer(host='localhost', port=rpyc_port, mode='threaded')
        server.start()

        assert server.server_process.is_alive()

        # Stop should work even without context manager
        server.stop()
        time.sleep(0.5)
        assert not server.server_process.is_alive()


class TestServerModes:
    """Test different RPyC server threading models"""

    def test_rpyc_threaded_server(self, rpyc_port):
        """Test RPyC ThreadedServer mode"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded') as server:
            conn = create_rpyc_connection('localhost', rpyc_port)
            result = conn.root.ping()
            assert result == "pong"
            conn.close()

    def test_rpyc_forking_server(self, rpyc_port):
        """Test RPyC ForkingServer mode"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='forking') as server:
            conn = create_rpyc_connection('localhost', rpyc_port)
            result = conn.root.ping()
            assert result == "pong"
            conn.close()

    def test_multiple_concurrent_connections_threaded(self, rpyc_port):
        """Test multiple concurrent connections to threaded server"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            # Create multiple connections
            conns = [create_rpyc_connection('localhost', rpyc_port) for _ in range(5)]

            # All should work
            for conn in conns:
                result = conn.root.ping()
                assert result == "pong"

            # Cleanup
            for conn in conns:
                conn.close()


class TestServerReadiness:
    """Test server readiness synchronization"""

    def test_server_ready_before_return(self, rpyc_port):
        """Test that start() doesn't return until server is ready"""
        server = RPyCServer(host='localhost', port=rpyc_port, mode='threaded')
        start_time = time.time()
        server.start()
        elapsed = time.time() - start_time

        # Should be ready immediately (within reasonable time)
        assert elapsed < 5.0

        # Should be able to connect immediately
        conn = create_rpyc_connection('localhost', rpyc_port, timeout=1)
        result = conn.root.ping()
        assert result == "pong"
        conn.close()

        server.stop()

    def test_http_server_ready_before_return(self, http_port):
        """Test that HTTP server is ready before start() returns"""
        server = HTTPBenchmarkServer(host='localhost', port=http_port)
        start_time = time.time()
        server.start()
        elapsed = time.time() - start_time

        assert elapsed < 5.0

        # Should be able to connect immediately
        session = create_http_session()
        response = session.get(f'http://localhost:{http_port}/ping', timeout=1)
        assert response.status_code == 200
        session.close()

        server.stop()


class TestServerEndpoints:
    """Test all server endpoints work correctly"""

    def test_rpyc_endpoints(self, rpyc_port):
        """Test all RPyC service methods"""
        with RPyCServer(host='localhost', port=rpyc_port, mode='threaded'):
            conn = create_rpyc_connection('localhost', rpyc_port)

            # Test ping
            assert conn.root.ping() == "pong"

            # Test echo
            test_data = b"hello world"
            assert conn.root.echo(test_data) == test_data

            # Test upload
            assert conn.root.upload(test_data) == len(test_data)

            # Test download
            downloaded = conn.root.download(100)
            assert len(downloaded) == 100

            # Test compute
            result = conn.root.compute(10)
            expected = sum(i * i for i in range(10))
            assert result == expected

            conn.close()

    def test_http_endpoints(self, http_port):
        """Test all HTTP endpoints"""
        with HTTPBenchmarkServer(host='localhost', port=http_port):
            session = create_http_session()
            base_url = f'http://localhost:{http_port}'

            # Test ping
            response = session.get(f'{base_url}/ping')
            assert response.status_code == 200
            assert response.json()['response'] == 'pong'

            # Test echo
            test_data = b"hello world"
            response = session.post(f'{base_url}/echo', data=test_data)
            assert response.status_code == 200
            assert response.content == test_data

            # Test upload
            response = session.post(f'{base_url}/upload', data=test_data)
            assert response.status_code == 200
            assert response.json()['size'] == len(test_data)

            # Test download
            response = session.get(f'{base_url}/download/100')
            assert response.status_code == 200
            assert len(response.content) == 100

            # Test compute
            response = session.get(f'{base_url}/compute/10')
            assert response.status_code == 200
            expected = sum(i * i for i in range(10))
            assert response.json()['result'] == expected

            session.close()
