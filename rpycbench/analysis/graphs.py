import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


class GraphGenerator:
    def __init__(self, results_data: Dict[str, Any], output_dir: Path):
        self.results = results_data
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        plt.style.use('seaborn-v0_8-darkgrid')
        self.colors = {
            'rpyc_threaded': '#2E86AB',
            'rpyc_forking': '#A23B72',
            'http': '#F18F01'
        }

    def generate_all(self):
        graphs_generated = []

        try:
            graphs_generated.append(self.generate_connection_time_comparison())
        except (KeyError, ValueError, RuntimeError) as e:
            print(f"Warning: Could not generate connection time comparison: {e}")

        try:
            graphs_generated.append(self.generate_latency_comparison())
        except (KeyError, ValueError, RuntimeError) as e:
            print(f"Warning: Could not generate latency comparison: {e}")

        try:
            graphs_generated.append(self.generate_bandwidth_comparison())
        except (KeyError, ValueError, RuntimeError) as e:
            print(f"Warning: Could not generate bandwidth comparison: {e}")

        try:
            graphs_generated.append(self.generate_percentile_comparison())
        except (KeyError, ValueError, RuntimeError) as e:
            print(f"Warning: Could not generate percentile comparison: {e}")

        return [g for g in graphs_generated if g]

    def generate_connection_time_comparison(self) -> Optional[str]:
        fig, ax = plt.subplots(figsize=(10, 6))

        protocols = []
        times = []
        errors = []

        for protocol_key, data in self.results.items():
            if 'connection_time' in data:
                ct = data['connection_time']
                protocols.append(self._format_label(protocol_key))
                times.append(ct['mean'] * 1000)
                errors.append(ct['stdev'] * 1000)

        if not protocols:
            return None

        x = np.arange(len(protocols))
        bars = ax.bar(x, times, yerr=errors, capsize=5,
                     color=[self._get_color(p) for p in self.results.keys()],
                     alpha=0.8, edgecolor='black', linewidth=1.2)

        ax.set_xlabel('Protocol / Server Mode', fontsize=12, fontweight='bold')
        ax.set_ylabel('Connection Time (ms)', fontsize=12, fontweight='bold')
        ax.set_title('Connection Establishment Time Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(protocols, rotation=15, ha='right')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / 'connection_time_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def generate_latency_comparison(self) -> Optional[str]:
        fig, ax = plt.subplots(figsize=(10, 6))

        protocols = []
        means = []
        errors = []

        for protocol_key, data in self.results.items():
            if 'latency' in data:
                lat = data['latency']
                protocols.append(self._format_label(protocol_key))
                means.append(lat['mean'] * 1000)
                errors.append(lat['stdev'] * 1000)

        if not protocols:
            return None

        x = np.arange(len(protocols))
        bars = ax.bar(x, means, yerr=errors, capsize=5,
                     color=[self._get_color(p) for p in self.results.keys()],
                     alpha=0.8, edgecolor='black', linewidth=1.2)

        ax.set_xlabel('Protocol / Server Mode', fontsize=12, fontweight='bold')
        ax.set_ylabel('Latency (ms)', fontsize=12, fontweight='bold')
        ax.set_title('Mean Latency Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(protocols, rotation=15, ha='right')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / 'latency_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def generate_bandwidth_comparison(self) -> Optional[str]:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        protocols = []
        upload = []
        download = []

        for protocol_key, data in self.results.items():
            label = self._format_label(protocol_key)
            protocols.append(label)

            if 'upload_bandwidth' in data:
                ub = data['upload_bandwidth']['mean'] / (1024 * 1024)
                upload.append(ub)
            else:
                upload.append(0)

            if 'download_bandwidth' in data:
                db = data['download_bandwidth']['mean'] / (1024 * 1024)
                download.append(db)
            else:
                download.append(0)

        if not protocols or (all(u == 0 for u in upload) and all(d == 0 for d in download)):
            return None

        x = np.arange(len(protocols))
        width = 0.6

        ax1.bar(x, upload, width, color=[self._get_color(p) for p in self.results.keys()],
               alpha=0.8, edgecolor='black', linewidth=1.2)
        ax1.set_xlabel('Protocol / Server Mode', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Upload Bandwidth (MB/s)', fontsize=11, fontweight='bold')
        ax1.set_title('Upload Bandwidth', fontsize=12, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(protocols, rotation=15, ha='right')
        ax1.grid(axis='y', alpha=0.3)

        ax2.bar(x, download, width, color=[self._get_color(p) for p in self.results.keys()],
               alpha=0.8, edgecolor='black', linewidth=1.2)
        ax2.set_xlabel('Protocol / Server Mode', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Download Bandwidth (MB/s)', fontsize=11, fontweight='bold')
        ax2.set_title('Download Bandwidth', fontsize=12, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(protocols, rotation=15, ha='right')
        ax2.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / 'bandwidth_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def generate_percentile_comparison(self) -> Optional[str]:
        fig, ax = plt.subplots(figsize=(10, 6))

        protocols = []
        p50_values = []
        p95_values = []
        p99_values = []

        for protocol_key, data in self.results.items():
            if 'latency' in data:
                lat = data['latency']
                protocols.append(self._format_label(protocol_key))
                p50_values.append(lat.get('median', 0) * 1000)
                p95_values.append(lat.get('p95', 0) * 1000)
                p99_values.append(lat.get('p99', 0) * 1000)

        if not protocols:
            return None

        x = np.arange(len(protocols))
        width = 0.25

        ax.bar(x - width, p50_values, width, label='P50 (Median)',
              color='#4CAF50', alpha=0.8, edgecolor='black', linewidth=1)
        ax.bar(x, p95_values, width, label='P95',
              color='#FF9800', alpha=0.8, edgecolor='black', linewidth=1)
        ax.bar(x + width, p99_values, width, label='P99',
              color='#F44336', alpha=0.8, edgecolor='black', linewidth=1)

        ax.set_xlabel('Protocol / Server Mode', fontsize=12, fontweight='bold')
        ax.set_ylabel('Latency (ms)', fontsize=12, fontweight='bold')
        ax.set_title('Latency Percentiles Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(protocols, rotation=15, ha='right')
        ax.legend(fontsize=10)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / 'percentile_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(output_path)

    def _format_label(self, protocol_key: str) -> str:
        return protocol_key.replace('_', ' ').title()

    def _get_color(self, protocol_key: str) -> str:
        return self.colors.get(protocol_key, '#666666')


def generate_graphs_from_json(json_path: Path, output_dir: Path) -> List[str]:
    with open(json_path, 'r') as f:
        data = json.load(f)

    results = data.get('results', data)

    generator = GraphGenerator(results, output_dir)
    return generator.generate_all()
