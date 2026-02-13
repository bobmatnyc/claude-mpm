"""Tests for skill-to-agent linking endpoints and SkillToAgentMapper.

Tests:
- Full bidirectional mapping endpoint
- Per-agent skill detail endpoint
- Pagination (cursor, limit, backward compat)
- Empty states (no agents, no skills)
- SkillToAgentMapper service logic
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from claude_mpm.services.monitor.handlers.skill_link_handler import SkillToAgentMapper

# --- SkillToAgentMapper Unit Tests ---


class TestSkillToAgentMapper:
    """Test SkillToAgentMapper in-memory bidirectional index."""

    def _make_agent_file(self, tmp_path: Path, name: str, content: str) -> Path:
        """Create a mock agent markdown file."""
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        agent_file = agents_dir / f"{name}.md"
        agent_file.write_text(content)
        return agent_file

    def test_empty_agents_dir(self, tmp_path):
        """Test mapper with no agents directory."""
        mapper = SkillToAgentMapper()
        with patch(
            "claude_mpm.services.monitor.handlers.skill_link_handler.Path"
        ) as mock_path:
            mock_cwd = MagicMock()
            mock_agents = MagicMock()
            mock_agents.exists.return_value = False
            mock_cwd.__truediv__ = MagicMock(return_value=mock_cwd)
            mock_cwd.__truediv__.side_effect = (
                lambda x: mock_agents if x == "agents" else mock_cwd
            )
            mock_path.cwd.return_value = mock_cwd

            mapper._build_index()

        assert mapper._initialized
        assert len(mapper._agent_to_skills) == 0
        assert len(mapper._skill_to_agents) == 0

    def test_agent_with_frontmatter_skills(self, tmp_path):
        """Test mapper extracts skills from YAML frontmatter."""
        content = """---
name: Engineer
skills:
- brainstorming
- git-workflow
- test-driven-development
---

# Engineer Agent

Instructions here.
"""
        self._make_agent_file(tmp_path, "engineer", content)

        mapper = SkillToAgentMapper()
        agents_dir = tmp_path / ".claude" / "agents"

        # Patch Path.cwd() and deployed skills
        with patch(
            "claude_mpm.services.monitor.handlers.skill_link_handler.Path"
        ) as mock_path:
            mock_path.cwd.return_value = tmp_path
            mapper._deployed_skill_names = {"brainstorming", "git-workflow"}
            mapper._initialized = False

            # Directly process the file
            mapper._process_agent_file("engineer", agents_dir / "engineer.md")

        assert "engineer" in mapper._agent_to_skills
        assert "brainstorming" in mapper._agent_to_skills["engineer"]["frontmatter"]
        assert "git-workflow" in mapper._agent_to_skills["engineer"]["frontmatter"]
        assert (
            "test-driven-development"
            in mapper._agent_to_skills["engineer"]["frontmatter"]
        )

    def test_agent_with_content_markers(self, tmp_path):
        """Test mapper extracts [SKILL: ...] markers from content body."""
        content = """---
name: PM Agent
---

# PM Agent

Use these skills:
**[SKILL: mpm-delegation-patterns]**
[SKILL: mpm-verification-protocols]
"""
        self._make_agent_file(tmp_path, "pm", content)

        mapper = SkillToAgentMapper()
        agents_dir = tmp_path / ".claude" / "agents"
        mapper._deployed_skill_names = set()

        mapper._process_agent_file("pm", agents_dir / "pm.md")

        assert "pm" in mapper._agent_to_skills
        assert (
            "mpm-delegation-patterns"
            in mapper._agent_to_skills["pm"]["content_markers"]
        )
        assert (
            "mpm-verification-protocols"
            in mapper._agent_to_skills["pm"]["content_markers"]
        )

    def test_agent_with_dict_skills_format(self, tmp_path):
        """Test mapper handles required/optional dict format."""
        content = """---
name: Python Engineer
skills:
  required:
  - python-core
  - testing-patterns
  optional:
  - code-review
---

# Python Engineer
"""
        self._make_agent_file(tmp_path, "python-engineer", content)

        mapper = SkillToAgentMapper()
        agents_dir = tmp_path / ".claude" / "agents"
        mapper._deployed_skill_names = set()

        mapper._process_agent_file("python-engineer", agents_dir / "python-engineer.md")

        fm_skills = mapper._agent_to_skills["python-engineer"]["frontmatter"]
        assert "python-core" in fm_skills
        assert "testing-patterns" in fm_skills
        assert "code-review" in fm_skills

    def test_bidirectional_index(self, tmp_path):
        """Test reverse index (skill -> agents) is built correctly."""
        eng_content = """---
name: Engineer
skills:
- shared-skill
- engineer-only
---
"""
        qa_content = """---
name: QA
skills:
- shared-skill
- qa-only
---
"""
        self._make_agent_file(tmp_path, "engineer", eng_content)
        self._make_agent_file(tmp_path, "qa", qa_content)

        mapper = SkillToAgentMapper()
        agents_dir = tmp_path / ".claude" / "agents"
        mapper._deployed_skill_names = set()

        mapper._process_agent_file("engineer", agents_dir / "engineer.md")
        mapper._process_agent_file("qa", agents_dir / "qa.md")

        # shared-skill should have both agents
        assert "engineer" in mapper._skill_to_agents["shared-skill"]["agents"]
        assert "qa" in mapper._skill_to_agents["shared-skill"]["agents"]

        # engineer-only should only have engineer
        assert "engineer" in mapper._skill_to_agents["engineer-only"]["agents"]
        assert "qa" not in mapper._skill_to_agents["engineer-only"]["agents"]

    def test_get_stats(self, tmp_path):
        """Test statistics calculation."""
        content = """---
name: Agent
skills:
- skill-a
- skill-b
---
"""
        self._make_agent_file(tmp_path, "agent", content)

        mapper = SkillToAgentMapper()
        agents_dir = tmp_path / ".claude" / "agents"
        mapper._deployed_skill_names = {"skill-a"}

        mapper._process_agent_file("agent", agents_dir / "agent.md")
        mapper._initialized = True

        stats = mapper.get_stats()
        assert stats["total_agents"] == 1
        assert stats["total_skills"] == 2
        assert stats["deployed_skills"] == 1
        assert stats["avg_skills_per_agent"] == 2.0
        assert stats["avg_agents_per_skill"] == 1.0

    def test_get_agent_skills_not_found(self):
        """Test get_agent_skills returns None for unknown agent."""
        mapper = SkillToAgentMapper()
        mapper._initialized = True

        result = mapper.get_agent_skills("nonexistent")
        assert result is None

    def test_get_all_links_serializable(self, tmp_path):
        """Test that get_all_links returns JSON-serializable data."""
        content = """---
name: Test
skills:
- test-skill
---
"""
        self._make_agent_file(tmp_path, "test", content)

        mapper = SkillToAgentMapper()
        agents_dir = tmp_path / ".claude" / "agents"
        mapper._deployed_skill_names = {"test-skill"}

        mapper._process_agent_file("test", agents_dir / "test.md")
        mapper._initialized = True

        links = mapper.get_all_links()
        # Should be JSON-serializable (no sets)
        json_str = json.dumps(links)
        assert "test-skill" in json_str
        assert "test" in json_str

    def test_invalidate_resets_state(self, tmp_path):
        """Test that invalidate() clears cached data."""
        mapper = SkillToAgentMapper()
        mapper._initialized = True
        mapper._agent_to_skills["test"] = {
            "frontmatter": set(),
            "content_markers": set(),
        }

        mapper.invalidate()

        assert not mapper._initialized
        assert len(mapper._agent_to_skills) == 0


# --- Pagination Tests ---


class TestPagination:
    """Test cursor-based pagination utility."""

    def test_no_pagination_returns_all(self):
        from claude_mpm.services.monitor.pagination import paginate

        items = [{"name": f"item-{i}"} for i in range(10)]
        result = paginate(items)

        assert len(result.items) == 10
        assert result.total == 10
        assert not result.has_more
        assert result.next_cursor is None
        assert result.limit is None

    def test_limit_returns_subset(self):
        from claude_mpm.services.monitor.pagination import paginate

        items = [{"name": f"item-{i}"} for i in range(10)]
        result = paginate(items, limit=3)

        assert len(result.items) == 3
        assert result.total == 10
        assert result.has_more
        assert result.next_cursor is not None
        assert result.limit == 3

    def test_cursor_continues_from_offset(self):
        from claude_mpm.services.monitor.pagination import _encode_cursor, paginate

        items = [{"name": f"item-{i}"} for i in range(10)]
        cursor = _encode_cursor(5)
        result = paginate(items, limit=3, cursor=cursor)

        assert len(result.items) == 3
        assert result.items[0]["name"] == "item-5"
        assert result.has_more

    def test_last_page_no_more(self):
        from claude_mpm.services.monitor.pagination import _encode_cursor, paginate

        items = [{"name": f"item-{i}"} for i in range(10)]
        cursor = _encode_cursor(8)
        result = paginate(items, limit=5)

        # From start, limit=5 on 10 items
        result = paginate(items, limit=5, cursor=_encode_cursor(5))
        assert len(result.items) == 5
        assert not result.has_more

    def test_max_limit_clamped(self):
        from claude_mpm.services.monitor.pagination import MAX_LIMIT, paginate

        items = [{"name": f"item-{i}"} for i in range(200)]
        result = paginate(items, limit=500)

        assert result.limit == MAX_LIMIT
        assert len(result.items) == MAX_LIMIT

    def test_sort_key(self):
        from claude_mpm.services.monitor.pagination import paginate

        items = [{"name": "charlie"}, {"name": "alpha"}, {"name": "bravo"}]
        result = paginate(items, limit=3, sort_key=lambda x: x["name"])

        assert result.items[0]["name"] == "alpha"
        assert result.items[1]["name"] == "bravo"
        assert result.items[2]["name"] == "charlie"

    def test_sort_desc(self):
        from claude_mpm.services.monitor.pagination import paginate

        items = [{"name": "alpha"}, {"name": "charlie"}, {"name": "bravo"}]
        result = paginate(items, limit=3, sort_key=lambda x: x["name"], sort_desc=True)

        assert result.items[0]["name"] == "charlie"

    def test_invalid_cursor_defaults_to_zero(self):
        from claude_mpm.services.monitor.pagination import paginate

        items = [{"name": f"item-{i}"} for i in range(5)]
        result = paginate(items, limit=3, cursor="invalid-garbage")

        assert len(result.items) == 3
        assert result.items[0]["name"] == "item-0"

    def test_empty_items(self):
        from claude_mpm.services.monitor.pagination import paginate

        result = paginate([], limit=10)
        assert len(result.items) == 0
        assert result.total == 0
        assert not result.has_more

    def test_paginated_json_format(self):
        from claude_mpm.services.monitor.pagination import paginate, paginated_json

        items = [{"name": f"item-{i}"} for i in range(10)]
        result = paginate(items, limit=3)
        json_data = paginated_json(result, items_key="agents")

        assert json_data["success"] is True
        assert len(json_data["agents"]) == 3
        assert json_data["total"] == 10
        assert "pagination" in json_data
        assert json_data["pagination"]["has_more"] is True

    def test_paginated_json_no_pagination_metadata(self):
        from claude_mpm.services.monitor.pagination import paginate, paginated_json

        items = [{"name": "only"}]
        result = paginate(items)
        json_data = paginated_json(result, items_key="items")

        assert json_data["success"] is True
        assert "pagination" not in json_data


# --- Route Handler Tests (with mocking) ---


class TestSkillLinksEndpoints:
    """Test the HTTP endpoint handlers for skill links."""

    @pytest.fixture
    def mock_mapper(self):
        """Create a mock SkillToAgentMapper."""
        mapper = MagicMock()
        mapper.get_all_links.return_value = {
            "by_agent": {
                "engineer": {
                    "frontmatter_skills": ["brainstorming", "git-workflow"],
                    "content_marker_skills": [],
                    "total": 2,
                },
            },
            "by_skill": {
                "brainstorming": {
                    "agents": ["engineer"],
                    "sources": ["frontmatter"],
                    "is_deployed": True,
                },
            },
        }
        mapper.get_stats.return_value = {
            "total_agents": 1,
            "total_skills": 1,
            "deployed_skills": 1,
            "avg_agents_per_skill": 1.0,
            "avg_skills_per_agent": 2.0,
        }
        mapper.get_agent_skills.return_value = {
            "agent_name": "engineer",
            "skills": [
                {"name": "brainstorming", "source": "frontmatter", "is_deployed": True},
            ],
            "frontmatter_skills": ["brainstorming"],
            "content_marker_skills": [],
            "total": 1,
        }
        return mapper

    @pytest.mark.asyncio
    async def test_handle_skill_links_success(self, mock_mapper):
        """Test GET /api/config/skill-links/ returns mapping."""
        from claude_mpm.services.monitor.config_routes import handle_skill_links

        request = MagicMock()
        request.query = {}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skill_to_agent_mapper",
            return_value=mock_mapper,
        ):
            response = await handle_skill_links(request)

        data = json.loads(response.body)
        assert data["success"] is True
        assert "by_agent" in data
        assert "by_skill" in data
        assert "stats" in data

    @pytest.mark.asyncio
    async def test_handle_skill_links_agent_found(self, mock_mapper):
        """Test GET /api/config/skill-links/agent/{name} returns agent skills."""
        from claude_mpm.services.monitor.config_routes import handle_skill_links_agent

        request = MagicMock()
        request.match_info = {"agent_name": "engineer"}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skill_to_agent_mapper",
            return_value=mock_mapper,
        ):
            response = await handle_skill_links_agent(request)

        data = json.loads(response.body)
        assert data["success"] is True
        assert data["data"]["agent_name"] == "engineer"

    @pytest.mark.asyncio
    async def test_handle_skill_links_agent_not_found(self, mock_mapper):
        """Test GET /api/config/skill-links/agent/{name} returns 404."""
        from claude_mpm.services.monitor.config_routes import handle_skill_links_agent

        mock_mapper.get_agent_skills.return_value = None

        request = MagicMock()
        request.match_info = {"agent_name": "nonexistent"}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skill_to_agent_mapper",
            return_value=mock_mapper,
        ):
            response = await handle_skill_links_agent(request)

        assert response.status == 404
        data = json.loads(response.body)
        assert data["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_handle_skill_links_with_pagination(self, mock_mapper):
        """Test GET /api/config/skill-links/ with pagination params."""
        from claude_mpm.services.monitor.config_routes import handle_skill_links

        request = MagicMock()
        request.query = {"limit": "1", "sort": "asc"}

        with patch(
            "claude_mpm.services.monitor.config_routes._get_skill_to_agent_mapper",
            return_value=mock_mapper,
        ):
            response = await handle_skill_links(request)

        data = json.loads(response.body)
        assert data["success"] is True
        assert "pagination" in data
