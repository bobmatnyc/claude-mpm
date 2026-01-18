"""Example usage of Commander memory system.

Demonstrates:
1. Capturing conversations from Project
2. Searching conversations semantically
3. Loading context for session resumption
4. Entity extraction and filtering
"""

import asyncio

from ..models.project import Project, ProjectState, ThreadMessage
from .entities import EntityType
from .integration import MemoryIntegration


async def example_basic_usage():
    """Example 1: Basic conversation capture and search."""
    print("\n=== Example 1: Basic Usage ===\n")

    # Initialize memory integration
    memory = MemoryIntegration.create()

    # Create sample project with conversation
    project = Project(
        id="proj-example-123",
        path="/Users/masa/Projects/example-app",
        name="example-app",
        state=ProjectState.IDLE,
    )

    # Add sample conversation to project
    project.thread = [
        ThreadMessage(
            id="msg-1",
            role="user",
            content="Fix the login authentication bug in src/auth.py",
        ),
        ThreadMessage(
            id="msg-2",
            role="assistant",
            content="I'll investigate the authentication bug. Let me read the auth.py file.",
        ),
        ThreadMessage(
            id="msg-3",
            role="assistant",
            content="Found the issue in UserService.authenticate() - the token validation was missing expiry check. Fixed it.",
        ),
        ThreadMessage(
            id="msg-4",
            role="user",
            content="Great! Can you also add tests for this fix?",
        ),
        ThreadMessage(
            id="msg-5",
            role="assistant",
            content="Added test_token_expiry_validation() in tests/test_auth.py. All tests passing.",
        ),
    ]

    # Capture conversation
    conversation = await memory.capture_project_conversation(
        project, instance_name="claude-code-1", session_id="sess-abc123"
    )

    print(f"✅ Captured conversation: {conversation.id}")
    print(f"   Messages: {len(conversation.messages)}")
    print(f"   Summary: {conversation.summary}")
    print(
        f"   Entities extracted: {len([e for msg in conversation.messages for e in msg.entities])}"
    )

    # Search conversations
    print("\n🔍 Searching for 'authentication bug'...")
    results = await memory.search_conversations(
        "authentication bug fix", project_id=project.id, limit=3
    )

    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result.score:.3f}")
        print(f"   Conversation: {result.conversation.id}")
        print(f"   Snippet: {result.snippet[:100]}...")


async def example_entity_search():
    """Example 2: Entity-based search and filtering."""
    print("\n=== Example 2: Entity Search ===\n")

    memory = MemoryIntegration.create()

    # Create project with file references
    project = Project(
        id="proj-example-456",
        path="/Users/masa/Projects/example-app",
        name="example-app",
    )

    project.thread = [
        ThreadMessage(
            id="msg-1",
            role="user",
            content="Update the UserService class in src/services/user_service.py",
        ),
        ThreadMessage(
            id="msg-2",
            role="assistant",
            content="I'll update UserService.create_user() to include email validation. Also updating tests/test_user_service.py.",
        ),
    ]

    # Capture
    conversation = await memory.capture_project_conversation(
        project, instance_name="claude-code-2"
    )

    # Extract entities
    entities = []
    for msg in conversation.messages:
        entities.extend(msg.entities)

    # Filter by type
    files = memory.extractor.get_unique_values(
        [memory.extractor.Entity.from_dict(e) for e in entities], EntityType.FILE
    )
    print(f"📁 Files mentioned: {files}")

    classes = memory.extractor.get_unique_values(
        [memory.extractor.Entity.from_dict(e) for e in entities], EntityType.CLASS
    )
    print(f"🏗️  Classes mentioned: {classes}")

    # Search by entity
    print("\n🔍 Finding conversations that mention 'src/services/user_service.py'...")
    results = await memory.search.search_by_entities(
        EntityType.FILE,
        "src/services/user_service.py",
        project_id=project.id,
    )

    print(f"Found {len(results)} conversations mentioning this file")


async def example_context_loading():
    """Example 3: Load context for session resumption."""
    print("\n=== Example 3: Context Loading for Session Resumption ===\n")

    memory = MemoryIntegration.create()

    # Create multiple conversations (simulating historical work)
    project = Project(
        id="proj-example-789",
        path="/Users/masa/Projects/example-app",
        name="example-app",
    )

    # Conversation 1: Week ago
    project.thread = [
        ThreadMessage(
            id="msg-1",
            role="user",
            content="Implement user registration with email verification",
        ),
        ThreadMessage(
            id="msg-2",
            role="assistant",
            content="Implemented registration in src/auth.py with email service integration",
        ),
    ]
    await memory.capture_project_conversation(project, instance_name="claude-code-1")

    # Conversation 2: Yesterday
    project.thread = [
        ThreadMessage(
            id="msg-3",
            role="user",
            content="Fix the email verification bug - tokens not expiring",
        ),
        ThreadMessage(
            id="msg-4",
            role="assistant",
            content="Fixed token expiry check in src/auth.py and added tests",
        ),
    ]
    await memory.capture_project_conversation(project, instance_name="claude-code-1")

    # Load context for resumption
    print("📖 Loading context for session resumption...")
    context = await memory.load_context_for_session(
        project.id, max_tokens=4000, limit_conversations=10
    )

    print(f"✅ Loaded context ({len(context)} chars):\n")
    print(context[:500] + "...\n")

    print(
        "This context would be injected into the new session to provide historical awareness."
    )


async def example_similarity_search():
    """Example 4: Find similar conversations."""
    print("\n=== Example 4: Similarity Search ===\n")

    memory = MemoryIntegration.create()

    # Create project with multiple conversations
    project = Project(
        id="proj-example-999",
        path="/Users/masa/Projects/example-app",
        name="example-app",
    )

    # Reference conversation
    project.thread = [
        ThreadMessage(
            id="msg-1",
            role="user",
            content="Fix the authentication bug in login flow",
        ),
        ThreadMessage(
            id="msg-2",
            role="assistant",
            content="Fixed token validation in src/auth.py",
        ),
    ]
    ref_conv = await memory.capture_project_conversation(project)

    # Similar conversation
    project.thread = [
        ThreadMessage(
            id="msg-3",
            role="user",
            content="Update the login authentication to use OAuth",
        ),
        ThreadMessage(
            id="msg-4",
            role="assistant",
            content="Implemented OAuth in src/auth.py",
        ),
    ]
    await memory.capture_project_conversation(project)

    # Different conversation
    project.thread = [
        ThreadMessage(
            id="msg-5",
            role="user",
            content="Add dark mode toggle to the UI",
        ),
        ThreadMessage(
            id="msg-6",
            role="assistant",
            content="Added dark mode CSS in styles/theme.css",
        ),
    ]
    await memory.capture_project_conversation(project)

    # Find similar
    print(f"🔍 Finding conversations similar to: {ref_conv.id}")
    similar = await memory.search.find_similar(ref_conv.id, limit=3)

    for i, result in enumerate(similar, 1):
        print(f"\n{i}. Similarity: {result.score:.3f}")
        print(f"   Conversation: {result.conversation.id}")
        print(f"   Summary: {result.conversation.summary}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Commander Memory System - Example Usage")
    print("=" * 60)

    # Run examples
    await example_basic_usage()
    await example_entity_search()
    await example_context_loading()
    await example_similarity_search()

    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60 + "\n")

    print("📚 For more information, see:")
    print("   - src/claude_mpm/commander/memory/README.md")
    print("   - API documentation in each module")


if __name__ == "__main__":
    asyncio.run(main())
