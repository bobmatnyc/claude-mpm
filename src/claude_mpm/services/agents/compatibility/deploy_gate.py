"""Deploy-time version gate for cached agents.

Checks manifest compatibility when agents are deployed from cache to
project .claude/agents/ directories, preventing stale cached agents
from being deployed if they've become incompatible.
"""

import logging
from typing import TYPE_CHECKING, Optional

from .manifest_checker import CompatibilityResult, ManifestChecker, ManifestCheckResult

if TYPE_CHECKING:
    from .manifest_cache import ManifestCache

logger = logging.getLogger(__name__)


class DeploymentVersionGate:
    """Checks manifest compatibility at deploy time (not just sync time).

    Reads cached manifest check results and re-validates during deployment.
    This prevents scenarios where cached agents from an old sync are
    deployed to a new project.

    Example::

        gate = DeploymentVersionGate()
        result = gate.check_before_deploy(
            source_id="https://raw.githubusercontent.com/owner/repo/main",
            cli_version="5.10.0",
            cached_manifest_content=manifest_yaml_text,
        )
        if result.status == CompatibilityResult.INCOMPATIBLE_HARD:
            raise RuntimeError(result.message)
    """

    def __init__(self, manifest_cache: Optional["ManifestCache"] = None):
        self._checker = ManifestChecker()
        self._manifest_cache = manifest_cache

    def check_before_deploy(
        self,
        source_id: str,
        cli_version: str,
        cached_manifest_content: Optional[str] = None,
    ) -> ManifestCheckResult:
        """Check compatibility before deploying agents from cache.

        Resolution order for manifest content:
        1. Use ``cached_manifest_content`` if provided.
        2. If None, attempt to read from the injected ManifestCache using
           the ``raw_content`` field of the stored entry.
        3. If still None, run the check with no manifest (fail-open).

        Args:
            source_id: Identifier for the agent source (e.g. repository URL).
            cli_version: Current CLI version string.
            cached_manifest_content: Optional cached manifest YAML.  If None,
                attempts to read from ManifestCache.

        Returns:
            ManifestCheckResult with compatibility status.
        """
        content = cached_manifest_content

        if content is None and self._manifest_cache is not None:
            cached = self._manifest_cache.get(source_id)
            if cached is not None:
                content = cached.get("raw_content")

        result = self._checker.check(content, cli_version)

        if result.status == CompatibilityResult.INCOMPATIBLE_WARN:
            logger.warning(
                "Deploy-time compatibility warning for source '%s': %s",
                source_id,
                result.message,
            )

        return result
