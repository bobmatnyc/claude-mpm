# CLI Structure Documentation

## CLI Architecture Overview

Claude MPM's CLI follows a modular command pattern:
- **Parsers** define argument structure
- **Commands** implement functionality
- **Shared utilities** reduce duplication
- **Interactive wizards** for complex workflows

## CLI Directory Structure

```
src/claude_mpm/cli/
├── __init__.py              # CLI package init
├── __main__.py              # Entry point
├── parser.py                # Main argument parser
├── executor.py              # Command execution
├── startup.py               # Initialization
├── startup_display.py       # Startup UI
├── startup_logging.py       # Logging setup
├── helpers.py               # Common helpers
├── utils.py                 # Utility functions
├── commands/                # Command implementations
│   ├── __init__.py
│   ├── agents.py            # Agent management
│   ├── analyze.py           # Code analysis
│   ├── config.py            # Configuration
│   ├── configure.py         # Interactive config
│   ├── dashboard.py         # Dashboard control
│   ├── debug.py             # Debug utilities
│   ├── doctor.py            # Diagnostics
│   ├── mcp.py               # MCP gateway
│   ├── memory.py            # Memory management
│   ├── monitor.py           # Monitoring
│   ├── run.py               # Interactive mode
│   ├── search.py            # Code search
│   ├── skills.py            # Skills management
│   ├── tickets.py           # Ticketing
│   └── ...
├── parsers/                 # Argument parsers
│   ├── __init__.py
│   ├── base_parser.py       # Base parser class
│   ├── agents_parser.py
│   ├── config_parser.py
│   ├── run_parser.py
│   └── ...
├── shared/                  # Shared utilities
│   ├── __init__.py
│   ├── argument_patterns.py # Reusable arguments
│   ├── base_command.py      # Base command class
│   ├── error_handling.py    # Error patterns
│   └── output_formatters.py # Output formatting
└── interactive/             # Interactive wizards
    ├── __init__.py
    ├── agent_wizard.py
    └── skills_wizard.py
```

## Entry Point Flow

```
bin/claude-mpm (entry script)
    │
    └── cli/__main__.py:main()
        │
        ├── cli/startup.py:initialize_startup()
        │   ├── Setup logging
        │   ├── Initialize container
        │   └── Load configuration
        │
        ├── cli/parser.py:create_parser()
        │   └── Add subcommand parsers
        │
        └── cli/executor.py:execute_command(args)
            └── Route to specific command handler
```

## Command Pattern

### Base Command Class
```python
# cli/shared/base_command.py
class BaseCommand(ABC):
    """Base class for all CLI commands"""
    
    def __init__(self, container: DIContainer):
        self.container = container
        self.console = Console()
    
    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the command, return exit code"""
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get service from container"""
        return self.container.get(service_type)
    
    def print_success(self, message: str) -> None:
        """Print success message"""
        self.console.print(f"[green]✓[/green] {message}")
    
    def print_error(self, message: str) -> None:
        """Print error message"""
        self.console.print(f"[red]✗[/red] {message}")
```

### Example Command Implementation
```python
# cli/commands/agents.py
from cli.shared.base_command import BaseCommand

class AgentsCommand(BaseCommand):
    """Manage agents"""
    
    def execute(self, args: argparse.Namespace) -> int:
        if args.subcommand == "list":
            return self.list_agents(args)
        elif args.subcommand == "deploy":
            return self.deploy_agents(args)
        return 0
    
    def list_agents(self, args: argparse.Namespace) -> int:
        registry = self.get_service(IAgentRegistry)
        agents = registry.list_agents()
        self.print_table(agents)
        return 0
    
    def deploy_agents(self, args: argparse.Namespace) -> int:
        deployment = self.get_service(AgentDeploymentInterface)
        result = deployment.deploy_agents(force=args.force)
        if result["success"]:
            self.print_success(f"Deployed {result['count']} agents")
            return 0
        self.print_error(result["error"])
        return 1
```

## Parser Pattern

### Base Parser
```python
# cli/parsers/base_parser.py
class BaseParser:
    """Base class for argument parsers"""
    
    @staticmethod
    def add_common_args(parser: argparse.ArgumentParser) -> None:
        """Add common arguments"""
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Verbose output"
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON"
        )
```

### Example Parser
```python
# cli/parsers/agents_parser.py
from cli.parsers.base_parser import BaseParser
from cli.shared.argument_patterns import add_force_arg

def setup_agents_parser(subparsers) -> None:
    """Setup agents command parser"""
    parser = subparsers.add_parser(
        "agents",
        help="Manage agents"
    )
    BaseParser.add_common_args(parser)
    
    # Subcommands
    agent_subs = parser.add_subparsers(dest="subcommand")
    
    # List command
    list_parser = agent_subs.add_parser("list", help="List agents")
    list_parser.add_argument("--tier", choices=["project", "user", "system"])
    list_parser.add_argument("--type", help="Filter by agent type")
    
    # Deploy command
    deploy_parser = agent_subs.add_parser("deploy", help="Deploy agents")
    add_force_arg(deploy_parser)
    deploy_parser.add_argument("agent_name", nargs="?", help="Specific agent")
```

## Shared Utilities

### Argument Patterns
```python
# cli/shared/argument_patterns.py

def add_force_arg(parser: argparse.ArgumentParser) -> None:
    """Add --force argument"""
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force operation"
    )

def add_output_format_arg(parser: argparse.ArgumentParser) -> None:
    """Add output format arguments"""
    parser.add_argument(
        "--format",
        choices=["table", "json", "yaml"],
        default="table",
        help="Output format"
    )

def add_filter_args(parser: argparse.ArgumentParser) -> None:
    """Add common filter arguments"""
    parser.add_argument("--status", help="Filter by status")
    parser.add_argument("--type", help="Filter by type")
    parser.add_argument("--since", help="Filter by date")
```

### Output Formatters
```python
# cli/shared/output_formatters.py
from rich.console import Console
from rich.table import Table

class OutputFormatter:
    """Format command output"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
    
    def print_table(
        self,
        data: List[Dict],
        columns: List[str],
        title: str = None
    ) -> None:
        """Print data as table"""
        table = Table(title=title)
        for col in columns:
            table.add_column(col)
        for row in data:
            table.add_row(*[str(row.get(c, "")) for c in columns])
        self.console.print(table)
    
    def print_json(self, data: Any) -> None:
        """Print data as JSON"""
        import json
        self.console.print(json.dumps(data, indent=2))
    
    def print_yaml(self, data: Any) -> None:
        """Print data as YAML"""
        import yaml
        self.console.print(yaml.dump(data))
```

### Error Handling
```python
# cli/shared/error_handling.py
from functools import wraps

def handle_errors(func):
    """Decorator for command error handling"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled[/yellow]")
            return 130
        except ServiceNotFoundError as e:
            console.print(f"[red]Service error:[/red] {e}")
            return 1
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            if verbose:
                console.print_exception()
            return 1
    return wrapper
```

## Interactive Wizards

### Agent Wizard
```python
# cli/interactive/agent_wizard.py
from rich.prompt import Prompt, Confirm

class AgentWizard:
    """Interactive agent configuration wizard"""
    
    def run(self) -> Dict[str, Any]:
        """Run the wizard"""
        self.console.print("[bold]Agent Configuration Wizard[/bold]\n")
        
        name = Prompt.ask("Agent name")
        agent_type = Prompt.ask(
            "Agent type",
            choices=["engineer", "qa", "ops", "custom"],
            default="engineer"
        )
        
        capabilities = []
        while True:
            cap = Prompt.ask("Add capability (empty to finish)")
            if not cap:
                break
            capabilities.append(cap)
        
        if Confirm.ask("Create agent?"):
            return {
                "name": name,
                "type": agent_type,
                "capabilities": capabilities
            }
        return None
```

### Skills Wizard
```python
# cli/interactive/skills_wizard.py
class SkillsWizard:
    """Interactive skills management wizard"""
    
    def run(self) -> None:
        """Run the wizard"""
        self.console.print("[bold]Skills Management[/bold]\n")
        
        choice = Prompt.ask(
            "Action",
            choices=["list", "enable", "disable", "auto-link", "exit"]
        )
        
        if choice == "list":
            self.list_skills()
        elif choice == "enable":
            self.enable_skill()
        # ...
```

## Command Reference

### Core Commands
| Command | Handler | Description |
|---------|---------|-------------|
| `run` | `commands/run.py` | Start interactive session |
| `agents` | `commands/agents.py` | Agent management |
| `skills` | `commands/skills.py` | Skills management |
| `config` | `commands/config.py` | Configuration |
| `doctor` | `commands/doctor.py` | Diagnostics |
| `monitor` | `commands/monitor.py` | Dashboard |

### Agent Commands
```bash
claude-mpm agents list              # List all agents
claude-mpm agents deploy            # Deploy all agents
claude-mpm agents deploy <name>     # Deploy specific agent
claude-mpm agents status <name>     # Check agent status
claude-mpm agents remove <name>     # Remove agent
```

### Skills Commands
```bash
claude-mpm skills list              # List available skills
claude-mpm skills enable <skill>    # Enable skill
claude-mpm skills disable <skill>   # Disable skill
claude-mpm skills deploy-github     # Deploy from GitHub
```

### Memory Commands
```bash
claude-mpm memory list              # List memories
claude-mpm memory show <agent>      # Show agent memory
claude-mpm memory clear <agent>     # Clear memory
claude-mpm memory optimize          # Optimize all
```

### MCP Commands
```bash
claude-mpm mcp start                # Start MCP gateway
claude-mpm mcp stop                 # Stop MCP gateway
claude-mpm mcp status               # Check status
claude-mpm mcp tools                # List tools
```

## Adding New Commands

### 1. Create Parser
```python
# cli/parsers/mycommand_parser.py
def setup_mycommand_parser(subparsers) -> None:
    parser = subparsers.add_parser("mycommand", help="My command")
    parser.add_argument("--option", help="An option")
```

### 2. Create Command
```python
# cli/commands/mycommand.py
from cli.shared.base_command import BaseCommand

class MyCommand(BaseCommand):
    def execute(self, args) -> int:
        # Implementation
        return 0
```

### 3. Register in Parser
```python
# cli/parser.py
from cli.parsers.mycommand_parser import setup_mycommand_parser

def create_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    setup_mycommand_parser(subparsers)
    # ...
```

### 4. Register in Executor
```python
# cli/executor.py
from cli.commands.mycommand import MyCommand

COMMAND_MAP = {
    "mycommand": MyCommand,
    # ...
}
```

## CLI Configuration

### Environment Variables
```bash
CLAUDE_MPM_DEBUG=1          # Enable debug mode
CLAUDE_MPM_LOG_LEVEL=DEBUG  # Set log level
CLAUDE_MPM_NO_COLOR=1       # Disable colors
CLAUDE_MPM_CONFIG=path      # Custom config path
```

### Configuration File
```yaml
# .claude-mpm/configuration.yaml
cli:
  default_output_format: table
  color_enabled: true
  verbose: false
  confirm_destructive: true
```

---
See also:
- [CODE-PATHS.md](CODE-PATHS.md) for execution flows
- [SERVICE-LAYER.md](SERVICE-LAYER.md) for service integration
