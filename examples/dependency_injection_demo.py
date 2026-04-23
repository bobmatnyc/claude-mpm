#!/usr/bin/env python3
"""
Dependency Injection Demo for Claude MPM.

This example demonstrates how to use the DI container to:
- Register services
- Resolve dependencies
- Use factories
- Test with mocks
"""

import asyncio

# Import DI components
from claude_mpm.core import (
    Config,
    DIContainer,
    InjectableService,
    ServiceLifetime,
)


# Define interfaces (abstract base classes)
class IEmailService:
    """Interface for email service."""

    def send(self, to: str, subject: str, body: str) -> bool:
        raise NotImplementedError


class ITemplateEngine:
    """Interface for template engine."""

    def render(self, template: str, context: dict) -> str:
        raise NotImplementedError


# Implement concrete services
class ConsoleEmailService(IEmailService):
    """Email service that prints to console (for demo)."""

    def send(self, to: str, subject: str, body: str) -> bool:
        print(f"📧 Sending email to: {to}")
        print(f"   Subject: {subject}")
        print(f"   Body: {body[:50]}...")
        return True


class SimpleTemplateEngine(ITemplateEngine):
    """Simple template engine using string format."""

    def render(self, template: str, context: dict) -> str:
        return template.format(**context)


# Create a service that uses dependency injection
class NotificationService(InjectableService):
    """Service that sends templated notifications."""

    # Dependencies are injected automatically
    email_service: IEmailService
    template_engine: ITemplateEngine
    config: Config

    async def _initialize(self) -> None:
        """Initialize the service."""
        print("✅ NotificationService initialized")

    async def _cleanup(self) -> None:
        """Cleanup resources."""
        print("🧹 NotificationService cleaned up")

    async def send_welcome_email(self, user_email: str, username: str) -> bool:
        """Send a welcome email to a new user."""
        # Use injected template engine
        template = self.config.get(
            "email.welcome_template", "Welcome {username}! Thanks for joining."
        )
        body = self.template_engine.render(template, {"username": username})

        # Use injected email service
        return self.email_service.send(to=user_email, subject="Welcome!", body=body)


async def main():
    """Demonstrate dependency injection."""

    print("🚀 Claude MPM Dependency Injection Demo\n")

    # 1. Create DI container
    container = DIContainer()
    print("1️⃣ Created DI container")

    # 2. Register configuration
    config = Config(
        {
            "email.welcome_template": "Hello {username}! Welcome to Claude MPM.",
            "app.name": "Claude MPM Demo",
        }
    )
    container.register_singleton(Config, instance=config)
    print("2️⃣ Registered configuration")

    # 3. Register services
    container.register_singleton(IEmailService, ConsoleEmailService)
    container.register_singleton(ITemplateEngine, SimpleTemplateEngine)
    container.register_singleton(NotificationService)
    print("3️⃣ Registered services")

    # 4. Resolve and use service
    print("\n4️⃣ Resolving NotificationService...")
    notification_service = container.resolve(NotificationService)

    # Dependencies are automatically injected!
    print(
        f"   - Email service: {notification_service.email_service.__class__.__name__}"
    )
    print(
        f"   - Template engine: {notification_service.template_engine.__class__.__name__}"
    )
    print(f"   - Config available: {notification_service.config is not None}")

    # 5. Use the service
    print("\n5️⃣ Sending welcome email...")
    await notification_service.send_welcome_email(
        user_email="user@example.com", username="Alice"
    )

    # 6. Demonstrate factory pattern
    print("\n6️⃣ Using factory pattern...")

    def create_notification_service(container: DIContainer) -> NotificationService:
        """Factory function for creating notification service."""
        print("   🏭 Factory creating NotificationService...")

        # Could add custom logic here
        return NotificationService(
            name="factory_notification",
            config=container.resolve(Config),
            email_service=container.resolve(IEmailService),
            template_engine=container.resolve(ITemplateEngine),
        )

    # Register with factory
    container.register_factory(
        NotificationService,
        create_notification_service,
        lifetime=ServiceLifetime.TRANSIENT,
    )

    # Each resolution creates a new instance (transient)
    service1 = container.resolve(NotificationService)
    service2 = container.resolve(NotificationService)
    print(f"   - Same instance? {service1 is service2}")  # Should be False

    # 7. Demonstrate testing with mocks
    print("\n7️⃣ Testing with mocks...")

    class MockEmailService(IEmailService):
        """Mock email service for testing."""

        def __init__(self):
            self.sent_emails = []

        def send(self, to: str, subject: str, body: str) -> bool:
            self.sent_emails.append({"to": to, "subject": subject, "body": body})
            print(f"   📋 Mock: Email queued for {to}")
            return True

    # Create test container
    test_container = DIContainer()
    test_container.register_singleton(Config, instance=config)
    test_container.register_singleton(IEmailService, instance=MockEmailService())
    test_container.register_singleton(ITemplateEngine, SimpleTemplateEngine)
    test_container.register_singleton(NotificationService)

    # Get service with mock
    test_service = test_container.resolve(NotificationService)
    mock_email = test_container.resolve(IEmailService)

    # Test the service
    await test_service.send_welcome_email("test@example.com", "TestUser")

    # Verify mock was called
    print(f"   - Emails sent: {len(mock_email.sent_emails)}")
    print(f"   - Last email to: {mock_email.sent_emails[0]['to']}")

    print("\n✨ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
