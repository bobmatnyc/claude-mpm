"""
Tests demonstrating improved testability with dependency injection.

Shows how DI makes it easy to:
- Mock dependencies
- Test in isolation
- Configure services for testing
- Verify interactions
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from typing import Any, Dict, List

from claude_mpm.core.container import DIContainer, ServiceLifetime
from claude_mpm.core.service_registry import ServiceRegistry
from claude_mpm.core.config import Config
from claude_mpm.services.ticket_manager_di import (
    TicketManagerDI, ITaskManagerAdapter
)


class MockTaskAdapter(ITaskManagerAdapter):
    """Mock task adapter for testing."""
    
    def __init__(self):
        """Initialize mock adapter."""
        self.created_tasks = []
        self.tasks = {}
        self.call_count = {
            'create_task': 0,
            'get_recent_tasks': 0,
            'load_task': 0
        }
        
    def create_task(self, **kwargs) -> Any:
        """Mock task creation."""
        self.call_count['create_task'] += 1
        
        # Create mock task
        task = Mock()
        task.id = f"TSK-{len(self.created_tasks) + 1:04d}"
        task.title = kwargs.get('title', 'Test Task')
        task.status = kwargs.get('status', 'open')
        task.priority = kwargs.get('priority', 'medium')
        task.tags = kwargs.get('tags', [])
        task.created_at = '2024-01-01T12:00:00'
        
        self.created_tasks.append(task)
        self.tasks[task.id] = task
        
        return task
        
    def get_recent_tasks(self, limit: int) -> List[Any]:
        """Mock getting recent tasks."""
        self.call_count['get_recent_tasks'] += 1
        return self.created_tasks[-limit:]
        
    def load_task(self, task_id: str) -> Any:
        """Mock loading a task."""
        self.call_count['load_task'] += 1
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not found")
        return self.tasks[task_id]


class TestDependencyInjection(unittest.TestCase):
    """Test dependency injection functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.container = DIContainer()
        self.config = Config({'project.path': '/tmp/test-project'})
        
    def test_container_registration(self):
        """Test basic container registration and resolution."""
        # Register a service
        self.container.register_singleton(Config, instance=self.config)
        
        # Resolve the service
        resolved_config = self.container.resolve(Config)
        
        # Should be the same instance
        self.assertIs(resolved_config, self.config)
        
    def test_constructor_injection(self):
        """Test automatic constructor injection."""
        # Register dependencies
        self.container.register_singleton(Config, instance=self.config)
        
        # Create a service that depends on Config
        class TestService:
            def __init__(self, config: Config):
                self.config = config
                
        # Register and resolve
        self.container.register(TestService)
        service = self.container.resolve(TestService)
        
        # Config should be injected
        self.assertIsInstance(service.config, Config)
        self.assertIs(service.config, self.config)
        
    def test_factory_pattern(self):
        """Test factory-based service creation."""
        # Counter to track factory calls
        call_count = {'count': 0}
        
        def create_service(container: DIContainer) -> Any:
            call_count['count'] += 1
            config = container.resolve(Config)
            return {'config': config, 'instance': call_count['count']}
            
        # Register dependencies and factory
        self.container.register_singleton(Config, instance=self.config)
        self.container.register_factory(dict, create_service, lifetime=ServiceLifetime.TRANSIENT)
        
        # Resolve multiple times
        service1 = self.container.resolve(dict)
        service2 = self.container.resolve(dict)
        
        # Should create new instances (transient)
        self.assertEqual(service1['instance'], 1)
        self.assertEqual(service2['instance'], 2)
        self.assertEqual(call_count['count'], 2)
        
    def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected."""
        class ServiceA:
            def __init__(self, b: 'ServiceB'):
                self.b = b
                
        class ServiceB:
            def __init__(self, a: ServiceA):
                self.a = a
                
        # Register circular dependency
        self.container.register(ServiceA)
        self.container.register(ServiceB)
        
        # Should raise CircularDependencyError
        with self.assertRaises(Exception) as ctx:
            self.container.resolve(ServiceA)
            
        self.assertIn("Circular dependency", str(ctx.exception))
        
    def test_ticket_manager_with_mock_adapter(self):
        """Test TicketManager with mocked dependencies."""
        # Create mock adapter
        mock_adapter = MockTaskAdapter()
        
        # Create ticket manager with mock
        ticket_manager = TicketManagerDI(
            config=self.config,
            task_adapter=mock_adapter
        )
        
        # Create a ticket
        ticket_id = ticket_manager.create_ticket(
            title="Test Ticket",
            description="Test description",
            priority="high",
            tags=["test", "unit-test"]
        )
        
        # Verify ticket was created
        self.assertEqual(ticket_id, "TSK-0001")
        self.assertEqual(mock_adapter.call_count['create_task'], 1)
        
        # Verify task data
        created_task = mock_adapter.created_tasks[0]
        self.assertEqual(created_task.title, "Test Ticket")
        self.assertEqual(created_task.priority, "high")
        self.assertIn("test", created_task.tags)
        
    def test_ticket_manager_list_with_mock(self):
        """Test listing tickets with mock adapter."""
        # Create mock adapter with pre-populated tasks
        mock_adapter = MockTaskAdapter()
        
        # Create some tasks
        for i in range(5):
            mock_adapter.create_task(title=f"Task {i+1}")
            
        # Create ticket manager
        ticket_manager = TicketManagerDI(
            config=self.config,
            task_adapter=mock_adapter
        )
        
        # List recent tickets
        tickets = ticket_manager.list_recent_tickets(limit=3)
        
        # Verify results
        self.assertEqual(len(tickets), 3)
        self.assertEqual(tickets[0]['title'], "Task 3")
        self.assertEqual(tickets[1]['title'], "Task 4")
        self.assertEqual(tickets[2]['title'], "Task 5")
        self.assertEqual(mock_adapter.call_count['get_recent_tasks'], 1)
        
    def test_service_registry_integration(self):
        """Test service registry with DI container."""
        # Create registry with container
        registry = ServiceRegistry(self.container)
        
        # Register a mock service
        mock_config = Config({'test': 'value'})
        self.container.register_singleton(Config, instance=mock_config)
        
        # Register ticket manager with mock adapter
        mock_adapter = MockTaskAdapter()
        registry.register_service(
            "ticket_manager",
            TicketManagerDI,
            lifetime=ServiceLifetime.SINGLETON,
            factory=lambda c: TicketManagerDI(
                config=c.resolve(Config),
                task_adapter=mock_adapter
            )
        )
        
        # Resolve service
        ticket_manager = registry.get_service("ticket_manager")
        
        # Verify it works
        self.assertIsInstance(ticket_manager, TicketManagerDI)
        self.assertIs(ticket_manager.config, mock_config)
        self.assertIs(ticket_manager.task_adapter, mock_adapter)
        
    def test_service_with_optional_dependencies(self):
        """Test service with optional dependencies."""
        class OptionalService:
            def __init__(self, config: Config, logger=None):
                self.config = config
                self.logger = logger or Mock()
                
        # Register only required dependency
        self.container.register_singleton(Config, instance=self.config)
        self.container.register(OptionalService)
        
        # Resolve - should work with default logger
        service = self.container.resolve(OptionalService)
        
        self.assertIsInstance(service.config, Config)
        self.assertIsInstance(service.logger, Mock)
        
    def test_scoped_container(self):
        """Test child container for scoped scenarios."""
        # Register in parent
        self.container.register_singleton(Config, instance=self.config)
        
        # Create child container
        child_container = self.container.create_child_container()
        
        # Child should inherit registrations
        self.assertTrue(child_container.is_registered(Config))
        
        # But not singleton instances
        child_config = Config({'child': 'config'})
        child_container.register_singleton(Config, instance=child_config)
        
        # Parent and child should have different instances
        parent_resolved = self.container.resolve(Config)
        child_resolved = child_container.resolve(Config)
        
        self.assertIsNot(parent_resolved, child_resolved)
        self.assertEqual(parent_resolved.get('project.path'), '/tmp/test-project')
        self.assertEqual(child_resolved.get('child'), 'config')


class TestServiceTestability(unittest.TestCase):
    """Test improved testability of services with DI."""
    
    def test_isolated_service_testing(self):
        """Test service in complete isolation."""
        # Create all dependencies as mocks
        mock_config = Mock(spec=Config)
        mock_config.get.return_value = '/test/path'
        
        mock_adapter = Mock(spec=ITaskManagerAdapter)
        mock_adapter.create_task.return_value = Mock(id='TEST-001')
        
        # Create service with mocks
        service = TicketManagerDI(
            config=mock_config,
            task_adapter=mock_adapter
        )
        
        # Test behavior
        result = service.create_ticket(title="Test")
        
        # Verify interactions
        self.assertEqual(result, 'TEST-001')
        mock_adapter.create_task.assert_called_once()
        
        # Verify call arguments
        call_args = mock_adapter.create_task.call_args[1]
        self.assertEqual(call_args['title'], "Test")
        self.assertIn('task', call_args['tags'])
        
    def test_partial_mocking(self):
        """Test with partial mocking of dependencies."""
        # Real config, mock adapter
        real_config = Config({'project.path': '/real/path'})
        mock_adapter = MockTaskAdapter()
        
        # Create service
        service = TicketManagerDI(
            config=real_config,
            task_adapter=mock_adapter
        )
        
        # Should use real config values
        self.assertEqual(service.config.get('project.path'), '/real/path')
        
        # But mock adapter behavior
        ticket_id = service.create_ticket(title="Mixed Test")
        self.assertEqual(ticket_id, "TSK-0001")
        
    def test_behavior_verification(self):
        """Test behavior verification with mocks."""
        # Create mock that tracks behavior
        behavior_tracker = {
            'validations': [],
            'transformations': []
        }
        
        class TrackingAdapter(ITaskManagerAdapter):
            def create_task(self, **kwargs):
                # Track validations
                if 'title' in kwargs and len(kwargs['title']) > 0:
                    behavior_tracker['validations'].append('title_validated')
                    
                # Track transformations
                if 'priority' in kwargs:
                    behavior_tracker['transformations'].append(
                        f"priority_{kwargs['priority']}"
                    )
                    
                return Mock(id='TRACK-001')
                
            def get_recent_tasks(self, limit):
                return []
                
            def load_task(self, task_id):
                return Mock()
                
        # Use tracking adapter
        service = TicketManagerDI(
            config=Config(),
            task_adapter=TrackingAdapter()
        )
        
        # Create ticket
        service.create_ticket(
            title="Behavior Test",
            priority="high"
        )
        
        # Verify expected behavior occurred
        self.assertIn('title_validated', behavior_tracker['validations'])
        self.assertIn('priority_high', behavior_tracker['transformations'])


if __name__ == '__main__':
    unittest.main()