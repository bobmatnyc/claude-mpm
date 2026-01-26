"""MPM API client for Slack integration."""

import logging
from typing import Any

import httpx

from ..config import settings
from ..models.ticket import Ticket, TicketCreate, TicketUpdate

logger = logging.getLogger(__name__)


class MPMClient:
    """Client for interacting with the MPM API."""

    def __init__(self) -> None:
        """Initialize the MPM client."""
        self.base_url = settings.mpm_api_url.rstrip("/")
        self.headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if settings.mpm_api_key:
            self.headers["Authorization"] = f"Bearer {settings.mpm_api_key}"

    async def create_ticket(self, ticket: TicketCreate) -> Ticket:
        """Create a new ticket.

        Args:
            ticket: Ticket creation data.

        Returns:
            The created ticket.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/tickets",
                json=ticket.model_dump(),
                headers=self.headers,
            )
            response.raise_for_status()
            return Ticket.model_validate(response.json())

    async def get_ticket(self, ticket_id: str) -> Ticket:
        """Get a ticket by ID.

        Args:
            ticket_id: The ticket ID.

        Returns:
            The ticket.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/tickets/{ticket_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return Ticket.model_validate(response.json())

    async def list_tickets(
        self,
        status: str | None = None,
        assignee: str | None = None,
        limit: int = 20,
    ) -> list[Ticket]:
        """List tickets with optional filters.

        Args:
            status: Filter by status.
            assignee: Filter by assignee.
            limit: Maximum number of tickets to return.

        Returns:
            List of tickets.
        """
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if assignee:
            params["assignee"] = assignee

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/tickets",
                params=params,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            return [Ticket.model_validate(t) for t in data.get("tickets", [])]

    async def update_ticket(self, ticket_id: str, update: TicketUpdate) -> Ticket:
        """Update a ticket.

        Args:
            ticket_id: The ticket ID.
            update: Ticket update data.

        Returns:
            The updated ticket.
        """
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/api/tickets/{ticket_id}",
                json=update.model_dump(exclude_unset=True),
                headers=self.headers,
            )
            response.raise_for_status()
            return Ticket.model_validate(response.json())

    async def delegate_ticket(
        self,
        ticket_id: str,
        agent_type: str = "default",
    ) -> dict[str, Any]:
        """Delegate a ticket to a Claude agent.

        Args:
            ticket_id: The ticket ID.
            agent_type: Type of agent to delegate to.

        Returns:
            Delegation result.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/tickets/{ticket_id}/delegate",
                json={"agent_type": agent_type},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_system_status(self) -> dict[str, Any]:
        """Get MPM system status.

        Returns:
            System status information.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/status",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
