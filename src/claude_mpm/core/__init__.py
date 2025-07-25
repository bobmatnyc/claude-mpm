"""Core components for Claude MPM."""

from .agent_registry import AgentRegistryAdapter
# Alias for backward compatibility
AgentRegistry = AgentRegistryAdapter
from .framework_loader import FrameworkLoader
from .claude_launcher import ClaudeLauncher, LaunchMode
from .mixins import LoggerMixin

# Import config components if needed
try:
    from .config import Config
    from .config_aliases import ConfigAliases
except ImportError:
    pass

__all__ = [
    "AgentRegistryAdapter",
    "AgentRegistry",  # Alias for AgentRegistryAdapter
    "FrameworkLoader",
    "ClaudeLauncher",
    "LaunchMode",
    "LoggerMixin",
    "validate_core_system",
]


def validate_core_system():
    """Validate core system health and configuration."""
    import sys
    from pathlib import Path
    
    try:
        # Check if we can import core components
        from . import ClaudeLauncher, AgentRegistry, FrameworkLoader
        
        # Check framework path
        framework_path = Path(__file__).parent.parent.parent.parent
        if not framework_path.exists():
            print("❌ Framework path not found")
            return False
        
        # Check if agents directory exists
        agents_dir = framework_path / "src" / "claude_mpm" / "agents"
        if not agents_dir.exists():
            print("❌ Agents directory not found")
            return False
        
        # Try to initialize core components
        try:
            launcher = ClaudeLauncher()
            print("✅ ClaudeLauncher initialized successfully")
        except Exception as e:
            print(f"❌ ClaudeLauncher initialization failed: {e}")
            return False
        
        try:
            registry = AgentRegistry()
            agents = registry.list_agents()
            print(f"✅ AgentRegistry found {len(agents)} agents")
        except Exception as e:
            print(f"❌ AgentRegistry initialization failed: {e}")
            return False
        
        print("✅ Core system validation passed")
        return True
        
    except ImportError as e:
        print(f"❌ Core system import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Core system validation error: {e}")
        return False