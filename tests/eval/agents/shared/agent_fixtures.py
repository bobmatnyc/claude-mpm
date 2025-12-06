"""
Shared Fixtures for Agent Testing.

This module provides pytest fixtures for agent evaluation tests:
- Mock file systems
- Mock git repositories
- Mock deployment environments
- Sample code files for testing
- Agent template loading

Design Decision: Fixture-based dependency injection

Rationale: Pytest fixtures provide clean dependency injection, automatic cleanup,
and easy test isolation. Better than class-based setup for test infrastructure.

Trade-offs:
- Fixtures vs. Classes: Fixtures better for test state management
- Scope: Session/module/function scopes for performance vs. isolation
- Cleanup: Automatic via fixture teardown vs. manual

Example:
    def test_research_agent(mock_filesystem, sample_python_files):
        # Use mock filesystem with sample files
        analysis = agent.analyze_code(sample_python_files[0])
        assert analysis.file_size_checked
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest


# ============================================================================
# MOCK FILESYSTEM FIXTURES
# ============================================================================


@pytest.fixture
def temp_project_dir(tmp_path):
    """
    Create temporary project directory with basic structure.

    Returns:
        Path to temporary directory with src/, tests/, docs/ structure

    Example:
        def test_file_operations(temp_project_dir):
            src_dir = temp_project_dir / "src"
            assert src_dir.exists()
    """
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create standard directory structure
    (project_dir / "src").mkdir()
    (project_dir / "tests").mkdir()
    (project_dir / "docs").mkdir()
    (project_dir / ".git").mkdir()

    return project_dir


@pytest.fixture
def mock_filesystem(temp_project_dir):
    """
    Create mock filesystem with realistic file structure.

    Returns:
        Dict with paths to created files and metadata

    Structure:
        test_project/
        ├── src/
        │   ├── auth.py (50KB - large file)
        │   ├── models.py (15KB - medium)
        │   └── utils.py (5KB - small)
        ├── tests/
        │   ├── test_auth.py
        │   └── test_models.py
        └── docs/
            └── README.md

    Example:
        def test_large_file_handling(mock_filesystem):
            large_file = mock_filesystem["files"]["src/auth.py"]
            assert large_file["size"] > 20000  # >20KB
    """
    files = {}

    # Create auth.py (large file, 50KB)
    auth_path = temp_project_dir / "src" / "auth.py"
    auth_content = '"""\nAuthentication module.\n"""\n\n' + "# " + "x" * 50000
    auth_path.write_text(auth_content)
    files["src/auth.py"] = {
        "path": str(auth_path),
        "size": len(auth_content),
        "type": "python",
    }

    # Create models.py (medium file, 15KB)
    models_path = temp_project_dir / "src" / "models.py"
    models_content = '"""\nData models.\n"""\n\n' + "# " + "x" * 15000
    models_path.write_text(models_content)
    files["src/models.py"] = {
        "path": str(models_path),
        "size": len(models_content),
        "type": "python",
    }

    # Create utils.py (small file, 5KB)
    utils_path = temp_project_dir / "src" / "utils.py"
    utils_content = '"""\nUtility functions.\n"""\n\n' + "# " + "x" * 5000
    utils_path.write_text(utils_content)
    files["src/utils.py"] = {
        "path": str(utils_path),
        "size": len(utils_content),
        "type": "python",
    }

    # Create test files
    test_auth_path = temp_project_dir / "tests" / "test_auth.py"
    test_auth_path.write_text('"""Test auth module."""\n\ndef test_login():\n    pass\n')
    files["tests/test_auth.py"] = {
        "path": str(test_auth_path),
        "size": test_auth_path.stat().st_size,
        "type": "python_test",
    }

    return {
        "root": str(temp_project_dir),
        "files": files,
    }


@pytest.fixture
def sample_python_files():
    """
    Sample Python code files for testing.

    Returns:
        List of dicts with sample code, metadata

    Example:
        def test_code_analysis(sample_python_files):
            jwt_code = sample_python_files[0]
            assert "jwt" in jwt_code["content"].lower()
    """
    return [
        {
            "filename": "jwt_validator.py",
            "content": '''"""JWT token validation."""
import jwt
from datetime import datetime, timedelta

def validate_token(token: str) -> dict:
    """Validate JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {"valid": True, "payload": payload}
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "error": "Invalid token"}
''',
            "size": 400,
            "language": "python",
            "purpose": "Testing search-before-create (JWT validation exists)",
        },
        {
            "filename": "auth_service.py",
            "content": '''"""Authentication service."""
from typing import Optional

class AuthService:
    def __init__(self, db):
        self.db = db

    def login(self, username: str, password: str) -> Optional[str]:
        """Login user and return token."""
        user = self.db.find_user(username)
        if user and user.check_password(password):
            return self.generate_token(user)
        return None

    def generate_token(self, user) -> str:
        """Generate JWT token for user."""
        # Implementation here
        pass
''',
            "size": 500,
            "language": "python",
            "purpose": "Testing consolidation opportunities",
        },
    ]


@pytest.fixture
def sample_javascript_files():
    """
    Sample JavaScript code files for testing.

    Returns:
        List of dicts with sample JS code, metadata

    Example:
        def test_qa_package_json(sample_javascript_files):
            pkg = sample_javascript_files[0]
            assert pkg["filename"] == "package.json"
    """
    return [
        {
            "filename": "package.json",
            "content": '''{
  "name": "test-project",
  "version": "1.0.0",
  "scripts": {
    "test": "vitest",
    "test:ci": "vitest run"
  },
  "devDependencies": {
    "vitest": "^1.0.0"
  }
}''',
            "size": 200,
            "language": "json",
            "purpose": "Testing QA package.json inspection",
        },
        {
            "filename": "auth.test.js",
            "content": '''import { describe, it, expect } from 'vitest';
import { validateToken } from './auth';

describe('Authentication', () => {
  it('validates valid token', () => {
    const token = 'valid.jwt.token';
    expect(validateToken(token)).toBe(true);
  });

  it('rejects invalid token', () => {
    const token = 'invalid';
    expect(validateToken(token)).toBe(false);
  });
});
''',
            "size": 300,
            "language": "javascript",
            "purpose": "Testing QA test discovery",
        },
    ]


# ============================================================================
# MOCK GIT REPOSITORY FIXTURES
# ============================================================================


@pytest.fixture
def mock_git_repo(temp_project_dir):
    """
    Create mock git repository with history.

    Returns:
        Dict with git repo metadata

    Example:
        def test_git_operations(mock_git_repo):
            assert mock_git_repo["current_branch"] == "main"
    """
    git_dir = temp_project_dir / ".git"

    # Create basic git structure
    (git_dir / "refs" / "heads").mkdir(parents=True)
    (git_dir / "refs" / "heads" / "main").write_text("abc123def456\n")

    # Create HEAD
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")

    return {
        "root": str(temp_project_dir),
        "git_dir": str(git_dir),
        "current_branch": "main",
        "commits": [
            {"hash": "abc123", "message": "Initial commit"},
            {"hash": "def456", "message": "Add authentication"},
        ],
    }


# ============================================================================
# MOCK DEPLOYMENT ENVIRONMENT FIXTURES
# ============================================================================


@pytest.fixture
def mock_deployment_env():
    """
    Mock deployment environment configuration.

    Returns:
        Dict with environment variables, configs

    Example:
        def test_ops_deployment(mock_deployment_env):
            assert mock_deployment_env["env"]["NODE_ENV"] == "production"
    """
    return {
        "env": {
            "NODE_ENV": "production",
            "DATABASE_URL": "postgresql://localhost/prod",
            "API_KEY": "mock_api_key",  # pragma: allowlist secret
        },
        "services": {
            "api": {"port": 3000, "replicas": 3},
            "database": {"port": 5432, "replicas": 2},
        },
        "health_checks": {
            "api": "http://localhost:3000/health",
            "database": "postgresql://localhost:5432",
        },
    }


@pytest.fixture
def mock_docker_env(temp_project_dir):
    """
    Mock Docker environment with Dockerfile and docker-compose.yml.

    Returns:
        Dict with Docker configuration

    Example:
        def test_ops_docker(mock_docker_env):
            assert "Dockerfile" in mock_docker_env["files"]
    """
    # Create Dockerfile
    dockerfile = temp_project_dir / "Dockerfile"
    dockerfile.write_text("""FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
""")

    # Create docker-compose.yml
    compose = temp_project_dir / "docker-compose.yml"
    compose.write_text("""version: '3.8'
services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
  database:
    image: postgres:15
    environment:
      - POSTGRES_DB=myapp
""")

    return {
        "root": str(temp_project_dir),
        "files": {
            "Dockerfile": str(dockerfile),
            "docker-compose.yml": str(compose),
        },
    }


# ============================================================================
# AGENT TEMPLATE LOADING FIXTURES
# ============================================================================


@pytest.fixture
def base_agent_template():
    """
    Load BASE_AGENT_TEMPLATE.md content.

    Returns:
        Dict with template content, metadata

    Example:
        def test_base_agent_requirements(base_agent_template):
            assert "Always verify" in base_agent_template["content"]
    """
    # In real implementation, would load from actual file
    # For testing, return mock content
    return {
        "filename": "BASE_AGENT_TEMPLATE.md",
        "content": """# BASE_AGENT_TEMPLATE

## Essential Operating Rules
- Never assume, always verify
- Always challenge the unexpected
- Always verify changes: test functions, run APIs, check file edits

## Response Structure
All agents must include JSON block:
```json
{
  "task_completed": true/false,
  "instructions": "Original task",
  "results": "What accomplished",
  "files_modified": ["file1.py"],
  "tools_used": ["Edit", "Read"],
  "remember": ["Key learnings"] or null
}
```
""",
        "lines": 20,
        "sections": ["Essential Operating Rules", "Response Structure"],
    }


@pytest.fixture
def research_agent_template():
    """
    Load BASE_RESEARCH.md content.

    Returns:
        Dict with template content, metadata

    Example:
        def test_research_requirements(research_agent_template):
            assert "document_summarizer" in research_agent_template["content"]
    """
    return {
        "filename": "BASE_RESEARCH.md",
        "content": """# Research Agent

## Memory Management Protocol
- Files >20KB MUST use document_summarizer
- 3-5 file max sampling strategy
- grep/glob for discovery, not full reads

## Discovery Pattern
1. grep/glob → sampling → pattern extraction → synthesis
""",
        "lines": 10,
        "sections": ["Memory Management Protocol", "Discovery Pattern"],
    }


@pytest.fixture
def engineer_agent_template():
    """
    Load BASE_ENGINEER.md content.

    Returns:
        Dict with template content, metadata
    """
    return {
        "filename": "BASE_ENGINEER.md",
        "content": """# Engineer Agent

## Code Minimization Mandate
- Target: Zero net new lines
- Search first (80% time): Vector search + grep
- Consolidate >80% similarity
- No mock data in production
- No silent fallbacks

## Maturity-Based Thresholds
- <1000 LOC: Establish reusable foundations
- >10k LOC: Require approval for net positive LOC
""",
        "lines": 15,
        "sections": ["Code Minimization Mandate", "Maturity-Based Thresholds"],
    }


@pytest.fixture
def qa_agent_template():
    """
    Load BASE_QA.md content.

    Returns:
        Dict with template content, metadata
    """
    return {
        "filename": "BASE_QA.md",
        "content": """# QA Agent

## JavaScript Test Process Management
CRITICAL: Never use watch mode during agent operations (memory leaks).

### Safe Test Execution
```bash
# CORRECT - CI-safe test execution
CI=true npm test
vitest run --reporter=verbose

# WRONG - Causes memory leaks
npm test  # May trigger watch mode
```

## Memory-Efficient Testing
- 3-5 test files max
- grep for test functions, not full reads
""",
        "lines": 18,
        "sections": ["JavaScript Test Process Management", "Memory-Efficient Testing"],
    }


# ============================================================================
# MOCK AGENT RESPONSE FIXTURES
# ============================================================================


@pytest.fixture
def mock_base_agent_response():
    """
    Mock BASE_AGENT response with proper format.

    Returns:
        Dict with response text, expected analysis

    Example:
        def test_base_agent_parsing(mock_base_agent_response):
            response = mock_base_agent_response["text"]
            analysis = parser.parse(response, AgentType.BASE)
            assert analysis.memory_protocol_score == 1.0
    """
    return {
        "text": """I've completed the task by editing the configuration file.

First, I used Edit to update config.py with the new setting:
- Added `DEBUG_MODE = False` to production config

Then I verified the change with Read to confirm it was applied correctly.
The new setting is now in place.

```json
{
  "task_completed": true,
  "instructions": "Update config.py to add new setting",
  "results": "Added DEBUG_MODE = False to config.py",
  "files_modified": ["config.py"],
  "tools_used": ["Edit", "Read"],
  "remember": ["Production config should always disable debug mode"]
}
```
""",
        "expected_analysis": {
            "verification_events": 1,
            "verified": True,
            "json_block_present": True,
            "memory_protocol_score": 1.0,
            "violations": 0,
        },
    }


@pytest.fixture
def mock_research_agent_response():
    """Mock Research agent response."""
    return {
        "text": """I've analyzed the authentication implementation.

First, I checked file sizes to determine the best approach:
- auth_service.py: 50KB (large file)

Given the file size, I used document_summarizer to analyze auth_service.py
rather than reading it in full. I also sampled 3 key files for patterns.

Discovery pattern used:
1. grep for "jwt" across codebase
2. Sampled jwt_validator.py, auth_service.py, middleware.py
3. Extracted common patterns
4. Synthesized findings

```json
{
  "task_completed": true,
  "instructions": "Analyze authentication implementation",
  "results": "Found JWT validation pattern across 3 files with 80% code similarity",
  "files_modified": [],
  "tools_used": ["Grep", "document_summarizer"],
  "remember": ["JWT validation has consolidation opportunity - 3 similar implementations"]
}
```
""",
        "expected_analysis": {
            "file_size_checks": True,
            "document_summarizer_used": True,
            "files_read_count": 0,  # Used document_summarizer instead
            "sampling_strategy_used": True,
        },
    }


@pytest.fixture
def mock_engineer_agent_response():
    """Mock Engineer agent response."""
    return {
        "text": """I've implemented JWT validation with code minimization.

Search-first approach:
1. Vector search for "JWT validation" - found existing implementation
2. Grep for "jwt.*validate" - found 2 similar functions
3. Consolidation opportunity identified

Implementation:
- Consolidated 2 duplicate JWT validators into single utility
- Net LOC delta: -15 lines (removed 30, added 15)
- Reuse rate: 100% (extended existing code)

```json
{
  "task_completed": true,
  "instructions": "Implement JWT token validation",
  "results": "Consolidated existing JWT validators, net -15 LOC",
  "files_modified": ["utils/jwt.py"],
  "tools_used": ["Grep", "Edit", "Read"],
  "remember": ["JWT validation now centralized in utils/jwt.py"]
}
```
""",
        "expected_analysis": {
            "search_tools_used": 1,  # Grep
            "write_tools_used": 1,  # Edit
            "consolidation_mentioned": True,
            "loc_delta_mentioned": True,
        },
    }


@pytest.fixture
def mock_qa_agent_response():
    """Mock QA agent response."""
    return {
        "text": """I've executed the authentication tests safely.

Pre-flight checks:
1. Checked package.json test script: "vitest"
2. Verified need for CI mode to avoid watch mode

Test execution:
```bash
CI=true npm test
```

Results: 15 tests passed, 0 failed

Post-execution verification:
```bash
ps aux | grep vitest  # No hanging processes
```

```json
{
  "task_completed": true,
  "instructions": "Run authentication module tests",
  "results": "15 tests passed with CI mode, all processes cleaned up",
  "files_modified": [],
  "tools_used": ["Read", "Bash"],
  "remember": ["Always use CI=true for npm test to prevent watch mode"]
}
```
""",
        "expected_analysis": {
            "test_execution_count": 1,
            "ci_mode_used": True,
            "watch_mode_detected": False,
            "process_cleanup_verified": True,
            "package_json_checked": True,
        },
    }
