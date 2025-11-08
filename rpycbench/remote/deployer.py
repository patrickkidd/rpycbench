import os
import sys
import tarfile
import tempfile
import hashlib
from pathlib import Path
from typing import Optional
from .executor import SSHExecutor


class RemoteDeployer:
    def __init__(self, executor: SSHExecutor, verbose: bool = True):
        self.executor = executor
        self.verbose = verbose
        self.remote_base_dir = "~/.rpycbench_remote"
        self.remote_venv_dir = f"{self.remote_base_dir}/venv"
        self.remote_code_dir = f"{self.remote_base_dir}/code"

    def _log(self, message: str):
        if self.verbose:
            print(f"[Remote Deploy] {message}")

    def _compute_code_checksum(self, package_path: Path) -> str:
        hasher = hashlib.sha256()

        for root, dirs, files in os.walk(package_path):
            dirs.sort()
            for filename in sorted(files):
                if filename.endswith('.pyc') or filename.startswith('.'):
                    continue

                filepath = Path(root) / filename
                try:
                    with open(filepath, 'rb') as f:
                        hasher.update(f.read())
                except (IOError, OSError):
                    continue

        return hasher.hexdigest()

    def _create_package_tarball(self, source_dir: Path, output_path: Path) -> str:
        with tarfile.open(output_path, 'w:gz') as tar:
            for root, dirs, files in os.walk(source_dir):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                for filename in files:
                    if filename.endswith('.pyc') or filename.startswith('.'):
                        continue

                    filepath = Path(root) / filename
                    arcname = filepath.relative_to(source_dir.parent)
                    tar.add(filepath, arcname=arcname)

        checksum = hashlib.sha256()
        with open(output_path, 'rb') as f:
            checksum.update(f.read())
        return checksum.hexdigest()

    def _get_remote_checksum(self) -> Optional[str]:
        checksum_file = f"{self.remote_code_dir}/.checksum"
        stdout, stderr, exit_code = self.executor.execute(f"cat {checksum_file}", timeout=5.0)

        if exit_code == 0:
            return stdout.strip()
        return None

    def _write_remote_checksum(self, checksum: str):
        checksum_file = f"{self.remote_code_dir}/.checksum"
        self.executor.execute(f"echo '{checksum}' > {checksum_file}", timeout=5.0)

    def _setup_remote_directories(self):
        self.executor.execute(f"mkdir -p {self.remote_base_dir}", timeout=10.0)
        self.executor.execute(f"mkdir -p {self.remote_code_dir}", timeout=10.0)

    def _check_uv_installed(self) -> bool:
        stdout, stderr, exit_code = self.executor.execute("which uv", timeout=5.0)
        return exit_code == 0

    def deploy(self) -> str:
        self._log("Starting deployment to remote host...")

        package_root = Path(__file__).parent.parent.parent
        rpycbench_package = package_root / "rpycbench"

        if not rpycbench_package.exists():
            raise RuntimeError(f"Cannot find rpycbench package at {rpycbench_package}")

        local_checksum = self._compute_code_checksum(rpycbench_package)

        self._log(f"Local code checksum: {local_checksum[:12]}...")

        self._setup_remote_directories()

        remote_checksum = self._get_remote_checksum()

        if remote_checksum == local_checksum:
            self._log(f"Using cached deployment (checksum: {local_checksum[:12]}...)")
            return self.remote_venv_dir

        self._log("Checksums differ, deploying new code...")

        with tempfile.TemporaryDirectory() as tmpdir:
            tarball_path = Path(tmpdir) / "rpycbench.tar.gz"
            self._log("Packaging code...")
            tarball_checksum = self._create_package_tarball(rpycbench_package, tarball_path)

            remote_tarball = f"{self.remote_base_dir}/rpycbench.tar.gz"
            self._log(f"Transferring code to {self.executor.host}...")
            self.executor.transfer_file(str(tarball_path), remote_tarball)

            self._log("Extracting code on remote host...")
            self.executor.execute(f"rm -rf {self.remote_code_dir}/*", timeout=10.0)
            self.executor.execute(
                f"tar -xzf {remote_tarball} -C {self.remote_base_dir}",
                timeout=30.0
            )

        if not self._check_uv_installed():
            raise RuntimeError("uv is not installed on remote host. Please install it first.")

        self._log("Setting up Python environment...")
        venv_exists_stdout, _, venv_check_code = self.executor.execute(
            f"test -d {self.remote_venv_dir} && echo 'exists' || echo 'missing'",
            timeout=5.0
        )

        if 'missing' in venv_exists_stdout:
            self._log("Creating virtual environment...")
            stdout, stderr, exit_code = self.executor.execute(
                f"cd {self.remote_code_dir} && uv venv {self.remote_venv_dir}",
                timeout=60.0
            )
            if exit_code != 0:
                raise RuntimeError(f"Failed to create venv: {stderr}")

        self._log("Installing dependencies...")
        stdout, stderr, exit_code = self.executor.execute(
            f"cd {self.remote_code_dir} && {self.remote_venv_dir}/bin/pip install -e .",
            timeout=120.0
        )

        if exit_code != 0:
            raise RuntimeError(f"Failed to install rpycbench: {stderr}")

        self._write_remote_checksum(local_checksum)

        self._log("Deployment complete")

        return self.remote_venv_dir
