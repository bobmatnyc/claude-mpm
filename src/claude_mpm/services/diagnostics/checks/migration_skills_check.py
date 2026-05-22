"""Diagnostic check for migration skill state.

WHY: Surface pending migration skill recommendations (and the status of
declined / deferred / completed ones) so users can see what optional services
are available and run `/mpm-migrate <state_key>` to install them.
"""

from __future__ import annotations

import logging

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck

logger = logging.getLogger(__name__)


class MigrationSkillsCheck(BaseDiagnosticCheck):
    """Report pending and recorded migration skill choices."""

    @property
    def name(self) -> str:
        return "migration_skills"

    @property
    def category(self) -> str:
        return "Migration Skills"

    @property
    def description(self) -> str:
        return "Pending setup recommendations"

    def run(self) -> DiagnosticResult:
        try:
            from claude_mpm.migrations.user_choices import UserChoicesManager
            from claude_mpm.skills.skill_manager import get_manager
        except Exception as exc:  # pragma: no cover - defensive
            return DiagnosticResult(
                category=self.category,
                status=ValidationSeverity.WARNING,
                message=f"Could not load migration skill subsystem: {exc}",
            )

        try:
            skill_manager = get_manager()
            all_migrations = skill_manager.get_migration_skills()
        except Exception as exc:  # pragma: no cover - defensive
            return DiagnosticResult(
                category=self.category,
                status=ValidationSeverity.WARNING,
                message=f"Could not enumerate migration skills: {exc}",
            )

        if not all_migrations:
            return DiagnosticResult(
                category=self.category,
                status=OperationResult.SUCCESS,
                message="No migration skills configured",
                details={"count": 0},
            )

        choices = UserChoicesManager()
        sub_results: list[DiagnosticResult] = []
        pending_count = 0

        for skill in all_migrations:
            state_key = skill.get("state_key") or skill.get("name", "unknown")
            description = skill.get("description", "")
            entry = choices.get_choice(state_key)
            is_pending = choices.is_pending(state_key)

            if is_pending:
                pending_count += 1
                status = ValidationSeverity.WARNING
                msg = f"{state_key}: pending setup"
                if description:
                    msg += f" — {description}"
                sub_results.append(
                    DiagnosticResult(
                        category=self.category,
                        status=status,
                        message=msg,
                        fix_command=f"# /mpm-migrate {state_key}",
                        fix_description=(
                            f"Run /mpm-migrate {state_key} in Claude Code to "
                            "install, or tell the PM to decline it permanently."
                        ),
                        details={"state_key": state_key, "entry": entry},
                    )
                )
            else:
                # Declined / completed / deferred-not-yet-expired
                recorded_status = entry.get("status") if entry else "unknown"
                sub_results.append(
                    DiagnosticResult(
                        category=self.category,
                        status=OperationResult.SUCCESS,
                        message=f"{state_key}: {recorded_status}",
                        details={"state_key": state_key, "entry": entry},
                    )
                )

        if pending_count > 0:
            overall_status: OperationResult | ValidationSeverity = (
                ValidationSeverity.WARNING
            )
            overall_msg = (
                f"{pending_count} migration skill(s) pending; "
                "run /mpm-migrate <state_key> to install"
            )
        else:
            overall_status = OperationResult.SUCCESS
            overall_msg = f"All {len(all_migrations)} migration skill(s) handled"

        return DiagnosticResult(
            category=self.category,
            status=overall_status,
            message=overall_msg,
            details={
                "total": len(all_migrations),
                "pending": pending_count,
            },
            sub_results=sub_results,
        )
