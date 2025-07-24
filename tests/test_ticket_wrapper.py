"""Tests for the ticket command wrapper."""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import subprocess

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestTicketCLI:
    """Test the TicketCLI class methods."""
    
    @pytest.fixture
    def mock_ticket_manager(self):
        """Mock the TicketManager module."""
        with patch('sys.modules', {'claude_mpm.services.ticket_manager': MagicMock(), 
                                   'claude_mpm.utils.logger': MagicMock()}):
            yield
    
    @pytest.fixture
    def ticket_module(self, mock_ticket_manager):
        """Load the ticket module dynamically."""
        import importlib.util
        ticket_path = Path(__file__).parent.parent / "scripts" / "ticket"
        spec = importlib.util.spec_from_file_location("ticket", str(ticket_path))
        ticket = importlib.util.module_from_spec(spec)
        
        # Mock the imports before executing
        with patch.dict('sys.modules', {
            'claude_mpm.services.ticket_manager': MagicMock(TicketManager=MagicMock),
            'claude_mpm.utils.logger': MagicMock(get_logger=MagicMock())
        }):
            spec.loader.exec_module(ticket)
        
        return ticket
    
    @pytest.fixture
    def cli(self, ticket_module):
        """Create a TicketCLI instance with mocked dependencies."""
        with patch.object(ticket_module, 'TicketManager') as mock_tm:
            cli = ticket_module.TicketCLI()
            cli.ticket_manager = mock_tm()
            return cli
    
    def test_create_basic(self, cli, ticket_module, capsys):
        """Test basic ticket creation."""
        # Mock successful creation
        cli.ticket_manager.create_ticket.return_value = "TSK-0001"
        
        # Create args
        args = Mock()
        args.title = "Fix login bug"
        args.type = "bug"
        args.priority = "high"
        args.description = None
        args.tags = None
        args.verbose = False
        
        # Execute
        cli.create(args)
        
        # Verify
        cli.ticket_manager.create_ticket.assert_called_once_with(
            title="Fix login bug",
            ticket_type="bug",
            description="",
            priority="high",
            tags=[],
            source="ticket-cli"
        )
        
        # Check output
        captured = capsys.readouterr()
        assert "✅ Created ticket: TSK-0001" in captured.out
    
    def test_create_with_description(self, cli, ticket_module, capsys):
        """Test ticket creation with description."""
        cli.ticket_manager.create_ticket.return_value = "TSK-0002"
        
        args = Mock()
        args.title = "Add feature"
        args.type = "feature"
        args.priority = "medium"
        args.description = ["This", "is", "a", "description"]
        args.tags = None
        args.verbose = False
        
        cli.create(args)
        
        cli.ticket_manager.create_ticket.assert_called_once_with(
            title="Add feature",
            ticket_type="feature",
            description="This is a description",
            priority="medium",
            tags=[],
            source="ticket-cli"
        )
    
    def test_create_with_tags(self, cli, ticket_module, capsys):
        """Test ticket creation with tags."""
        cli.ticket_manager.create_ticket.return_value = "TSK-0003"
        
        args = Mock()
        args.title = "Task with tags"
        args.type = "task"
        args.priority = "low"
        args.description = None
        args.tags = "frontend,ui,urgent"
        args.verbose = False
        
        cli.create(args)
        
        cli.ticket_manager.create_ticket.assert_called_once_with(
            title="Task with tags",
            ticket_type="task",
            description="",
            priority="low",
            tags=["frontend", "ui", "urgent"],
            source="ticket-cli"
        )
    
    def test_create_verbose(self, cli, ticket_module, capsys):
        """Test ticket creation with verbose output."""
        cli.ticket_manager.create_ticket.return_value = "TSK-0004"
        
        args = Mock()
        args.title = "Verbose ticket"
        args.type = "issue"
        args.priority = "critical"
        args.description = None
        args.tags = "backend,api"
        args.verbose = True
        
        cli.create(args)
        
        captured = capsys.readouterr()
        assert "✅ Created ticket: TSK-0004" in captured.out
        assert "Type: issue" in captured.out
        assert "Priority: critical" in captured.out
        assert "Tags: backend, api" in captured.out
    
    def test_create_failure(self, cli, ticket_module, capsys):
        """Test ticket creation failure."""
        cli.ticket_manager.create_ticket.return_value = None
        
        args = Mock()
        args.title = "Failed ticket"
        args.type = "task"
        args.priority = "medium"
        args.description = None
        args.tags = None
        args.verbose = False
        
        with pytest.raises(SystemExit) as exc_info:
            cli.create(args)
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "❌ Failed to create ticket" in captured.out
    
    def test_list_empty(self, cli, ticket_module, capsys):
        """Test listing tickets when none exist."""
        cli.ticket_manager.list_recent_tickets.return_value = []
        
        args = Mock()
        args.limit = 10
        args.verbose = False
        
        cli.list(args)
        
        cli.ticket_manager.list_recent_tickets.assert_called_once_with(limit=10)
        captured = capsys.readouterr()
        assert "No tickets found." in captured.out
    
    def test_list_basic(self, cli, ticket_module, capsys):
        """Test basic ticket listing."""
        cli.ticket_manager.list_recent_tickets.return_value = [
            {
                'id': 'TSK-0001',
                'title': 'First ticket',
                'status': 'open',
                'priority': 'high',
                'tags': ['bug'],
                'created_at': '2025-01-01T10:00:00'
            },
            {
                'id': 'TSK-0002',
                'title': 'Second ticket',
                'status': 'closed',
                'priority': 'low',
                'tags': ['feature', 'ui'],
                'created_at': '2025-01-02T10:00:00'
            }
        ]
        
        args = Mock()
        args.limit = 10
        args.verbose = False
        
        cli.list(args)
        
        captured = capsys.readouterr()
        assert "Recent tickets (showing 2):" in captured.out
        assert "🔵 [TSK-0001] First ticket" in captured.out
        assert "✅ [TSK-0002] Second ticket" in captured.out
    
    def test_list_verbose(self, cli, ticket_module, capsys):
        """Test verbose ticket listing."""
        cli.ticket_manager.list_recent_tickets.return_value = [
            {
                'id': 'TSK-0001',
                'title': 'Verbose ticket',
                'status': 'open',
                'priority': 'medium',
                'tags': ['backend', 'api'],
                'created_at': '2025-01-01T10:00:00'
            }
        ]
        
        args = Mock()
        args.limit = 5
        args.verbose = True
        
        cli.list(args)
        
        captured = capsys.readouterr()
        assert "Status: open | Priority: medium" in captured.out
        assert "Tags: backend, api" in captured.out
        assert "Created: 2025-01-01T10:00:00" in captured.out
    
    def test_view_success(self, cli, ticket_module, capsys):
        """Test viewing a ticket successfully."""
        cli.ticket_manager.get_ticket.return_value = {
            'id': 'TSK-0001',
            'title': 'Test ticket',
            'status': 'in_progress',
            'priority': 'high',
            'tags': ['bug', 'critical'],
            'assignees': ['user1', 'user2'],
            'description': 'This is a test description',
            'created_at': '2025-01-01T10:00:00',
            'updated_at': '2025-01-02T15:00:00',
            'metadata': {
                'ticket_type': 'bug',
                'source': 'ticket-cli'
            }
        }
        
        args = Mock()
        args.id = 'TSK-0001'
        args.verbose = False
        
        cli.view(args)
        
        cli.ticket_manager.get_ticket.assert_called_once_with('TSK-0001')
        
        captured = capsys.readouterr()
        assert "Ticket: TSK-0001" in captured.out
        assert "Title: Test ticket" in captured.out
        assert "Type: bug" in captured.out
        assert "Status: in_progress" in captured.out
        assert "Priority: high" in captured.out
        assert "Tags: bug, critical" in captured.out
        assert "Assignees: user1, user2" in captured.out
        assert "This is a test description" in captured.out
        assert "Created: 2025-01-01T10:00:00" in captured.out
        assert "Updated: 2025-01-02T15:00:00" in captured.out
    
    def test_view_verbose(self, cli, ticket_module, capsys):
        """Test viewing a ticket with verbose output."""
        cli.ticket_manager.get_ticket.return_value = {
            'id': 'TSK-0001',
            'title': 'Test ticket',
            'status': 'open',
            'priority': 'low',
            'tags': [],
            'assignees': [],
            'description': 'Short desc',
            'created_at': '2025-01-01T10:00:00',
            'updated_at': '2025-01-01T10:00:00',
            'metadata': {
                'custom_field': 'custom_value',
                'another_field': 'another_value'
            }
        }
        
        args = Mock()
        args.id = 'TSK-0001'
        args.verbose = True
        
        cli.view(args)
        
        captured = capsys.readouterr()
        assert "Metadata:" in captured.out
        assert "custom_field: custom_value" in captured.out
        assert "another_field: another_value" in captured.out
    
    def test_view_not_found(self, cli, ticket_module, capsys):
        """Test viewing a non-existent ticket."""
        cli.ticket_manager.get_ticket.return_value = None
        
        args = Mock()
        args.id = 'TSK-9999'
        args.verbose = False
        
        with pytest.raises(SystemExit) as exc_info:
            cli.view(args)
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "❌ Ticket TSK-9999 not found" in captured.out
    
    @patch('subprocess.run')
    def test_update_all_fields(self, mock_run, cli, ticket_module, capsys):
        """Test updating a ticket with all fields."""
        args = Mock()
        args.id = 'TSK-0001'
        args.status = 'in_progress'
        args.priority = 'critical'
        args.assign = 'user123'
        args.tags = 'urgent,backend'
        
        cli.update(args)
        
        mock_run.assert_called_once_with(
            ["ai-trackdown", "update", "TSK-0001", 
             "--status", "in_progress",
             "--priority", "critical",
             "--assign", "user123",
             "--tags", "urgent,backend"],
            check=True
        )
        
        captured = capsys.readouterr()
        assert "✅ Updated ticket: TSK-0001" in captured.out
    
    @patch('subprocess.run')
    def test_update_partial(self, mock_run, cli, ticket_module, capsys):
        """Test updating a ticket with only some fields."""
        args = Mock()
        args.id = 'TSK-0002'
        args.status = 'closed'
        args.priority = None
        args.assign = None
        args.tags = None
        
        cli.update(args)
        
        mock_run.assert_called_once_with(
            ["ai-trackdown", "update", "TSK-0002", "--status", "closed"],
            check=True
        )
    
    @patch('subprocess.run')
    def test_update_failure(self, mock_run, cli, ticket_module, capsys):
        """Test update failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ai-trackdown")
        
        args = Mock()
        args.id = 'TSK-0001'
        args.status = 'invalid'
        args.priority = None
        args.assign = None
        args.tags = None
        
        with pytest.raises(SystemExit) as exc_info:
            cli.update(args)
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "❌ Failed to update ticket: TSK-0001" in captured.out
    
    @patch('subprocess.run')
    def test_close_success(self, mock_run, cli, ticket_module, capsys):
        """Test closing a ticket successfully."""
        args = Mock()
        args.id = 'TSK-0001'
        
        cli.close(args)
        
        mock_run.assert_called_once_with(
            ["ai-trackdown", "update", "TSK-0001", "--status", "closed"],
            check=True
        )
        
        captured = capsys.readouterr()
        assert "✅ Closed ticket: TSK-0001" in captured.out
    
    @patch('subprocess.run')
    def test_close_failure(self, mock_run, cli, ticket_module, capsys):
        """Test close failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ai-trackdown")
        
        args = Mock()
        args.id = 'TSK-9999'
        
        with pytest.raises(SystemExit) as exc_info:
            cli.close(args)
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "❌ Failed to close ticket: TSK-9999" in captured.out


class TestMain:
    """Test the main entry point."""
    
    @pytest.fixture
    def ticket_module(self):
        """Load the ticket module dynamically."""
        import importlib.util
        ticket_path = Path(__file__).parent.parent / "scripts" / "ticket"
        spec = importlib.util.spec_from_file_location("ticket", str(ticket_path))
        ticket = importlib.util.module_from_spec(spec)
        
        # Mock the imports before executing
        with patch.dict('sys.modules', {
            'claude_mpm.services.ticket_manager': MagicMock(TicketManager=MagicMock),
            'claude_mpm.utils.logger': MagicMock(get_logger=MagicMock())
        }):
            spec.loader.exec_module(ticket)
        
        return ticket
    
    def test_main_no_args(self, ticket_module, capsys):
        """Test main with no arguments shows help."""
        with patch.object(ticket_module, 'TicketCLI'):
            with patch('sys.argv', ['ticket']):
                ticket_module.main()
        
        captured = capsys.readouterr()
        assert "Simplified ticket management" in captured.out
        assert "Available commands" in captured.out
    
    def test_main_help_command(self, ticket_module, capsys):
        """Test explicit help command."""
        with patch.object(ticket_module, 'TicketCLI'):
            with patch('sys.argv', ['ticket', 'help']):
                ticket_module.main()
        
        captured = capsys.readouterr()
        assert "Simplified ticket management" in captured.out
    
    def test_main_create_command(self, ticket_module):
        """Test create command routing."""
        mock_cli = Mock()
        with patch.object(ticket_module, 'TicketCLI', return_value=mock_cli):
            with patch('sys.argv', ['ticket', 'create', 'Test title', '-t', 'bug']):
                ticket_module.main()
        
        mock_cli.create.assert_called_once()
        args = mock_cli.create.call_args[0][0]
        assert args.title == 'Test title'
        assert args.type == 'bug'
    
    def test_main_list_command(self, ticket_module):
        """Test list command routing."""
        mock_cli = Mock()
        with patch.object(ticket_module, 'TicketCLI', return_value=mock_cli):
            with patch('sys.argv', ['ticket', 'list', '--limit', '20']):
                ticket_module.main()
        
        mock_cli.list.assert_called_once()
        args = mock_cli.list.call_args[0][0]
        assert args.limit == 20
    
    def test_main_keyboard_interrupt(self, ticket_module, capsys):
        """Test handling keyboard interrupt."""
        mock_cli = Mock()
        mock_cli.create.side_effect = KeyboardInterrupt
        
        with patch.object(ticket_module, 'TicketCLI', return_value=mock_cli):
            with patch('sys.argv', ['ticket', 'create', 'Test']):
                with pytest.raises(SystemExit) as exc_info:
                    ticket_module.main()
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Operation cancelled" in captured.out
    
    def test_main_exception(self, ticket_module, capsys):
        """Test handling general exception."""
        mock_cli = Mock()
        mock_cli.list.side_effect = Exception("Test error")
        
        with patch.object(ticket_module, 'TicketCLI', return_value=mock_cli):
            with patch('sys.argv', ['ticket', 'list']):
                with pytest.raises(SystemExit) as exc_info:
                    ticket_module.main()
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "❌ Error: Test error" in captured.out