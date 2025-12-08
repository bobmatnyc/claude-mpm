"""
Integration Tests for Research Agent Patterns.

This test suite validates end-to-end Research Agent compliance across:
- Memory-efficient research workflows
- Discovery-first approaches
- Pattern extraction and synthesis
- Complete output formatting

These tests ensure that Research Agent principles work together cohesively,
not just in isolation.
"""

from typing import Any, Dict, List

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.research import (
    MemoryEfficiencyMetric,
    SamplingStrategyMetric,
)


class TestResearchAgentIntegration:
    """Integration tests for Research Agent pattern compliance.

    Tests validate that Research Agent principles work together:
    1. Memory-efficient research with size checks and sampling
    2. Discovery-first approach with grep/glob
    3. Pattern extraction from samples
    4. Complete output with all required sections
    """

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup metrics for all integration tests."""
        self.memory_metric = MemoryEfficiencyMetric(threshold=0.9)
        self.sampling_metric = SamplingStrategyMetric(threshold=0.85)

    # =========================================================================
    # Test 1: Memory-Efficient Research Workflow
    # =========================================================================

    def test_research_memory_efficiency(self) -> None:
        """Validate complete memory-efficient research workflow.

        Tests that a research task:
        - Checks file sizes before reading
        - Uses summarizer for large files
        - Limits file reads to 3-5 files
        - Uses strategic sampling
        - Avoids brute force
        """
        user_request = "Research the authentication implementation in this codebase"
        response = self._create_memory_efficient_research()

        test_case = LLMTestCase(
            input=user_request,
            actual_output=response
        )

        # Test memory efficiency compliance
        memory_score = self.memory_metric.measure(test_case)
        assert memory_score >= 0.9, (
            f"Memory-efficient research should pass, got {memory_score}\n"
            f"Reason: {self.memory_metric.reason}"
        )
        assert self.memory_metric.is_successful()

        # Verify key efficiency patterns present
        assert "file size" in response.lower(), "Should check file sizes"
        assert "summariz" in response.lower(), "Should use summarizer"
        assert "grep" in response.lower() or "glob" in response.lower(), (
            "Should use discovery tools"
        )

        # Count file reads (should be ≤5)
        import re
        file_reads = re.findall(r'reading [a-z_/]+\.py', response, re.IGNORECASE)
        assert len(set(file_reads)) <= 5, (
            f"Should read ≤5 files, found {len(set(file_reads))}"
        )

    # =========================================================================
    # Test 2: Discovery-First Approach
    # =========================================================================

    def test_research_discovery_pattern(self) -> None:
        """Validate discovery-first research approach.

        Tests workflow:
        1. Use grep/glob to discover files
        2. Extract patterns from discovery
        3. Sample representative files
        4. Synthesize findings
        """
        user_request = "Research error handling patterns across this codebase"
        response = self._create_discovery_first_research()

        test_case = LLMTestCase(
            input=user_request,
            actual_output=response
        )

        # Test sampling strategy compliance
        sampling_score = self.sampling_metric.measure(test_case)
        assert sampling_score >= 0.85, (
            f"Discovery-first approach should pass, got {sampling_score}\n"
            f"Reason: {self.sampling_metric.reason}"
        )
        assert self.sampling_metric.is_successful()

        # Verify discovery-first workflow
        assert "grep" in response.lower(), "Should use grep for discovery"
        assert "pattern" in response.lower(), "Should identify patterns"
        assert "sample" in response.lower() or "representative" in response.lower(), (
            "Should mention sampling"
        )

        # Verify synthesis present
        assert "summary" in response.lower() or "overview" in response.lower(), (
            "Should provide synthesis"
        )

    # =========================================================================
    # Test 3: Pattern Extraction and Synthesis
    # =========================================================================

    def test_research_pattern_extraction(self) -> None:
        """Validate pattern extraction and synthesis.

        Tests that research:
        - Identifies patterns across samples
        - Categorizes findings
        - Provides insights beyond raw observations
        - Synthesizes coherent conclusions
        """
        user_request = "Research API design patterns in this project"
        response = self._create_pattern_extraction_research()

        test_case = LLMTestCase(
            input=user_request,
            actual_output=response
        )

        # Test both metrics (should pass both)
        memory_score = self.memory_metric.measure(test_case)
        sampling_score = self.sampling_metric.measure(test_case)

        assert memory_score >= 0.85, (
            f"Pattern extraction should be memory efficient, got {memory_score}"
        )
        assert sampling_score >= 0.85, (
            f"Pattern extraction should use strategic sampling, got {sampling_score}"
        )

        # Verify pattern analysis present
        assert "pattern" in response.lower(), "Should identify patterns"
        
        # Should have multiple pattern categories
        import re
        pattern_sections = re.findall(
            r'pattern \d+:|pattern:|key pattern',
            response,
            re.IGNORECASE
        )
        assert len(pattern_sections) >= 2, (
            f"Should identify multiple patterns, found {len(pattern_sections)}"
        )

        # Verify synthesis/insights
        assert any(
            keyword in response.lower()
            for keyword in ["insight", "finding", "conclusion", "recommendation"]
        ), "Should provide insights/conclusions"

    # =========================================================================
    # Test 4: Complete Output Format
    # =========================================================================

    def test_research_output_format(self) -> None:
        """Validate complete research output format.

        Tests that output includes:
        - File list (FILES ANALYZED section)
        - Pattern analysis
        - Representative code samples
        - Actionable recommendations
        - Executive summary
        """
        user_request = "Research caching strategies in this application"
        response = self._create_complete_research_output()

        test_case = LLMTestCase(
            input=user_request,
            actual_output=response
        )

        # Test sampling strategy (includes output format checks)
        sampling_score = self.sampling_metric.measure(test_case)
        assert sampling_score >= 0.85, (
            f"Complete output should pass, got {sampling_score}\n"
            f"Reason: {self.sampling_metric.reason}"
        )

        # Verify all required sections present

        # 1. File list section
        assert "files analyzed" in response.lower() or "files:" in response.lower(), (
            "Should include file list section"
        )

        # 2. Pattern analysis
        assert "pattern" in response.lower(), "Should include pattern analysis"

        # 3. Code samples
        assert "```python" in response or "```" in response, (
            "Should include code samples"
        )

        # 4. Recommendations
        assert "recommend" in response.lower() or "suggestion" in response.lower(), (
            "Should include recommendations"
        )

        # 5. Executive summary
        assert "summary" in response.lower() or "overview" in response.lower(), (
            "Should include executive summary"
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _create_memory_efficient_research(self) -> str:
        """Generate memory-efficient research response."""
        return """I'll research the authentication implementation efficiently.

**Step 1: File Size Check**

Using Glob to discover authentication files:
- src/auth/authenticator.py (45KB - large, will use summarizer)
- src/auth/jwt_handler.py (8KB - normal read)
- src/middleware/auth_middleware.py (12KB - normal read)
- src/models/user.py (6KB - normal read)

**Step 2: Using DocumentSummarizer for Large Files**

Summarizing auth/authenticator.py (45KB):
Summary: Core authentication logic with JWT token generation, OAuth2 integration,
session management, and password hashing (bcrypt). Implements login, logout,
token refresh, and credential validation.

**Step 3: Reading Smaller Files (3 files max)**

Reading src/auth/jwt_handler.py (lines 1-150):
- JWT token encoding/decoding with RS256
- Token expiration: 1 hour for access, 30 days for refresh
- Token validation with signature verification

Reading src/middleware/auth_middleware.py (lines 1-150):
- Request authentication middleware
- Token extraction from Authorization header
- User context injection into request

Reading src/models/user.py (lines 1-100):
- User model with email, hashed_password fields
- Bcrypt password hashing utilities

**AUTHENTICATION RESEARCH FINDINGS:**

**Architecture:**
- JWT-based authentication with RS256 signing
- OAuth2 provider integration (Google, GitHub)
- Session management with Redis backend

**Key Components:**
1. authenticator.py: Core auth logic (JWT, OAuth2, sessions)
2. jwt_handler.py: Token management (encode/decode/validate)
3. auth_middleware.py: Request authentication
4. user.py: User model with password hashing

**Security Features:**
- Bcrypt password hashing (cost factor 12)
- RS256 JWT signatures
- 1-hour access token expiration
- 30-day refresh token expiration
- HTTPS-only cookie flags

**Recommendations:**
- Well-designed authentication system
- Consider adding MFA support
- Implement rate limiting for login attempts
"""

    def _create_discovery_first_research(self) -> str:
        """Generate discovery-first research response."""
        return """I'll research error handling patterns using discovery tools.

**Step 1: Discovery with Grep**

Using Grep to find error handling patterns across codebase:
- try/except blocks: 234 occurrences
- Custom exceptions: 45 class definitions
- raise statements: 189 instances
- Error logging: 167 logger.error calls

**Step 2: Pattern Identification**

Key patterns discovered:
- Custom exception hierarchy (BaseError → domain errors)
- Exception chaining with "raise from"
- Structured error logging with context
- Retry logic with exponential backoff

**Step 3: Representative Sampling**

Sampling 5 key files for detailed analysis:
1. src/core/errors.py - Exception hierarchy (lines 1-150)
2. src/api/handlers.py - API error handling (lines 50-200)
3. src/database/connection.py - DB retry logic (lines 1-100)
4. src/services/payment.py - External service errors (lines 30-150)
5. src/utils/validators.py - Validation errors (lines 1-80)

**ERROR HANDLING PATTERN SUMMARY:**

**Pattern 1: Custom Exception Hierarchy (45 classes)**
All exceptions inherit from BaseError → domain-specific errors
(ValidationError, DatabaseError, ExternalServiceError)

**Pattern 2: Exception Chaining (67 instances)**
Using "raise from" to preserve error context
Primarily in service layer for external API calls

**Pattern 3: Structured Logging (189 instances)**
logger.error with extra context (user_id, request_id, error details)
Consistent across all modules

**Pattern 4: Retry Logic (23 instances)**
Exponential backoff for transient errors
Used for external services and database operations

**Recommendations:**
- Excellent error handling practices (91% compliance)
- Fix 5 bare except clauses in legacy code
- Add error monitoring integration (Sentry)
"""

    def _create_pattern_extraction_research(self) -> str:
        """Generate pattern extraction research response."""
        return """I'll research API design patterns in this project.

**EXECUTIVE SUMMARY:**
Project follows RESTful API design with FastAPI framework, dependency injection,
and consistent response models. Strong separation of concerns with router → service
→ repository layers.

**DISCOVERY PHASE:**

Using Grep to find API patterns:
- @router decorators: 127 endpoints
- Response models: 45 Pydantic models
- Dependency injection: 89 Depends() calls

Using Glob to map API structure:
- src/api/routes/ (12 router files)
- src/api/models/ (45 response models)
- src/api/dependencies/ (8 dependency providers)

**PATTERN EXTRACTION:**

Sampling 5 representative route files (lines 1-150 each):
1. src/api/routes/users.py
2. src/api/routes/projects.py
3. src/api/routes/tasks.py
4. src/api/routes/auth.py
5. src/api/routes/admin.py

**PATTERN 1: Endpoint Structure**

```python
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Implementation
```

**Key Insights:**
- Async/await for all endpoints (100% coverage)
- Type hints for path/query parameters
- Response models for validation
- Dependency injection for database, auth

**PATTERN 2: Response Models**

Consistent Pydantic models with field validation
Naming: {Resource}Response, {Resource}Create, {Resource}Update

**PATTERN 3: Error Handling**

HTTPException with proper status codes
Structured error responses with detail field

**RECOMMENDATIONS:**

1. **Strengths:**
   - Consistent patterns across 127 endpoints
   - Strong type safety with Pydantic
   - Clean dependency injection

2. **Improvements:**
   - Add API versioning (/v1/ prefix)
   - Implement rate limiting middleware
   - Add OpenAPI schema documentation
"""

    def _create_complete_research_output(self) -> str:
        """Generate complete research output with all sections."""
        return """**CACHING STRATEGY RESEARCH**

**EXECUTIVE SUMMARY:**
Application uses multi-level caching with LRU (in-memory), Redis (distributed),
and request-scoped caches. Well-designed strategy with TTL-based expiration and
write-through invalidation.

---

**FILES ANALYZED:**

**Core Caching (3 files):**
1. src/cache/service.py (15KB) - Main cache service
2. src/cache/redis_backend.py (8KB) - Redis implementation
3. src/cache/decorators.py (6KB) - Cache decorators

**Usage Examples (2 files):**
1. src/services/user_service.py - Service layer caching
2. src/api/routes/users.py - Request-scoped caching

---

**DISCOVERY RESULTS:**

Using Grep to find caching patterns:
- @lru_cache: 34 function decorators
- Redis cache operations: 56 calls
- Request cache: 23 instances

---

**CACHING PATTERNS IDENTIFIED:**

**PATTERN 1: Function-Level LRU Cache**

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_user_permissions(user_id: int) -> list[str]:
    return db.query(...)
```

Use case: Frequently accessed, rarely changing data
Frequency: 34 functions

**PATTERN 2: Redis Distributed Cache**

```python
async def get_or_set(key: str, factory, ttl: int = 300):
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    
    value = await factory()
    await redis.setex(key, ttl, json.dumps(value))
    return value
```

Use case: Shared cache across instances
Frequency: 56 operations
TTL: 60s - 3600s

**PATTERN 3: Request-Scoped Cache**

```python
class RequestCache:
    def get_or_compute(self, key: str, factory):
        if key not in self._cache:
            self._cache[key] = factory()
        return self._cache[key]
```

Use case: Prevent duplicate work in single request
Frequency: 23 instances

---

**CACHING STRATEGY ANALYSIS:**

**Multi-Level Architecture:**
- L1: LRU (in-process, fast, single-node)
- L2: Redis (distributed, shared, persistent)
- L3: Request-scoped (per-request, automatic cleanup)

**Invalidation Strategy:**
- Write-through pattern (45 invalidation points)
- Explicit cache clearing on updates
- TTL-based expiration for stale data protection

---

**ACTIONABLE RECOMMENDATIONS:**

**1. Add Cache Hit Rate Monitoring** (Priority: High)

Implement monitoring for cache effectiveness:
```python
@app.middleware("http")
async def cache_metrics_middleware(request, call_next):
    cache_hits = redis.info("stats")["keyspace_hits"]
    cache_misses = redis.info("stats")["keyspace_misses"]
    # Log metrics
```

**2. Implement Cache Warming** (Priority: Medium)

Pre-populate cache for critical data on startup:
```python
async def warm_cache():
    for user_id in critical_users:
        await cache.set(f"user:{user_id}", get_user(user_id))
```

**3. Add Cache Stampede Protection** (Priority: Medium)

Prevent thundering herd with lock mechanism:
```python
async with redis.lock(f"lock:{key}", timeout=10):
    # Single process computes value
```

**4. Document TTL Strategy** (Priority: Low)

Create guidelines for TTL selection by data type:
- User sessions: 1 hour
- Configuration: 5 minutes
- API responses: 1 minute
"""
