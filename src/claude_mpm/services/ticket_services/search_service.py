"""
Search service for tickets.

WHY: Extracts search logic into a dedicated service for better
organization and testability of search functionality.

DESIGN DECISIONS:
- Supports text-based search across multiple fields
- Handles filtering by type and status
- Provides relevance ranking for search results
- Abstracts search backend (can switch between different implementations)
"""

from typing import Any, Dict, List, Optional

from ...core.logger import get_logger


class TicketSearchService:
    """Service for searching tickets."""

    def __init__(self, ticket_manager=None):
        """
        Initialize the search service.

        Args:
            ticket_manager: Optional ticket manager instance for testing
        """
        self.logger = get_logger("services.ticket_search")
        self._ticket_manager = ticket_manager

    @property
    def ticket_manager(self):
        """Lazy load ticket manager."""
        if self._ticket_manager is None:
            try:
                from ..ticket_manager import TicketManager
            except ImportError:
                from claude_mpm.services.ticket_manager import TicketManager
            self._ticket_manager = TicketManager()
        return self._ticket_manager

    def search_tickets(
        self,
        query: str,
        type_filter: str = "all",
        status_filter: str = "all",
        limit: int = 10,
        search_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search tickets by query string.

        Args:
            query: Search query
            type_filter: Filter by ticket type
            status_filter: Filter by status
            limit: Maximum results to return
            search_fields: Fields to search in (default: title, description, tags)

        Returns:
            List of matching tickets
        """
        if not search_fields:
            search_fields = ["title", "description", "tags"]

        try:
            # Get all available tickets
            all_tickets = self.ticket_manager.list_recent_tickets(limit=100)

            # Search and filter
            matched_tickets = []
            query_lower = query.lower()

            for ticket in all_tickets:
                # Check if query matches any search field
                if self._matches_query(ticket, query_lower, search_fields):
                    # Apply type filter
                    if not self._passes_type_filter(ticket, type_filter):
                        continue

                    # Apply status filter
                    if not self._passes_status_filter(ticket, status_filter):
                        continue

                    matched_tickets.append(ticket)

                    if len(matched_tickets) >= limit:
                        break

            # Sort by relevance
            return self._sort_by_relevance(matched_tickets, query_lower)

        except Exception as e:
            self.logger.error(f"Error searching tickets: {e}")
            return []

    def _matches_query(
        self, ticket: Dict[str, Any], query: str, search_fields: List[str]
    ) -> bool:
        """
        Check if ticket matches the search query.

        Returns:
            True if ticket matches query in any search field
        """
        for field in search_fields:
            if field == "title" and query in ticket.get("title", "").lower():
                return True

            if (
                field == "description"
                and query in ticket.get("description", "").lower()
            ):
                return True

            if field == "tags":
                tags = ticket.get("tags", [])
                if any(query in tag.lower() for tag in tags):
                    return True

            if field == "id" and query in ticket.get("id", "").lower():
                return True

            # Search in metadata fields
            if field == "metadata":
                metadata = ticket.get("metadata", {})
                for value in metadata.values():
                    if isinstance(value, str) and query in value.lower():
                        return True

        return False

    def _passes_type_filter(self, ticket: Dict[str, Any], type_filter: str) -> bool:
        """
        Check if ticket passes type filter.

        Returns:
            True if ticket matches type filter
        """
        if type_filter == "all":
            return True

        ticket_type = ticket.get("metadata", {}).get("ticket_type", "unknown")
        return ticket_type == type_filter

    def _passes_status_filter(self, ticket: Dict[str, Any], status_filter: str) -> bool:
        """
        Check if ticket passes status filter.

        Returns:
            True if ticket matches status filter
        """
        if status_filter == "all":
            return True

        return ticket.get("status") == status_filter

    def _sort_by_relevance(
        self, tickets: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """
        Sort tickets by relevance to search query.

        Returns:
            Sorted list of tickets (most relevant first)
        """

        def relevance_score(ticket):
            score = 0

            # Title matches are most relevant
            if query in ticket.get("title", "").lower():
                score += 10

            # ID matches are very relevant
            if query in ticket.get("id", "").lower():
                score += 8

            # Tag matches are moderately relevant
            tags = ticket.get("tags", [])
            for tag in tags:
                if query in tag.lower():
                    score += 5

            # Description matches are less relevant
            if query in ticket.get("description", "").lower():
                score += 2

            # Boost recent tickets slightly
            if ticket.get("status") in ["open", "in_progress"]:
                score += 1

            return score

        return sorted(tickets, key=relevance_score, reverse=True)

    def find_similar_tickets(
        self, ticket_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find tickets similar to a given ticket.

        Args:
            ticket_id: ID of the reference ticket
            limit: Maximum similar tickets to return

        Returns:
            List of similar tickets
        """
        try:
            # Get the reference ticket
            reference = self.ticket_manager.get_ticket(ticket_id)
            if not reference:
                return []

            # Extract keywords from title and tags
            keywords = self._extract_keywords(reference)

            # Search for similar tickets
            similar = []
            all_tickets = self.ticket_manager.list_recent_tickets(limit=50)

            for ticket in all_tickets:
                if ticket["id"] == ticket_id:
                    continue  # Skip the reference ticket

                # Calculate similarity score
                score = self._calculate_similarity(reference, ticket, keywords)

                if score > 0:
                    similar.append((score, ticket))

            # Sort by similarity and return top results
            similar.sort(key=lambda x: x[0], reverse=True)
            return [ticket for _, ticket in similar[:limit]]

        except Exception as e:
            self.logger.error(f"Error finding similar tickets: {e}")
            return []

    def _extract_keywords(self, ticket: Dict[str, Any]) -> List[str]:
        """
        Extract keywords from a ticket for similarity matching.

        Returns:
            List of keywords
        """
        keywords = []

        # Extract words from title
        title = ticket.get("title", "")
        keywords.extend(title.lower().split())

        # Add tags as keywords
        keywords.extend([tag.lower() for tag in ticket.get("tags", [])])

        # Extract key words from description (first 100 chars)
        desc = ticket.get("description", "")[:100]
        keywords.extend(desc.lower().split()[:10])

        # Remove common words
        common_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
        }
        keywords = [w for w in keywords if w not in common_words and len(w) > 2]

        return list(set(keywords))  # Remove duplicates

    def _calculate_similarity(
        self, ref_ticket: Dict[str, Any], ticket: Dict[str, Any], keywords: List[str]
    ) -> float:
        """
        Calculate similarity score between two tickets.

        Returns:
            Similarity score (0-100)
        """
        score = 0.0

        # Same type bonus
        ref_type = ref_ticket.get("metadata", {}).get("ticket_type")
        ticket_type = ticket.get("metadata", {}).get("ticket_type")
        if ref_type and ticket_type and ref_type == ticket_type:
            score += 10

        # Same status bonus
        if ref_ticket.get("status") == ticket.get("status"):
            score += 5

        # Same priority bonus
        if ref_ticket.get("priority") == ticket.get("priority"):
            score += 3

        # Keyword matches
        ticket_text = (
            ticket.get("title", "").lower()
            + " "
            + ticket.get("description", "").lower()
            + " "
            + " ".join(ticket.get("tags", []))
        ).lower()

        for keyword in keywords:
            if keyword in ticket_text:
                score += 2

        # Common tags
        ref_tags = set(ref_ticket.get("tags", []))
        ticket_tags = set(ticket.get("tags", []))
        common_tags = ref_tags.intersection(ticket_tags)
        score += len(common_tags) * 5

        return min(score, 100)  # Cap at 100
