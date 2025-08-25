"""Ticket manager stub for backward compatibility."""


class TicketManager:
    """Stub TicketManager class for backward compatibility."""

    def create_task(self, *args, **kwargs):
        """Stub method."""
        return "TSK-STUB-001"  # Return a stub ticket ID

    def create_ticket(self, *args, **kwargs):
        """Stub method - alias for create_task."""
        return self.create_task(*args, **kwargs)

    def list_recent_tickets(self, *args, **kwargs):
        """Stub method."""
        return []

    def get_ticket(self, *args, **kwargs):
        """Stub method."""
        return

    def update_task(self, *args, **kwargs):
        """Stub method."""
        return False

    def close_task(self, *args, **kwargs):
        """Stub method."""
        return False
