# Integration Tests

Integration tests that verify remote execution functionality by actually connecting via SSH and running servers.

## Running Integration Tests

### Skip by Default
When running all tests, integration tests are automatically skipped:
```bash
pytest rpycbench/tests          # Integration tests skipped
```

### Run with --integration Flag
```bash
# Run against localhost (default)
pytest --integration rpycbench/tests/integration

# Run against a specific host
pytest --integration --integration-host parallels@hurin rpycbench/tests/integration
```

### Explicit Selection (VS Code Test Explorer)
When you explicitly select integration tests in VS Code Test Explorer, they run automatically:
- Click on `tests/integration` folder → runs all integration tests
- Click on a specific test → runs that test
- Uses `--integration-host localhost` by default

## Requirements

- SSH access to target host with public key authentication
- `uv` installed on target host
- Network connectivity on test ports (18815, 18816, 5005, 5006)

## Test Coverage

1. **test_ssh_executor_connection** - Basic SSH connectivity
2. **test_ssh_executor_home_directory_expansion** - Home directory path resolution
3. **test_deployer_actual_deployment** - Full code deployment
4. **test_deployer_caching** - Verify deployment caching works
5. **test_remote_rpyc_server** - RPyC server startup on remote host
6. **test_remote_http_server** - HTTP server startup on remote host
7. **test_end_to_end_rpyc_benchmark** - Complete RPyC benchmark workflow
8. **test_end_to_end_http_benchmark** - Complete HTTP benchmark workflow

## Configuration

Set custom integration host in pytest.ini or via command line:
```bash
pytest --integration --integration-host user@hostname rpycbench/tests/integration
```
