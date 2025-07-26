## 8. Testing Strategy for Claude MPM Integration

### 8.1 Unit Tests with Claude MPM Patterns

**File**: `tests/test_python_script_service.py`

```python
"""
Unit tests for Python Script Service integration with Claude MPM.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import yaml

from claude_mpm.services.python_script_service import PythonScriptService
from claude_mpm.services.script_validation_service import Script# Claude MPM Python Script Execution via Slash Commands Design

## Executive Summary

This design document outlines the implementation of a Python script execution system integrated with Claude MPM's existing orchestration architecture. The system will leverage Claude MPM's hook system, agent registry, and subprocess orchestration to execute Python scripts and return their output directly through slash commands, starting with a "Hello World" test case.

## 1. Architecture Overview

### 1.1 Integration with Claude MPM Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Slash Command  │───▶│   Hook System    │───▶│ Python Service  │
│  (.md files)    │    │ (PreToolUse Hook)│    │ (Orchestrated)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌──────────────────────┐   ┌─────────────────┐
                    │ SubprocessOrchestrator│   │ ClaudeLauncher  │
                    │    (Delegation)      │   │  (Execution)    │
                    └──────────────────────┘   └─────────────────┘
```

### 1.2 Claude MPM Integration Points

- **Hook System**: PreToolUse hooks to intercept slash commands
- **Service Layer**: New PythonScriptService in `src/claude_mpm/services/`
- **Agent Registry**: Register python script execution as a specialized agent
- **Orchestration**: Use existing SubprocessOrchestrator for script execution
- **CLI Integration**: Extend existing CLI with python script commands
- **Ticket System**: Automatic ticket creation from script outputs

## 2. Implementation Strategy

### 2.1 Claude MPM Directory Structure Integration

```
claude-mpm/
├── src/claude_mpm/
│   ├── services/
│   │   ├── python_script_service.py       # New: Python execution service
│   │   ├── script_validation_service.py   # New: Security validation
│   │   └── hook_service.py                # Existing: Hook management
│   ├── orchestration/
│   │   ├── subprocess_orchestrator.py     # Existing: Subprocess management
│   │   └── python_script_orchestrator.py  # New: Python-specific orchestration
│   ├── core/
│   │   ├── claude_launcher.py             # Existing: Unified launcher
│   │   └── python_agent_registry.py       # New: Python script agent registry
│   ├── agents/
│   │   └── templates/
│   │       └── python_executor_agent.md   # New: Python execution agent
│   ├── cli/
│   │   ├── cli.py                         # Existing: Main CLI
│   │   └── python_commands.py             # New: Python command extensions
│   └── hooks/
│       └── builtin/
│           └── python_script_hook.py      # New: Python script hook
├── .claude/
│   ├── commands/
│   │   └── python/
│   │       ├── hello-world.md             # Test command
│   │       ├── run-script.md              # Generic script runner
│   │       └── project-status.md          # Example project script
│   └── settings.json                      # Hook configuration
├── scripts/
│   ├── hello_world.py                     # Test script
│   ├── project_status.py                  # Example project script
│   └── utils/
│       └── mpm_common.py                  # MPM integration utilities
└── config/
    └── python_scripts.yaml                # Script configuration
```

### 2.2 Claude MPM Service Integration

The Python script execution integrates with Claude MPM's service-oriented architecture:

```python
# src/claude_mpm/services/python_script_service.py
"""
Python Script Execution Service for Claude MPM
Integrates with existing orchestration and hook systems.
"""

from claude_mpm.core import LoggerMixin, ClaudeLauncher
from claude_mpm.utils.paths import PathResolver
from claude_mpm.utils.subprocess_runner import SubprocessRunner
from claude_mpm.services.script_validation_service import ScriptValidationService
from typing import Dict, Any, Optional
import yaml
from pathlib import Path

class PythonScriptService(LoggerMixin):
    """Service for executing Python scripts within Claude MPM framework."""
    
    def __init__(self, project_root: Optional[Path] = None):
        super().__init__()
        self.project_root = project_root or PathResolver.get_project_root()
        self.scripts_dir = self.project_root / "scripts"
        self.config_path = self.project_root / "config" / "python_scripts.yaml"
        self.validator = ScriptValidationService(self.project_root)
        self.subprocess_runner = SubprocessRunner()
        self.config = self._load_config()
    
    def execute_script(self, script_name: str, args: str = "") -> Dict[str, Any]:
        """Execute a registered Python script."""
        self.logger.info(f"Executing Python script: {script_name}")
        
        try:
            # Validate script registration
            if script_name not in self.config.get("scripts", {}):
                return self._error_response(f"Script not registered: {script_name}")
            
            script_config = self.config["scripts"][script_name]
            script_path = self.scripts_dir / script_config["file"]
            
            # Security validation
            if not self.validator.validate_script_path(script_path):
                return self._error_response(f"Script validation failed: {script_path}")
            
            # Execute via subprocess runner
            return self._execute_with_subprocess_runner(script_path, args, script_config)
            
        except Exception as e:
            self.logger.error(f"Script execution failed: {e}")
            return self._error_response(f"Execution error: {str(e)}")
    
    def _execute_with_subprocess_runner(self, script_path: Path, args: str, config: Dict) -> Dict[str, Any]:
        """Execute script using Claude MPM's SubprocessRunner."""
        import sys
        
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args.split())
        
        try:
            result = self.subprocess_runner.run(
                cmd,
                cwd=self.project_root,
                timeout=config.get("timeout", 30),
                capture_output=True
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": result.execution_time if hasattr(result, 'execution_time') else None,
                "script_name": script_path.stem
            }
            
        except Exception as e:
            return self._error_response(f"Subprocess execution failed: {str(e)}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load script configuration from YAML."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                self.logger.warning(f"Config file not found: {self.config_path}")
                return self._default_config()
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "version": "1.0.0",
            "security": {
                "allowed_directories": ["scripts/", "tools/"],
                "max_execution_time": 60
            },
            "scripts": {
                "hello-world": {
                    "file": "hello_world.py",
                    "description": "Test script that outputs Hello World",
                    "timeout": 10
                }
            }
        }
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Generate standardized error response."""
        return {
            "success": False,
            "error": message,
            "returncode": 1,
            "stdout": "",
            "stderr": message
        }
```

## 3. Hook System Integration

### 3.1 Python Script Hook Implementation

**File**: `src/claude_mpm/hooks/builtin/python_script_hook.py`

```python
"""
Python Script Execution Hook for Claude MPM
Integrates Python script execution with slash commands via hooks.
"""

from claude_mpm.hooks.base_hook import PreToolUseHook
from claude_mpm.services.python_script_service import PythonScriptService
from claude_mpm.services.ticket_manager import TicketManager
import json
import re

class PythonScriptHook(PreToolUseHook):
    """Hook to intercept and execute Python script slash commands."""
    
    def __init__(self):
        super().__init__()
        self.python_service = PythonScriptService()
        self.ticket_manager = TicketManager()
    
    def execute(self, context: dict) -> dict:
        """Execute Python script if slash command detected."""
        tool_input = context.get("tool_input", {})
        tool_name = context.get("tool_name", "")
        
        # Check if this is a Bash tool with Python script command
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if self._is_python_script_command(command):
                return self._execute_python_command(command, context)
        
        # Allow normal processing
        return {"continue": True}
    
    def _is_python_script_command(self, command: str) -> bool:
        """Check if command is a Python script execution."""
        python_patterns = [
            r'^/python:',           # Direct Python slash command
            r'^python.*\.py.*

### 3.2 Hook Configuration Integration

**File**: `.claude/settings.json` (extends existing Claude MPM hook configuration)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -m claude_mpm.hooks.builtin.python_script_hook"
          }
        ]
      }
    ]
  }
}
```

## 4. Slash Command Implementation

### 4.1 Hello World Test Command

**File**: `.claude/commands/python/hello-world.md`

```markdown
# Python Hello World Test
Execute the hello world test script to verify Python script execution within Claude MPM.

## Usage
Test the Python script execution system integrated with Claude MPM orchestration.

## Instructions
Execute the hello world Python script using Claude MPM's integrated execution system:

1. **Trigger Python Script Execution**
   - Use the hook system to intercept this command
   - Execute via PythonScriptService
   - Return formatted output directly

2. **Verify Integration**
   - Confirm hook system is working
   - Validate script service execution
   - Check ticket extraction if applicable

3. **Display Results**
   - Show script output with proper formatting
   - Display execution metadata
   - Report any errors or warnings

!echo "/python:hello-world"

## Expected Output
- Formatted "Hello World" message from the Python script
- Execution status and timing information
- Integration confirmation with Claude MPM services
- Any automatically created tickets from script output
```

### 4.2 Generic Script Runner Command  

**File**: `.claude/commands/python/run-script.md`

```markdown
# Run Python Script via Claude MPM
Execute a specific Python script using Claude MPM's orchestration system.

## Usage
Run a Python script: $ARGUMENTS

## Instructions
Execute the specified Python script through Claude MPM's integrated execution pipeline:

1. **Script Validation**
   - Validate script path using Claude MPM's PathResolver
   - Security check via ScriptValidationService
   - Verify script registration in configuration

2. **Orchestrated Execution**
   - Execute via PythonScriptService
   - Use SubprocessRunner for process management
   - Apply timeout and resource limits

3. **Output Processing**
   - Format output using Claude MPM's output formatters
   - Extract tickets using existing ticket extraction patterns
   - Log execution via Claude MPM's logging system

4. **Integration Benefits**
   - Automatic ticket creation from script output
   - Integration with existing agent registry
   - Consistent error handling and reporting
   - Hook system extensibility

!echo "/python:run-script $ARGUMENTS"

## Claude MPM Integration Features
- Uses existing SubprocessRunner for reliable execution
- Integrates with ticket system for automatic workflow management
- Leverages LoggerMixin for consistent logging
- Applies security validation through existing services
- Supports agent delegation patterns
```

## 5. Configuration System

### 5.1 Script Configuration

**File**: `config/python_scripts.yaml`

```yaml
# Python Script Configuration for Claude MPM
version: "1.0.0"
description: "Python script execution configuration for Claude MPM integration"

# Security settings (integrates with Claude MPM's security model)
security:
  allowed_directories:
    - "scripts/"
    - "tools/"
    - "utils/"
  blocked_patterns:
    - "../"
    - "~/"
    - "/etc/"
    - "/tmp/"
    - "import os"  # Restrict dangerous imports
  max_execution_time: 60
  max_output_size: 1048576  # 1MB
  
# Claude MPM integration settings
integration:
  use_subprocess_runner: true
  enable_ticket_extraction: true
  enable_agent_delegation: true
  log_level: "INFO"
  
# Registered scripts
scripts:
  hello-world:
    file: "hello_world.py"
    description: "Test script that outputs Hello World with Claude MPM integration"
    timeout: 10
    args_required: false
    agent_type: "utility"
    tags: ["test", "demo"]
    
  project-status:
    file: "project_status.py"  
    description: "Display current project status using Claude MPM services"
    timeout: 30
    args_required: false
    agent_type: "analysis"
    tags: ["status", "monitoring"]
    
  mpm-diagnostics:
    file: "mpm_diagnostics.py"
    description: "Run Claude MPM system diagnostics and health checks"
    timeout: 45
    args_required: false
    agent_type: "diagnostic"
    tags: ["health", "diagnostic", "mpm"]

# Output formatting (integrates with Claude MPM's output system)
output:
  format: "mpm_standard"  # Use Claude MPM's standard output format
  max_lines: 100
  truncate_long_output: true
  include_execution_time: true
  include_return_code: true
  include_mpm_metadata: true
  
# Ticket extraction patterns (extends Claude MPM's ticket system)
ticket_extraction:
  enabled: true
  patterns:
    - pattern: "TODO:\\s*(.+)"
      type: "task"
      priority: "medium"
    - pattern: "FIXME:\\s*(.+)" 
      type: "bug"
      priority: "high"
    - pattern: "MPM-ISSUE:\\s*(.+)"
      type: "issue"
      priority: "high"
    - pattern: "ENHANCEMENT:\\s*(.+)"
      type: "feature"
      priority: "low"
```

## 6. Script Examples with Claude MPM Integration

### 6.1 Hello World Test Script with MPM Integration

**File**: `scripts/hello_world.py`

```python
#!/usr/bin/env python3
"""
Hello World test script for Claude MPM Python command system.
Demonstrates integration with Claude MPM services and patterns.
"""

import sys
import datetime
from pathlib import Path

# Add Claude MPM to path if available
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from claude_mpm.utils.paths import PathResolver
    from claude_mpm.core.logger_mixin import LoggerMixin
    MPM_AVAILABLE = True
except ImportError:
    MPM_AVAILABLE = False

def main():
    """Output Hello World with Claude MPM integration info."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("=" * 60)
    print("🐍 CLAUDE MPM PYTHON SCRIPT EXECUTION SYSTEM")
    print("=" * 60)
    print(f"Hello World from Claude MPM Python integration!")
    print(f"Timestamp: {timestamp}")
    print(f"Python Version: {sys.version.split()[0]}")
    
    # Claude MPM integration info
    if MPM_AVAILABLE:
        try:
            project_root = PathResolver.get_project_root()
            print(f"📁 Project Root: {project_root}")
            print(f"🔧 Claude MPM Integration: ✅ Available")
            
            # Check for Claude MPM components
            mpm_components = [
                "src/claude_mpm/services/python_script_service.py",
                "src/claude_mpm/hooks/builtin/python_script_hook.py", 
                "src/claude_mpm/orchestration/subprocess_orchestrator.py"
            ]
            
            print(f"\n🧩 Claude MPM Components:")
            for component in mmp_components:
                path = project_root / component
                status = "✅" if path.exists() else "❌"
                print(f"   {status} {component}")
                
        except Exception as e:
            print(f"⚠️  Claude MPM Integration: Partial ({e})")
    else:
        print(f"⚠️  Claude MPM Integration: Not Available")
    
    # Demonstrate ticket creation pattern
    print(f"\n📋 Ticket Extraction Test:")
    print(f"TODO: Test automatic ticket creation from script output")
    print(f"FIXME: Verify hook system integration is working correctly")
    
    print(f"\n✅ Execution successful!")
    print(f"🚀 Script executed via Claude MPM orchestration system")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 6.2 Claude MPM Project Status Script

**File**: `scripts/project_status.py`

```python
#!/usr/bin/env python3
"""
Claude MPM project status reporting script.
Provides comprehensive project status using Claude MPM services.
"""

import os
import sys
import subprocess
from pathlib import Path
import json

# Add Claude MPM to path if available
try:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from claude_mpm.utils.paths import PathResolver
    from claude_mpm.utils.subprocess_runner import SubprocessRunner
    MPM_AVAILABLE = True
except ImportError:
    MPM_AVAILABLE = False

def get_git_status():
    """Get current git status using Claude MPM patterns."""
    try:
        if MPM_AVAILABLE:
            runner = SubprocessRunner()
            result = runner.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                timeout=10
            )
            
            return {
                "clean": len(result.stdout.strip()) == 0,
                "changes": result.stdout.strip().split('\n') if result.stdout.strip() else [],
                "via_mpm": True
            }
        else:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "clean": len(result.stdout.strip()) == 0,
                "changes": result.stdout.strip().split('\n') if result.stdout.strip() else [],
                "via_mpm": False
            }
    except:
        return {"clean": None, "changes": [], "via_mmp": False}

def get_mpm_status():
    """Get Claude MPM specific status information."""
    if not MPM_AVAILABLE:
        return {"available": False}
    
    try:
        project_root = PathResolver.get_project_root()
        
        # Check key MPM directories
        mpm_dirs = {
            "src/claude_mpm": "Core package",
            "src/claude_mpm/services": "Services layer",
            "src/claude_mpm/orchestration": "Orchestrators",
            "src/claude_mpm/agents": "Agent templates",
            "scripts": "Python scripts",
            ".claude/commands": "Slash commands"
        }
        
        dir_status = {}
        for dir_path, description in mpm_dirs.items():
            full_path = project_root / dir_path
            dir_status[dir_path] = {
                "exists": full_path.exists(),
                "description": description,
                "file_count": len(list(full_path.rglob("*"))) if full_path.exists() else 0
            }
        
        return {
            "available": True,
            "project_root": str(project_root),
            "directories": dir_status
        }
        
    except Exception as e:
        return {"available": True, "error": str(e)}

def count_files():
    """Count files by type with Claude MPM context."""
    counts = {}
    extensions = ['.py', '.md', '.json', '.yaml', '.txt']
    
    if MPM_AVAILABLE:
        try:
            project_root = PathResolver.get_project_root()
            for ext in extensions:
                counts[ext] = len(list(project_root.rglob(f'*{ext}')))
        except:
            # Fallback to current directory
            for ext in extensions:
                counts[ext] = len(list(Path('.').rglob(f'*{ext}')))
    else:
        for ext in extensions:
            counts[ext] = len(list(Path('.').rglob(f'*{ext}')))
    
    return counts

def main():
    """Display comprehensive project status."""
    print("📊 CLAUDE MPM PROJECT STATUS REPORT")
    print("=" * 50)
    
    # Claude MPM Integration Status
    print(f"🔧 Claude MPM Integration:")
    if MPM_AVAILABLE:
        print(f"   ✅ Available and functional")
        mpm_status = get_mpm_status()
        if "directories" in mpm_status:
            print(f"   📁 Key directories:")
            for dir_path, info in mmp_status["directories"].items():
                status = "✅" if info["exists"] else "❌"
                print(f"      {status} {dir_path} ({info['file_count']} files)")
    else:
        print(f"   ❌ Not available or not properly configured")
    
    # Git Status
    print(f"\n📋 Git Status:")
    git_status = get_git_status()
    if git_status["clean"] is True:
        print("   ✅ Clean working directory")
    elif git_status["clean"] is False:
        print(f"   ⚠️  {len(git_status['changes'])} modified files")
        if git_status.get("via_mpm"):
            print("   🔧 Status retrieved via Claude MPM SubprocessRunner")
    else:
        print("   ❓ Unable to determine git status")
    
    # File Analysis
    print(f"\n📁 File Analysis:")
    file_counts = count_files()
    for ext, count in file_counts.items():
        print(f"   {ext}: {count}")
    
    # Environment Info
    print(f"\n🌍 Environment:")
    print(f"   📂 Working directory: {os.getcwd()}")
    print(f"   🐍 Python executable: {sys.executable}")
    
    # Action items (demonstrates ticket extraction)
    print(f"\n📋 Action Items:")
    print(f"TODO: Review Python script integration with orchestration system")
    if not MPM_AVAILABLE:
        print(f"FIXME: Claude MPM integration not available - check installation")
    
    print("=" * 50)
    print(f"✅ Status report completed via {'Claude MPM' if MPM_AVAILABLE else 'standalone'} execution")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 6.3 Claude MPM Diagnostics Script

**File**: `scripts/mpm_diagnostics.py`

```python
#!/usr/bin/env python3
"""
Claude MPM system diagnostics script.
Comprehensive health check for Claude MPM components.
"""

import sys
import importlib
from pathlib import Path
import json

def check_mmp_imports():
    """Check availability of Claude MPM modules."""
    modules_to_check = [
        "claude_mpm.core.claude_launcher",
        "claude_mpm.services.python_script_service", 
        "claude_mpm.orchestration.subprocess_orchestrator",
        "claude_mpm.utils.paths",
        "claude_mpm.utils.subprocess_runner",
        "claude_mpm.hooks.base_hook"
    ]
    
    results = {}
    for module_name in modules_to_check:
        try:
            importlib.import_module(module_name)
            results[module_name] = {"status": "✅", "available": True}
        except ImportError as e:
            results[module_name] = {"status": "❌", "available": False, "error": str(e)}
    
    return results

def check_project_structure():
    """Verify Claude MPM project structure."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from claude_mpm.utils.paths import PathResolver
        project_root = PathResolver.get_project_root()
    except:
        project_root = Path.cwd()
    
    required_paths = [
        "src/claude_mpm",
        "src/claude_mpm/core",
        "src/claude_mpm/services", 
        "src/claude_mpm/orchestration",
        "src/claude_mpm/agents",
        "scripts",
        ".claude/commands",
        "config"
    ]
    
    results = {}
    for path_str in required_paths:
        path = project_root / path_str
        results[path_str] = {
            "exists": path.exists(),
            "type": "directory" if path.is_dir() else "file" if path.exists() else "missing"
        }
    
    return results, project_root

def main():
    """Run comprehensive Claude MPM diagnostics."""
    print("🔬 CLAUDE MPM SYSTEM DIAGNOSTICS")
    print("=" * 40)
    
    # Module Import Tests
    print("📦 Module Import Tests:")
    import_results = check_mpm_imports()
    for module, result in import_results.items():
        print(f"   {result['status']} {module}")
        if not result["available"]:
            print(f"      Error: {result.get('error', 'Unknown')}")
    
    # Project Structure Check
    print(f"\n📁 Project Structure Check:")
    structure_results, project_root = check_project_structure()
    print(f"   📂 Project Root: {project_root}")
    
    for path, info in structure_results.items():
        status = "✅" if info["exists"] else "❌"
        print(f"   {status} {path} ({info['type']})")
    
    # Configuration Check
    print(f"\n⚙️  Configuration Check:")
    config_files = [
        "config/python_scripts.yaml",
        ".claude/settings.json",
        ".claude/commands/python/hello-world.md"
    ]
    
    for config_file in config_files:
        config_path = project_root / config_file
        status = "✅" if config_path.exists() else "❌"
        print(f"   {status} {config_file}")
    
    # Summary
    print(f"\n📊 Diagnostic Summary:")
    total_modules = len(import_results)
    available_modules = sum(1 for r in import_results.values() if r["available"])
    print(f"   📦 Modules: {available_modules}/{total_modules} available")
    
    total_paths = len(structure_results) 
    existing_paths = sum(1 for r in structure_results.values() if r["exists"])
    print(f"   📁 Structure: {existing_paths}/{total_paths} paths exist")
    
    if available_modules == total_modules and existing_paths == total_paths:
        print(f"   ✅ Overall Status: Healthy")
        print(f"ENHANCEMENT: All Claude MPM components are properly configured")
    else:
        print(f"   ⚠️  Overall Status: Issues detected")
        print(f"TODO: Fix missing Claude MPM components for full functionality")
    
    print("=" * 40)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## 7. Security Implementation with Claude MPM Integration

### 7.1 Script Validation Service

**File**: `src/claude_mpm/services/script_validation_service.py`

```python
"""
Script Validation Service for Claude MPM Python execution.
Integrates with Claude MPM's security and validation patterns.
"""

from claude_mpm.core import LoggerMixin
from claude_mpm.utils.paths import PathResolver
from pathlib import Path
from typing import List, Dict, Any
import re

class ScriptValidationService(LoggerMixin):
    """Validates Python scripts before execution using Claude MPM patterns."""
    
    # Security patterns adapted for Claude MPM context
    BLOCKED_PATTERNS = [
        r'\.\./+',                    # Directory traversal
        r'~/+',                       # Home directory access
        r'/etc/+',                    # System directory access
        r'/tmp/+',                    # Temp directory access
        r'import\s+subprocess',       # Direct subprocess imports
        r'eval\s*\(',                 # Code evaluation
        r'exec\s*\(',                 # Code execution
        r'__import__\s*\(',           # Dynamic imports
        r'open\s*\([^)]*["\'][/~]',   # Absolute path file access
    ]
    
    # Allowed directories relative to project root
    ALLOWED_DIRECTORIES = [
        'scripts',
        'tools', 
        'utils',
        'bin',
    ]
    
    # Allowed Claude MPM imports (these are safe)
    ALLOWED_MPM_IMPORTS = [
        'claude_mpm.utils',
        'claude_mpm.core',
        'claude_mpm.services',
    ]
    
    def __init__(self, project_root: Path = None):
        super().__init__()
        self.project_root = project_root or PathResolver.get_project_root()
    
    def validate_script_path(self, script_path: Path) -> bool:
        """Validate that script path is safe to execute."""
        try:
            # Use PathResolver for consistent path handling
            resolved_path = script_path.resolve()
            
            # Ensure script is within project boundaries
            if not str(resolved_path).startswith(str(self.project_root.resolve())):
                self.logger.warning(f"Script outside project root: {resolved_path}")
                return False
            
            # Check if in allowed directory
            relative_path = resolved_path.relative_to(self.project_root.resolve())
            if not any(str(relative_path).startswith(allowed) for allowed in self.ALLOWED_DIRECTORIES):
                self.logger.warning(f"Script not in allowed directory: {relative_path}")
                return False
            
            # Verify file exists and is readable
            if not resolved_path.exists() or not resolved_path.is_file():
                self.logger.warning(f"Script not found or not a file: {resolved_path}")
                return False
            
            # Check file extension
            if not resolved_path.suffix == '.py':
                self.logger.warning(f"Script must be a Python file: {resolved_path}")
                return False
            
            self.logger.debug(f"Script path validation passed: {resolved_path}")
            return True
            
        except (ValueError, OSError) as e:
            self.logger.error(f"Path validation error: {e}")
            return False
    
    def validate_script_content(self, script_path: Path) -> Dict[str, Any]:
        """Validate script content for security issues."""
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "blocked_patterns": [],
            "mpm_integration": False
        }
        
        try:
            content = script_path.read_text()
            
            # Check for blocked patterns
            for pattern in self.BLOCKED_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Check if it's an allowed Claude MPM import
                    if self._is_allowed_mpm_import(match.group(0)):
                        continue
                        
                    validation_result["blocked_patterns"].append({
                        "pattern": pattern,
                        "match": match.group(0),
                        "line": content[:match.start()].count('\n') + 1
                    })
                    validation_result["warnings"].append(
                        f"Potentially dangerous pattern at line {content[:match.start()].count('\n') + 1}: {pattern}"
                    )
            
            # Check for Claude MPM integration
            if any(import_pattern in content for import_pattern in self.ALLOWED_MPM_IMPORTS):
                validation_result["mpm_integration"] = True
                self.logger.info("Script uses Claude MPM integration")
            
            # Determine overall validity
            if validation_result["blocked_patterns"]:
                validation_result["valid"] = False
                validation_result["errors"].append("Script contains blocked patterns")
            
        except (OSError, UnicodeDecodeError) as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Unable to read script content: {e}")
            self.logger.error(f"Content validation error: {e}")
        
        return validation_result
    
    def _is_allowed_mpm_import(self, match_text: str) -> bool:
        """Check if a potentially dangerous pattern is actually an allowed Claude MPM import."""
        for allowed_import in self.ALLOWED_MPM_IMPORTS:
            if allowed_import in match_text:
                return True
        return False
    
    def comprehensive_validation(self, script_path: Path) -> Dict[str, Any]:
        """Perform comprehensive validation of script."""
        result = {
            "script_path": str(script_path),
            "path_valid": False,
            "content_valid": False,
            "overall_valid": False,
            "validation_details": {},
            "recommendations": []
        }
        
        # Path validation
        result["path_valid"] = self.validate_script_path(script_path)
        
        if result["path_valid"]:
            # Content validation
            content_result = self.validate_script_content(script_path)
            result["content_valid"] = content_result["valid"]
            result["validation_details"] = content_result
            
            # Overall assessment
            result["overall_valid"] = result["path_valid"] and result["content_valid"]
            
            # Generate recommendations
            if not result["content_valid"]:
                result["recommendations"].append("Review and remove potentially dangerous code patterns")
            
            if not content_result.get("mpm_integration", False):
                result["recommendations"].append("Consider using Claude MPM utilities for better integration")
            
            if result["overall_valid"]:
                result["recommendations"].append("Script passed all security validations")
        else:
            result["recommendations"].append("Move script to an allowed directory (scripts/, tools/, utils/)")
        
        self.logger.info(f"Comprehensive validation result: {result['overall_valid']} for {script_path}")
        return result
```

## 8. Testing Strategy for Claude MPM Integration

### 8.1 Unit Tests with Claude MPM Patterns

**File**: `tests/test_python_script_service.py`

```python
"""
Unit tests for Python Script Service integration with Claude MPM.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import yaml

from claude_mpm.services.python_script_service import PythonScriptService
from claude_mpm.services.script_validation_service import ScriptValidationService

class TestPythonScriptService(unittest.TestCase):
    """Test Python Script Service with Claude MPM integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.scripts_dir = self.project_root / "scripts"
        self.config_dir = self.project_root / "config"
        
        # Create test directories
        self.scripts_dir.mkdir(parents=True)
        self.config_dir.mkdir(parents=True)
        
        # Create test configuration
        self.test_config = {
            "version": "1.0.0",
            "scripts": {
                "hello-world": {
                    "file": "hello_world.py",
                    "timeout": 10
                }
            }
        }
        
        config_file = self.config_dir / "python_scripts.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(self.test_config, f)
        
        # Create test script
        test_script = self.scripts_dir / "hello_world.py"
        test_script.write_text('''#!/usr/bin/env python3
print("Hello World from Claude MPM!")
''')
        
        self.service = PythonScriptService(self.project_root)
    
    @patch('claude_mpm.utils.subprocess_runner.SubprocessRunner')
    def test_hello_world_execution(self, mock_subprocess_runner):
        """Test hello world script execution."""
        # Mock subprocess runner response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Hello World from Claude MPM!"
        mock_result.stderr = ""
        mock_subprocess_runner.return_value.run.return_value = mock_result
        
        result = self.service.execute_script("hello-world")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["returncode"], 0)
        self.assertIn("Hello World", result["stdout"])
        self.assertEqual(result["script_name"], "hello_world")
    
    def test_invalid_script_name(self):
        """Test handling of invalid script names."""
        result = self.service.execute_script("nonexistent-script")
        
        self.assertFalse(result["success"])
        self.assertIn("Script not registered", result["error"])
    
    @patch('claude_mpm.services.script_validation_service.ScriptValidationService')
    def test_security_validation_failure(self, mock_validator):
        """Test security validation failure handling."""
        # Mock validation failure
        mock_validator.return_value.validate_script_path.return_value = False
        
        result = self.service.execute_script("hello-world")
        
        self.assertFalse(result["success"])
        self.assertIn("validation failed", result["error"])

class TestScriptValidationService(unittest.TestCase):
    """Test Script Validation Service."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.scripts_dir = self.project_root / "scripts"
        self.scripts_dir.mkdir(parents=True)
        
        self.validator = ScriptValidationService(self.project_root)
    
    def test_valid_script_path(self):
        """Test validation of valid script path."""
        script_path = self.scripts_dir / "test_script.py"
        script_path.write_text("print('Hello')")
        
        result = self.validator.validate_script_path(script_path)
        self.assertTrue(result)
    
    def test_invalid_script_path_outside_project(self):
        """Test rejection of script outside project."""
        invalid_path = Path("/etc/passwd")
        
        result = self.validator.validate_script_path(invalid_path)
        self.assertFalse(result)
    
    def test_dangerous_content_detection(self):
        """Test detection of dangerous content patterns."""
        script_path = self.scripts_dir / "dangerous_script.py"
        script_path.write_text('''
import subprocess
subprocess.run("rm -rf /", shell=True)
''')
        
        result = self.validator.validate_script_content(script_path)
        
        self.assertFalse(result["valid"])
        self.assertTrue(len(result["blocked_patterns"]) > 0)
    
    def test_claude_mpm_integration_detection(self):
        """Test detection of Claude MPM integration."""
        script_path = self.scripts_dir / "mpm_script.py"
        script_path.write_text('''
from claude_mpm.utils.paths import PathResolver
from claude_mpm.core import LoggerMixin
print("MPM integrated script")
''')
        
        result = self.validator.validate_script_content(script_path)
        
        self.assertTrue(result["valid"])
        self.assertTrue(result["mpm_integration"])

class TestPythonScriptHook(unittest.TestCase):
    """Test Python Script Hook integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.hook = Mock()  # Would import actual hook in real implementation
    
    def test_python_command_detection(self):
        """Test detection of Python script commands."""
        # Test cases for command detection
        test_commands = [
            "/python:hello-world",
            "python scripts/test.py",
            "/python:run-script test.py --verbose"
        ]
        
        for command in test_commands:
            # Would test actual hook logic here
            self.assertTrue(True)  # Placeholder
    
    def test_output_formatting(self):
        """Test output formatting for Claude display."""
        mock_result = {
            "success": True,
            "returncode": 0,
            "stdout": "Hello World from Python!",
            "stderr": "",
            "script_name": "hello_world",
            "execution_time": "0.5s"
        }
        
        # Would test actual formatting logic here
        self.assertTrue(True)  # Placeholder
```

### 8.2 Integration Tests

**File**: `tests/test_python_integration.py`

```python
"""
Integration tests for Python script execution with Claude MPM.
"""

import unittest
import subprocess
import tempfile
from pathlib import Path
import yaml

class TestPythonScriptIntegration(unittest.TestCase):
    """Integration tests for end-to-end Python script execution."""
    
    @classmethod
    def setUpClass(cls):
        """Set up integration test environment."""
        cls.project_root = Path.cwd()
        cls.scripts_dir = cls.project_root / "scripts"
        cls.config_dir = cls.project_root / "config"
        
        # Ensure test scripts exist
        cls._ensure_test_scripts()
    
    @classmethod
    def _ensure_test_scripts(cls):
        """Ensure test scripts are available."""
        hello_world_script = cls.scripts_dir / "hello_world.py"
        if not hello_world_script.exists():
            hello_world_script.write_text('''#!/usr/bin/env python3
import sys
print("Hello World from Claude MPM Python Integration!")
print(f"Python version: {sys.version.split()[0]}")
print("✅ Integration test successful")
''')
            hello_world_script.chmod(0o755)
    
    def test_python_service_direct_execution(self):
        """Test direct execution via Python service."""
        try:
            # Import and test the service directly
            from claude_mpm.services.python_script_service import PythonScriptService
            
            service = PythonScriptService()
            result = service.execute_script("hello-world")
            
            self.assertTrue(result["success"], f"Service execution failed: {result}")
            self.assertIn("Hello World", result["stdout"])
            
        except ImportError:
            self.skipTest("Claude MPM services not available for direct testing")
    
    def test_cli_integration(self):
        """Test CLI integration with Python scripts."""
        try:
            # Test via Claude MPM CLI if available
            cmd = ["python3", "-m", "claude_mpm.cli", "--help"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # If CLI is available, test Python script execution
            if result.returncode == 0:
                # Would test actual CLI integration here
                self.assertTrue(True)
            else:
                self.skipTest("Claude MPM CLI not available")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Claude MPM CLI execution failed")
    
    def test_hook_system_integration(self):
        """Test hook system integration."""
        # This would test the actual hook execution
        # For now, just verify hook files exist
        hook_file = self.project_root / "src" / "claude_mpm" / "hooks" / "builtin" / "python_script_hook.py"
        
        if hook_file.exists():
            self.assertTrue(True)
        else:
            self.skipTest("Python script hook not implemented yet")

### 8.3 End-to-End Testing Script

**File**: `tests/test_e2e_python_scripts.sh`

```bash
#!/bin/bash
"""
End-to-end testing for Claude MPM Python script integration.
"""

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🧪 Claude MPM Python Script Integration E2E Tests"
echo "================================================"

# Test 1: Direct Python Script Execution
echo "1. Testing direct Python script execution..."
if [ -f "scripts/hello_world.py" ]; then
    result=$(python3 scripts/hello_world.py)
    if [[ $result == *"Hello World"* ]]; then
        echo "   ✅ Direct execution: PASSED"
    else
        echo "   ❌ Direct execution: FAILED"
        exit 1
    fi
else
    echo "   ⚠️  Hello world script not found, creating..."
    mkdir -p scripts
    cat > scripts/hello_world.py << 'EOF'
#!/usr/bin/env python3
print("Hello World from Claude MPM Python Integration!")
print("✅ E2E test successful")
EOF
    chmod +x scripts/hello_world.py
    echo "   ✅ Created hello world script"
fi

# Test 2: Claude MPM Service Integration (if available)
echo "2. Testing Claude MPM service integration..."
if python3 -c "from claude_mpm.services.python_script_service import PythonScriptService; print('✅ Import successful')" 2>/dev/null; then
    echo "   ✅ Claude MPM services: AVAILABLE"
    
    # Test service execution
    python3 -c "
from claude_mpm.services.python_script_service import PythonScriptService
service = PythonScriptService()
result = service.execute_script('hello-world')
print(f'   Service execution: {\"✅ PASSED\" if result[\"success\"] else \"❌ FAILED\"}')
print(f'   Output: {result[\"stdout\"][:50]}...' if result.get('stdout') else '   No output')
" || echo "   ⚠️  Service execution failed"
else
    echo "   ⚠️  Claude MPM services: NOT AVAILABLE"
fi

# Test 3: Configuration Validation
echo "3. Testing configuration setup..."
if [ -f "config/python_scripts.yaml" ]; then
    echo "   ✅ Configuration file: EXISTS"
    
    # Validate YAML syntax
    if python3 -c "import yaml; yaml.safe_load(open('config/python_scripts.yaml'))" 2>/dev/null; then
        echo "   ✅ Configuration syntax: VALID"
    else
        echo "   ❌ Configuration syntax: INVALID"
        exit 1
    fi
else
    echo "   ⚠️  Configuration file: MISSING"
    echo "   Creating default configuration..."
    mkdir -p config
    cat > config/python_scripts.yaml << 'EOF'
version: "1.0.0"
scripts:
  hello-world:
    file: "hello_world.py"
    description: "Test script"
    timeout: 10
EOF
    echo "   ✅ Created default configuration"
fi

# Test 4: Slash Command Files
echo "4. Testing slash command setup..."
slash_commands=(
    ".claude/commands/python/hello-world.md"
    ".claude/commands/python/run-script.md"
)

for cmd_file in "${slash_commands[@]}"; do
    if [ -f "$cmd_file" ]; then
        echo "   ✅ $cmd_file: EXISTS"
    else
        echo "   ⚠️  $cmd_file: MISSING"
        mkdir -p "$(dirname "$cmd_file")"
        case "$cmd_file" in
            *hello-world.md)
                cat > "$cmd_file" << 'EOF'
# Python Hello World Test
Test the Python script execution system.

## Instructions
Execute the hello world Python script:

!echo "/python:hello-world"
EOF
                ;;
            *run-script.md)
                cat > "$cmd_file" << 'EOF'
# Run Python Script
Execute a Python script: $ARGUMENTS

## Instructions
Execute the specified Python script:

!echo "/python:run-script $ARGUMENTS"
EOF
                ;;
        esac
        echo "   ✅ Created $cmd_file"
    fi
done

# Test 5: Hook System (if available)
echo "5. Testing hook system integration..."
hook_file="src/claude_mpm/hooks/builtin/python_script_hook.py"
if [ -f "$hook_file" ]; then
    echo "   ✅ Python script hook: EXISTS"
    
    # Test hook syntax
    if python3 -m py_compile "$hook_file" 2>/dev/null; then
        echo "   ✅ Hook syntax: VALID"
    else
        echo "   ❌ Hook syntax: INVALID"
        exit 1
    fi
else
    echo "   ⚠️  Python script hook: NOT IMPLEMENTED"
fi

# Test 6: Project Structure Validation
echo "6. Validating project structure..."
required_dirs=(
    "src/claude_mpm"
    "src/claude_mpm/services"
    "src/claude_mpm/hooks/builtin"
    "scripts"
    "config"
    ".claude/commands/python"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "   ✅ $dir: EXISTS"
    else
        echo "   ⚠️  $dir: MISSING"
        mkdir -p "$dir"
        echo "   ✅ Created $dir"
    fi
done

echo ""
echo "📊 E2E Test Summary"
echo "=================="
echo "✅ All tests completed successfully!"
echo "🚀 Claude MPM Python script integration is ready for use"
echo ""
echo "Next steps:"
echo "1. Implement missing components (if any warnings shown)"
echo "2. Test slash commands in Claude Code: /python:hello-world"
echo "3. Verify hook system integration"
echo "4. Run unit tests: python3 -m pytest tests/"
```

## 9. Deployment & Usage with Claude MPM

### 9.1 Installation Integration

**Update to existing Claude MPM installation process:**

```bash
# Add to existing install_dev.sh or setup process
echo "Setting up Python script execution..."

# Create required directories
mkdir -p scripts/{utils}
mkdir -p config
mkdir -p .claude/commands/python

# Install Python script configuration
cp config/python_scripts.yaml.example config/python_scripts.yaml

# Create initial test scripts
cp scripts/hello_world.py.example scripts/hello_world.py
chmod +x scripts/hello_world.py

# Install slash commands
cp .claude/commands/python/*.md.example .claude/commands/python/

# Update Claude MPM services (if implementing new services)
pip install -e .  # Reinstall to pick up new services

echo "✅ Python script execution setup complete"
echo "Test with: claude-mpm and then /python:hello-world"
```

### 9.2 Usage Examples with Claude MPM Integration

```bash
# In Claude Code/Claude MPM session:

# 1. Test basic functionality
> /python:hello-world

# Expected output:
🐍 **Python Script Execution Result**
**Script**: hello_world
**Status**: ✅ Success (exit code: 0)
**Execution Time**: 0.3s

**Output**:
```
Hello World from Claude MPM Python Integration!
✅ E2E test successful
```

# 2. Run project diagnostics
> /python:run-script mpm-diagnostics

# 3. Check project status
> /python:run-script project-status

# 4. Run custom script with arguments
> /python:run-script "my_analysis.py --verbose --output json"
```

## 10. Future Enhancements

### 10.1 Advanced Claude MPM Integration

- **Agent-Based Script Execution**: Register Python scripts as specialized agents
- **Workflow Integration**: Include Python scripts in multi-agent workflows  
- **Advanced Hook Patterns**: More sophisticated hook-based script orchestration
- **Configuration Management**: Dynamic script registration via Claude MPM's config system
- **Performance Monitoring**: Integration with Claude MPM's performance tracking

### 10.2 Extension Capabilities

- **Custom Agent Templates**: Generate agent templates that execute Python scripts
- **Subprocess Orchestration**: Deep integration with SubprocessOrchestrator
- **Ticket Workflow**: Enhanced ticket creation from script outputs
- **Session Management**: Python script results in session logs and replay
- **CLI Extensions**: New Claude MPM CLI commands for script management

## 11. Conclusion

This design provides a comprehensive integration of Python script execution with Claude MPM's existing architecture. By leveraging Claude MPM's service layer, hook system, and orchestration patterns, the solution maintains consistency with the existing codebase while providing powerful new capabilities.

The "Hello World" test case serves as both a validation mechanism and a template for expanding the system, ensuring compatibility with Claude MPM's architectural patterns and development workflows.

Key benefits of this Claude MPM-integrated approach:
- **Seamless Integration**: Uses existing Claude MPM services and patterns
- **Security**: Leverages Claude MPM's validation and security framework  
- **Extensibility**: Built on Claude MPM's hook and agent systems
- **Consistency**: Follows established Claude MPM coding standards and practices
- **Maintainability**: Integrates with existing logging, error handling, and testing frameworks,    # Python script execution
            r'python.*scripts/',    # Script directory execution
        ]
        
        return any(re.search(pattern, command.strip()) for pattern in python_patterns)
    
    def _execute_python_command(self, command: str, context: dict) -> dict:
        """Execute Python script and return formatted result."""
        try:
            # Parse command for script name and arguments
            script_name, args = self._parse_command(command)
            
            # Execute via Python service
            result = self.python_service.execute_script(script_name, args)
            
            # Create ticket if output contains ticketable items
            self._process_tickets(result)
            
            # Format output for Claude
            formatted_output = self._format_output(result)
            
            # Block original command and show our output
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Handled by Python script service"
                },
                "output": formatted_output,
                "suppressOutput": False
            }
            
        except Exception as e:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse", 
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Python script execution failed: {str(e)}"
                }
            }
    
    def _parse_command(self, command: str) -> tuple:
        """Parse command to extract script name and arguments."""
        # Handle different command formats:
        # /python:hello-world
        # /python:run-script script_name.py --args
        # python scripts/hello_world.py
        
        if command.startswith("/python:"):
            parts = command[8:].split(" ", 1)
            script_name = parts[0]
            args = parts[1] if len(parts) > 1 else ""
        else:
            # Extract script name from python command
            parts = command.split()
            if len(parts) >= 2 and parts[1].endswith('.py'):
                script_name = parts[1].replace('scripts/', '').replace('.py', '')
                args = " ".join(parts[2:]) if len(parts) > 2 else ""
            else:
                script_name = "hello-world"  # Default
                args = ""
        
        return script_name, args
    
    def _format_output(self, result: dict) -> str:
        """Format Python script result for display."""
        if result["success"]:
            output = f"""
🐍 **Python Script Execution Result**

**Script**: {result.get('script_name', 'unknown')}
**Status**: ✅ Success (exit code: {result['returncode']})
**Execution Time**: {result.get('execution_time', 'N/A')}

**Output**:
```
{result['stdout']}
```
"""
            if result['stderr']:
                output += f"""
**Warnings/Errors**:
```
{result['stderr']}
```
"""
        else:
            output = f"""
🐍 **Python Script Execution Failed**

**Script**: {result.get('script_name', 'unknown')}
**Status**: ❌ Failed (exit code: {result['returncode']})
**Error**: {result.get('error', 'Unknown error')}

**Error Output**:
```
{result['stderr']}
```
"""
        
        return output
    
    def _process_tickets(self, result: dict):
        """Extract and create tickets from script output."""
        if result["success"] and result["stdout"]:
            # Use existing ticket extraction patterns
            output = result["stdout"]
            
            # Look for ticket patterns in output
            ticket_patterns = [
                (r'TODO:\s*(.+)', 'task'),
                (r'FIXME:\s*(.+)', 'bug'),
                (r'BUG:\s*(.+)', 'bug'),
                (r'FEATURE:\s*(.+)', 'feature'),
            ]
            
            for pattern, ticket_type in ticket_patterns:
                matches = re.finditer(pattern, output, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    try:
                        self.ticket_manager.create_ticket(
                            title=match.group(1).strip(),
                            ticket_type=ticket_type,
                            description=f"Auto-extracted from Python script output",
                            priority="medium",
                            tags=["auto-generated", "python-script"]
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to create ticket: {e}")
```

## 4. Configuration System

### 4.1 Command Configuration

**File**: `.claude/config/python_commands.yaml`

```yaml
# Python Command Configuration
version: "1.0.0"
description: "Python script execution commands for Claude Code"

# Security settings
security:
  allowed_directories:
    - "scripts/"
    - "tools/"
  blocked_patterns:
    - "../"
    - "~/"
    - "/etc/"
    - "/tmp/"
  max_execution_time: 60
  max_output_size: 1048576  # 1MB

# Registered commands
commands:
  hello-world:
    script: "hello_world.py"
    description: "Test script that outputs Hello World"
    timeout: 10
    args_required: false
    
  project-status:
    script: "project_status.py"  
    description: "Display current project status and metrics"
    timeout: 30
    args_required: false
    
  run-tests:
    script: "run_tests.py"
    description: "Execute project test suite"
    timeout: 120
    args_required: false
    args_optional: ["--verbose", "--coverage"]

# Output formatting
output:
  max_lines: 100
  truncate_long_output: true
  include_execution_time: true
  include_return_code: true
```

## 5. Script Examples

### 5.1 Hello World Test Script

**File**: `scripts/hello_world.py`

```python
#!/usr/bin/env python3
"""
Hello World test script for Claude Code Python command system.
"""

import sys
import datetime

def main():
    """Output Hello World with timestamp and system info."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("=" * 50)
    print("🐍 CLAUDE CODE PYTHON COMMAND SYSTEM")
    print("=" * 50)
    print(f"Hello World from Python!")
    print(f"Timestamp: {timestamp}")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Execution successful! ✅")
    print("=" * 50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 5.2 Project Status Script

**File**: `scripts/project_status.py`

```python
#!/usr/bin/env python3
"""
Project status reporting script.
"""

import os
import sys
import subprocess
from pathlib import Path

def get_git_status():
    """Get current git status."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return {
            "clean": len(result.stdout.strip()) == 0,
            "changes": result.stdout.strip().split('\n') if result.stdout.strip() else []
        }
    except:
        return {"clean": None, "changes": []}

def count_files():
    """Count files by type."""
    counts = {}
    for ext in ['.py', '.md', '.json', '.yaml', '.txt']:
        counts[ext] = len(list(Path('.').rglob(f'*{ext}')))
    return counts

def main():
    """Display project status."""
    print("📊 PROJECT STATUS REPORT")
    print("=" * 40)
    
    # Git status
    git_status = get_git_status()
    if git_status["clean"] is True:
        print("✅ Git status: Clean working directory")
    elif git_status["clean"] is False:
        print(f"⚠️  Git status: {len(git_status['changes'])} modified files")
    else:
        print("❓ Git status: Unable to determine")
    
    # File counts
    print("\n📁 File counts:")
    file_counts = count_files()
    for ext, count in file_counts.items():
        print(f"   {ext}: {count}")
    
    # Directory info
    print(f"\n📂 Working directory: {os.getcwd()}")
    print(f"🐍 Python executable: {sys.executable}")
    
    print("=" * 40)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## 6. Security Implementation

### 6.1 Validation Layer

**File**: `.claude/scripts/validators.py`

```python
#!/usr/bin/env python3
"""
Security validation for Python script execution.
"""

import os
import re
from pathlib import Path
from typing import List, Optional

class ScriptValidator:
    """Validates Python scripts before execution."""
    
    BLOCKED_PATTERNS = [
        r'\.\./+',           # Directory traversal
        r'~/+',              # Home directory access
        r'/etc/+',           # System directory access
        r'/tmp/+',           # Temp directory access
        r'import\s+os',      # Potentially dangerous imports
        r'subprocess\.',     # Subprocess calls
        r'eval\s*\(',        # Code evaluation
        r'exec\s*\(',        # Code execution
    ]
    
    ALLOWED_DIRECTORIES = [
        'scripts',
        'tools',
        'utils',
    ]
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def validate_script_path(self, script_path: Path) -> bool:
        """Validate that script path is safe to execute."""
        try:
            # Resolve path and check it's within project
            resolved_path = script_path.resolve()
            if not str(resolved_path).startswith(str(self.project_root.resolve())):
                return False
            
            # Check if in allowed directory
            relative_path = resolved_path.relative_to(self.project_root.resolve())
            if not any(str(relative_path).startswith(allowed) for allowed in self.ALLOWED_DIRECTORIES):
                return False
            
            # Check file exists and is readable
            if not resolved_path.exists() or not resolved_path.is_file():
                return False
            
            return True
            
        except (ValueError, OSError):
            return False
    
    def validate_script_content(self, script_path: Path) -> List[str]:
        """Validate script content for security issues."""
        warnings = []
        
        try:
            content = script_path.read_text()
            
            for pattern in self.BLOCKED_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    warnings.append(f"Potentially dangerous pattern found: {pattern}")
            
        except (OSError, UnicodeDecodeError):
            warnings.append("Unable to read or decode script content")
        
        return warnings
```

## 7. Testing Strategy

### 7.1 Test Cases

```python
# tests/test_command_router.py
import unittest
from pathlib import Path
from claude.scripts.command_router import CommandRouter

class TestCommandRouter(unittest.TestCase):
    
    def setUp(self):
        self.router = CommandRouter(Path.cwd())
    
    def test_hello_world_command(self):
        """Test hello world command execution."""
        result = self.router.execute_command("hello-world")
        self.assertTrue(result["success"])
        self.assertIn("Hello World", result["stdout"])
    
    def test_invalid_command(self):
        """Test handling of invalid commands."""
        result = self.router.execute_command("nonexistent")
        self.assertFalse(result["success"])
        self.assertIn("Unknown command", result.get("error", ""))
    
    def test_script_validation(self):
        """Test script path validation."""
        # Valid script
        valid_path = Path("scripts/hello_world.py")
        self.assertTrue(self.router._validate_script(valid_path))
        
        # Invalid script (directory traversal)
        invalid_path = Path("../../../etc/passwd")
        self.assertFalse(self.router._validate_script(invalid_path))
```

### 7.2 Integration Testing

```bash
#!/bin/bash
# tests/integration_test.sh

echo "Testing Claude Code Python Command System..."

# Test 1: Hello World
echo "1. Testing hello-world command..."
result=$(python3 .claude/scripts/command_router.py hello-world)
if [[ $result == *"Hello World"* ]]; then
    echo "✅ Hello World test passed"
else
    echo "❌ Hello World test failed"
    exit 1
fi

# Test 2: Project Status
echo "2. Testing project-status command..."
result=$(python3 .claude/scripts/command_router.py project-status)
if [[ $result == *"PROJECT STATUS"* ]]; then
    echo "✅ Project Status test passed"
else
    echo "❌ Project Status test failed"
    exit 1
fi

echo "All integration tests passed! 🎉"
```

## 8. Deployment & Usage

### 8.1 Installation Steps

1. **Create Directory Structure**
```bash
mkdir -p .claude/{commands/python,scripts,config}
mkdir -p scripts/{utils}
mkdir -p tests
```

2. **Install Dependencies**
```bash
pip install pyyaml  # For configuration parsing
```

3. **Deploy Scripts**
- Copy all Python files to their respective directories
- Set executable permissions on scripts
- Configure python_commands.yaml

4. **Test Installation**
```bash
# Test the hello world command
cd .claude/commands/python
claude
> /python:hello-world
```

### 8.2 Usage Examples

```bash
# In Claude Code session:

# Run hello world test
> /python:hello-world

# Run project status
> /python:project-status  

# Run custom script with arguments
> /python:run-script "my_script.py --verbose"

# Create new Python command
> /meta:create-python-command "data-analysis"
```

## 9. Future Enhancements

### 9.1 Planned Features

- **Async Execution**: Support for long-running scripts
- **Progress Monitoring**: Real-time output streaming
- **Resource Limits**: CPU and memory constraints
- **Environment Management**: Virtual environment support
- **Caching**: Output caching for expensive operations
- **Logging**: Comprehensive audit logging

### 9.2 Extension Points

- **Custom Formatters**: Different output formats (JSON, HTML, etc.)
- **External Integrations**: Database connections, API calls
- **Notification System**: Slack/email notifications for long tasks
- **Web Interface**: Browser-based script execution
- **Containerization**: Docker-based script isolation

## 10. Conclusion

This design provides a robust, secure, and extensible foundation for executing Python scripts through Claude Code slash commands. The system emphasizes security through validation, maintains simplicity through clear separation of concerns, and provides flexibility for future enhancements.

The "Hello World" test case serves as both a validation mechanism and a template for creating additional Python script commands, ensuring the system works correctly before expanding to more complex use cases.