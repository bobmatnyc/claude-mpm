# Dashboard Installation Guide

This guide covers how to install and run the Claude MPM dashboard across different installation methods.

## 🚀 Quick Start

The dashboard server works with all installation methods and automatically detects your setup:

```bash
# Method 1: Using the CLI (recommended)
claude-mpm dashboard start

# Method 2: Direct script (for development)
python scripts/start-dashboard.py

# Method 3: Python module
python -m claude_mpm.services.dashboard.stable_server
```

## 📦 Installation Methods

### 1. **Direct Python Install (pip)**

```bash
# Install
pip install claude-mpm

# Start dashboard
claude-mpm dashboard start
# or
python -m claude_mpm dashboard start
```

### 2. **Isolated Install (pipx)**

```bash
# Install
pipx install claude-mpm

# Start dashboard
claude-mpm dashboard start
```

### 3. **Homebrew (macOS)**

```bash
# Install
brew install claude-mpm

# Start dashboard
claude-mpm dashboard start
```

### 4. **NPM Global Install**

```bash
# Install
npm install -g claude-mpm

# Start dashboard
claude-mpm dashboard start
```

### 5. **Development Install**

```bash
# Clone and install
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm
pip install -e .

# Start dashboard
python scripts/start-dashboard.py
# or
claude-mpm dashboard start
```

## 🔧 Dashboard Options

### Basic Usage

```bash
# Start on default port (8765)
claude-mpm dashboard start

# Start on custom port
claude-mpm dashboard start --port 9000

# Start on custom host
claude-mpm dashboard start --host 0.0.0.0 --port 8765

# Start in background
claude-mpm dashboard start --background

# Check status
claude-mpm dashboard status

# Stop dashboard
claude-mpm dashboard stop

# Open in browser
claude-mpm dashboard open
```

### Advanced Options

```bash
# Enable debug mode
claude-mpm dashboard start --debug

# Verbose status
claude-mpm dashboard status --verbose

# Check all ports
claude-mpm dashboard status --show-ports
```

## 🌐 Accessing the Dashboard

Once started, the dashboard is available at:

- **Local access**: http://localhost:8765
- **Network access**: http://YOUR_IP:8765 (if started with `--host 0.0.0.0`)

## 🔍 Features

### HTTP + SocketIO Server
- **Stable architecture**: Uses proven `python-socketio` + `aiohttp`
- **Real-time updates**: WebSocket communication for live analysis
- **HTTP fallback**: Graceful degradation when WebSocket fails
- **Cross-platform**: Works on macOS, Linux, and Windows

### Code Analysis
- **AST Analysis**: Real-time code structure analysis
- **Multiple languages**: Python, JavaScript, TypeScript support
- **Mock data**: Demonstrates structure with realistic examples
- **Interactive tree**: Expandable code structure visualization

### Installation Detection
- **Auto-discovery**: Automatically finds dashboard files across installation methods
- **Robust paths**: Handles pip, pipx, homebrew, npm, and development installs
- **Graceful fallbacks**: Clear error messages for missing dependencies

## 🛠️ Troubleshooting

### Common Issues

#### 1. **Dashboard files not found**
```
❌ Error: Could not find dashboard files
```

**Solution**: Ensure Claude MPM is properly installed:
```bash
pip install --upgrade claude-mpm
# or reinstall
pip uninstall claude-mpm && pip install claude-mpm
```

#### 2. **Missing dependencies**
```
❌ Error: Missing dependencies: No module named 'aiohttp'
```

**Solution**: Install with dashboard dependencies:
```bash
pip install 'claude-mpm[dashboard]'
```

#### 3. **Port already in use**
```
❌ Error: [Errno 48] Address already in use
```

**Solution**: Use a different port or stop existing server:
```bash
claude-mpm dashboard stop
# or use different port
claude-mpm dashboard start --port 9000
```

#### 4. **Permission denied**
```
❌ Error: [Errno 13] Permission denied
```

**Solution**: Use a port > 1024 or run with appropriate permissions:
```bash
claude-mpm dashboard start --port 8765
```

### Debug Mode

Enable debug mode for detailed error information:

```bash
claude-mpm dashboard start --debug
```

This will show:
- Detailed error traces
- Dashboard file discovery process
- Server startup information
- Connection details

## 🔧 Development

### Running from Source

```bash
# Clone repository
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Install in development mode
pip install -e .

# Start dashboard
python scripts/start-dashboard.py --debug
```

### Custom Server

You can also create a custom server:

```python
from claude_mpm.services.dashboard.stable_server import StableDashboardServer

server = StableDashboardServer(host='localhost', port=8765, debug=True)
server.run()
```

## 📚 API Endpoints

The dashboard provides these HTTP endpoints:

- `GET /` - Dashboard HTML interface
- `GET /static/*` - Static files (JS, CSS)
- `GET /api/directory/list` - Directory listing API

And these SocketIO events:

- `code:analyze:file` - Request file analysis
- `code:file:analyzed` - Analysis results

## 🎯 Next Steps

Once the dashboard is running:

1. **Navigate to Code tab** - Explore your project structure
2. **Click on files** - See AST analysis with expandable code elements
3. **Use language filters** - Toggle Python, JavaScript, TypeScript
4. **Explore features** - Tree visualization, search, statistics

For more information, see the [Dashboard User Guide](dashboard-user-guide.md).
