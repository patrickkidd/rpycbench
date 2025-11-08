import time
from typing import Optional
from .executor import SSHExecutor
from .deployer import RemoteDeployer


class RemoteRPyCServer:
    def __init__(
        self,
        remote_host: str,
        host: str = 'localhost',
        port: int = 18812,
        mode: str = 'threaded',
        auto_register: bool = False,
        ssh_port: int = 22,
        verbose: bool = True,
    ):
        self.remote_host = remote_host
        self.host = host
        self.port = port
        self.mode = mode
        self.auto_register = auto_register
        self.ssh_port = ssh_port
        self.verbose = verbose

        self.executor: Optional[SSHExecutor] = None
        self.deployer: Optional[RemoteDeployer] = None
        self.server_pid: Optional[int] = None
        self.venv_dir: Optional[str] = None

    def _log(self, message: str):
        if self.verbose:
            print(f"[Remote RPyC] {message}")

    def start(self):
        self._log(f"Connecting to {self.remote_host}...")
        self.executor = SSHExecutor(self.remote_host, port=self.ssh_port)
        self.executor.connect()

        self.deployer = RemoteDeployer(self.executor, verbose=self.verbose)
        self.venv_dir = self.deployer.deploy()

        actual_host = self.remote_host.split('@')[1] if '@' in self.remote_host else self.remote_host
        self._log(f"Starting RPyC server ({self.mode}) binding to {self.host}:{self.port} on {actual_host}...")

        python_exe = f"{self.venv_dir}/bin/python"
        server_cmd = (
            f"{python_exe} -c '"
            f"from rpycbench.servers.rpyc_servers import _run_rpyc_server; "
            f"import multiprocessing; "
            f"_run_rpyc_server(\"{self.host}\", {self.port}, \"{self.mode}\", multiprocessing.Event())'"
        )

        self.server_pid = self.executor.execute_background(server_cmd)
        self._log(f"Server started with PID {self.server_pid}")

        if not self.executor.wait_for_port(self.port, timeout=30.0):
            raise TimeoutError(
                f"Server on {self.executor.host}:{self.port} did not start within 30s. "
                f"Check that: (1) port {self.port} is not in use, "
                f"(2) firewall allows connections on port {self.port}, "
                f"(3) remote process (PID {self.server_pid}) is running."
            )

        self._log("Server ready")

    def stop(self):
        if not self.executor:
            return

        if self.server_pid:
            self._log(f"Stopping server (PID {self.server_pid})...")
            try:
                self.executor.kill(self.server_pid, signal=15)
                time.sleep(1)

                if self.executor.is_alive(self.server_pid):
                    self._log("Force killing server...")
                    self.executor.kill(self.server_pid, signal=9)
            except Exception as e:
                self._log(f"Error stopping server: {e}")

        self.executor.disconnect()
        self._log("Disconnected")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


class RemoteHTTPServer:
    def __init__(
        self,
        remote_host: str,
        host: str = 'localhost',
        port: int = 5000,
        threaded: bool = True,
        ssh_port: int = 22,
        verbose: bool = True,
    ):
        self.remote_host = remote_host
        self.host = host
        self.port = port
        self.threaded = threaded
        self.ssh_port = ssh_port
        self.verbose = verbose

        self.executor: Optional[SSHExecutor] = None
        self.deployer: Optional[RemoteDeployer] = None
        self.server_pid: Optional[int] = None
        self.venv_dir: Optional[str] = None

    def _log(self, message: str):
        if self.verbose:
            print(f"[Remote HTTP] {message}")

    def start(self):
        self._log(f"Connecting to {self.remote_host}...")
        self.executor = SSHExecutor(self.remote_host, port=self.ssh_port)
        self.executor.connect()

        self.deployer = RemoteDeployer(self.executor, verbose=self.verbose)
        self.venv_dir = self.deployer.deploy()

        actual_host = self.remote_host.split('@')[1] if '@' in self.remote_host else self.remote_host
        self._log(f"Starting HTTP server binding to {self.host}:{self.port} on {actual_host}...")

        python_exe = f"{self.venv_dir}/bin/python"
        threaded_str = "True" if self.threaded else "False"
        server_cmd = (
            f"{python_exe} -c '"
            f"from rpycbench.servers.http_servers import _run_http_server; "
            f"import multiprocessing; "
            f"_run_http_server(\"{self.host}\", {self.port}, {threaded_str}, multiprocessing.Event())'"
        )

        self.server_pid = self.executor.execute_background(server_cmd)
        self._log(f"Server started with PID {self.server_pid}")

        if not self.executor.wait_for_port(self.port, timeout=30.0):
            raise TimeoutError(
                f"Server on {self.executor.host}:{self.port} did not start within 30s. "
                f"Check that: (1) port {self.port} is not in use, "
                f"(2) firewall allows connections on port {self.port}, "
                f"(3) remote process (PID {self.server_pid}) is running."
            )

        self._log("Server ready")

    def stop(self):
        if not self.executor:
            return

        if self.server_pid:
            self._log(f"Stopping server (PID {self.server_pid})...")
            try:
                self.executor.kill(self.server_pid, signal=15)
                time.sleep(1)

                if self.executor.is_alive(self.server_pid):
                    self._log("Force killing server...")
                    self.executor.kill(self.server_pid, signal=9)
            except Exception as e:
                self._log(f"Error stopping server: {e}")

        self.executor.disconnect()
        self._log("Disconnected")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
