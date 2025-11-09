# RPyC vs HTTP/REST Performance Study - Implementation Plan

## Overview
Create comprehensive performance comparison between RPyC and HTTP/REST with academic-style research paper, reproducible benchmarks, and visualization graphs.

## User Requirements Summary
- Generic test results comparing RPyC with HTTP/REST
- Results applicable to most systems (relative differences)
- Test parameters: server models, bandwidth, latency, parallelism, local vs remote
- Output: Academic-style markdown paper with graphs
- Reproducible on different system topologies

## User Preferences (from Q&A)
- Remote host: `parallels@hurin`
- Sweep granularity: Quick sweep (15-30 min)
- Literature review: Brief comparison only
- Include graphs as PNG files accessible via GitHub markdown

## 1. Design Parameter Sweep

### Test Matrix
- **Payload sizes**: 1KB, 1MB, 100MB (bandwidth tests)
- **Concurrency levels**: 1, 10, 50, 100 clients
- **Server models**: RPyC Threaded, RPyC Forking, HTTP Threaded
- **Locations**: localhost, remote (parallels@hurin - configurable)
- **Metrics**:
  - Connection establishment time
  - Latency (p50/p95/p99)
  - Bandwidth (throughput in Mbps)
  - Concurrency throughput

## 2. Create CLI Sweep Tool

### File: `rpycbench/runners/sweep.py`

**CLI Command**: `rpycbench-sweep`

**Parameters**:
- `--remote-host USER@HOST` - Optional remote host for network testing
- `--output-dir PATH` - Output directory for results and graphs (default: `benchmarks/`)
- `--skip-graphs` - Skip graph generation
- `--description TEXT` - Topology description (e.g., "Parallels VM on same MacOS host", "Ethernet LAN")

**Functionality**:
- Automated parameter iteration calling `rpycbench` with varying configs
- JSON output per configuration
- Aggregate results JSON with metadata
- System metadata collection for **both local and remote hosts**:
  - CPU model, core count, frequency
  - RAM capacity
  - OS, kernel version
  - Python version
  - Network interface details (detect VM vs physical)
  - Network topology notes
- Replicable on any system topology

## 3. Create Graphing Module

### File: `rpycbench/analysis/graphs.py`

Generate publication-quality graphs with matplotlib:

1. **Connection Time Comparison**: Bar chart (RPyC Threaded vs Forking vs HTTP)
2. **Latency vs Payload Size**: Line plot with error bars (3 server types × 3 payload sizes)
3. **Bandwidth vs Payload Size**: Line plot showing throughput (Mbps) scaling from 1KB to 100MB
4. **Concurrency Scaling**: Line plot of throughput vs concurrent clients
5. **Latency Percentiles**: Box plots or violin plots (p50/p95/p99 comparison)
6. **Local vs Remote**: Side-by-side comparison showing network impact

**Output**: Save to `benchmarks/graphs/*.png` for GitHub markdown embedding

## 4. Run Benchmarks

### Local Benchmarks
```bash
rpycbench-sweep --output-dir benchmarks/ --description "localhost only"
```

### Remote Benchmarks
```bash
rpycbench-sweep --remote-host parallels@hurin --output-dir benchmarks/ --description "Parallels VM on same MacOS host"
```

**Output Files**:
- `benchmarks/results_local.json`
- `benchmarks/results_remote.json`
- `benchmarks/graphs/*.png`

Each JSON includes full system specs for both client and server hosts.

## 5. Write Academic Paper

### File: `benchmarks/PERFORMANCE_STUDY.md`

**Structure**:

1. **Title & Abstract**: 3-4 sentence summary of findings

2. **Introduction**: Brief RPC landscape positioning (1-2 paragraphs)
   - Brief comparison to gRPC, Thrift, XML-RPC
   - Focus: when to use RPyC vs HTTP/REST

3. **Experimental Design**:
   - Test matrix and methodology
   - **Hardware & Network Topology Table**:
     - Local host specs
     - Remote host specs
     - Network type (Parallels VM vs future ethernet LAN tests)

4. **Results**:
   - Embedded graphs with analysis tables
   - Key findings per dimension:
     - Connection establishment
     - Latency characteristics
     - Bandwidth scaling
     - Concurrency performance
     - Local vs remote impact

5. **Discussion**:
   - When to use RPyC vs HTTP
   - Scaling characteristics
   - Network sensitivity
   - VM overhead observations
   - Data-driven, minimal speculation

6. **Conclusion**: 2-3 sentence actionable takeaway

7. **Reproducibility**:
   - Command to replicate: `rpycbench-sweep --remote-host USER@HOST --description "your topology"`
   - Note: Results are topology-specific; ethernet LAN expected to show different characteristics

**Graph Embedding**: Use relative paths: `![Description](graphs/filename.png)`

## 6. Update Package Configuration

### File: `pyproject.toml`

**Changes**:
1. Add `rpycbench-sweep` console script entry point
2. Add matplotlib dependency for graphing
3. Ensure `rpycbench/analysis/` and `rpycbench/runners/sweep.py` are included in wheel

## Implementation Checklist

- [ ] Create `rpycbench/analysis/` directory
- [ ] Implement `rpycbench/analysis/graphs.py` graphing module
- [ ] Implement `rpycbench/runners/sweep.py` CLI tool
- [ ] Update `pyproject.toml` with console script and dependencies
- [ ] Test `rpycbench-sweep --help`
- [ ] Run local benchmark sweep
- [ ] Run remote benchmark sweep on `parallels@hurin`
- [ ] Generate graphs from results
- [ ] Write `benchmarks/PERFORMANCE_STUDY.md` academic paper
- [ ] Run code-style-enforcer agent
- [ ] Test reproducibility on different system

## Estimated Time
30-40 minutes total

## Future Use Cases
After initial implementation, users can:
1. Clone rpycbench on different lab with ethernet LAN
2. Run: `rpycbench-sweep --remote-host lab@server --description "Ethernet LAN"`
3. Compare results to see performance on different network topologies
