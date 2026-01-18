"""Tests for ConversationStore."""

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from claude_mpm.commander.memory.store import (
    Conversation,
    ConversationMessage,
    ConversationStore,
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
async def store(temp_db):
    """Create ConversationStore with temp database."""
    store = ConversationStore(db_path=temp_db, enable_vector=False)
    # Wait for schema initialization
    await asyncio.sleep(0.1)
    return store


@pytest.fixture
def sample_conversation():
    """Create sample conversation for testing."""
    messages = [
        ConversationMessage(
            role="user",
            content="Fix the login bug in src/auth.py",
            timestamp=datetime.now(timezone.utc),
        ),
        ConversationMessage(
            role="assistant",
            content="I'll investigate the bug. Let me read auth.py.",
            timestamp=datetime.now(timezone.utc),
        ),
        ConversationMessage(
            role="assistant",
            content="Found the issue - token validation was missing. Fixed it.",
            timestamp=datetime.now(timezone.utc),
        ),
    ]

    return Conversation(
        id="conv-test-123",
        project_id="proj-abc",
        instance_name="claude-code-1",
        session_id="sess-xyz",
        messages=messages,
        summary="Fixed login authentication bug in src/auth.py",
    )


@pytest.mark.asyncio
async def test_save_and_load(store, sample_conversation):
    """Test saving and loading conversations."""
    # Save
    await store.save(sample_conversation)

    # Load
    loaded = await store.load(sample_conversation.id)

    assert loaded is not None
    assert loaded.id == sample_conversation.id
    assert loaded.project_id == sample_conversation.project_id
    assert loaded.instance_name == sample_conversation.instance_name
    assert loaded.session_id == sample_conversation.session_id
    assert loaded.summary == sample_conversation.summary
    assert len(loaded.messages) == len(sample_conversation.messages)

    # Check first message
    assert loaded.messages[0].role == "user"
    assert loaded.messages[0].content == "Fix the login bug in src/auth.py"


@pytest.mark.asyncio
async def test_load_nonexistent(store):
    """Test loading non-existent conversation."""
    loaded = await store.load("conv-does-not-exist")
    assert loaded is None


@pytest.mark.asyncio
async def test_list_by_project(store, sample_conversation):
    """Test listing conversations by project."""
    # Save conversation
    await store.save(sample_conversation)

    # Create another conversation for same project
    conv2 = Conversation(
        id="conv-test-456",
        project_id="proj-abc",
        instance_name="claude-code-1",
        session_id="sess-def",
        messages=[
            ConversationMessage(role="user", content="Update README"),
            ConversationMessage(role="assistant", content="Updated README.md"),
        ],
    )
    await store.save(conv2)

    # Create conversation for different project
    conv3 = Conversation(
        id="conv-test-789",
        project_id="proj-xyz",
        instance_name="claude-code-1",
        session_id="sess-ghi",
        messages=[ConversationMessage(role="user", content="Add tests")],
    )
    await store.save(conv3)

    # List by project
    conversations = await store.list_by_project("proj-abc")

    assert len(conversations) == 2
    assert all(c.project_id == "proj-abc" for c in conversations)


@pytest.mark.asyncio
async def test_search_by_text(store, sample_conversation):
    """Test text search."""
    # Save conversation
    await store.save(sample_conversation)

    # Search for "login"
    results = await store.search_by_text("login", project_id="proj-abc")

    assert len(results) > 0
    assert any("login" in r.summary.lower() for r in results if r.summary)


@pytest.mark.asyncio
async def test_delete(store, sample_conversation):
    """Test deleting conversations."""
    # Save
    await store.save(sample_conversation)

    # Verify exists
    loaded = await store.load(sample_conversation.id)
    assert loaded is not None

    # Delete
    await store.delete(sample_conversation.id)

    # Verify deleted
    loaded = await store.load(sample_conversation.id)
    assert loaded is None


@pytest.mark.asyncio
async def test_conversation_properties(sample_conversation):
    """Test Conversation computed properties."""
    assert sample_conversation.message_count == 3
    assert sample_conversation.total_tokens > 0

    full_text = sample_conversation.get_full_text()
    assert "USER:" in full_text
    assert "ASSISTANT:" in full_text
    assert "login bug" in full_text


def test_conversation_message_from_thread_message():
    """Test converting ThreadMessage to ConversationMessage."""
    from claude_mpm.commander.models.project import ThreadMessage

    thread_msg = ThreadMessage(
        id="msg-123",
        role="user",
        content="Fix the bug",
        session_id="sess-abc",
    )

    conv_msg = ConversationMessage.from_thread_message(thread_msg)

    assert conv_msg.role == "user"
    assert conv_msg.content == "Fix the bug"
    assert conv_msg.metadata["thread_message_id"] == "msg-123"
    assert conv_msg.metadata["session_id"] == "sess-abc"
    assert conv_msg.token_count > 0
