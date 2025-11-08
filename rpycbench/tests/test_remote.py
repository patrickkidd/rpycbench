"""Tests for remote execution functionality"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from rpycbench.remote.executor import SSHExecutor
from rpycbench.remote.deployer import RemoteDeployer
from rpycbench.remote.servers import RemoteRPyCServer, RemoteHTTPServer


def test_ssh_executor_init_with_user_at_host():
    executor = SSHExecutor('user@hostname')
    assert executor.user == 'user'
    assert executor.host == 'hostname'
    assert executor.port == 22


def test_ssh_executor_init_without_user():
    executor = SSHExecutor('hostname', user='testuser')
    assert executor.user == 'testuser'
    assert executor.host == 'hostname'
    assert executor.port == 22


@patch('rpycbench.remote.executor.paramiko.SSHClient')
def test_ssh_executor_connect(ssh_client_mock):
    executor = SSHExecutor('user@hostname')

    client_instance = MagicMock()
    ssh_client_mock.return_value = client_instance

    executor.connect()

    assert executor.client is not None
    client_instance.set_missing_host_key_policy.assert_called_once()
    client_instance.connect.assert_called_once_with(
        'hostname',
        port=22,
        username='user',
        look_for_keys=True,
        allow_agent=True,
    )


@patch('rpycbench.remote.executor.paramiko.SSHClient')
def test_ssh_executor_execute(ssh_client_mock):
    executor = SSHExecutor('user@hostname')

    client_instance = MagicMock()
    ssh_client_mock.return_value = client_instance

    stdin_mock = MagicMock()
    stdout_mock = MagicMock()
    stderr_mock = MagicMock()

    stdout_mock.channel.recv_exit_status.return_value = 0
    stdout_mock.read.return_value = b'output'
    stderr_mock.read.return_value = b''

    client_instance.exec_command.return_value = (stdin_mock, stdout_mock, stderr_mock)

    executor.connect()
    stdout, stderr, exit_code = executor.execute('ls -la')

    assert stdout == 'output'
    assert stderr == ''
    assert exit_code == 0


@patch('rpycbench.remote.executor.paramiko.SSHClient')
def test_ssh_executor_execute_background(ssh_client_mock):
    executor = SSHExecutor('user@hostname')

    client_instance = MagicMock()
    ssh_client_mock.return_value = client_instance

    stdin_mock = MagicMock()
    stdout_mock = MagicMock()
    stderr_mock = MagicMock()

    stdout_mock.channel.recv_exit_status.return_value = 0
    stdout_mock.read.return_value = b'12345'
    stderr_mock.read.return_value = b''

    client_instance.exec_command.return_value = (stdin_mock, stdout_mock, stderr_mock)

    executor.connect()
    pid = executor.execute_background('python server.py')

    assert pid == 12345
    client_instance.exec_command.assert_called_once()


@patch('rpycbench.remote.executor.socket.socket')
@patch('rpycbench.remote.executor.paramiko.SSHClient')
def test_ssh_executor_check_port_open(ssh_client_mock, socket_mock):
    executor = SSHExecutor('user@hostname')

    sock_instance = MagicMock()
    socket_mock.return_value = sock_instance
    sock_instance.connect_ex.return_value = 0

    executor.connect()
    result = executor.check_port_open(8080)

    assert result is True
    sock_instance.connect_ex.assert_called_once_with(('hostname', 8080))


@patch('rpycbench.remote.deployer.Path')
@patch('rpycbench.remote.deployer.os.walk')
def test_deployer_compute_checksum(walk_mock, path_mock):
    executor_mock = MagicMock()
    deployer = RemoteDeployer(executor_mock, verbose=False)

    walk_mock.return_value = [
        ('/test', [], ['file1.py', 'file2.py']),
    ]

    path_mock.return_value = MagicMock()

    with patch('builtins.open', create=True) as open_mock:
        open_mock.return_value.__enter__.return_value.read.return_value = b'content'
        checksum = deployer._compute_code_checksum(path_mock.return_value)

    assert isinstance(checksum, str)
    assert len(checksum) == 64


def test_deployer_get_remote_checksum():
    executor_mock = MagicMock()
    executor_mock.execute.side_effect = [
        ('/home/user', '', 0),
        ('abc123', '', 0),
    ]

    deployer = RemoteDeployer(executor_mock, verbose=False)
    checksum = deployer._get_remote_checksum()

    assert checksum == 'abc123'


def test_deployer_get_remote_checksum_not_found():
    executor_mock = MagicMock()
    executor_mock.execute.side_effect = [
        ('/home/user', '', 0),
        ('', 'not found', 1),
    ]

    deployer = RemoteDeployer(executor_mock, verbose=False)
    checksum = deployer._get_remote_checksum()

    assert checksum is None


@patch('rpycbench.remote.servers.SSHExecutor')
@patch('rpycbench.remote.servers.RemoteDeployer')
def test_remote_rpyc_server_start(deployer_mock, executor_mock):
    executor_instance = MagicMock()
    executor_mock.return_value = executor_instance

    deployer_instance = MagicMock()
    deployer_mock.return_value = deployer_instance
    deployer_instance.deploy.return_value = '/remote/venv'

    executor_instance.execute_background.return_value = 12345
    executor_instance.wait_for_port.return_value = True

    server = RemoteRPyCServer('user@hostname', verbose=False)
    server.start()

    assert server.server_pid == 12345
    executor_instance.connect.assert_called_once()
    deployer_instance.deploy.assert_called_once()
    executor_instance.execute_background.assert_called_once()
    executor_instance.wait_for_port.assert_called_once()


@patch('rpycbench.remote.servers.SSHExecutor')
@patch('rpycbench.remote.servers.RemoteDeployer')
def test_remote_rpyc_server_stop(deployer_mock, executor_mock):
    executor_instance = MagicMock()
    executor_mock.return_value = executor_instance

    deployer_instance = MagicMock()
    deployer_mock.return_value = deployer_instance
    deployer_instance.deploy.return_value = '/remote/venv'

    executor_instance.execute_background.return_value = 12345
    executor_instance.wait_for_port.return_value = True
    executor_instance.is_alive.return_value = False

    server = RemoteRPyCServer('user@hostname', verbose=False)
    server.start()
    server.stop()

    executor_instance.kill.assert_called_once_with(12345, signal=15)
    executor_instance.disconnect.assert_called_once()


@patch('rpycbench.remote.servers.SSHExecutor')
@patch('rpycbench.remote.servers.RemoteDeployer')
def test_remote_http_server_start(deployer_mock, executor_mock):
    executor_instance = MagicMock()
    executor_mock.return_value = executor_instance

    deployer_instance = MagicMock()
    deployer_mock.return_value = deployer_instance
    deployer_instance.deploy.return_value = '/remote/venv'

    executor_instance.execute_background.return_value = 54321
    executor_instance.wait_for_port.return_value = True

    server = RemoteHTTPServer('user@hostname', verbose=False)
    server.start()

    assert server.server_pid == 54321
    executor_instance.connect.assert_called_once()
    deployer_instance.deploy.assert_called_once()
    executor_instance.execute_background.assert_called_once()
    executor_instance.wait_for_port.assert_called_once()


@patch('rpycbench.remote.servers.SSHExecutor')
@patch('rpycbench.remote.servers.RemoteDeployer')
def test_remote_http_server_context_manager(deployer_mock, executor_mock):
    executor_instance = MagicMock()
    executor_mock.return_value = executor_instance

    deployer_instance = MagicMock()
    deployer_mock.return_value = deployer_instance
    deployer_instance.deploy.return_value = '/remote/venv'

    executor_instance.execute_background.return_value = 54321
    executor_instance.wait_for_port.return_value = True
    executor_instance.is_alive.return_value = False

    with RemoteHTTPServer('user@hostname', verbose=False) as server:
        assert server.server_pid == 54321

    executor_instance.disconnect.assert_called_once()
