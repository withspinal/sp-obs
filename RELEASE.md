# Release Instructions

## Pre-release Checklist

- [ ] All tests pass
- [ ] Version bumped in pyproject.toml
- [ ] CHANGELOG.md updated with release notes
- [ ] README.md is up to date
- [ ] Code is linted and formatted

## Build Package

```bash
# Clean previous builds
rm -rf dist/

# Build the package
python -m build
```

## Test with TestPyPI

1. Upload to TestPyPI first:
```bash
python -m twine upload --repository testpypi dist/*
```

2. Test installation from TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple sp-obs
```

3. Verify the package works correctly

## Release to PyPI

```bash
python -m twine upload dist/*
```

## Post-release

1. Create a git tag:
```bash
git tag -a v0.1.1 -m "Release version 0.1.1"
git push origin v0.1.1
```

2. Create a GitHub release with the changelog

## Required Tools

Make sure you have these installed:
```bash
pip install build twine
```

## Configuration

Create `~/.pypirc` if it doesn't exist:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-...
```