# LPCPU Testing Infrastructure

Simple automated testing setup for LPCPU improvements.

## What's Included

- **Basic Python tests** - Simple tests to verify testing infrastructure works
- **3 Container definitions** - Fedora, RHEL, SLES
- **GitHub Actions workflow** - Automatically runs tests on PRs

## Files Created

```
.github/workflows/test-pr.yml    # GitHub Actions workflow
containers/
  ├── Containerfile.fedora       # Fedora container
  ├── Containerfile.rhel         # RHEL container
  ├── Containerfile.sles         # SLES container
  └── test-entrypoint.sh         # Test runner script
tests/
  ├── __init__.py                # Python package marker
  ├── conftest.py                # Pytest config
  └── test_core.py               # Basic Python tests
requirements-test.txt            # Python dependencies (just pytest)
```

## How to Use

### Local Testing

```bash
# Build container (pick one)
podman build -t lpcpu-test-fedora -f containers/Containerfile.fedora .
podman build -t lpcpu-test-rhel -f containers/Containerfile.rhel .
podman build -t lpcpu-test-sles -f containers/Containerfile.sles .

# Run tests
podman run --rm lpcpu-test-fedora
```

### Automatic Testing

When you create a pull request, GitHub Actions will automatically:
1. Build containers for Fedora, RHEL, and SLES
2. Run tests in each container
3. Report results in the PR

## What Gets Tested

Currently just basic Python functionality to verify the infrastructure works:
- Python is working
- Basic math operations
- String operations
- List operations
- Pytest features

**Note**: These are placeholder tests. Add your own tests as you develop features.

## Adding Your Own Tests

1. Edit `tests/test_core.py` or create new test files
2. Test locally: `podman run --rm lpcpu-test-fedora`
3. Commit and push - tests run automatically on PR

## Requirements

- **Podman** for local testing
- **GitHub Actions** enabled in repository for automatic testing