"""Slack Block Kit utilities for formatting messages."""

from typing import Any

from ..models.ticket import Ticket, TicketPriority, TicketStatus

STATUS_EMOJI = {
    TicketStatus.OPEN: ":white_circle:",
    TicketStatus.IN_PROGRESS: ":large_blue_circle:",
    TicketStatus.REVIEW: ":large_yellow_circle:",
    TicketStatus.CLOSED: ":white_check_mark:",
    TicketStatus.BLOCKED: ":red_circle:",
}

PRIORITY_EMOJI = {
    TicketPriority.LOW: ":small_blue_diamond:",
    TicketPriority.MEDIUM: ":small_orange_diamond:",
    TicketPriority.HIGH: ":large_orange_diamond:",
    TicketPriority.URGENT: ":rotating_light:",
}


def format_ticket_blocks(ticket: Ticket) -> list[dict[str, Any]]:
    """Format a ticket as Slack blocks.

    Args:
        ticket: The ticket to format.

    Returns:
        List of Slack block elements.
    """
    status_emoji = STATUS_EMOJI.get(ticket.status, ":grey_question:")
    priority_emoji = PRIORITY_EMOJI.get(ticket.priority, "")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{priority_emoji} {ticket.title}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*ID:*\n`{ticket.id}`",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Status:*\n{status_emoji} {ticket.status.value}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Priority:*\n{ticket.priority.value}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Assignee:*\n{ticket.assignee or 'Unassigned'}",
                },
            ],
        },
    ]

    if ticket.description:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{ticket.description}",
                },
            }
        )

    if ticket.labels:
        labels_text = " ".join(f"`{label}`" for label in ticket.labels)
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Labels:* {labels_text}",
                    },
                ],
            }
        )

    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M')} | Updated: {ticket.updated_at.strftime('%Y-%m-%d %H:%M')}",
                },
            ],
        }
    )

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Update Status",
                        "emoji": True,
                    },
                    "action_id": f"update_status_{ticket.id}",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Delegate", "emoji": True},
                    "action_id": f"delegate_{ticket.id}",
                    "style": "primary",
                },
            ],
        }
    )

    return blocks


def format_ticket_list_blocks(tickets: list[Ticket]) -> list[dict[str, Any]]:
    """Format a list of tickets as Slack blocks.

    Args:
        tickets: List of tickets to format.

    Returns:
        List of Slack block elements.
    """
    if not tickets:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_No tickets found._",
                },
            }
        ]

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Tickets ({len(tickets)})",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    for ticket in tickets:
        status_emoji = STATUS_EMOJI.get(ticket.status, ":grey_question:")
        priority_emoji = PRIORITY_EMOJI.get(ticket.priority, "")

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{status_emoji} {priority_emoji} *{ticket.title}*\n`{ticket.id}` | {ticket.status.value} | {ticket.assignee or 'Unassigned'}",
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View", "emoji": True},
                    "action_id": f"view_ticket_{ticket.id}",
                },
            }
        )

    return blocks


def format_error_block(message: str) -> list[dict[str, Any]]:
    """Format an error message as Slack blocks.

    Args:
        message: The error message.

    Returns:
        List of Slack block elements.
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":x: *Error:* {message}",
            },
        }
    ]


def format_success_block(message: str) -> list[dict[str, Any]]:
    """Format a success message as Slack blocks.

    Args:
        message: The success message.

    Returns:
        List of Slack block elements.
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":white_check_mark: {message}",
            },
        }
    ]
