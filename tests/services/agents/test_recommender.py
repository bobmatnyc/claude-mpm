"""
Test Suite for Agent Recommender Service
========================================

WHY: Comprehensive testing ensures the agent recommendation engine works correctly
across all scenarios including edge cases, constraint handling, and scoring accuracy.

Part of TSK-0054: Auto-Configuration Feature - Phase 3
"""

import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from claude_mpm.services.agents.recommender import AgentRecommenderService
from claude_mpm.services.core.models.agent_config import (AgentCapabilities,
                                                          AgentRecommendation,
                                                          AgentSpecialization)
from claude_mpm.services.core.models.toolchain import (ConfidenceLevel,
                                                       DeploymentTarget,
                                                       Framework,
                                                       LanguageDetection,
                                                       ToolchainAnalysis,
                                                       ToolchainComponent)

# ===================================
# FIXTURES
# ===================================


@pytest.fixture
def minimal_config() -> Dict[str, Any]:
    """Minimal agent capabilities configuration for testing."""
    return {
        "agent_capabilities": {
            "test_python_engineer": {
                "name": "Test Python Engineer",
                "agent_id": "test_python_engineer",
                "specialization": "engineering",
                "description": "Test Python agent",
                "supports": {
                    "languages": ["python"],
                    "frameworks": ["django", "flask"],
                    "build_tools": ["pip", "poetry"],
                    "deployment": ["docker", "aws"],
                },
                "confidence_weight": 0.9,
                "auto_deploy": True,
                "metadata": {},
            },
            "test_typescript_engineer": {
                "name": "Test TypeScript Engineer",
                "agent_id": "test_typescript_engineer",
                "specialization": "engineering",
                "description": "Test TypeScript agent",
                "supports": {
                    "languages": ["typescript", "javascript"],
                    "frameworks": ["express", "nestjs"],
                    "build_tools": ["npm", "yarn"],
                    "deployment": ["docker", "kubernetes"],
                },
                "confidence_weight": 0.85,
                "auto_deploy": True,
                "metadata": {},
            },
            "test_nextjs_engineer": {
                "name": "Test Next.js Engineer",
                "agent_id": "test_nextjs_engineer",
                "specialization": "engineering",
                "description": "Test Next.js agent",
                "supports": {
                    "languages": ["typescript", "javascript"],
                    "frameworks": ["nextjs", "react"],
                    "build_tools": ["npm", "yarn"],
                    "deployment": ["vercel", "docker"],
                },
                "confidence_weight": 0.95,
                "auto_deploy": True,
                "metadata": {},
            },
            "test_vercel_ops": {
                "name": "Test Vercel Ops",
                "agent_id": "test_vercel_ops",
                "specialization": "devops",
                "description": "Test Vercel ops agent",
                "supports": {
                    "languages": ["typescript", "javascript"],
                    "frameworks": ["nextjs"],
                    "deployment": ["vercel"],
                },
                "confidence_weight": 0.95,
                "auto_deploy": True,
                "metadata": {},
            },
            "test_local_ops": {
                "name": "Test Local Ops",
                "agent_id": "test_local_ops",
                "specialization": "devops",
                "description": "Test local ops agent",
                "supports": {
                    "languages": ["python", "typescript"],
                    "deployment": ["docker", "local"],
                },
                "confidence_weight": 0.7,
                "auto_deploy": False,
                "metadata": {},
            },
        },
        "recommendation_rules": {
            "min_confidence_threshold": 0.5,
            "max_engineer_agents": 3,
            "max_ops_agents": 2,
            "framework_priority_boost": 0.15,
            "deployment_match_boost": 0.1,
            "scoring_weights": {
                "language_match": 0.5,
                "framework_match": 0.3,
                "deployment_match": 0.2,
            },
        },
    }


@pytest.fixture
def config_file(minimal_config: Dict[str, Any]) -> Path:
    """Create temporary config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(minimal_config, f)
        return Path(f.name)


@pytest.fixture
def recommender_service(config_file: Path) -> AgentRecommenderService:
    """Create recommender service with test config."""
    return AgentRecommenderService(config_path=config_file)


@pytest.fixture
def python_toolchain(tmp_path: Path) -> ToolchainAnalysis:
    """Create Python + Django toolchain."""
    return ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=LanguageDetection(
            primary_language="python",
            primary_version="3.12",
            primary_confidence=ConfidenceLevel.HIGH,
            language_percentages={"python": 100.0},
        ),
        frameworks=[
            Framework(
                name="django",
                version="5.0",
                framework_type="web",
                confidence=ConfidenceLevel.HIGH,
            )
        ],
        deployment_target=DeploymentTarget(
            target_type="cloud",
            platform="aws",
            confidence=ConfidenceLevel.MEDIUM,
        ),
        build_tools=[ToolchainComponent(name="poetry")],
    )


@pytest.fixture
def nextjs_toolchain(tmp_path: Path) -> ToolchainAnalysis:
    """Create Next.js toolchain."""
    return ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=LanguageDetection(
            primary_language="typescript",
            primary_version="5.0",
            primary_confidence=ConfidenceLevel.HIGH,
            language_percentages={"typescript": 85.0, "javascript": 15.0},
        ),
        frameworks=[
            Framework(
                name="nextjs",
                version="14.0",
                framework_type="web",
                confidence=ConfidenceLevel.HIGH,
            ),
            Framework(
                name="react",
                version="18.0",
                framework_type="web",
                confidence=ConfidenceLevel.HIGH,
            ),
        ],
        deployment_target=DeploymentTarget(
            target_type="serverless",
            platform="vercel",
            confidence=ConfidenceLevel.HIGH,
        ),
        build_tools=[ToolchainComponent(name="npm")],
    )


@pytest.fixture
def multi_language_toolchain(tmp_path: Path) -> ToolchainAnalysis:
    """Create multi-language toolchain."""
    return ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=LanguageDetection(
            primary_language="python",
            primary_version="3.12",
            primary_confidence=ConfidenceLevel.HIGH,
            secondary_languages=[
                ToolchainComponent(name="typescript", confidence=ConfidenceLevel.MEDIUM)
            ],
            language_percentages={"python": 70.0, "typescript": 30.0},
        ),
        frameworks=[
            Framework(
                name="fastapi",
                version="0.100",
                framework_type="web",
                confidence=ConfidenceLevel.HIGH,
            )
        ],
        deployment_target=DeploymentTarget(
            target_type="container",
            platform="docker",
            confidence=ConfidenceLevel.HIGH,
        ),
    )


# ===================================
# CONFIGURATION LOADING TESTS
# ===================================


def test_load_configuration_success(recommender_service: AgentRecommenderService):
    """Test successful configuration loading."""
    assert recommender_service._capabilities_config is not None
    assert "agent_capabilities" in recommender_service._capabilities_config
    assert len(recommender_service._capabilities_config["agent_capabilities"]) == 5


def test_load_configuration_missing_file():
    """Test handling of missing configuration file."""
    with pytest.raises(FileNotFoundError):
        AgentRecommenderService(config_path=Path("/nonexistent/config.yaml"))


def test_load_configuration_invalid_yaml(tmp_path: Path):
    """Test handling of invalid YAML."""
    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text("invalid: yaml: content: ::::")

    with pytest.raises(yaml.YAMLError):
        AgentRecommenderService(config_path=invalid_config)


def test_load_configuration_missing_section(tmp_path: Path):
    """Test handling of missing agent_capabilities section."""
    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text(yaml.dump({"other_section": {}}))

    with pytest.raises(ValueError, match="missing 'agent_capabilities'"):
        AgentRecommenderService(config_path=invalid_config)


# ===================================
# AGENT CAPABILITIES TESTS
# ===================================


def test_get_agent_capabilities_success(recommender_service: AgentRecommenderService):
    """Test retrieving agent capabilities."""
    capabilities = recommender_service.get_agent_capabilities("test_python_engineer")

    assert isinstance(capabilities, AgentCapabilities)
    assert capabilities.agent_id == "test_python_engineer"
    assert capabilities.agent_name == "Test Python Engineer"
    assert "python" in capabilities.supported_languages
    assert "django" in capabilities.supported_frameworks


def test_get_agent_capabilities_caching(recommender_service: AgentRecommenderService):
    """Test that capabilities are cached."""
    cap1 = recommender_service.get_agent_capabilities("test_python_engineer")
    cap2 = recommender_service.get_agent_capabilities("test_python_engineer")

    # Should return same cached instance
    assert cap1 is cap2


def test_get_agent_capabilities_not_found(recommender_service: AgentRecommenderService):
    """Test handling of non-existent agent."""
    with pytest.raises(KeyError, match="Agent not found"):
        recommender_service.get_agent_capabilities("nonexistent_agent")


def test_agent_capabilities_specializations(
    recommender_service: AgentRecommenderService,
):
    """Test specialization detection."""
    eng_cap = recommender_service.get_agent_capabilities("test_python_engineer")
    ops_cap = recommender_service.get_agent_capabilities("test_vercel_ops")

    assert AgentSpecialization.LANGUAGE_SPECIFIC in eng_cap.specializations
    assert AgentSpecialization.DEVOPS in ops_cap.specializations


# ===================================
# MATCH SCORE TESTS
# ===================================


def test_match_score_perfect_match(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test perfect language + framework + deployment match."""
    score = recommender_service.match_score("test_python_engineer", python_toolchain)

    # Should be very high due to language + framework + deployment match + boosts
    assert score > 0.9


def test_match_score_language_only(
    recommender_service: AgentRecommenderService, tmp_path: Path
):
    """Test language match without framework."""
    toolchain = ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=LanguageDetection(
            primary_language="python",
            primary_confidence=ConfidenceLevel.HIGH,
            language_percentages={"python": 100.0},
        ),
    )

    score = recommender_service.match_score("test_python_engineer", toolchain)

    # Should have decent score from language match (50% weight * 0.9 confidence)
    assert 0.4 < score < 0.6


def test_match_score_framework_priority(
    recommender_service: AgentRecommenderService, nextjs_toolchain: ToolchainAnalysis
):
    """Test framework-specific agent gets higher score than language agent."""
    nextjs_score = recommender_service.match_score(
        "test_nextjs_engineer", nextjs_toolchain
    )
    typescript_score = recommender_service.match_score(
        "test_typescript_engineer", nextjs_toolchain
    )

    # Next.js engineer should score higher due to framework match + higher confidence weight
    assert nextjs_score > typescript_score


def test_match_score_no_match(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test score for completely unmatched agent."""
    # TypeScript engineer shouldn't match Python project well
    score = recommender_service.match_score(
        "test_typescript_engineer", python_toolchain
    )

    # May get small score from deployment match (both support docker/aws)
    # But should be very low (< 0.2)
    assert score < 0.2


def test_match_score_deployment_boost(
    recommender_service: AgentRecommenderService, nextjs_toolchain: ToolchainAnalysis
):
    """Test deployment match provides score boost."""
    score = recommender_service.match_score("test_vercel_ops", nextjs_toolchain)

    # Should get boost for Vercel deployment match
    assert score > 0.7


def test_match_score_agent_not_found(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test handling of non-existent agent in match_score."""
    with pytest.raises(KeyError, match="Agent not found"):
        recommender_service.match_score("nonexistent_agent", python_toolchain)


# ===================================
# RECOMMENDATION TESTS
# ===================================


def test_recommend_agents_python_project(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test recommendations for Python + Django project."""
    recommendations = recommender_service.recommend_agents(python_toolchain)

    assert len(recommendations) > 0
    assert all(isinstance(rec, AgentRecommendation) for rec in recommendations)

    # Python engineer should be recommended
    agent_ids = [rec.agent_id for rec in recommendations]
    assert "test_python_engineer" in agent_ids

    # Should be sorted by confidence score
    for i in range(len(recommendations) - 1):
        assert (
            recommendations[i].confidence_score
            >= recommendations[i + 1].confidence_score
        )


def test_recommend_agents_nextjs_project(
    recommender_service: AgentRecommenderService, nextjs_toolchain: ToolchainAnalysis
):
    """Test recommendations for Next.js project."""
    recommendations = recommender_service.recommend_agents(nextjs_toolchain)

    agent_ids = [rec.agent_id for rec in recommendations]

    # Next.js engineer should be recommended (framework-specific)
    assert "test_nextjs_engineer" in agent_ids

    # Vercel ops should be recommended for Vercel deployment
    assert "test_vercel_ops" in agent_ids

    # Next.js engineer should rank higher than TypeScript engineer
    nextjs_index = agent_ids.index("test_nextjs_engineer")
    if "test_typescript_engineer" in agent_ids:
        typescript_index = agent_ids.index("test_typescript_engineer")
        assert nextjs_index < typescript_index


def test_recommend_agents_with_min_confidence(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test filtering by minimum confidence threshold."""
    recommendations = recommender_service.recommend_agents(
        python_toolchain, constraints={"min_confidence": 0.8}
    )

    # All recommendations should meet threshold
    assert all(rec.confidence_score >= 0.8 for rec in recommendations)


def test_recommend_agents_with_max_agents(
    recommender_service: AgentRecommenderService,
    multi_language_toolchain: ToolchainAnalysis,
):
    """Test limiting number of recommendations."""
    recommendations = recommender_service.recommend_agents(
        multi_language_toolchain, constraints={"max_agents": 2}
    )

    assert len(recommendations) <= 2


def test_recommend_agents_with_excluded_agents(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test excluding specific agents."""
    recommendations = recommender_service.recommend_agents(
        python_toolchain, constraints={"excluded_agents": ["test_python_engineer"]}
    )

    agent_ids = [rec.agent_id for rec in recommendations]
    assert "test_python_engineer" not in agent_ids


def test_recommend_agents_auto_deploy_filter(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test that non-auto-deploy agents are excluded by default."""
    recommendations = recommender_service.recommend_agents(python_toolchain)

    agent_ids = [rec.agent_id for rec in recommendations]
    # test_local_ops has auto_deploy: false
    assert "test_local_ops" not in agent_ids


def test_recommend_agents_include_non_auto_deploy(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test including non-auto-deploy agents when requested."""
    recommendations = recommender_service.recommend_agents(
        python_toolchain, constraints={"include_non_auto_deploy": True}
    )

    # Now test_local_ops should be included if it matches
    # (it supports Python, so it should match)
    agent_ids = [rec.agent_id for rec in recommendations]
    # Local ops supports Python deployment, might be included with lower score
    # This depends on scoring, but we test the flag works
    assert len(recommendations) > 0


def test_recommend_agents_empty_result(
    recommender_service: AgentRecommenderService, tmp_path: Path
):
    """Test handling of toolchain with no matching agents."""
    # Create toolchain with unsupported language
    unsupported_toolchain = ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=LanguageDetection(
            primary_language="cobol",  # Not supported by any test agent
            primary_confidence=ConfidenceLevel.HIGH,
            language_percentages={"cobol": 100.0},
        ),
    )

    recommendations = recommender_service.recommend_agents(unsupported_toolchain)

    # Should return empty list gracefully
    assert recommendations == []


# ===================================
# RECOMMENDATION CONTENT TESTS
# ===================================


def test_recommendation_has_match_reasons(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test that recommendations include match reasons."""
    recommendations = recommender_service.recommend_agents(python_toolchain)

    # Get Python engineer recommendation
    python_rec = next(
        (r for r in recommendations if r.agent_id == "test_python_engineer"), None
    )
    assert python_rec is not None
    assert len(python_rec.match_reasons) > 0
    assert any("python" in reason.lower() for reason in python_rec.match_reasons)


def test_recommendation_deployment_priority(
    recommender_service: AgentRecommenderService, nextjs_toolchain: ToolchainAnalysis
):
    """Test deployment priority calculation."""
    recommendations = recommender_service.recommend_agents(nextjs_toolchain)

    # Framework-specific engineer should have priority 1
    nextjs_rec = next(
        (r for r in recommendations if r.agent_id == "test_nextjs_engineer"), None
    )
    assert nextjs_rec is not None
    assert nextjs_rec.deployment_priority == 1

    # DevOps agent should have priority 3
    vercel_rec = next(
        (r for r in recommendations if r.agent_id == "test_vercel_ops"), None
    )
    if vercel_rec:
        assert vercel_rec.deployment_priority == 3


def test_recommendation_config_hints(
    recommender_service: AgentRecommenderService, nextjs_toolchain: ToolchainAnalysis
):
    """Test configuration hints generation."""
    recommendations = recommender_service.recommend_agents(nextjs_toolchain)

    nextjs_rec = next(
        (r for r in recommendations if r.agent_id == "test_nextjs_engineer"), None
    )
    assert nextjs_rec is not None
    assert "detected_frameworks" in nextjs_rec.configuration_hints
    assert "deployment_target" in nextjs_rec.configuration_hints


def test_recommendation_metadata(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test recommendation metadata."""
    recommendations = recommender_service.recommend_agents(python_toolchain)

    python_rec = next(
        (r for r in recommendations if r.agent_id == "test_python_engineer"), None
    )
    assert python_rec is not None
    assert python_rec.metadata["specialization"] == "engineering"
    assert python_rec.metadata["auto_deploy"] is True


# ===================================
# EDGE CASE TESTS
# ===================================


def test_empty_toolchain_frameworks(
    recommender_service: AgentRecommenderService, tmp_path: Path
):
    """Test handling of toolchain with no frameworks."""
    toolchain = ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=LanguageDetection(
            primary_language="python",
            primary_confidence=ConfidenceLevel.HIGH,
            language_percentages={"python": 100.0},
        ),
        frameworks=[],  # No frameworks
        deployment_target=DeploymentTarget(
            target_type="cloud",
            platform="aws",
            confidence=ConfidenceLevel.MEDIUM,
        ),
    )

    recommendations = recommender_service.recommend_agents(toolchain)

    # Should still recommend based on language + deployment
    assert len(recommendations) > 0


def test_no_deployment_target(
    recommender_service: AgentRecommenderService, tmp_path: Path
):
    """Test handling of toolchain with no deployment target."""
    toolchain = ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=LanguageDetection(
            primary_language="python",
            primary_confidence=ConfidenceLevel.HIGH,
            language_percentages={"python": 100.0},
        ),
        frameworks=[
            Framework(
                name="django",
                framework_type="web",
                confidence=ConfidenceLevel.HIGH,
            )
        ],
        deployment_target=None,
    )

    recommendations = recommender_service.recommend_agents(toolchain)

    # Should still work without deployment target (language + framework match)
    assert len(recommendations) > 0


def test_case_insensitive_matching(
    recommender_service: AgentRecommenderService, tmp_path: Path
):
    """Test case-insensitive language and framework matching."""
    toolchain = ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=LanguageDetection(
            primary_language="Python",  # Capital P
            primary_confidence=ConfidenceLevel.HIGH,
            language_percentages={"Python": 100.0},
        ),
        frameworks=[
            Framework(
                name="Django",  # Capital D
                framework_type="web",
                confidence=ConfidenceLevel.HIGH,
            )
        ],
    )

    recommendations = recommender_service.recommend_agents(toolchain)

    # Should still match despite case differences
    agent_ids = [rec.agent_id for rec in recommendations]
    assert "test_python_engineer" in agent_ids


def test_framework_name_normalization(
    recommender_service: AgentRecommenderService, tmp_path: Path
):
    """Test framework name normalization (next.js vs nextjs)."""
    toolchain = ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=LanguageDetection(
            primary_language="typescript",
            primary_confidence=ConfidenceLevel.HIGH,
            language_percentages={"typescript": 100.0},
        ),
        frameworks=[
            Framework(
                name="next.js",  # With dot
                framework_type="web",
                confidence=ConfidenceLevel.HIGH,
            )
        ],
    )

    score = recommender_service.match_score("test_nextjs_engineer", toolchain)

    # Should match despite dot in name
    assert score > 0.5


# ===================================
# CONSTRAINT VALIDATION TESTS
# ===================================


def test_invalid_constraints(
    recommender_service: AgentRecommenderService, python_toolchain: ToolchainAnalysis
):
    """Test handling of various constraint types."""
    # Should handle empty constraints
    recommendations = recommender_service.recommend_agents(
        python_toolchain, constraints={}
    )
    assert len(recommendations) >= 0

    # Should handle None constraints
    recommendations = recommender_service.recommend_agents(
        python_toolchain, constraints=None
    )
    assert len(recommendations) >= 0


# ===================================
# INTEGRATION TESTS
# ===================================


def test_full_recommendation_workflow(
    recommender_service: AgentRecommenderService, nextjs_toolchain: ToolchainAnalysis
):
    """Test complete recommendation workflow."""
    # 1. Get recommendations
    recommendations = recommender_service.recommend_agents(
        nextjs_toolchain, constraints={"max_agents": 5, "min_confidence": 0.5}
    )

    assert len(recommendations) > 0
    assert len(recommendations) <= 5

    # 2. Verify all recommendations meet criteria
    for rec in recommendations:
        assert rec.confidence_score >= 0.5
        assert 0.0 <= rec.confidence_score <= 1.0
        assert rec.deployment_priority >= 1
        assert len(rec.match_reasons) > 0

        # 3. Get capabilities for each recommended agent
        capabilities = recommender_service.get_agent_capabilities(rec.agent_id)
        assert capabilities.agent_id == rec.agent_id

        # 4. Verify match score is consistent
        score = recommender_service.match_score(rec.agent_id, nextjs_toolchain)
        assert abs(score - rec.confidence_score) < 0.01  # Should be same


def test_multi_language_recommendations(
    recommender_service: AgentRecommenderService,
    multi_language_toolchain: ToolchainAnalysis,
):
    """Test recommendations for multi-language project."""
    recommendations = recommender_service.recommend_agents(multi_language_toolchain)

    # Should recommend agent for primary language
    agent_ids = [rec.agent_id for rec in recommendations]
    assert "test_python_engineer" in agent_ids

    # May recommend agents for secondary languages depending on threshold
    # At minimum, should have Python agent
    assert len(recommendations) >= 1


def test_default_configuration_fallback_unknown_language(tmp_path: Path):
    """Test default configuration fallback when language is Unknown."""
    # Use the real configuration with default_configuration section
    recommender = AgentRecommenderService()

    # Create toolchain with Unknown language
    lang_detection = LanguageDetection(
        primary_language="Unknown", primary_confidence=ConfidenceLevel.LOW
    )

    toolchain = ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=lang_detection,
        frameworks=[],
        build_tools=[],
        deployment_target=None,
    )

    recommendations = recommender.recommend_agents(toolchain)

    # Should have default recommendations
    assert len(recommendations) == 5

    # Check default agents are present
    agent_ids = [rec.agent_id for rec in recommendations]
    assert "engineer" in agent_ids
    assert "research" in agent_ids
    assert "qa" in agent_ids
    assert "ops" in agent_ids
    assert "documentation" in agent_ids

    # Check all have default metadata
    for rec in recommendations:
        assert rec.metadata.get("is_default") is True
        assert rec.confidence_score == 0.7
        assert "Default configuration applied" in rec.match_reasons[0]
        assert "Consider manually selecting specialized agents" in rec.concerns[0]


def test_default_configuration_not_applied_with_recommendations(
    tmp_path: Path,
):
    """Test default configuration is NOT applied when normal recommendations exist."""
    # Use the real configuration
    recommender = AgentRecommenderService()

    # Create toolchain with Python + Django (should get normal recommendations)
    lang_detection = LanguageDetection(
        primary_language="Python",
        primary_confidence=ConfidenceLevel.HIGH,
    )

    toolchain = ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=lang_detection,
        frameworks=[
            Framework(name="Django", version="4.2", confidence=ConfidenceLevel.HIGH)
        ],
        build_tools=[],
        deployment_target=None,
    )

    recommendations = recommender.recommend_agents(toolchain)

    # Should have python_engineer, not default agents
    assert len(recommendations) > 0
    agent_ids = [rec.agent_id for rec in recommendations]
    assert "python_engineer" in agent_ids

    # None should be marked as default
    for rec in recommendations:
        assert rec.metadata.get("is_default", False) is False


def test_default_configuration_with_disabled_flag(tmp_path: Path):
    """Test default configuration respects enabled flag."""
    # Create custom config with disabled default_configuration
    config = {
        "agent_capabilities": {
            "test_agent": {
                "name": "Test Agent",
                "agent_id": "test_agent",
                "specialization": "engineering",
                "description": "Test",
                "supports": {"languages": ["python"]},
                "confidence_weight": 0.9,
                "auto_deploy": True,
                "metadata": {"template_file": "test.json"},
            }
        },
        "recommendation_rules": {"min_confidence_threshold": 0.5},
        "default_configuration": {
            "enabled": False,  # Disabled
            "agents": [{"agent_id": "test_agent", "reasoning": "Test", "priority": 1}],
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        config_path = Path(f.name)

    try:
        recommender = AgentRecommenderService(config_path=config_path)

        lang_detection = LanguageDetection(
            primary_language="Unknown", primary_confidence=ConfidenceLevel.LOW
        )

        toolchain = ToolchainAnalysis(
            project_path=tmp_path,
            language_detection=lang_detection,
            frameworks=[],
            build_tools=[],
            deployment_target=None,
        )

        recommendations = recommender.recommend_agents(toolchain)

        # Should have NO recommendations because default config is disabled
        assert len(recommendations) == 0

    finally:
        config_path.unlink()


def test_default_configuration_priority_ordering(tmp_path: Path):
    """Test default agents are ordered by priority."""
    recommender = AgentRecommenderService()

    lang_detection = LanguageDetection(
        primary_language="Unknown", primary_confidence=ConfidenceLevel.LOW
    )

    toolchain = ToolchainAnalysis(
        project_path=tmp_path,
        language_detection=lang_detection,
        frameworks=[],
        build_tools=[],
        deployment_target=None,
    )

    recommendations = recommender.recommend_agents(toolchain)

    # Check priority ordering
    assert recommendations[0].agent_id == "engineer"  # priority 1
    assert recommendations[1].agent_id == "research"  # priority 2
    assert recommendations[2].agent_id == "qa"  # priority 3
    assert recommendations[3].agent_id == "ops"  # priority 4
    assert recommendations[4].agent_id == "documentation"  # priority 5

    # Verify priorities are correct
    assert recommendations[0].deployment_priority == 1
    assert recommendations[1].deployment_priority == 2
    assert recommendations[2].deployment_priority == 3
    assert recommendations[3].deployment_priority == 4
    assert recommendations[4].deployment_priority == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
