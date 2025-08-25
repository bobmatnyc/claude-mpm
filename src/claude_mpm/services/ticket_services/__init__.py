"""
Ticket services for clean separation of concerns.

WHY: Extract business logic from the god class TicketsCommand into
focused, testable service modules following SOLID principles.

DESIGN DECISIONS:
- Each service has a single responsibility
- Services use dependency injection for flexibility
- Clear interfaces for each service
- Services are stateless for better testability
"""

from .crud_service import TicketCRUDService
from .formatter_service import TicketFormatterService
from .search_service import TicketSearchService
from .validation_service import TicketValidationService
from .workflow_service import TicketWorkflowService

__all__ = [
    "TicketCRUDService",
    "TicketFormatterService",
    "TicketSearchService",
    "TicketValidationService",
    "TicketWorkflowService",
]
