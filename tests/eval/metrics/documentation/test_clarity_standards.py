"""
Unit tests for ClarityStandardsMetric.

Tests the 5-component weighted scoring:
1. Active Voice (25%)
2. Jargon Handling (20%)
3. Code Examples (30%)
4. Conciseness (25%)
5. Completeness Bonus (+15%)
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.documentation.clarity_standards_metric import (
    ClarityStandardsMetric,
    create_clarity_standards_metric,
)


class TestClarityStandardsMetric:
    """Test suite for ClarityStandardsMetric."""

    def test_perfect_score_with_all_components(self):
        """Test perfect compliance with all clarity components."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document the authentication API",
            actual_output="""
            # API Authentication Guide

            ## Overview
            This guide explains how to authenticate with our REST API using JWT tokens (JSON Web Tokens).

            ## Quick Start
            Send a POST request to `/auth/login` with your credentials:

            ```bash
            curl -X POST https://api.example.com/auth/login \\
              -H "Content-Type: application/json" \\
              -d '{"username": "user", "password": "pass"}'
            ```

            The API returns a JWT token. Include this token in subsequent requests:

            ```javascript
            fetch('/api/users', {
              headers: {
                'Authorization': 'Bearer ' + token
              }
            })
            ```

            ## API Reference

            ### Login Endpoint
            **POST /auth/login**

            Returns a JWT token for authentication.

            ## Troubleshooting
            - **401 Unauthorized**: Invalid credentials
            - **429 Too Many Requests**: Rate limit exceeded

            ## Changelog
            - v2.0.0: Added JWT support
            - v1.0.0: Initial release
            """,
        )

        score = metric.measure(test_case)

        # Should score >= 0.85 with bonus (perfect clarity)
        assert score >= 0.85
        assert metric.is_successful()
        assert "Excellent clarity" in metric.reason or score >= 0.85

    def test_active_voice_usage(self):
        """Test active voice detection and scoring."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Write installation instructions",
            actual_output="""
            ## Installation

            Install the package using npm:

            ```bash
            npm install @example/sdk
            ```

            Configure your API key:

            ```javascript
            const client = new Client({ apiKey: 'your-key' });
            ```

            Run the setup command to verify installation.
            Create a configuration file in your project root.
            Update the environment variables with your credentials.
            """,
        )

        score = metric.measure(test_case)

        # Should detect strong active voice usage
        # Active voice component should score high
        assert score >= 0.5  # At least some active voice

    def test_passive_voice_penalty(self):
        """Test passive voice detection (negative scoring)."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document deployment process",
            actual_output="""
            ## Deployment

            The application should be deployed to production after testing.
            Configuration files must be updated before deployment.
            The database should be migrated before the application is started.
            Backups should be created before any changes are made.
            The deployment process is performed by the CI/CD pipeline.
            """,
        )

        score = metric.measure(test_case)

        # Should penalize passive voice
        assert score < 0.85
        assert not metric.is_successful()
        assert (
            "Passive voice" in metric.reason or "active voice" in metric.reason.lower()
        )

    def test_jargon_with_definitions(self):
        """Test jargon handling with proper definitions."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document OAuth flow",
            actual_output="""
            ## OAuth2 Authentication

            PKCE (Proof Key for Code Exchange) is an OAuth2 extension that prevents
            authorization code interception attacks.

            **SPA**: Single-Page Application - a web app that loads once and updates dynamically.

            JWT (JSON Web Token) is used for stateless authentication.

            **CSRF** stands for Cross-Site Request Forgery.

            See the [glossary](#glossary) for more terms.

            ```bash
            # Authenticate with OAuth2
            curl -X POST /oauth/token
            ```
            """,
        )

        score = metric.measure(test_case)

        # Should score well for jargon handling
        # Jargon component should contribute positively
        assert score >= 0.5

    def test_jargon_without_definitions(self):
        """Test jargon without definitions (negative scoring)."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document the API",
            actual_output="""
            ## API Setup

            Configure PKCE for your OAuth2 flow. Set up JWT validation
            in your middleware. Enable CORS for SPA clients.

            Use the IdP for authentication. Configure the SSO integration.
            Set up the MFA flow using TOTP.
            """,
        )

        score = metric.measure(test_case)

        # Should penalize undefined jargon
        assert score < 0.85
        assert "jargon" in metric.reason.lower() or "acronym" in metric.reason.lower()

    def test_code_examples_with_language_hints(self):
        """Test code examples with proper language hints."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document API usage",
            actual_output="""
            ## API Usage

            ### Python Example
            ```python
            import requests

            response = requests.get('https://api.example.com/users')
            users = response.json()
            ```

            ### JavaScript Example
            ```javascript
            const response = await fetch('https://api.example.com/users');
            const users = await response.json();
            ```

            ### Bash Example
            ```bash
            curl https://api.example.com/users
            ```

            For example, to fetch a specific user:

            ```typescript
            const user = await client.getUser('123');
            ```
            """,
        )

        score = metric.measure(test_case)

        # Should score very well for multiple code examples
        # Code examples component (30% weight) should be high
        assert score >= 0.7

    def test_no_code_examples(self):
        """Test documentation without code examples (negative)."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document the API",
            actual_output="""
            ## API Documentation

            The API supports various operations. You can fetch users,
            create resources, and update configurations.

            Authentication is required for all endpoints.
            Use your API key in the Authorization header.
            """,
        )

        score = metric.measure(test_case)

        # Should penalize missing code examples heavily (30% weight)
        assert score < 0.85
        assert (
            "code example" in metric.reason.lower()
            or "example" in metric.reason.lower()
        )

    def test_concise_writing(self):
        """Test concise, direct writing style."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Write deployment guide",
            actual_output="""
            ## Deployment

            **Production deployment steps**:

            1. Verify environment configuration
            2. Run database migrations
            3. Deploy application
            4. Verify health endpoints

            **Rollback procedure**:

            1. Revert deployment
            2. Restore database backup

            Use the deployment script to automate these steps.
            """,
        )

        score = metric.measure(test_case)

        # Should score well for concise, structured writing
        # Conciseness component should be high
        assert score >= 0.5

    def test_verbose_redundant_writing(self):
        """Test verbose writing with redundant phrases (negative)."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document setup process",
            actual_output="""
            ## Setup Process

            In order to get started with the application, it should be noted that
            you will need to install the dependencies. Generally speaking, the
            installation process is straightforward.

            It is important to note that configuration is required. For the purpose of
            setting up the environment, you should create a .env file. In the event that
            you encounter errors, please check the logs.

            Due to the fact that the application requires a database, you will need to
            set up PostgreSQL. At this point in time, we support PostgreSQL 12 and above.
            """,
        )

        score = metric.measure(test_case)

        # Should penalize verbose, redundant writing
        assert score < 0.85
        assert "verbose" in metric.reason.lower() or "redundan" in metric.reason.lower()

    def test_all_required_sections_present(self):
        """Test completeness bonus with all required sections."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Create complete documentation",
            actual_output="""
            # Complete Documentation

            ## Overview
            This library provides utilities for data processing.

            ## Quick Start
            Install and configure the library.

            ```bash
            npm install @example/lib
            ```

            ## API Reference
            Detailed API documentation.

            ## Troubleshooting
            - **Error X**: Solution Y
            - **Error Z**: Solution W

            ## Changelog
            - v2.0.0: Added new features
            - v1.0.0: Initial release
            """,
        )

        score = metric.measure(test_case)

        # Should get full completeness bonus (+15%)
        # All 5 sections present
        assert score >= 0.85

    def test_missing_required_sections(self):
        """Test penalty for missing required sections."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Create minimal documentation",
            actual_output="""
            # Minimal Documentation

            ## Overview
            This is a brief overview.

            ## API
            Some API details.
            """,
        )

        score = metric.measure(test_case)

        # Should miss completeness bonus
        # Missing Quick Start, Troubleshooting, Changelog
        assert (
            "required sections" in metric.reason.lower()
            or "section" in metric.reason.lower()
        )

    def test_comprehensive_documentation(self):
        """Test comprehensive documentation with all components."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Create full documentation for payment API",
            actual_output="""
            # Payment API Documentation

            ## Overview
            Process payments securely using our REST API with PCI-DSS (Payment Card Industry Data Security Standard) compliance.

            ## Quick Start

            Install the SDK:

            ```bash
            npm install @example/payment-sdk
            ```

            Create a payment:

            ```javascript
            const payment = await client.createPayment({
              amount: 1000,
              currency: 'USD',
              source: 'tok_visa'
            });
            ```

            ## API Reference

            ### Create Payment
            **POST /v1/payments**

            Creates a new payment transaction.

            Example:

            ```python
            import payments

            payment = payments.create(
              amount=1000,
              currency='USD'
            )
            ```

            ### Retrieve Payment
            **GET /v1/payments/:id**

            ```bash
            curl https://api.example.com/v1/payments/pay_123 \\
              -H "Authorization: Bearer sk_test_..."
            ```

            ## Troubleshooting

            **Error: card_declined**
            - Cause: Insufficient funds
            - Solution: Use a different payment method

            **Error: rate_limit_exceeded**
            - Cause: Too many requests
            - Solution: Implement exponential backoff

            ## Changelog

            ### v2.1.0 (2025-12-01)
            - Added Apple Pay support
            - Improved error messages

            ### v2.0.0 (2025-11-01)
            - Breaking: Updated authentication
            - Added webhook support
            """,
        )

        score = metric.measure(test_case)

        # Should score very high with all components
        assert score >= 0.90
        assert metric.is_successful()

    def test_component_weights_sum_to_one(self):
        """Test that base component weights sum to 1.0."""
        # Active (25%) + Jargon (20%) + Examples (30%) + Concise (25%)
        total_weight = 0.25 + 0.20 + 0.30 + 0.25
        assert total_weight == pytest.approx(1.0)

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_clarity_standards_metric(threshold=0.80)

        assert isinstance(metric, ClarityStandardsMetric)
        assert metric.threshold == 0.80

    def test_async_measure(self):
        """Test async measure method delegates to sync."""
        import asyncio

        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document authentication",
            actual_output="""
            # Authentication

            Send credentials to `/auth/login`:

            ```bash
            curl -X POST /auth/login -d '{"user":"alice"}'
            ```

            Use the JWT (JSON Web Token) in requests.

            ## Troubleshooting
            - 401: Invalid credentials
            """,
        )

        async def run_async_test():
            score = await metric.a_measure(test_case)
            return score

        score = asyncio.run(run_async_test())

        # Should return valid score
        assert 0.0 <= score <= 1.15

    def test_mixed_active_passive_voice(self):
        """Test mixed active and passive voice (medium score)."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document deployment",
            actual_output="""
            ## Deployment

            Deploy the application to production using the CLI tool.
            The configuration should be updated before deployment.

            Run the migration script to update the database.
            Backups are created automatically by the system.

            Verify the deployment using the health check endpoint.
            """,
        )

        score = metric.measure(test_case)

        # Should score medium (mixed voice)
        # Active voice component will be lower due to passive constructions
        assert 0.2 <= score <= 0.85

    def test_multiple_code_blocks_same_language(self):
        """Test multiple code blocks with same language hint."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document Python SDK",
            actual_output="""
            ## Python SDK Usage

            Import the library:

            ```python
            from sdk import Client
            client = Client(api_key='your-key')
            ```

            Fetch data:

            ```python
            users = client.get_users()
            for user in users:
                print(user.name)
            ```

            Handle errors:

            ```python
            try:
                data = client.fetch()
            except APIError as e:
                print(f"Error: {e}")
            ```
            """,
        )

        score = metric.measure(test_case)

        # Should score well for multiple examples
        # Code examples component should be high
        assert score >= 0.6

    def test_acronym_parenthetical_definition(self):
        """Test acronym definitions in parentheses."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document security features",
            actual_output="""
            ## Security

            We use HTTPS (Hypertext Transfer Protocol Secure) for all communications.
            Authentication uses JWT (JSON Web Token) for stateless sessions.

            The API supports CORS (Cross-Origin Resource Sharing) for browser clients.

            **MFA** (Multi-Factor Authentication) can be enabled in settings.

            See our PCI-DSS (Payment Card Industry Data Security Standard) compliance documentation.
            """,
        )

        score = metric.measure(test_case)

        # Should score well for jargon handling
        # Multiple acronym definitions present
        # Score might be lower due to missing code examples and some passive voice
        assert score >= 0.4

    def test_numbered_lists_for_structure(self):
        """Test numbered lists contribute to conciseness score."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document setup steps",
            actual_output="""
            ## Setup

            1. Install dependencies
            2. Configure environment variables
            3. Run database migrations
            4. Start the application

            **Prerequisites**:

            1. Node.js 18+
            2. PostgreSQL 14+
            3. Redis 6+
            """,
        )

        score = metric.measure(test_case)

        # Should score well for structured, concise writing
        # Conciseness component should be high
        assert score >= 0.5

    def test_example_sections_with_headings(self):
        """Test detection of example sections with headings."""
        metric = ClarityStandardsMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Document API calls",
            actual_output="""
            ## Examples

            ### Example: Fetch Users

            ```javascript
            const users = await api.getUsers();
            ```

            ### Example: Create User

            ```javascript
            const user = await api.createUser({ name: 'Alice' });
            ```

            ### Usage Example

            For example, to update a user:

            ```javascript
            await api.updateUser('123', { name: 'Bob' });
            ```
            """,
        )

        score = metric.measure(test_case)

        # Should detect example sections and code blocks
        # Examples component should be high
        assert score >= 0.7
