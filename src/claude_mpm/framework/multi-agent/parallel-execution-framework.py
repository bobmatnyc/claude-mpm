"""
Claude PM Framework - Parallel Execution Framework
Manages parallel execution of up to 5 concurrent agents with coordination and resource management.
"""

import asyncio
import threading
import os
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor, Future
import queue
import time

from git_worktree_manager import GitWorktreeManager, WorktreeContext


class AgentPriority(str, Enum):
    """Agent execution priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Task execution status."""
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    """Represents a task to be executed by an agent."""
    task_id: str
    agent_id: str
    agent_type: str
    priority: AgentPriority
    task_function: Callable
    task_args: Tuple = field(default_factory=tuple)
    task_kwargs: Dict[str, Any] = field(default_factory=dict)
    
    # Execution context
    worktree_required: bool = True
    git_branch: Optional[str] = None
    timeout_seconds: int = 3600  # 1 hour default
    
    # Status tracking
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[Exception] = None
    
    # Resource allocation
    worker_id: Optional[str] = None
    worktree_id: Optional[str] = None


@dataclass
class AgentWorker:
    """Represents an agent worker process."""
    worker_id: str
    agent_id: str
    agent_type: str
    thread: Optional[threading.Thread] = None
    future: Optional[Future] = None
    current_task: Optional[AgentTask] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_busy: bool = False


class ParallelExecutionFramework:
    """
    Manages parallel execution of agents with resource isolation and coordination.
    Supports up to 5 concurrent agents with git worktree isolation.
    """
    
    def __init__(self, base_repo_path: str, max_concurrent_agents: int = 5):
        """
        Initialize the parallel execution framework.
        
        Args:
            base_repo_path: Path to the git repository for worktree management
            max_concurrent_agents: Maximum number of concurrent agents (default 5)
        """
        self.max_concurrent_agents = max_concurrent_agents
        self.base_repo_path = base_repo_path
        
        # Core components
        self.worktree_manager = GitWorktreeManager(base_repo_path)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_agents)
        
        # Task management
        self.task_queue = queue.PriorityQueue()
        self.active_workers: Dict[str, AgentWorker] = {}
        self.completed_tasks: List[AgentTask] = []
        self.task_history: Dict[str, AgentTask] = {}
        
        # Coordination
        self.coordination_lock = threading.Lock()
        self.shutdown_event = threading.Event()
        
        # Start coordination thread
        self.coordination_thread = threading.Thread(target=self._coordination_loop, daemon=True)
        self.coordination_thread.start()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Parallel execution framework initialized with {max_concurrent_agents} max agents")
    
    def submit_task(
        self,
        agent_id: str,
        agent_type: str,
        task_function: Callable,
        priority: AgentPriority = AgentPriority.MEDIUM,
        *args,
        **kwargs
    ) -> str:
        """
        Submit a task for agent execution.
        
        Args:
            agent_id: ID of the agent to execute the task
            agent_type: Type of agent (architect, engineer, qa, etc.)
            task_function: Function to execute
            priority: Task execution priority
            *args: Positional arguments for the task function
            **kwargs: Keyword arguments for the task function
            
        Returns:
            task_id: Unique identifier for the submitted task
        """
        task_id = str(uuid.uuid4())
        
        # Extract framework-specific kwargs
        worktree_required = kwargs.pop('worktree_required', True)
        git_branch = kwargs.pop('git_branch', None)
        timeout_seconds = kwargs.pop('timeout_seconds', 3600)
        
        task = AgentTask(
            task_id=task_id,
            agent_id=agent_id,
            agent_type=agent_type,
            priority=priority,
            task_function=task_function,
            task_args=args,
            task_kwargs=kwargs,
            worktree_required=worktree_required,
            git_branch=git_branch,
            timeout_seconds=timeout_seconds
        )
        
        # Priority queue uses tuple comparison: (priority_value, timestamp, task)
        priority_value = self._get_priority_value(priority)
        queue_item = (priority_value, time.time(), task)
        
        self.task_queue.put(queue_item)
        self.task_history[task_id] = task
        
        self.logger.info(f"Submitted task {task_id} for agent {agent_id} with priority {priority}")
        return task_id
    
    def _get_priority_value(self, priority: AgentPriority) -> int:
        """Convert priority enum to numeric value for queue ordering (lower = higher priority)."""
        priority_map = {
            AgentPriority.CRITICAL: 1,
            AgentPriority.HIGH: 2,
            AgentPriority.MEDIUM: 3,
            AgentPriority.LOW: 4
        }
        return priority_map.get(priority, 3)
    
    def _coordination_loop(self):
        """Main coordination loop that assigns tasks to available workers."""
        while not self.shutdown_event.is_set():
            try:
                self._process_task_queue()
                self._cleanup_completed_workers()
                self._monitor_worker_health()
                time.sleep(1)  # Coordination loop interval
            except Exception as e:
                self.logger.error(f"Error in coordination loop: {e}")
    
    def _process_task_queue(self):
        """Process the task queue and assign tasks to available workers."""
        with self.coordination_lock:
            # Check if we have available capacity
            if len(self.active_workers) >= self.max_concurrent_agents:
                return
            
            # Try to get a task from the queue
            try:
                priority_value, timestamp, task = self.task_queue.get_nowait()
                self._assign_task_to_worker(task)
            except queue.Empty:
                pass  # No tasks to process
    
    def _assign_task_to_worker(self, task: AgentTask):
        """Assign a task to a new worker."""
        worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        
        # Create worker
        worker = AgentWorker(
            worker_id=worker_id,
            agent_id=task.agent_id,
            agent_type=task.agent_type,
            current_task=task
        )
        
        # Submit to thread pool
        future = self.executor.submit(self._execute_task, worker, task)
        worker.future = future
        
        # Track worker
        self.active_workers[worker_id] = worker
        task.worker_id = worker_id
        task.status = TaskStatus.ASSIGNED
        
        self.logger.info(f"Assigned task {task.task_id} to worker {worker_id}")
    
    def _execute_task(self, worker: AgentWorker, task: AgentTask):
        """Execute a task in a worker context."""
        worker.is_busy = True
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        try:
            self.logger.info(f"Starting execution of task {task.task_id} in worker {worker.worker_id}")
            
            if task.worktree_required:
                # Execute with worktree isolation
                with WorktreeContext(self.worktree_manager, task.agent_id, task.git_branch) as (worktree_id, worktree_path):
                    task.worktree_id = worktree_id
                    
                    # Update working directory for the task
                    original_cwd = os.getcwd()
                    try:
                        os.chdir(worktree_path)
                        task.result = task.task_function(*task.task_args, **task.task_kwargs)
                    finally:
                        os.chdir(original_cwd)
            else:
                # Execute without worktree isolation
                task.result = task.task_function(*task.task_args, **task.task_kwargs)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            self.logger.info(f"Successfully completed task {task.task_id}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = e
            task.completed_at = datetime.now()
            
            self.logger.error(f"Task {task.task_id} failed with error: {e}")
            
        finally:
            worker.is_busy = False
            worker.last_activity = datetime.now()
            
            # Move to completed tasks
            self.completed_tasks.append(task)
    
    def _cleanup_completed_workers(self):
        """Clean up completed workers."""
        with self.coordination_lock:
            completed_workers = []
            
            for worker_id, worker in self.active_workers.items():
                if worker.future and worker.future.done():
                    completed_workers.append(worker_id)
            
            for worker_id in completed_workers:
                worker = self.active_workers.pop(worker_id)
                self.logger.info(f"Cleaned up completed worker {worker_id}")
    
    def _monitor_worker_health(self):
        """Monitor worker health and handle timeouts."""
        current_time = datetime.now()
        
        with self.coordination_lock:
            timeout_workers = []
            
            for worker_id, worker in self.active_workers.items():
                if worker.current_task and worker.current_task.status == TaskStatus.RUNNING:
                    elapsed_time = current_time - worker.current_task.started_at
                    timeout_duration = timedelta(seconds=worker.current_task.timeout_seconds)
                    
                    if elapsed_time > timeout_duration:
                        timeout_workers.append(worker_id)
            
            for worker_id in timeout_workers:
                self._handle_worker_timeout(worker_id)
    
    def _handle_worker_timeout(self, worker_id: str):
        """Handle worker timeout."""
        worker = self.active_workers.get(worker_id)
        if not worker:
            return
        
        self.logger.warning(f"Worker {worker_id} timed out on task {worker.current_task.task_id}")
        
        # Cancel the future
        if worker.future:
            worker.future.cancel()
        
        # Update task status
        if worker.current_task:
            worker.current_task.status = TaskStatus.CANCELLED
            worker.current_task.completed_at = datetime.now()
            worker.current_task.error = TimeoutError("Task execution timed out")
            self.completed_tasks.append(worker.current_task)
        
        # Remove worker
        del self.active_workers[worker_id]
    
    def get_task_status(self, task_id: str) -> Optional[AgentTask]:
        """Get the status of a specific task."""
        return self.task_history.get(task_id)
    
    def list_active_workers(self) -> List[AgentWorker]:
        """List all active workers."""
        with self.coordination_lock:
            return list(self.active_workers.values())
    
    def list_completed_tasks(self, limit: int = 100) -> List[AgentTask]:
        """List completed tasks (most recent first)."""
        return sorted(self.completed_tasks, key=lambda t: t.completed_at or datetime.min, reverse=True)[:limit]
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task if it's still queued or running.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if cancelled successfully, False if not found or already completed
        """
        task = self.task_history.get(task_id)
        if not task:
            return False
        
        with self.coordination_lock:
            if task.status in [TaskStatus.QUEUED, TaskStatus.ASSIGNED]:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                self.completed_tasks.append(task)
                return True
            
            elif task.status == TaskStatus.RUNNING and task.worker_id:
                worker = self.active_workers.get(task.worker_id)
                if worker and worker.future:
                    worker.future.cancel()
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now()
                    self.completed_tasks.append(task)
                    return True
        
        return False
    
    def wait_for_task(self, task_id: str, timeout: Optional[int] = None) -> Optional[AgentTask]:
        """
        Wait for a task to complete.
        
        Args:
            task_id: ID of the task to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Task object when completed, None if timeout
        """
        task = self.task_history.get(task_id)
        if not task:
            return None
        
        start_time = time.time()
        
        while task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            if timeout and (time.time() - start_time) > timeout:
                return None
            time.sleep(0.1)
        
        return task
    
    def get_framework_stats(self) -> Dict[str, Any]:
        """Get framework execution statistics."""
        with self.coordination_lock:
            active_workers = len(self.active_workers)
            queued_tasks = self.task_queue.qsize()
            
            completed_count = len(self.completed_tasks)
            failed_count = sum(1 for t in self.completed_tasks if t.status == TaskStatus.FAILED)
            cancelled_count = sum(1 for t in self.completed_tasks if t.status == TaskStatus.CANCELLED)
            
            # Calculate average execution time
            execution_times = [
                (t.completed_at - t.started_at).total_seconds()
                for t in self.completed_tasks
                if t.started_at and t.completed_at and t.status == TaskStatus.COMPLETED
            ]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            return {
                "active_workers": active_workers,
                "max_concurrent_agents": self.max_concurrent_agents,
                "queued_tasks": queued_tasks,
                "completed_tasks": completed_count,
                "failed_tasks": failed_count,
                "cancelled_tasks": cancelled_count,
                "success_rate": (completed_count - failed_count) / max(completed_count, 1),
                "average_execution_time_seconds": avg_execution_time,
                "worktree_stats": self.worktree_manager.get_stats()
            }
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the execution framework.
        
        Args:
            wait: Whether to wait for active tasks to complete
        """
        self.logger.info("Shutting down parallel execution framework")
        
        self.shutdown_event.set()
        
        if wait:
            # Wait for active workers to complete
            with self.coordination_lock:
                active_futures = [worker.future for worker in self.active_workers.values() if worker.future]
            
            for future in active_futures:
                try:
                    future.result(timeout=30)  # 30 second timeout for graceful shutdown
                except Exception:
                    pass
        
        # Shutdown thread pool
        self.executor.shutdown(wait=wait)
        
        # Wait for coordination thread
        if self.coordination_thread.is_alive():
            self.coordination_thread.join(timeout=5)
        
        self.logger.info("Parallel execution framework shutdown complete")


# Convenience functions
def create_execution_framework(base_repo_path: str, max_concurrent_agents: int = 5) -> ParallelExecutionFramework:
    """Create and initialize a parallel execution framework."""
    return ParallelExecutionFramework(base_repo_path, max_concurrent_agents)


# Decorator for easy task submission
def agent_task(framework: ParallelExecutionFramework, agent_id: str, agent_type: str, priority: AgentPriority = AgentPriority.MEDIUM):
    """Decorator to automatically submit functions as agent tasks."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            task_id = framework.submit_task(agent_id, agent_type, func, priority, *args, **kwargs)
            return task_id
        return wrapper
    return decorator