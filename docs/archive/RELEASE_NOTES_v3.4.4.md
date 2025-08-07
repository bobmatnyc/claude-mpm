# Claude MPM v3.4.4 Release Notes

**Release Date**: August 7, 2025  
**Version**: 3.4.4 (Patch Release)

## 🚀 New Features

### Monitor Command with Socket.IO Server Management

This release introduces the new `claude-mpm monitor` command, providing comprehensive management of the Socket.IO monitoring server for real-time Claude MPM session insights.

#### Available Commands

```bash
# Start monitoring server on default port (8765)
claude-mpm monitor start

# Stop running monitoring server
claude-mpm monitor stop

# Restart monitoring server
claude-mpm monitor restart

# Start/restart on specific port
claude-mpm monitor port 9000
```

#### Features

- **Comprehensive Server Management**: Start, stop, restart, and port management
- **Multi-Port Support**: Run monitoring servers on different ports simultaneously
- **Intelligent Port Detection**: Automatically detects running servers and handles conflicts
- **User-Friendly Guidance**: Detailed troubleshooting information and command suggestions
- **Error Recovery**: Robust error handling with fallback options

#### Technical Details

- New `MonitorCommands` enum for consistent command handling
- Integrated with existing CLI architecture
- Full Socket.IO server lifecycle management
- Comprehensive logging and error reporting

## 📝 Documentation Improvements

### PM Framework Guidelines Enhancement

Updated the PM framework `INSTRUCTIONS.md` to clarify important behavioral guidelines:

- **Clarified PM Role Boundaries**: PM agents should never create todos with `[PM]` prefix for implementation work
- **Delegation Requirements**: All implementation work must be properly delegated to specialized agents
- **Todo Formatting**: Enhanced examples showing correct vs. incorrect todo patterns

## 🔧 Technical Improvements

- Enhanced CLI parser with monitor command integration
- Updated command structure with proper subcommand handling
- Improved constants organization for better maintainability

## 🏗 Infrastructure

- All E2E tests passing
- Version synchronization maintained
- Conventional commits followed for proper versioning

## 📋 Usage Examples

### Basic Monitor Operations

```bash
# Quick server status and commands
claude-mpm monitor

# Start monitoring server
claude-mpm monitor start

# Check server with custom port
claude-mpm monitor port 8080

# Stop all running servers
claude-mpm monitor stop
```

### Advanced Usage

```bash
# Start on specific port with host
claude-mpm monitor start --port 9000 --host localhost

# Stop specific server by port
claude-mpm monitor stop --port 9000

# Restart with port detection
claude-mpm monitor restart
```

## 🔗 WebSocket Integration

Once started, the monitoring server provides:
- Real-time session monitoring
- WebSocket connection management
- System performance insights
- Connection status tracking

Access via: `ws://localhost:{port}` (default: `ws://localhost:8765`)

## 🛠 Development Notes

This release maintains full backward compatibility while adding new monitoring capabilities. The monitor command integrates seamlessly with the existing claude-mpm ecosystem and follows established CLI patterns.

## 📦 Installation

No special installation steps required - the monitor command is available immediately upon upgrade:

```bash
# If installing from source
pip install -e .

# Or from PyPI (when published)
pip install --upgrade claude-mpm
```

## 🔍 Verification

Test the new monitor command:

```bash
claude-mpm monitor --help
claude-mpm monitor start
claude-mpm monitor stop
```

---

**Full Changelog**: [v3.4.3...v3.4.4](https://github.com/your-repo/claude-mpm/compare/v3.4.3...v3.4.4)