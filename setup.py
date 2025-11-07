from setuptools import setup, find_packages

setup(
    name="rpycbench",
    version="0.1.0",
    description="Benchmark suite comparing RPyC with HTTP/REST",
    author="",
    packages=find_packages(),
    install_requires=[
        "rpyc>=5.3.0",
        "requests>=2.31.0",
        "flask>=3.0.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "matplotlib>=3.7.0",
        "psutil>=5.9.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "rpycbench=rpycbench.runners.autonomous:main",
        ],
    },
)
