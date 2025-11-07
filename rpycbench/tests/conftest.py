"""Pytest configuration and fixtures"""

import pytest
import time
import socket


def find_free_port():
    """Find a free port for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture
def rpyc_port():
    """Provide a free port for RPyC server"""
    return find_free_port()


@pytest.fixture
def http_port():
    """Provide a free port for HTTP server"""
    return find_free_port()


@pytest.fixture
def test_data_small():
    """Small test data (1KB)"""
    return b'x' * 1024


@pytest.fixture
def test_data_medium():
    """Medium test data (10KB)"""
    return b'x' * 10240


@pytest.fixture
def test_data_large():
    """Large test data (100KB)"""
    return b'x' * 102400
