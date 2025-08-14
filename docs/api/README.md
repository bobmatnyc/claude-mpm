# Claude MPM API Documentation

This directory contains the Sphinx-based API documentation for the Claude MPM framework.

## Building Documentation

### Prerequisites

Install documentation dependencies:

```bash
# Install from requirements file
pip install -r ../requirements.txt

# Or install manually
pip install sphinx sphinx-rtd-theme sphinx-autobuild
```

### Build Commands

**Build HTML documentation:**
```bash
make html
```

**Build and open in browser:**
```bash
make html-open
```

**Development with live reload:**
```bash
make live
```

**Generate autodoc stubs:**
```bash
make autodoc
```

**Clean build directory:**
```bash
make clean
```

**Build all formats:**
```bash
make all
```

**Check for documentation issues:**
```bash
make check
```

**Generate coverage report:**
```bash
make coverage
```

### Windows Support

Use the batch file for Windows:

```cmd
make.bat html
make.bat html-open  
make.bat all
```

## Documentation Structure

The API documentation is organized into the following sections:

- **Core API** - Service interfaces, dependency injection, and framework initialization
- **Services API** - Service-oriented architecture with five specialized domains
- **Agents API** - Agent lifecycle, registry, loading, and validation
- **Hooks API** - Extensibility system with interceptors and plugins  
- **CLI API** - Command-line interface and utilities

## Features

- **Automatic API Extraction** - Uses Sphinx autodoc to generate documentation from docstrings
- **Type Annotations** - Full support for Python type hints and annotations
- **Cross-References** - Automatic linking between related classes and methods
- **Search Functionality** - Built-in search across all documentation
- **Mobile Responsive** - Optimized for viewing on all device sizes
- **Theme Customization** - Custom CSS for improved readability and navigation

## Configuration

The documentation is configured in `conf.py` with:

- Read the Docs theme with custom styling
- Napoleon extension for Google/NumPy docstring support
- Intersphinx linking to Python and third-party documentation
- Coverage reporting for documentation completeness
- Mock imports for optional dependencies

## Development

When adding new modules or services:

1. Run `make autodoc` to regenerate module documentation
2. Update the appropriate index.rst files if needed
3. Build and review the documentation with `make html-open`
4. Check for any warnings or errors with `make check`

## Deployment

The documentation can be deployed to:

- **Read the Docs** - Configure with the provided requirements.txt
- **GitHub Pages** - Use GitHub Actions to build and deploy
- **Local Hosting** - Serve the `_build/html` directory with any web server

For automated deployment, the documentation build should be integrated into the CI/CD pipeline to ensure it stays up-to-date with code changes.