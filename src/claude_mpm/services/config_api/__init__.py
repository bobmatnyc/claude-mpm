"""Configuration API for the Claude MPM Dashboard.

Phase 3: Safety infrastructure + deployment endpoint handlers.

Safety modules:
- BackupManager: Timestamped backups before destructive operations
- OperationJournal: Crash-recovery journal for in-flight operations
- DeploymentVerifier: Post-deployment verification checks
- detect_active_claude_sessions: Active Claude Code session detection

Endpoint handlers:
- register_agent_deployment_routes: Agent deploy/undeploy/batch/collections
- register_skill_deployment_routes: Skill deploy/undeploy/mode switch
- register_autoconfig_routes: Toolchain detect/preview/apply
"""

from claude_mpm.services.config_api.agent_deployment_handler import (
    register_agent_deployment_routes,
)
from claude_mpm.services.config_api.autoconfig_handler import (
    register_autoconfig_routes,
)
from claude_mpm.services.config_api.backup_manager import (
    BackupManager,
    BackupMetadata,
    BackupResult,
    RestoreResult,
)
from claude_mpm.services.config_api.deployment_verifier import (
    DeploymentVerifier,
    VerificationCheck,
    VerificationResult,
)
from claude_mpm.services.config_api.operation_journal import (
    JournalEntry,
    OperationJournal,
)
from claude_mpm.services.config_api.session_detector import (
    detect_active_claude_sessions,
)
from claude_mpm.services.config_api.skill_deployment_handler import (
    register_skill_deployment_routes,
)

__all__ = [
    "BackupManager",
    "BackupMetadata",
    "BackupResult",
    "DeploymentVerifier",
    "JournalEntry",
    "OperationJournal",
    "RestoreResult",
    "VerificationCheck",
    "VerificationResult",
    "detect_active_claude_sessions",
    "register_agent_deployment_routes",
    "register_autoconfig_routes",
    "register_skill_deployment_routes",
]
