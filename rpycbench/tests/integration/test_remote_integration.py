"""Integration tests for remote execution that actually use SSH to localhost"""

import pytest
import subprocess
from pathlib import Path
from rpycbench.remote.executor import SSHExecutor
from rpycbench.remote.deployer import RemoteDeployer
from rpycbench.remote.servers import RemoteRPyCServer, RemoteHTTPServer


@pytest.fixture
def check_ssh(integration_host):
    """Verify SSH to integration host is available"""
    try:
        result = subprocess.run(
            ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=2', integration_host, 'echo', 'ok'],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            pytest.skip(f"SSH to {integration_host} not configured with public key auth")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip(f"SSH not available or {integration_host} SSH not configured")


@pytest.mark.integration
def test_ssh_executor_connection(check_ssh, integration_host):
    """Test actual SSH connection to integration host"""
    executor = SSHExecutor(integration_host)
    executor.connect()

    stdout, stderr, exit_code = executor.execute('echo "test"')

    assert exit_code == 0
    assert 'test' in stdout

    executor.disconnect()


@pytest.mark.integration
def test_ssh_executor_home_directory_expansion(check_ssh, integration_host):
    """Test that home directory is properly expanded"""
    executor = SSHExecutor(integration_host)
    executor.connect()

    stdout, stderr, exit_code = executor.execute('echo $HOME')

    assert exit_code == 0
    assert stdout.strip() != ''
    assert stdout.strip() != '$HOME'

    executor.disconnect()


@pytest.mark.integration
def test_deployer_actual_deployment(check_ssh, integration_host):
    """Test actual deployment to localhost"""
    executor = SSHExecutor(integration_host)
    executor.connect()

    deployer = RemoteDeployer(executor, verbose=False)

    try:
        venv_dir = deployer.deploy()

        assert venv_dir is not None

        stdout, stderr, exit_code = executor.execute(f'test -d {venv_dir} && echo exists')
        assert exit_code == 0
        assert 'exists' in stdout

        stdout, stderr, exit_code = executor.execute(f'test -f {venv_dir}/bin/python && echo exists')
        assert exit_code == 0
        assert 'exists' in stdout

    finally:
        executor.execute('rm -rf ~/.rpycbench_remote', timeout=10.0)
        executor.disconnect()


@pytest.mark.integration
def test_deployer_caching(check_ssh, integration_host):
    """Test that deployment caching works correctly"""
    executor = SSHExecutor(integration_host)
    executor.connect()

    deployer = RemoteDeployer(executor, verbose=False)

    try:
        venv_dir1 = deployer.deploy()

        deployer2 = RemoteDeployer(executor, verbose=False)
        venv_dir2 = deployer2.deploy()

        assert venv_dir1 == venv_dir2

    finally:
        executor.execute('rm -rf ~/.rpycbench_remote', timeout=10.0)
        executor.disconnect()


@pytest.mark.integration
def test_remote_rpyc_server(check_ssh, integration_host):
    """Test remote RPyC server on integration host"""
    server = RemoteRPyCServer(
        remote_host=integration_host,
        host='0.0.0.0',
        port=18815,
        mode='threaded',
        verbose=False
    )

    try:
        server.start()

        assert server.executor is not None
        assert server.server_pid is not None

        stdout, stderr, exit_code = server.executor.execute(f'ps -p {server.server_pid}')
        assert exit_code == 0

        assert server.executor.check_port_open(18815, timeout=2.0)

    finally:
        if server.executor and server.server_pid:
            server.stop()
            # Cleanup - reconnect if needed
            if not server.executor.client:
                server.executor.connect()
            server.executor.execute('rm -rf ~/.rpycbench_remote', timeout=10.0)
            server.executor.disconnect()


@pytest.mark.integration
def test_remote_http_server(check_ssh, integration_host):
    """Test remote HTTP server on integration host"""
    server = RemoteHTTPServer(
        remote_host=integration_host,
        host='0.0.0.0',
        port=5005,
        verbose=False
    )

    try:
        server.start()

        assert server.executor is not None
        assert server.server_pid is not None

        stdout, stderr, exit_code = server.executor.execute(f'ps -p {server.server_pid}')
        assert exit_code == 0

        assert server.executor.check_port_open(5005, timeout=2.0)

    finally:
        if server.executor and server.server_pid:
            server.stop()
            # Cleanup - reconnect if needed
            if not server.executor.client:
                server.executor.connect()
            server.executor.execute('rm -rf ~/.rpycbench_remote', timeout=10.0)
            server.executor.disconnect()


@pytest.mark.integration
def test_end_to_end_rpyc_benchmark(check_ssh, integration_host):
    """Test complete benchmark flow with remote server"""
    from rpycbench.servers.rpyc_servers import create_rpyc_connection

    connect_host = integration_host.split('@')[1] if '@' in integration_host else integration_host

    server = RemoteRPyCServer(
        remote_host=integration_host,
        host='0.0.0.0',
        port=18816,
        mode='threaded',
        verbose=False
    )

    try:
        server.start()

        conn = create_rpyc_connection(connect_host, 18816)

        result = conn.root.ping()
        assert result == 'pong'

        data = b'test data'
        echo_result = conn.root.echo(data)
        assert echo_result == data

        conn.close()

    finally:
        if server.executor and server.server_pid:
            server.stop()
            # Cleanup - reconnect if needed
            if not server.executor.client:
                server.executor.connect()
            server.executor.execute('rm -rf ~/.rpycbench_remote', timeout=10.0)
            server.executor.disconnect()


@pytest.mark.integration
def test_end_to_end_http_benchmark(check_ssh, integration_host):
    """Test complete benchmark flow with remote HTTP server"""
    import requests

    connect_host = integration_host.split('@')[1] if '@' in integration_host else integration_host

    server = RemoteHTTPServer(
        remote_host=integration_host,
        host='0.0.0.0',
        port=5006,
        verbose=False
    )

    try:
        server.start()

        response = requests.get(f'http://{connect_host}:5006/ping')
        assert response.status_code == 200
        assert response.json()['response'] == 'pong'

        test_data = b'test data'
        response = requests.post(f'http://{connect_host}:5006/echo', data=test_data)
        assert response.status_code == 200
        assert response.content == test_data

    finally:
        if server.executor and server.server_pid:
            server.stop()
            # Cleanup - reconnect if needed
            if not server.executor.client:
                server.executor.connect()
            server.executor.execute('rm -rf ~/.rpycbench_remote', timeout=10.0)
            server.executor.disconnect()
