"""
Observer Pattern for Auto-Configuration Progress Tracking
=========================================================

WHY: Auto-configuration involves multiple steps (analysis, recommendation,
deployment) that can take significant time. Observers enable real-time
progress tracking and user feedback.

DESIGN DECISION: Observer pattern allows decoupling of progress notification
from core business logic. Multiple observers can be attached for different
output targets (console, file, network).

Part of TSK-0054: Auto-Configuration Feature - Phase 4
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..core.models.agent_config import AgentRecommendation
from ..core.models.toolchain import ToolchainAnalysis


class IDeploymentObserver(ABC):
    """
    Observer interface for deployment events.

    WHY: Standardizes the observer interface to enable multiple observer
    implementations (console, GUI, logging, metrics) that all receive
    the same event notifications.

    DESIGN DECISION: Separate methods for each event type enable fine-grained
    control over which events observers handle. All methods are optional
    (have default implementations) to simplify observer creation.
    """

    @abstractmethod
    def on_analysis_started(self, project_path: str) -> None:
        """
        Called when toolchain analysis starts.

        Args:
            project_path: Path to the project being analyzed
        """

    @abstractmethod
    def on_analysis_completed(
        self, toolchain: ToolchainAnalysis, duration_ms: float
    ) -> None:
        """
        Called when toolchain analysis completes.

        Args:
            toolchain: Complete toolchain analysis result
            duration_ms: Analysis duration in milliseconds
        """

    @abstractmethod
    def on_recommendation_started(self) -> None:
        """Called when agent recommendation starts."""

    @abstractmethod
    def on_recommendation_completed(
        self, recommendations: List[AgentRecommendation], duration_ms: float
    ) -> None:
        """
        Called when agent recommendation completes.

        Args:
            recommendations: List of agent recommendations
            duration_ms: Recommendation duration in milliseconds
        """

    @abstractmethod
    def on_validation_started(self) -> None:
        """Called when configuration validation starts."""

    @abstractmethod
    def on_validation_completed(
        self, is_valid: bool, error_count: int, warning_count: int
    ) -> None:
        """
        Called when configuration validation completes.

        Args:
            is_valid: Whether validation passed
            error_count: Number of validation errors
            warning_count: Number of validation warnings
        """

    @abstractmethod
    def on_deployment_started(self, total_agents: int) -> None:
        """
        Called when deployment of agents starts.

        Args:
            total_agents: Total number of agents to deploy
        """

    @abstractmethod
    def on_agent_deployment_started(
        self, agent_id: str, agent_name: str, index: int, total: int
    ) -> None:
        """
        Called when deployment of a specific agent starts.

        Args:
            agent_id: Agent identifier
            agent_name: Human-readable agent name
            index: Current agent index (1-based)
            total: Total number of agents being deployed
        """

    @abstractmethod
    def on_agent_deployment_progress(
        self, agent_id: str, progress: int, message: str = ""
    ) -> None:
        """
        Called to report progress of agent deployment.

        Args:
            agent_id: Agent identifier
            progress: Progress percentage (0-100)
            message: Optional progress message
        """

    @abstractmethod
    def on_agent_deployment_completed(
        self, agent_id: str, agent_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        """
        Called when deployment of a specific agent completes.

        Args:
            agent_id: Agent identifier
            agent_name: Human-readable agent name
            success: Whether deployment succeeded
            error: Error message if deployment failed
        """

    @abstractmethod
    def on_deployment_completed(
        self, success_count: int, failure_count: int, duration_ms: float
    ) -> None:
        """
        Called when all agent deployments complete.

        Args:
            success_count: Number of successfully deployed agents
            failure_count: Number of failed deployments
            duration_ms: Total deployment duration in milliseconds
        """

    @abstractmethod
    def on_rollback_started(self, agent_ids: List[str]) -> None:
        """
        Called when rollback of failed deployments starts.

        Args:
            agent_ids: List of agent IDs to roll back
        """

    @abstractmethod
    def on_rollback_completed(self, success: bool) -> None:
        """
        Called when rollback completes.

        Args:
            success: Whether rollback succeeded
        """

    @abstractmethod
    def on_error(
        self, phase: str, error_message: str, exception: Optional[Exception] = None
    ) -> None:
        """
        Called when an error occurs during auto-configuration.

        Args:
            phase: Phase where error occurred (analysis, recommendation, deployment)
            error_message: Human-readable error message
            exception: Optional exception object
        """


class NullObserver(IDeploymentObserver):
    """
    Null Object pattern implementation of observer.

    WHY: Provides a no-op observer to simplify code when no observer is needed.
    Eliminates need for null checks before calling observer methods.

    DESIGN DECISION: All methods do nothing, making this a safe default observer.
    """

    def on_analysis_started(self, project_path: str) -> None:
        """No-op: discards analysis start notification.

        WHY: Null Object pattern — callers need not check if an observer is attached.
        WHAT: Accepts the event and immediately returns without side effects.
        TEST: Call with any string; assert no exception is raised and nothing is printed.
        """

    def on_analysis_completed(
        self, toolchain: ToolchainAnalysis, duration_ms: float
    ) -> None:
        """No-op: discards analysis completion notification.

        WHY: Null Object pattern — silently absorbs events from the analysis phase.
        WHAT: Accepts toolchain result and duration; does nothing.
        TEST: Call with a mock ToolchainAnalysis and float; assert no exception.
        """

    def on_recommendation_started(self) -> None:
        """No-op: discards recommendation start notification.

        WHY: Null Object pattern — allows recommendation phase to proceed without observer.
        WHAT: Accepts event; does nothing.
        TEST: Call with no arguments; assert no exception.
        """

    def on_recommendation_completed(
        self, recommendations: List[AgentRecommendation], duration_ms: float
    ) -> None:
        """No-op: discards recommendation completion notification.

        WHY: Null Object pattern — absorbs recommendation results without output.
        WHAT: Accepts recommendation list and duration; does nothing.
        TEST: Call with empty list and 0.0; assert no exception.
        """

    def on_validation_started(self) -> None:
        """No-op: discards validation start notification.

        WHY: Null Object pattern — allows validation to proceed without observer output.
        WHAT: Accepts event; does nothing.
        TEST: Call with no arguments; assert no exception.
        """

    def on_validation_completed(
        self, is_valid: bool, error_count: int, warning_count: int
    ) -> None:
        """No-op: discards validation completion notification.

        WHY: Null Object pattern — absorbs validation results without output.
        WHAT: Accepts validity flag and counts; does nothing.
        TEST: Call with (True, 0, 0); assert no exception.
        """

    def on_deployment_started(self, total_agents: int) -> None:
        """No-op: discards deployment start notification.

        WHY: Null Object pattern — allows deployment to start without observer output.
        WHAT: Accepts agent count; does nothing.
        TEST: Call with 5; assert no exception.
        """

    def on_agent_deployment_started(
        self, agent_id: str, agent_name: str, index: int, total: int
    ) -> None:
        """No-op: discards per-agent deployment start notification.

        WHY: Null Object pattern — absorbs per-agent events without output.
        WHAT: Accepts agent identifiers and position; does nothing.
        TEST: Call with ("id", "name", 1, 3); assert no exception.
        """

    def on_agent_deployment_progress(
        self, agent_id: str, progress: int, message: str = ""
    ) -> None:
        """No-op: discards per-agent deployment progress notification.

        WHY: Null Object pattern — absorbs progress events without output.
        WHAT: Accepts agent id, percentage, and message; does nothing.
        TEST: Call with ("id", 50, "halfway"); assert no exception.
        """

    def on_agent_deployment_completed(
        self, agent_id: str, agent_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        """No-op: discards per-agent deployment completion notification.

        WHY: Null Object pattern — absorbs completion events without output.
        WHAT: Accepts agent identifiers, success flag, and optional error; does nothing.
        TEST: Call with ("id", "name", True); assert no exception.
        """

    def on_deployment_completed(
        self, success_count: int, failure_count: int, duration_ms: float
    ) -> None:
        """No-op: discards overall deployment completion notification.

        WHY: Null Object pattern — absorbs summary events without output.
        WHAT: Accepts counts and duration; does nothing.
        TEST: Call with (3, 0, 1500.0); assert no exception.
        """

    def on_rollback_started(self, agent_ids: List[str]) -> None:
        """No-op: discards rollback start notification.

        WHY: Null Object pattern — absorbs rollback events without output.
        WHAT: Accepts list of agent IDs to roll back; does nothing.
        TEST: Call with ["agent_a", "agent_b"]; assert no exception.
        """

    def on_rollback_completed(self, success: bool) -> None:
        """No-op: discards rollback completion notification.

        WHY: Null Object pattern — absorbs rollback result without output.
        WHAT: Accepts success flag; does nothing.
        TEST: Call with True and with False; assert no exception in both cases.
        """

    def on_error(
        self, phase: str, error_message: str, exception: Optional[Exception] = None
    ) -> None:
        """No-op: discards error notification.

        WHY: Null Object pattern — silently absorbs error events; callers don't need to
        guard against a missing observer when an error occurs.
        WHAT: Accepts phase name, message, and optional exception; does nothing.
        TEST: Call with ("deploying", "fail", ValueError()); assert no exception.
        """


class ConsoleProgressObserver(IDeploymentObserver):
    """
    Console-based progress observer with rich terminal output.

    WHY: Provides user-friendly progress feedback during auto-configuration.
    Uses rich library for enhanced terminal output with colors and progress bars.

    DESIGN DECISION: Conditionally imports rich library to avoid hard dependency.
    Falls back to simple print statements if rich is not available.
    """

    def __init__(self, use_rich: bool = True):
        """
        Initialize console observer.

        Args:
            use_rich: Whether to use rich library for enhanced output
        """
        self.use_rich = use_rich
        self._rich_available = False
        self._console = None
        self._progress = None
        self._task_id = None

        if self.use_rich:
            try:
                from rich.console import Console
                from rich.progress import (
                    BarColumn,
                    Progress,
                    SpinnerColumn,
                    TextColumn,
                    TimeRemainingColumn,
                )

                self._Console = Console
                self._Progress = Progress
                self._SpinnerColumn = SpinnerColumn
                self._TextColumn = TextColumn
                self._BarColumn = BarColumn
                self._TimeRemainingColumn = TimeRemainingColumn
                self._rich_available = True
                self._console = Console()
            except ImportError:
                self._rich_available = False

    def _print(self, message: str, style: str = "") -> None:
        """
        Print message with optional styling.

        Args:
            message: Message to print
            style: Rich style string (e.g., "bold green", "red")
        """
        if self._rich_available and self._console:
            self._console.print(message, style=style)
        else:
            print(message)

    def on_analysis_started(self, project_path: str) -> None:
        """Called when toolchain analysis starts."""
        self._print(f"\n🔍 Analyzing project toolchain: {project_path}", "bold cyan")

    def on_analysis_completed(
        self, toolchain: ToolchainAnalysis, duration_ms: float
    ) -> None:
        """Called when toolchain analysis completes."""
        self._print(
            f"✓ Analysis complete ({duration_ms:.0f}ms): "
            f"{toolchain.primary_language} with {len(toolchain.frameworks)} frameworks",
            "bold green",
        )

    def on_recommendation_started(self) -> None:
        """Called when agent recommendation starts."""
        self._print("\n🤖 Generating agent recommendations...", "bold cyan")

    def on_recommendation_completed(
        self, recommendations: List[AgentRecommendation], duration_ms: float
    ) -> None:
        """Called when agent recommendation completes."""
        high_conf = sum(1 for r in recommendations if r.is_high_confidence)
        self._print(
            f"✓ Generated {len(recommendations)} recommendations ({duration_ms:.0f}ms): "
            f"{high_conf} high confidence",
            "bold green",
        )

    def on_validation_started(self) -> None:
        """Called when configuration validation starts."""
        self._print("\n✓ Validating configuration...", "bold cyan")

    def on_validation_completed(
        self, is_valid: bool, error_count: int, warning_count: int
    ) -> None:
        """Called when configuration validation completes."""
        if is_valid:
            self._print(
                f"✓ Validation passed ({warning_count} warnings)",
                "bold green",
            )
        else:
            self._print(
                f"✗ Validation failed: {error_count} errors, {warning_count} warnings",
                "bold red",
            )

    def on_deployment_started(self, total_agents: int) -> None:
        """Called when deployment of agents starts."""
        self._print(f"\n🚀 Deploying {total_agents} agents...", "bold cyan")

    def on_agent_deployment_started(
        self, agent_id: str, agent_name: str, index: int, total: int
    ) -> None:
        """Called when deployment of a specific agent starts."""
        self._print(f"  [{index}/{total}] Deploying {agent_name}...", "cyan")

    def on_agent_deployment_progress(
        self, agent_id: str, progress: int, message: str = ""
    ) -> None:
        """Called to report progress of agent deployment."""
        # Progress updates are too noisy for console, skip them

    def on_agent_deployment_completed(
        self, agent_id: str, agent_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        """Called when deployment of a specific agent completes."""
        if success:
            self._print(f"    ✓ {agent_name} deployed successfully", "green")
        else:
            error_msg = f": {error}" if error else ""
            self._print(f"    ✗ {agent_name} deployment failed{error_msg}", "red")

    def on_deployment_completed(
        self, success_count: int, failure_count: int, duration_ms: float
    ) -> None:
        """Called when all agent deployments complete."""
        if failure_count == 0:
            self._print(
                f"\n✓ All {success_count} agents deployed successfully ({duration_ms / 1000:.1f}s)",
                "bold green",
            )
        else:
            self._print(
                f"\n⚠ Deployment completed with issues: "
                f"{success_count} succeeded, {failure_count} failed ({duration_ms / 1000:.1f}s)",
                "bold yellow",
            )

    def on_rollback_started(self, agent_ids: List[str]) -> None:
        """Called when rollback of failed deployments starts."""
        self._print(f"\n⏪ Rolling back {len(agent_ids)} agents...", "bold yellow")

    def on_rollback_completed(self, success: bool) -> None:
        """Called when rollback completes."""
        if success:
            self._print("✓ Rollback completed successfully", "green")
        else:
            self._print("✗ Rollback failed", "red")

    def on_error(
        self, phase: str, error_message: str, exception: Optional[Exception] = None
    ) -> None:
        """Called when an error occurs during auto-configuration."""
        self._print(f"\n✗ Error in {phase}: {error_message}", "bold red")
        if exception:
            self._print(f"  Exception: {type(exception).__name__}: {exception}", "red")


class CompositeObserver(IDeploymentObserver):
    """
    Composite observer that broadcasts events to multiple observers.

    WHY: Enables simultaneous notification of multiple observers (e.g., console
    output + file logging + metrics collection) without coupling.

    DESIGN DECISION: Implements observer pattern by delegating all events to
    registered observers. Catches and logs exceptions from individual observers
    to prevent one failing observer from breaking others.
    """

    def __init__(self, observers: Optional[List[IDeploymentObserver]] = None):
        """
        Initialize composite observer.

        Args:
            observers: List of observers to notify
        """
        self._observers: List[IDeploymentObserver] = observers or []

    def add_observer(self, observer: IDeploymentObserver) -> None:
        """
        Add an observer to the composite.

        Args:
            observer: Observer to add
        """
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer: IDeploymentObserver) -> None:
        """
        Remove an observer from the composite.

        Args:
            observer: Observer to remove
        """
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify_all(self, method_name: str, *args, **kwargs) -> None:
        """
        Notify all observers by calling method on each.

        Args:
            method_name: Name of the observer method to call
            *args: Positional arguments to pass
            **kwargs: Keyword arguments to pass
        """
        for observer in self._observers:
            try:
                method = getattr(observer, method_name)
                method(*args, **kwargs)
            except Exception as e:
                # Log but don't re-raise to prevent one observer from breaking others
                print(
                    f"Error in observer {observer.__class__.__name__}.{method_name}: {e}"
                )

    def on_analysis_started(self, project_path: str) -> None:
        """Broadcast analysis-started event to all registered observers.

        WHY: Fans out the event so all observers receive simultaneous notification.
        WHAT: Delegates to _notify_all with the project path argument.
        TEST: Attach two mock observers; call this; assert both received the event.
        """
        self._notify_all("on_analysis_started", project_path)

    def on_analysis_completed(
        self, toolchain: ToolchainAnalysis, duration_ms: float
    ) -> None:
        """Broadcast analysis-completed event to all registered observers.

        WHY: Fans out the result so all observers can inspect the toolchain.
        WHAT: Delegates to _notify_all with toolchain and duration arguments.
        TEST: Attach two mock observers; call this; assert both received toolchain data.
        """
        self._notify_all("on_analysis_completed", toolchain, duration_ms)

    def on_recommendation_started(self) -> None:
        """Broadcast recommendation-started event to all registered observers.

        WHY: Notifies all observers that the recommendation phase has begun.
        WHAT: Delegates to _notify_all with no additional arguments.
        TEST: Attach mock observers; call this; assert all received the event.
        """
        self._notify_all("on_recommendation_started")

    def on_recommendation_completed(
        self, recommendations: List[AgentRecommendation], duration_ms: float
    ) -> None:
        """Broadcast recommendation-completed event to all registered observers.

        WHY: Fans out the recommendations so all observers can inspect results.
        WHAT: Delegates to _notify_all with recommendations list and duration.
        TEST: Attach mock observers; call this; assert all received the list.
        """
        self._notify_all("on_recommendation_completed", recommendations, duration_ms)

    def on_validation_started(self) -> None:
        """Broadcast validation-started event to all registered observers.

        WHY: Notifies all observers that configuration validation has begun.
        WHAT: Delegates to _notify_all with no additional arguments.
        TEST: Attach mock observers; call this; assert all received the event.
        """
        self._notify_all("on_validation_started")

    def on_validation_completed(
        self, is_valid: bool, error_count: int, warning_count: int
    ) -> None:
        """Broadcast validation-completed event to all registered observers.

        WHY: Fans out validation results so observers can react (e.g., abort on errors).
        WHAT: Delegates to _notify_all with validity flag and error/warning counts.
        TEST: Attach mock observers; call with (False, 2, 1); assert all received counts.
        """
        self._notify_all(
            "on_validation_completed", is_valid, error_count, warning_count
        )

    def on_deployment_started(self, total_agents: int) -> None:
        """Broadcast deployment-started event to all registered observers.

        WHY: Notifies all observers of the total scope so they can initialize progress UI.
        WHAT: Delegates to _notify_all with the total agent count.
        TEST: Attach mock observers; call with 5; assert all received total=5.
        """
        self._notify_all("on_deployment_started", total_agents)

    def on_agent_deployment_started(
        self, agent_id: str, agent_name: str, index: int, total: int
    ) -> None:
        """Broadcast per-agent deployment-started event to all registered observers.

        WHY: Fans out per-agent events so progress bars and logs can track each agent.
        WHAT: Delegates to _notify_all with agent identifiers and position.
        TEST: Attach mock observers; call with ("id", "name", 1, 3); assert all notified.
        """
        self._notify_all(
            "on_agent_deployment_started", agent_id, agent_name, index, total
        )

    def on_agent_deployment_progress(
        self, agent_id: str, progress: int, message: str = ""
    ) -> None:
        """Broadcast per-agent deployment progress to all registered observers.

        WHY: Fans out granular progress events for live dashboard updates.
        WHAT: Delegates to _notify_all with agent id, percentage, and message.
        TEST: Attach mock observers; call with ("id", 50, "halfway"); assert all notified.
        """
        self._notify_all("on_agent_deployment_progress", agent_id, progress, message)

    def on_agent_deployment_completed(
        self, agent_id: str, agent_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        """Broadcast per-agent deployment completion to all registered observers.

        WHY: Fans out individual agent outcomes so observers can update logs/counts.
        WHAT: Delegates to _notify_all with agent identifiers, success flag, and error.
        TEST: Attach mock observers; call with ("id", "name", False, "timeout"); assert all notified.
        """
        self._notify_all(
            "on_agent_deployment_completed", agent_id, agent_name, success, error
        )

    def on_deployment_completed(
        self, success_count: int, failure_count: int, duration_ms: float
    ) -> None:
        """Broadcast overall deployment completion to all registered observers.

        WHY: Fans out the final summary so all observers can display totals.
        WHAT: Delegates to _notify_all with success/failure counts and duration.
        TEST: Attach mock observers; call with (3, 1, 2500.0); assert all received counts.
        """
        self._notify_all(
            "on_deployment_completed", success_count, failure_count, duration_ms
        )

    def on_rollback_started(self, agent_ids: List[str]) -> None:
        """Broadcast rollback-started event to all registered observers.

        WHY: Fans out rollback notification so observers can update status indicators.
        WHAT: Delegates to _notify_all with list of agent IDs being rolled back.
        TEST: Attach mock observers; call with ["a", "b"]; assert all received the list.
        """
        self._notify_all("on_rollback_started", agent_ids)

    def on_rollback_completed(self, success: bool) -> None:
        """Broadcast rollback-completed event to all registered observers.

        WHY: Fans out rollback result so all observers know the final rollback outcome.
        WHAT: Delegates to _notify_all with success flag.
        TEST: Attach mock observers; call with False; assert all received success=False.
        """
        self._notify_all("on_rollback_completed", success)

    def on_error(
        self, phase: str, error_message: str, exception: Optional[Exception] = None
    ) -> None:
        """Broadcast error event to all registered observers.

        WHY: Fans out error notification so all observers can log or alert on failures.
        WHAT: Delegates to _notify_all with phase name, message, and optional exception.
        TEST: Attach mock observers; call with ("deploying", "fail", exc); assert all notified.
        """
        self._notify_all("on_error", phase, error_message, exception)
