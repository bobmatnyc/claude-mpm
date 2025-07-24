# Claude PM Framework - Tool Calling Implementation
# Complete implementation for Claude tool calling with subprocess orchestration

import subprocess
import json
import os
import time
import threading
import psutil
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import base64
from datetime import datetime
import uuid

# ==============================================================================
# Tool Definitions - JSON Schema for Claude
# ==============================================================================

CLAUDE_PM_TOOLS = [
    {
        "name": "execute_agent_subprocess",
        "description": "Execute a specialized agent in a controlled subprocess with memory monitoring",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "description": "Type of agent to execute",
                    "enum": [
                        "documentation", "qa", "security", "engineer", "ops", 
                        "versioner", "researcher", "data_engineer", "ticketer"
                    ]
                },
                "task_description": {
                    "type": "string",
                    "description": "Detailed description of the task for the agent"
                },
                "context": {
                    "type": "object",
                    "description": "Context and environment variables for the subprocess",
                    "properties": {
                        "project_root": {"type": "string"},
                        "file_paths": {"type": "array", "items": {"type": "string"}},
                        "user_requirements": {"type": "string"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high"]}
                    }
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds",
                    "default": 300
                },
                "memory_limit": {
                    "type": "integer", 
                    "description": "Memory limit in MB",
                    "default": 1024
                }
            },
            "required": ["agent_type", "task_description"]
        }
    },
    {
        "name": "discover_available_agents",
        "description": "Discover all available agents in the registry with their capabilities",
        "parameters": {
            "type": "object",
            "properties": {
                "specialization": {
                    "type": "string",
                    "description": "Filter by specialization (optional)"
                },
                "include_custom": {
                    "type": "boolean",
                    "description": "Include custom user agents",
                    "default": True
                }
            }
        }
    },
    {
        "name": "coordinate_multi_agent_workflow",
        "description": "Coordinate multiple agents for complex tasks",
        "parameters": {
            "type": "object",
            "properties": {
                "workflow_description": {
                    "type": "string",
                    "description": "Description of the overall workflow"
                },
                "agent_tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "agent_type": {"type": "string"},
                            "task": {"type": "string"},
                            "dependencies": {"type": "array", "items": {"type": "string"}},
                            "priority": {"type": "integer"}
                        }
                    }
                },
                "coordination_mode": {
                    "type": "string",
                    "enum": ["sequential", "parallel", "hybrid"],
                    "default": "hybrid"
                }
            },
            "required": ["workflow_description", "agent_tasks"]
        }
    },
    {
        "name": "create_tickets_from_output",
        "description": "Parse agent output and create tickets automatically",
        "parameters": {
            "type": "object",
            "properties": {
                "output_text": {
                    "type": "string",
                    "description": "Agent output to parse for ticket creation"
                },
                "source_agent": {
                    "type": "string",
                    "description": "Agent that generated the output"
                },
                "auto_create": {
                    "type": "boolean",
                    "description": "Automatically create tickets without confirmation",
                    "default": False
                }
            },
            "required": ["output_text", "source_agent"]
        }
    }
]

# ==============================================================================
# Core Data Structures
# ==============================================================================

@dataclass
class AgentExecutionResult:
    success: bool
    agent_type: str
    task_description: str
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    memory_usage: Dict[str, int]
    tickets_created: List[str]
    error: Optional[str] = None

@dataclass
class WorkflowTask:
    id: str
    agent_type: str
    task: str
    dependencies: List[str]
    priority: int
    status: str = "pending"
    result: Optional[AgentExecutionResult] = None

class ProcessStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    MEMORY_EXCEEDED = "memory_exceeded"

# ==============================================================================
# Memory Monitoring (from v1.3.0 features)
# ==============================================================================

class MemoryMonitor:
    def __init__(self, warning_threshold_mb: int = 1024, 
                 critical_threshold_mb: int = 2048, 
                 hard_limit_mb: int = 4096):
        self.warning_threshold = warning_threshold_mb * 1024 * 1024
        self.critical_threshold = critical_threshold_mb * 1024 * 1024
        self.hard_limit = hard_limit_mb * 1024 * 1024
        self.monitoring = False
        
    def start_monitoring(self, process: subprocess.Popen) -> threading.Thread:
        """Start memory monitoring in separate thread"""
        self.monitoring = True
        
        def monitor():
            try:
                ps_process = psutil.Process(process.pid)
                while self.monitoring and process.poll() is None:
                    memory_info = ps_process.memory_info()
                    rss = memory_info.rss
                    
                    if rss > self.hard_limit:
                        print(f"HARD LIMIT: Process {process.pid} exceeded {self.hard_limit/1024/1024}MB")
                        process.terminate()
                        break
                    elif rss > self.critical_threshold:
                        print(f"CRITICAL: Process {process.pid} using {rss/1024/1024}MB")
                    elif rss > self.warning_threshold:
                        print(f"WARNING: Process {process.pid} using {rss/1024/1024}MB")
                    
                    time.sleep(2)  # Check every 2 seconds
            except psutil.NoSuchProcess:
                pass
                
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        return thread
        
    def stop_monitoring(self):
        self.monitoring = False
        
    def get_memory_usage(self, process: subprocess.Popen) -> Dict[str, int]:
        """Get current memory usage statistics"""
        try:
            ps_process = psutil.Process(process.pid)
            memory_info = ps_process.memory_info()
            return {
                "rss_mb": memory_info.rss // (1024 * 1024),
                "vms_mb": memory_info.vms // (1024 * 1024),
                "percent": ps_process.memory_percent()
            }
        except psutil.NoSuchProcess:
            return {"rss_mb": 0, "vms_mb": 0, "percent": 0.0}

# ==============================================================================
# Process Manager (Orchestration Core)
# ==============================================================================

class ProcessManager:
    def __init__(self):
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.memory_monitors: Dict[str, MemoryMonitor] = {}
        
    def create_process(self, command: List[str], env: Dict[str, str], 
                      memory_limit_mb: int = 1024, timeout: int = 300) -> Tuple[str, subprocess.Popen]:
        """Create and return managed subprocess with memory monitoring"""
        
        process_id = str(uuid.uuid4())
        
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Start memory monitoring
            memory_monitor = MemoryMonitor(
                warning_threshold_mb=memory_limit_mb // 2,
                critical_threshold_mb=memory_limit_mb,
                hard_limit_mb=memory_limit_mb * 2
            )
            
            self.active_processes[process_id] = process
            self.memory_monitors[process_id] = memory_monitor
            memory_monitor.start_monitoring(process)
            
            return process_id, process
            
        except Exception as e:
            raise RuntimeError(f"Failed to create process: {e}")
    
    def communicate_with_process(self, process_id: str, input_data: str = "", 
                               timeout: int = 300) -> Tuple[str, str, Dict[str, int]]:
        """Communicate with process and return stdout, stderr, memory_usage"""
        
        if process_id not in self.active_processes:
            raise ValueError(f"Process {process_id} not found")
            
        process = self.active_processes[process_id]
        memory_monitor = self.memory_monitors[process_id]
        
        try:
            stdout, stderr = process.communicate(input=input_data, timeout=timeout)
            memory_usage = memory_monitor.get_memory_usage(process)
            return stdout, stderr, memory_usage
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise
        finally:
            memory_monitor.stop_monitoring()
            if process_id in self.active_processes:
                del self.active_processes[process_id]
            if process_id in self.memory_monitors:
                del self.memory_monitors[process_id]

# ==============================================================================
# Context Manager (Environment Preparation)
# ==============================================================================

class ContextManager:
    def __init__(self, framework_context: Dict[str, Any]):
        self.framework_context = framework_context
        
    def prepare_environment(self, agent_context: Dict[str, Any]) -> Dict[str, str]:
        """Prepare environment variables for orchestrated execution"""
        env = os.environ.copy()
        
        # Add orchestration markers
        env.update({
            'CLAUDE_PM_ORCHESTRATED': 'true',
            'CLAUDE_PM_SESSION_ID': str(uuid.uuid4()),
            'CLAUDE_PM_FRAMEWORK_VERSION': '1.4.0',
            'CLAUDE_PM_PROJECT_ROOT': agent_context.get('project_root', os.getcwd()),
            'CLAUDE_PM_LOG_LEVEL': 'INFO',
            'CLAUDE_PM_TICKET_AUTO_CREATE': 'true'
        })
        
        # Serialize complex context
        context_data = {**self.framework_context, **agent_context}
        env['CLAUDE_PM_CONTEXT'] = base64.b64encode(
            json.dumps(context_data).encode()
        ).decode()
        
        return env
        
    def filter_context_for_agent(self, context: Dict, agent_type: str) -> Dict:
        """Filter context based on agent specialization"""
        
        agent_context_rules = {
            'security': ['security_config', 'vulnerability_data', 'compliance_requirements', 'file_paths'],
            'qa': ['test_config', 'coverage_data', 'quality_metrics', 'file_paths'],
            'documentation': ['doc_config', 'api_schemas', 'user_guides', 'file_paths'],
            'engineer': ['code_config', 'build_config', 'dependencies', 'file_paths'],
            'ops': ['deployment_config', 'infrastructure', 'monitoring', 'file_paths'],
            'versioner': ['git_config', 'branch_strategy', 'release_config'],
            'researcher': ['research_sources', 'analysis_config', 'data_sources'],
            'data_engineer': ['data_config', 'pipeline_config', 'storage_config'],
            'ticketer': ['ticket_config', 'workflow_config', 'integration_config']
        }
        
        relevant_keys = agent_context_rules.get(agent_type, []) + ['project_root', 'user_requirements', 'priority']
        return {k: v for k, v in context.items() if k in relevant_keys}

# ==============================================================================
# Agent Registry Integration
# ==============================================================================

class AgentRegistry:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    def discover_agents(self, specialization: str = None, include_custom: bool = True) -> List[Dict[str, Any]]:
        """Discover available agents with caching"""
        
        cache_key = f"{specialization}_{include_custom}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data
        
        # Simulate agent discovery (replace with actual implementation)
        core_agents = [
            {"type": "documentation", "specializations": ["docs", "api", "guides"], "custom": False},
            {"type": "qa", "specializations": ["testing", "quality", "validation"], "custom": False},
            {"type": "security", "specializations": ["security", "vulnerability", "compliance"], "custom": False},
            {"type": "engineer", "specializations": ["code", "implementation", "development"], "custom": False},
            {"type": "ops", "specializations": ["deployment", "infrastructure", "monitoring"], "custom": False},
            {"type": "versioner", "specializations": ["git", "version", "release"], "custom": False},
            {"type": "researcher", "specializations": ["research", "analysis", "investigation"], "custom": False},
            {"type": "data_engineer", "specializations": ["data", "pipeline", "etl"], "custom": False},
            {"type": "ticketer", "specializations": ["tickets", "workflow", "tracking"], "custom": False}
        ]
        
        # Add custom agents if requested
        if include_custom:
            custom_agents = self._discover_custom_agents()
            core_agents.extend(custom_agents)
        
        # Filter by specialization
        if specialization:
            core_agents = [
                agent for agent in core_agents 
                if specialization in agent["specializations"]
            ]
        
        # Cache results
        self.cache[cache_key] = (time.time(), core_agents)
        return core_agents
        
    def _discover_custom_agents(self) -> List[Dict[str, Any]]:
        """Discover custom user agents"""
        # Placeholder for custom agent discovery
        return [
            {"type": "performance", "specializations": ["performance", "optimization", "profiling"], "custom": True},
            {"type": "architecture", "specializations": ["architecture", "design", "patterns"], "custom": True}
        ]

# ==============================================================================
# Ticket Creation System
# ==============================================================================

class TicketExtractor:
    """Extract ticket information from agent output"""
    
    TICKET_PATTERNS = [
        (r'TODO:\s*(.+)', 'task'),
        (r'FIXME:\s*(.+)', 'bug'), 
        (r'BUG:\s*(.+)', 'bug'),
        (r'FEATURE:\s*(.+)', 'feature'),
        (r'SECURITY:\s*(.+)', 'security'),
        (r'PERFORMANCE:\s*(.+)', 'performance'),
        (r'REFACTOR:\s*(.+)', 'refactor')
    ]
    
    def extract_tickets(self, output: str, source_agent: str) -> List[Dict[str, Any]]:
        """Extract structured ticket data from output"""
        import re
        
        tickets = []
        for pattern, ticket_type in self.TICKET_PATTERNS:
            matches = re.finditer(pattern, output, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                tickets.append({
                    'type': ticket_type,
                    'title': match.group(1).strip(),
                    'source_agent': source_agent,
                    'timestamp': datetime.now().isoformat(),
                    'priority': self._determine_priority(ticket_type),
                    'context': self._extract_surrounding_context(output, match)
                })
                
        return tickets
        
    def _determine_priority(self, ticket_type: str) -> str:
        priority_map = {
            'security': 'high',
            'bug': 'high',
            'performance': 'medium',
            'feature': 'medium',
            'task': 'low',
            'refactor': 'low'
        }
        return priority_map.get(ticket_type, 'medium')
        
    def _extract_surrounding_context(self, text: str, match) -> str:
        """Extract context around the match"""
        lines = text.split('\n')
        line_num = text[:match.start()].count('\n')
        start = max(0, line_num - 2)
        end = min(len(lines), line_num + 3)
        return '\n'.join(lines[start:end])

# ==============================================================================
# Main Tool Handler (Claude Integration)
# ==============================================================================

class ClaudeToolHandler:
    def __init__(self, framework_context: Dict[str, Any]):
        self.framework_context = framework_context
        self.process_manager = ProcessManager()
        self.context_manager = ContextManager(framework_context)
        self.agent_registry = AgentRegistry()
        self.ticket_extractor = TicketExtractor()
        
    def handle_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for handling Claude tool calls"""
        
        try:
            if tool_name == "execute_agent_subprocess":
                return self._execute_agent_subprocess(**parameters)
            elif tool_name == "discover_available_agents":
                return self._discover_available_agents(**parameters)
            elif tool_name == "coordinate_multi_agent_workflow":
                return self._coordinate_multi_agent_workflow(**parameters)
            elif tool_name == "create_tickets_from_output":
                return self._create_tickets_from_output(**parameters)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def _execute_agent_subprocess(self, agent_type: str, task_description: str, 
                                context: Dict[str, Any] = None, timeout: int = 300,
                                memory_limit: int = 1024) -> Dict[str, Any]:
        """Execute a specialized agent in controlled subprocess"""
        
        start_time = time.time()
        context = context or {}
        
        try:
            # Filter context for agent
            filtered_context = self.context_manager.filter_context_for_agent(context, agent_type)
            
            # Prepare environment
            env = self.context_manager.prepare_environment(filtered_context)
            
            # Build command (replace with actual agent executor)
            command = [
                'python', '-m', 'claude_pm.agents.executor',
                '--agent-type', agent_type,
                '--task', task_description
            ]
            
            # Execute with monitoring
            process_id, process = self.process_manager.create_process(
                command, env, memory_limit, timeout
            )
            
            stdout, stderr, memory_usage = self.process_manager.communicate_with_process(
                process_id, timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # Extract tickets from output
            tickets = self.ticket_extractor.extract_tickets(stdout, agent_type)
            ticket_ids = [f"TICKET-{i+1}" for i in range(len(tickets))]  # Placeholder
            
            result = AgentExecutionResult(
                success=process.returncode == 0,
                agent_type=agent_type,
                task_description=task_description,
                stdout=stdout,
                stderr=stderr,
                exit_code=process.returncode,
                execution_time=execution_time,
                memory_usage=memory_usage,
                tickets_created=ticket_ids
            )
            
            return {
                "success": result.success,
                "agent_type": result.agent_type,
                "task_description": result.task_description,
                "output": result.stdout,
                "errors": result.stderr if result.stderr else None,
                "execution_time_seconds": round(result.execution_time, 2),
                "memory_usage": result.memory_usage,
                "tickets_created": result.tickets_created,
                "exit_code": result.exit_code
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Agent {agent_type} timed out after {timeout} seconds",
                "agent_type": agent_type,
                "task_description": task_description
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent_type": agent_type,
                "task_description": task_description
            }
    
    def _discover_available_agents(self, specialization: str = None, 
                                 include_custom: bool = True) -> Dict[str, Any]:
        """Discover available agents in the registry"""
        
        agents = self.agent_registry.discover_agents(specialization, include_custom)
        
        return {
            "available_agents": agents,
            "total_count": len(agents),
            "specialization_filter": specialization,
            "includes_custom": include_custom
        }
    
    def _coordinate_multi_agent_workflow(self, workflow_description: str,
                                       agent_tasks: List[Dict[str, Any]],
                                       coordination_mode: str = "hybrid") -> Dict[str, Any]:
        """Coordinate multiple agents for complex workflows"""
        
        workflow_id = str(uuid.uuid4())
        tasks = []
        
        # Create workflow tasks
        for i, task_config in enumerate(agent_tasks):
            task = WorkflowTask(
                id=f"{workflow_id}-task-{i}",
                agent_type=task_config["agent_type"],
                task=task_config["task"],
                dependencies=task_config.get("dependencies", []),
                priority=task_config.get("priority", 1)
            )
            tasks.append(task)
        
        # Execute workflow based on coordination mode
        if coordination_mode == "sequential":
            results = self._execute_sequential_workflow(tasks)
        elif coordination_mode == "parallel":
            results = self._execute_parallel_workflow(tasks)
        else:  # hybrid
            results = self._execute_hybrid_workflow(tasks)
        
        return {
            "workflow_id": workflow_id,
            "workflow_description": workflow_description,
            "coordination_mode": coordination_mode,
            "total_tasks": len(tasks),
            "completed_tasks": len([r for r in results if r["success"]]),
            "failed_tasks": len([r for r in results if not r["success"]]),
            "task_results": results
        }
    
    def _create_tickets_from_output(self, output_text: str, source_agent: str,
                                  auto_create: bool = False) -> Dict[str, Any]:
        """Parse agent output and create tickets"""
        
        tickets = self.ticket_extractor.extract_tickets(output_text, source_agent)
        
        created_tickets = []
        if auto_create:
            # Simulate ticket creation (replace with actual ticketing system)
            for ticket in tickets:
                ticket_id = f"TICKET-{int(time.time())}-{len(created_tickets)}"
                created_tickets.append({
                    "id": ticket_id,
                    "title": ticket["title"],
                    "type": ticket["type"],
                    "priority": ticket["priority"],
                    "source_agent": ticket["source_agent"]
                })
        
        return {
            "tickets_found": len(tickets),
            "tickets_created": len(created_tickets) if auto_create else 0,
            "auto_create_enabled": auto_create,
            "ticket_details": tickets,
            "created_tickets": created_tickets
        }
    
    def _execute_sequential_workflow(self, tasks: List[WorkflowTask]) -> List[Dict[str, Any]]:
        """Execute tasks sequentially"""
        results = []
        for task in sorted(tasks, key=lambda t: t.priority):
            result = self._execute_agent_subprocess(task.agent_type, task.task)
            results.append(result)
        return results
    
    def _execute_parallel_workflow(self, tasks: List[WorkflowTask]) -> List[Dict[str, Any]]:
        """Execute tasks in parallel (simplified version)"""
        # In real implementation, use threading or asyncio
        results = []
        for task in tasks:
            result = self._execute_agent_subprocess(task.agent_type, task.task)
            results.append(result)
        return results
    
    def _execute_hybrid_workflow(self, tasks: List[WorkflowTask]) -> List[Dict[str, Any]]:
        """Execute tasks with dependency awareness"""
        # Simplified hybrid execution
        return self._execute_sequential_workflow(tasks)

# ==============================================================================
# Usage Example
# ==============================================================================

def example_usage():
    """Example of how to use the Claude tool calling system"""
    
    # Initialize framework context
    framework_context = {
        "project_root": "/path/to/project",
        "framework_version": "1.4.0",
        "user_preferences": {"model": "claude-sonnet", "timeout": 300}
    }
    
    # Create tool handler
    tool_handler = ClaudeToolHandler(framework_context)
    
    # Example 1: Execute single agent
    result1 = tool_handler.handle_tool_call("execute_agent_subprocess", {
        "agent_type": "documentation",
        "task_description": "Analyze project structure and generate API documentation",
        "context": {
            "project_root": "/path/to/project",
            "file_paths": ["src/", "docs/"],
            "user_requirements": "Focus on public APIs"
        },
        "timeout": 300,
        "memory_limit": 1024
    })
    
    print("Single Agent Result:", json.dumps(result1, indent=2))
    
    # Example 2: Discover agents
    result2 = tool_handler.handle_tool_call("discover_available_agents", {
        "specialization": "testing",
        "include_custom": True
    })
    
    print("Agent Discovery:", json.dumps(result2, indent=2))
    
    # Example 3: Multi-agent workflow
    result3 = tool_handler.handle_tool_call("coordinate_multi_agent_workflow", {
        "workflow_description": "Complete code review and deployment preparation",
        "agent_tasks": [
            {
                "agent_type": "qa",
                "task": "Run comprehensive test suite and generate coverage report",
                "priority": 1
            },
            {
                "agent_type": "security", 
                "task": "Perform security audit and vulnerability scan",
                "priority": 2
            },
            {
                "agent_type": "documentation",
                "task": "Update documentation for new features",
                "priority": 3
            }
        ],
        "coordination_mode": "hybrid"
    })
    
    print("Multi-Agent Workflow:", json.dumps(result3, indent=2))

if __name__ == "__main__":
    # Print tool definitions for Claude
    print("=== Claude PM Framework Tool Definitions ===")
    print(json.dumps(CLAUDE_PM_TOOLS, indent=2))
    print("\n=== Example Usage ===")
    example_usage()