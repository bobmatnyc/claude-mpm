"""Google Workspace tools module.

WHY: Provides CLI-accessible bulk operations for Google Workspace APIs.
Bypasses MCP protocol overhead for batch processing.

USAGE:
    claude-mpm tools google <action> [options]

ACTIONS:
    gmail-export           - Export emails matching query
    gmail-import           - Import emails from file
    calendar-bulk-create   - Create multiple calendar events
    calendar-export        - Export calendar events
    drive-batch-upload     - Upload multiple files to Drive
    drive-batch-download   - Download multiple files from Drive
"""

import json
from typing import Any, Optional

import requests

from claude_mpm.tools import register_service
from claude_mpm.tools.base import BaseToolModule, ToolResult


class GoogleTools(BaseToolModule):
    """Google Workspace bulk operations tool module."""

    def get_service_name(self) -> str:
        """Return service name."""
        return "google"

    def get_actions(self) -> list[str]:
        """Return list of available actions."""
        return [
            "gmail-export",
            "gmail-import",
            "calendar-bulk-create",
            "calendar-export",
            "drive-batch-upload",
            "drive-batch-download",
        ]

    def get_action_help(self, action: str) -> str:
        """Return help text for specific action."""
        help_texts = {
            "gmail-export": "Export emails matching query to JSON",
            "gmail-import": "Import emails from JSON file",
            "calendar-bulk-create": "Create multiple calendar events from JSON",
            "calendar-export": "Export calendar events to JSON",
            "drive-batch-upload": "Upload multiple files to Google Drive",
            "drive-batch-download": "Download multiple files from Google Drive",
        }
        return help_texts.get(action, "No help available")

    def _get_valid_token(self, service: str = "google-workspace-mpm") -> str:
        """Get valid access token.

        Args:
            service: Service name for token lookup

        Returns:
            Valid access token

        Raises:
            ValueError: If no token found or token is expired
        """
        stored = self.storage.retrieve(service)
        if not stored:
            raise ValueError(
                f"No token found for {service}. Run 'claude-mpm setup oauth google-workspace-mcp' first."
            )

        # Check if token is expired
        if stored.token.is_expired():
            raise ValueError(
                f"Token for {service} is expired. Run 'claude-mpm setup oauth google-workspace-mcp' to re-authenticate."
            )

        return stored.token.access_token

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        service: str = "google-workspace-mpm",
    ) -> dict[str, Any]:
        """Make authenticated API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            params: Query parameters
            json_data: JSON body for POST/PUT
            service: Service name for token

        Returns:
            Response JSON

        Raises:
            ValueError: If request fails
        """
        token = self._get_valid_token(service)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.HTTPError as e:
            raise ValueError(
                f"API request failed: {e.response.status_code} {e.response.text}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {e}") from e

    def _make_request_raw(
        self,
        method: str,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[dict[str, str]] = None,
        service: str = "google-workspace-mpm",
    ) -> dict[str, Any]:
        """Make authenticated API request with raw body.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            data: Raw bytes body
            headers: Additional headers
            service: Service name for token

        Returns:
            Response JSON

        Raises:
            ValueError: If request fails
        """
        token = self._get_valid_token(service)
        request_headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                data=data,
                timeout=60,
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.HTTPError as e:
            raise ValueError(
                f"API request failed: {e.response.status_code} {e.response.text}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {e}") from e

    def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute Google Workspace action.

        Args:
            action: Action name
            **kwargs: Action-specific arguments

        Returns:
            ToolResult with operation results
        """
        # Validate action
        self.validate_action(action)

        # Route to action handler
        if action == "gmail-export":
            return self._gmail_export(**kwargs)
        if action == "gmail-import":
            return self._gmail_import(**kwargs)
        if action == "calendar-bulk-create":
            return self._calendar_bulk_create(**kwargs)
        if action == "calendar-export":
            return self._calendar_export(**kwargs)
        if action == "drive-batch-upload":
            return self._drive_batch_upload(**kwargs)
        if action == "drive-batch-download":
            return self._drive_batch_download(**kwargs)
        return ToolResult(
            success=False,
            action=action,
            error=f"Action {action} not implemented yet",
        )

    def _gmail_export(self, **kwargs) -> ToolResult:
        """Export Gmail messages.

        Args:
            query: Gmail search query (default: "")
            max_results: Maximum number of messages to export (default: 100)
            format: Export format - "metadata" or "full" (default: "metadata")

        Returns:
            ToolResult with exported messages
        """
        query = kwargs.get("query", "")
        max_results = int(kwargs.get("max_results", 100))
        export_format = kwargs.get("format", "metadata")

        try:
            # Search for messages
            messages = []
            page_token = None
            base_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

            while len(messages) < max_results:
                # Build search params
                params = {
                    "q": query,
                    "maxResults": min(max_results - len(messages), 100),
                }
                if page_token:
                    params["pageToken"] = page_token

                # Search messages
                search_result = self._make_request("GET", base_url, params=params)
                message_list = search_result.get("messages", [])

                if not message_list:
                    break

                # Get full message details if requested
                if export_format == "full":
                    for msg in message_list:
                        msg_url = f"{base_url}/{msg['id']}"
                        full_msg = self._make_request(
                            "GET", msg_url, params={"format": "full"}
                        )
                        messages.append(full_msg)
                else:
                    # Just metadata (id and threadId)
                    messages.extend(message_list)

                # Check for next page
                page_token = search_result.get("nextPageToken")
                if not page_token:
                    break

            return ToolResult(
                success=True,
                action="gmail-export",
                data={
                    "messages": messages,
                    "query": query,
                    "format": export_format,
                },
                metadata={
                    "count": len(messages),
                    "max_results": max_results,
                },
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                action="gmail-export",
                error=str(e),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                action="gmail-export",
                error=f"Unexpected error: {e}",
            )

    def _gmail_import(self, **kwargs) -> ToolResult:
        """Import Gmail messages from file.

        Args:
            file: Path to JSON file with messages
            label: Label to apply to imported messages (optional)

        Returns:
            ToolResult with import results
        """
        file_path = kwargs.get("file")
        label = kwargs.get("label")

        if not file_path:
            return ToolResult(
                success=False,
                action="gmail-import",
                error="Required parameter 'file' not provided",
            )

        try:
            # Load messages from file
            with open(file_path) as f:
                data = json.load(f)

            messages = data.get("messages", [])
            if not messages:
                return ToolResult(
                    success=False,
                    action="gmail-import",
                    error="No messages found in file",
                )

            # Import messages
            imported = []
            failed = []
            base_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

            for msg in messages:
                try:
                    # Build import request
                    import_data = {"raw": msg.get("raw")}
                    if label:
                        import_data["labelIds"] = [label]

                    # Import message
                    result = self._make_request(
                        "POST",
                        f"{base_url}/import",
                        json_data=import_data,
                    )
                    imported.append(result.get("id"))

                except Exception as e:
                    failed.append({"message_id": msg.get("id"), "error": str(e)})

            return ToolResult(
                success=len(imported) > 0,
                action="gmail-import",
                data={
                    "imported": imported,
                    "failed": failed,
                },
                metadata={
                    "total": len(messages),
                    "imported_count": len(imported),
                    "failed_count": len(failed),
                },
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                action="gmail-import",
                error=f"File not found: {file_path}",
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                action="gmail-import",
                error=f"Invalid JSON in file: {e}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                action="gmail-import",
                error=f"Unexpected error: {e}",
            )

    def _calendar_bulk_create(self, **kwargs) -> ToolResult:
        """Create multiple calendar events from file.

        Args:
            file: Path to JSON file with events array
            calendar_id: Calendar ID (default: "primary")

        Returns:
            ToolResult with creation results
        """
        file_path = kwargs.get("file")
        calendar_id = kwargs.get("calendar_id", "primary")

        if not file_path:
            return ToolResult(
                success=False,
                action="calendar-bulk-create",
                error="Required parameter 'file' not provided",
            )

        try:
            # Load events from file
            with open(file_path) as f:
                data = json.load(f)

            events = data.get("events", [])
            if not events:
                return ToolResult(
                    success=False,
                    action="calendar-bulk-create",
                    error="No events found in file",
                )

            # Create events
            created = []
            failed = []
            base_url = (
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
            )

            for event in events:
                try:
                    # Validate required fields
                    if not all(
                        k in event for k in ["summary", "start_time", "end_time"]
                    ):
                        failed.append(
                            {
                                "event": event.get("summary", "unknown"),
                                "error": "Missing required fields (summary, start_time, end_time)",
                            }
                        )
                        continue

                    # Build event body
                    event_body = {
                        "summary": event["summary"],
                        "start": {"dateTime": event["start_time"]},
                        "end": {"dateTime": event["end_time"]},
                    }

                    # Optional fields
                    if "timezone" in event:
                        event_body["start"]["timeZone"] = event["timezone"]
                        event_body["end"]["timeZone"] = event["timezone"]

                    if "description" in event:
                        event_body["description"] = event["description"]

                    if "attendees" in event:
                        event_body["attendees"] = [
                            {"email": email} for email in event["attendees"]
                        ]

                    if "location" in event:
                        event_body["location"] = event["location"]

                    # Create event
                    result = self._make_request("POST", base_url, json_data=event_body)
                    created.append(
                        {
                            "id": result.get("id"),
                            "summary": result.get("summary"),
                            "start": result.get("start", {}).get("dateTime"),
                            "html_link": result.get("htmlLink"),
                        }
                    )

                except Exception as e:
                    failed.append(
                        {"event": event.get("summary", "unknown"), "error": str(e)}
                    )

            return ToolResult(
                success=len(created) > 0,
                action="calendar-bulk-create",
                data={
                    "created": created,
                    "failed": failed,
                },
                metadata={
                    "total": len(events),
                    "created_count": len(created),
                    "failed_count": len(failed),
                },
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                action="calendar-bulk-create",
                error=f"File not found: {file_path}",
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                action="calendar-bulk-create",
                error=f"Invalid JSON in file: {e}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                action="calendar-bulk-create",
                error=f"Unexpected error: {e}",
            )

    def _calendar_export(self, **kwargs) -> ToolResult:
        """Export calendar events.

        Args:
            calendar_id: Calendar ID (default: "primary")
            time_min: Minimum time for events (ISO 8601 format)
            time_max: Maximum time for events (ISO 8601 format)
            max_results: Maximum number of events to export (default: 250)

        Returns:
            ToolResult with exported events
        """
        calendar_id = kwargs.get("calendar_id", "primary")
        time_min = kwargs.get("time_min")
        time_max = kwargs.get("time_max")
        max_results = int(kwargs.get("max_results", 250))

        try:
            events = []
            page_token = None
            base_url = (
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
            )

            while len(events) < max_results:
                # Build request params
                params: dict[str, Any] = {
                    "maxResults": min(max_results - len(events), 250),
                    "singleEvents": True,
                    "orderBy": "startTime",
                }

                if time_min:
                    params["timeMin"] = time_min
                if time_max:
                    params["timeMax"] = time_max
                if page_token:
                    params["pageToken"] = page_token

                # Get events
                response = self._make_request("GET", base_url, params=params)
                items = response.get("items", [])

                if not items:
                    break

                # Extract event details
                for item in items:
                    start = item.get("start", {})
                    end = item.get("end", {})
                    events.append(
                        {
                            "id": item.get("id"),
                            "summary": item.get("summary"),
                            "description": item.get("description"),
                            "start": start.get("dateTime") or start.get("date"),
                            "end": end.get("dateTime") or end.get("date"),
                            "location": item.get("location"),
                            "attendees": [
                                a.get("email") for a in item.get("attendees", [])
                            ],
                            "html_link": item.get("htmlLink"),
                            "status": item.get("status"),
                        }
                    )

                # Check for next page
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            return ToolResult(
                success=True,
                action="calendar-export",
                data={
                    "events": events,
                    "calendar_id": calendar_id,
                    "time_min": time_min,
                    "time_max": time_max,
                },
                metadata={
                    "count": len(events),
                    "max_results": max_results,
                },
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                action="calendar-export",
                error=str(e),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                action="calendar-export",
                error=f"Unexpected error: {e}",
            )

    def _drive_batch_upload(self, **kwargs) -> ToolResult:
        """Batch upload files to Google Drive.

        Args:
            files: Comma-separated list of file paths to upload
            parent_id: Parent folder ID (optional)
            mime_type: MIME type override (optional, auto-detected if not provided)

        Returns:
            ToolResult with upload results
        """
        files_str = kwargs.get("files")
        parent_id = kwargs.get("parent_id")
        mime_type_override = kwargs.get("mime_type")

        if not files_str:
            return ToolResult(
                success=False,
                action="drive-batch-upload",
                error="Required parameter 'files' not provided (comma-separated paths)",
            )

        try:
            # Parse file paths
            from pathlib import Path

            file_paths = [p.strip() for p in files_str.split(",")]

            # Upload files
            uploaded = []
            failed = []
            base_url = (
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
            )

            for file_path in file_paths:
                try:
                    path = Path(file_path)
                    if not path.exists():
                        failed.append({"file": file_path, "error": "File not found"})
                        continue

                    # Read file content
                    content = path.read_text(encoding="utf-8")

                    # Determine MIME type
                    mime_type = mime_type_override
                    if not mime_type:
                        # Simple MIME type detection
                        ext = path.suffix.lower()
                        mime_types_map = {
                            ".txt": "text/plain",
                            ".json": "application/json",
                            ".html": "text/html",
                            ".md": "text/markdown",
                            ".py": "text/x-python",
                            ".js": "text/javascript",
                            ".css": "text/css",
                        }
                        mime_type = mime_types_map.get(ext, "text/plain")

                    # Build metadata
                    metadata_obj = {"name": path.name, "mimeType": mime_type}
                    if parent_id:
                        metadata_obj["parents"] = [parent_id]

                    # Build multipart body
                    boundary = "foo_bar_baz"
                    body_parts = [
                        f"--{boundary}",
                        "Content-Type: application/json; charset=UTF-8",
                        "",
                        json.dumps(metadata_obj),
                        f"--{boundary}",
                        f"Content-Type: {mime_type}",
                        "",
                        content,
                        f"--{boundary}--",
                    ]
                    body = "\r\n".join(body_parts)

                    # Upload
                    result = self._make_request_raw(
                        "POST",
                        base_url,
                        data=body.encode("utf-8"),
                        headers={
                            "Content-Type": f"multipart/related; boundary={boundary}"
                        },
                    )

                    uploaded.append(
                        {
                            "id": result.get("id"),
                            "name": result.get("name"),
                            "mimeType": result.get("mimeType"),
                            "webViewLink": result.get("webViewLink"),
                        }
                    )

                except UnicodeDecodeError:
                    failed.append(
                        {"file": file_path, "error": "File is binary (text files only)"}
                    )
                except Exception as e:
                    failed.append({"file": file_path, "error": str(e)})

            return ToolResult(
                success=len(uploaded) > 0,
                action="drive-batch-upload",
                data={
                    "uploaded": uploaded,
                    "failed": failed,
                },
                metadata={
                    "total": len(file_paths),
                    "uploaded_count": len(uploaded),
                    "failed_count": len(failed),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                action="drive-batch-upload",
                error=f"Unexpected error: {e}",
            )

    def _drive_batch_download(self, **kwargs) -> ToolResult:
        """Batch download files from Google Drive.

        Args:
            file_ids: Comma-separated list of file IDs to download
            output_dir: Output directory path (optional, defaults to current directory)

        Returns:
            ToolResult with download results
        """
        file_ids_str = kwargs.get("file_ids")
        output_dir = kwargs.get("output_dir", ".")

        if not file_ids_str:
            return ToolResult(
                success=False,
                action="drive-batch-download",
                error="Required parameter 'file_ids' not provided (comma-separated IDs)",
            )

        try:
            from pathlib import Path

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Parse file IDs
            file_ids = [fid.strip() for fid in file_ids_str.split(",")]

            # Download files
            downloaded = []
            failed = []
            base_url = "https://www.googleapis.com/drive/v3/files"

            for file_id in file_ids:
                try:
                    # Get file metadata
                    meta_url = f"{base_url}/{file_id}"
                    metadata = self._make_request(
                        "GET", meta_url, params={"fields": "id,name,mimeType,size"}
                    )

                    file_name = metadata.get("name", f"file_{file_id}")
                    mime_type = metadata.get("mimeType", "")

                    # Check if it's a Google Workspace file (needs export)
                    export_map = {
                        "application/vnd.google-apps.document": ("text/plain", ".txt"),
                        "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
                        "application/vnd.google-apps.presentation": (
                            "text/plain",
                            ".txt",
                        ),
                    }

                    token = self._get_valid_token()

                    if mime_type in export_map:
                        # Export Google Workspace files
                        export_mime, ext = export_map[mime_type]
                        export_url = f"{base_url}/{file_id}/export"
                        response = requests.get(
                            export_url,
                            params={"mimeType": export_mime},
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=60,
                        )
                        response.raise_for_status()
                        content = response.text

                        # Ensure file has proper extension
                        if not file_name.endswith(ext):
                            file_name = f"{file_name}{ext}"
                    else:
                        # Download regular files
                        download_url = f"{base_url}/{file_id}"
                        response = requests.get(
                            download_url,
                            params={"alt": "media"},
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=60,
                        )
                        response.raise_for_status()

                        # Save as text if possible, otherwise binary
                        try:
                            content = response.text
                        except UnicodeDecodeError:
                            # Binary file - save as bytes
                            file_path = output_path / file_name
                            file_path.write_bytes(response.content)
                            downloaded.append(
                                {
                                    "id": file_id,
                                    "name": file_name,
                                    "path": str(file_path),
                                    "size": len(response.content),
                                }
                            )
                            continue

                    # Save text content
                    file_path = output_path / file_name
                    file_path.write_text(content, encoding="utf-8")

                    downloaded.append(
                        {
                            "id": file_id,
                            "name": file_name,
                            "path": str(file_path),
                            "size": len(content),
                        }
                    )

                except Exception as e:
                    failed.append({"file_id": file_id, "error": str(e)})

            return ToolResult(
                success=len(downloaded) > 0,
                action="drive-batch-download",
                data={
                    "downloaded": downloaded,
                    "failed": failed,
                    "output_dir": str(output_path),
                },
                metadata={
                    "total": len(file_ids),
                    "downloaded_count": len(downloaded),
                    "failed_count": len(failed),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                action="drive-batch-download",
                error=f"Unexpected error: {e}",
            )


# Register this service
register_service("google", GoogleTools)
