"""Tests for prompt caching control and cache metrics.

Tests both Feature 1 (DISABLE_PROMPT_CACHING env var support) and
Feature 2 (cache metrics surfacing).
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from claude_mpm.config.api_provider import (
    APIBackend,
    APIProviderConfig,
)
from claude_mpm.services.infrastructure.context_usage_tracker import (
    ContextUsageTracker,
)


class TestDisablePromptCaching:
    """Tests for DISABLE_PROMPT_CACHING env var support."""

    def test_disable_prompt_caching_default_false(self):
        """By default, disable_prompt_caching is False and env var is not set."""
        # Clean env
        os.environ.pop("DISABLE_PROMPT_CACHING", None)
        os.environ.pop("CLAUDE_MPM_DISABLE_PROMPT_CACHING", None)

        config = APIProviderConfig()
        assert config.disable_prompt_caching is False

        changes = config.apply_environment()
        assert "DISABLE_PROMPT_CACHING" not in os.environ
        # The key should not appear in changes when it was never set
        assert changes.get("DISABLE_PROMPT_CACHING") is None

    def test_disable_prompt_caching_sets_env(self):
        """When config has disable_prompt_caching=True, verify DISABLE_PROMPT_CACHING=1."""
        # Clean env
        os.environ.pop("DISABLE_PROMPT_CACHING", None)
        os.environ.pop("CLAUDE_MPM_DISABLE_PROMPT_CACHING", None)

        config = APIProviderConfig(disable_prompt_caching=True)
        changes = config.apply_environment()

        assert os.environ.get("DISABLE_PROMPT_CACHING") == "1"
        assert changes["DISABLE_PROMPT_CACHING"] == "1"

        # Cleanup
        os.environ.pop("DISABLE_PROMPT_CACHING", None)

    def test_disable_prompt_caching_from_yaml(self):
        """Verify disable_prompt_caching is read from configuration.yaml."""
        yaml_content = {
            "api_provider": {
                "backend": "bedrock",
                "disable_prompt_caching": True,
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            f.flush()
            config = APIProviderConfig.load(Path(f.name))
            assert config.disable_prompt_caching is True
            os.unlink(f.name)

    def test_disable_prompt_caching_from_env_var(self):
        """Verify CLAUDE_MPM_DISABLE_PROMPT_CACHING=1 env var takes precedence."""
        os.environ["CLAUDE_MPM_DISABLE_PROMPT_CACHING"] = "1"
        try:
            # Even with YAML set to false, env var wins
            yaml_content = {
                "api_provider": {
                    "backend": "anthropic",
                    "disable_prompt_caching": False,
                }
            }

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                yaml.dump(yaml_content, f)
                f.flush()
                config = APIProviderConfig.load(Path(f.name))
                assert config.disable_prompt_caching is True
                os.unlink(f.name)
        finally:
            os.environ.pop("CLAUDE_MPM_DISABLE_PROMPT_CACHING", None)

    def test_disable_prompt_caching_env_var_true_variants(self):
        """Verify various truthy env var values are accepted."""
        for truthy_val in ["1", "true", "True", "TRUE", "yes", "YES"]:
            os.environ["CLAUDE_MPM_DISABLE_PROMPT_CACHING"] = truthy_val
            try:
                config = APIProviderConfig.load(Path("/nonexistent/path/config.yaml"))
                assert config.disable_prompt_caching is True, (
                    f"Expected True for env var value '{truthy_val}'"
                )
            finally:
                os.environ.pop("CLAUDE_MPM_DISABLE_PROMPT_CACHING", None)

    def test_disable_prompt_caching_unsets_when_disabled(self):
        """Verify env var is cleaned up when disable_prompt_caching is False."""
        # Simulate previous run setting the env var
        os.environ["DISABLE_PROMPT_CACHING"] = "1"

        config = APIProviderConfig(disable_prompt_caching=False)
        changes = config.apply_environment()

        assert "DISABLE_PROMPT_CACHING" not in os.environ
        assert changes.get("DISABLE_PROMPT_CACHING") == "(unset)"

    def test_disable_prompt_caching_saved_to_yaml(self):
        """Verify disable_prompt_caching is persisted when True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config = APIProviderConfig(
                backend=APIBackend.BEDROCK,
                disable_prompt_caching=True,
            )
            config.save(config_path)

            with open(config_path) as f:
                saved = yaml.safe_load(f)
            assert saved["api_provider"]["disable_prompt_caching"] is True

    def test_disable_prompt_caching_not_saved_when_false(self):
        """Verify disable_prompt_caching is omitted from YAML when False (default)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config = APIProviderConfig(
                backend=APIBackend.ANTHROPIC,
                disable_prompt_caching=False,
            )
            config.save(config_path)

            with open(config_path) as f:
                saved = yaml.safe_load(f)
            # Should not be in the saved YAML when False
            assert "disable_prompt_caching" not in saved["api_provider"]

    def test_provider_status_shows_cache_setting(self):
        """Verify to_dict includes disable_prompt_caching."""
        config = APIProviderConfig(disable_prompt_caching=True)
        d = config.to_dict()
        assert d["disable_prompt_caching"] is True

        config_default = APIProviderConfig()
        d_default = config_default.to_dict()
        assert d_default["disable_prompt_caching"] is False


class TestCacheMetrics:
    """Tests for cache metrics calculation and formatting."""

    def test_cache_hit_ratio_normal(self):
        """Verify ratio calculation with normal read/write values."""
        metrics = ContextUsageTracker.calculate_cache_metrics(
            cache_read=45230,
            cache_creation=12100,
        )
        # hit_rate = 45230 / (45230 + 12100) * 100 = 78.9%
        assert metrics["hit_rate"] == 78.9
        assert metrics["zero_reads_warning"] is False
        assert metrics["total_cache_tokens"] == 57330

    def test_cache_hit_ratio_all_reads(self):
        """Verify 100% hit rate when all tokens are reads."""
        metrics = ContextUsageTracker.calculate_cache_metrics(
            cache_read=50000,
            cache_creation=0,
        )
        assert metrics["hit_rate"] == 100.0
        assert metrics["zero_reads_warning"] is False

    def test_cache_hit_ratio_all_writes(self):
        """Verify 0% hit rate when all tokens are writes."""
        metrics = ContextUsageTracker.calculate_cache_metrics(
            cache_read=0,
            cache_creation=10000,
        )
        assert metrics["hit_rate"] == 0.0
        assert metrics["zero_reads_warning"] is True

    def test_cache_hit_ratio_zero_both(self):
        """Verify ratio is 0 when no cache activity."""
        metrics = ContextUsageTracker.calculate_cache_metrics(
            cache_read=0,
            cache_creation=0,
        )
        assert metrics["hit_rate"] == 0.0
        assert metrics["zero_reads_warning"] is False

    def test_zero_cache_reads_warning(self):
        """Verify warning when reads=0 but writes>0."""
        metrics = ContextUsageTracker.calculate_cache_metrics(
            cache_read=0,
            cache_creation=12100,
        )
        assert metrics["zero_reads_warning"] is True

    def test_no_zero_reads_warning_when_reads_present(self):
        """Verify no warning when reads are present."""
        metrics = ContextUsageTracker.calculate_cache_metrics(
            cache_read=1,
            cache_creation=12100,
        )
        assert metrics["zero_reads_warning"] is False

    def test_format_cache_summary_normal(self):
        """Verify formatted summary string for normal operation."""
        metrics = ContextUsageTracker.calculate_cache_metrics(
            cache_read=45230,
            cache_creation=12100,
        )
        summary = ContextUsageTracker.format_cache_summary(metrics)
        assert "45,230 read" in summary
        assert "12,100 written" in summary
        assert "78.9% hit rate" in summary
        assert "caching may not be working" not in summary

    def test_format_cache_summary_with_warning(self):
        """Verify formatted summary includes warning when reads=0."""
        metrics = ContextUsageTracker.calculate_cache_metrics(
            cache_read=0,
            cache_creation=12100,
        )
        summary = ContextUsageTracker.format_cache_summary(metrics)
        assert "0 read" in summary
        assert "12,100 written" in summary
        assert "0.0% hit rate" in summary
        assert "caching may not be working" in summary

    def test_usage_summary_includes_cache_metrics(self):
        """Verify get_usage_summary includes cache section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ContextUsageTracker(project_path=Path(tmpdir))
            tracker.update_usage(
                input_tokens=1000,
                output_tokens=500,
                cache_creation=200,
                cache_read=800,
            )
            summary = tracker.get_usage_summary()

            assert "cache" in summary
            cache = summary["cache"]
            assert cache["cache_read_tokens"] == 800
            assert cache["cache_creation_tokens"] == 200
            assert cache["total_cache_tokens"] == 1000
            assert cache["hit_rate"] == 80.0
            assert cache["zero_reads_warning"] is False
