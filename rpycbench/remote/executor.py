import time
import socket
from typing import Optional, Tuple
import paramiko


class SSHExecutor:
    def __init__(self, host: str, user: Optional[str] = None, port: int = 22):
        if '@' in host:
            self.user, self.host = host.split('@', 1)
        else:
            self.user = user
            self.host = host

        self.port = port
        self.client: Optional[paramiko.SSHClient] = None

    def connect(self):
        if self.client is not None:
            return

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.client.connect(
                self.host,
                port=self.port,
                username=self.user,
                look_for_keys=True,
                allow_agent=True,
            )
        except Exception as e:
            raise ConnectionError(
                f"Failed to SSH connect to {self.user}@{self.host}:{self.port}. "
                f"Check that: (1) host is reachable, (2) SSH is running on port {self.port}, "
                f"(3) public key authentication is configured. Error: {e}"
            ) from e

    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None

    def execute(self, command: str, timeout: Optional[float] = None) -> Tuple[str, str, int]:
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()

        stdout_text = stdout.read().decode('utf-8', errors='replace')
        stderr_text = stderr.read().decode('utf-8', errors='replace')

        return stdout_text, stderr_text, exit_code

    def execute_background(self, command: str) -> int:
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        bg_command = f"nohup {command} > /dev/null 2>&1 & echo $!"
        stdout, stderr, exit_code = self.execute(bg_command)

        if exit_code != 0:
            raise RuntimeError(f"Failed to start background process: {stderr}")

        pid = int(stdout.strip())
        return pid

    def kill(self, pid: int, signal: int = 15):
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        self.execute(f"kill -{signal} {pid}", timeout=5.0)

    def is_alive(self, pid: int) -> bool:
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        stdout, stderr, exit_code = self.execute(f"ps -p {pid}", timeout=5.0)
        return exit_code == 0

    def transfer_file(self, local_path: str, remote_path: str):
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        sftp = self.client.open_sftp()
        try:
            sftp.put(local_path, remote_path)
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Failed to transfer file to {self.host}:{remote_path}. "
                f"Remote directory may not exist. Ensure parent directories are created first."
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Failed to transfer {local_path} to {self.host}:{remote_path}: {e}"
            ) from e
        finally:
            sftp.close()

    def check_port_open(self, port: int, timeout: float = 1.0) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((self.host, port))
            return result == 0
        finally:
            sock.close()

    def wait_for_port(self, port: int, timeout: float = 30.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self.check_port_open(port, timeout=1.0):
                return True
            time.sleep(0.1)
        return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
