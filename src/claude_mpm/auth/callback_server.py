"""OAuth callback server for handling authorization redirects.

This module provides a local HTTP server that handles OAuth2 callback
redirects, capturing authorization codes and tokens from OAuth providers.

Security Features:
    - Binds only to localhost (127.0.0.1)
    - CSRF protection via state parameter validation
    - Automatic server shutdown after callback received
    - Configurable timeout for callback wait
"""

import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Optional

from aiohttp import web

# Default port for OAuth callback server
DEFAULT_PORT = 8789

# HTML response templates
SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Successful</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 40px 60px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        .success-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        h1 { color: #22c55e; margin: 0 0 10px 0; }
        p { color: #666; margin: 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">&#10004;</div>
        <h1>Authorization Successful</h1>
        <p>You can close this window and return to Claude.</p>
    </div>
</body>
</html>
"""

ERROR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Failed</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #f87171 0%, #dc2626 100%);
        }
        .container {
            background: white;
            padding: 40px 60px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        .error-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        h1 { color: #dc2626; margin: 0 0 10px 0; }
        p { color: #666; margin: 0; }
        .error-detail {
            color: #999;
            font-size: 14px;
            margin-top: 15px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 6px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">&#10006;</div>
        <h1>Authorization Failed</h1>
        <p>An error occurred during authorization.</p>
        <div class="error-detail">{error}</div>
    </div>
</body>
</html>
"""


@dataclass
class CallbackResult:
    """Result from an OAuth callback.

    Attributes:
        success: Whether the callback was successful.
        code: Authorization code if successful.
        state: State parameter from the callback.
        error: Error message if unsuccessful.
        error_description: Detailed error description from provider.
    """

    success: bool
    code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None
    error_description: Optional[str] = None


@dataclass
class OAuthCallbackServer:
    """Local HTTP server for OAuth2 callback handling.

    This server listens on localhost for OAuth redirect callbacks,
    captures the authorization code or token, and provides it to
    the calling code.

    The server implements CSRF protection by generating a unique
    state parameter that must be validated in the callback.

    Attributes:
        port: Port to listen on, defaults to 8789.
        host: Host to bind to, always 127.0.0.1 for security.

    Example:
        ```python
        server = OAuthCallbackServer()
        state = server.generate_state()

        # Use server.callback_url and state in OAuth authorization URL
        auth_url = f"https://provider.com/oauth/authorize?redirect_uri={server.callback_url}&state={state}"

        # Wait for callback (user completes auth in browser)
        result = await server.wait_for_callback(expected_state=state, timeout=300)

        if result.success:
            print(f"Got authorization code: {result.code}")
        else:
            print(f"Error: {result.error}")
        ```
    """

    port: int = DEFAULT_PORT
    host: str = field(default="127.0.0.1", init=False)
    _state: Optional[str] = field(default=None, init=False, repr=False)
    _result: Optional[CallbackResult] = field(default=None, init=False, repr=False)
    _callback_received: asyncio.Event = field(
        default_factory=asyncio.Event, init=False, repr=False
    )

    @property
    def callback_url(self) -> str:
        """Get the callback URL for OAuth configuration.

        Returns:
            The full callback URL including host and port.
        """
        return f"http://{self.host}:{self.port}/callback"

    def generate_state(self) -> str:
        """Generate a cryptographically secure state parameter.

        The state parameter is used for CSRF protection in the OAuth flow.
        It should be included in the authorization request and validated
        when the callback is received.

        Returns:
            A 32-character URL-safe random string.
        """
        self._state = secrets.token_urlsafe(24)
        return self._state

    async def _handle_callback(self, request: web.Request) -> web.Response:
        """Handle the OAuth callback request.

        Args:
            request: The incoming HTTP request.

        Returns:
            HTML response indicating success or failure.
        """
        # Extract query parameters
        code = request.query.get("code")
        state = request.query.get("state")
        error = request.query.get("error")
        error_description = request.query.get("error_description", "")

        # Check for error from provider
        if error:
            self._result = CallbackResult(
                success=False,
                state=state,
                error=error,
                error_description=error_description,
            )
            self._callback_received.set()
            return web.Response(
                text=ERROR_HTML.format(error=f"{error}: {error_description}"),
                content_type="text/html",
            )

        # Validate state parameter (CSRF protection)
        if self._state and state != self._state:
            self._result = CallbackResult(
                success=False,
                state=state,
                error="state_mismatch",
                error_description="State parameter does not match. Possible CSRF attack.",
            )
            self._callback_received.set()
            return web.Response(
                text=ERROR_HTML.format(error="State mismatch - possible CSRF attack"),
                content_type="text/html",
            )

        # Check for authorization code
        if not code:
            self._result = CallbackResult(
                success=False,
                state=state,
                error="missing_code",
                error_description="No authorization code received.",
            )
            self._callback_received.set()
            return web.Response(
                text=ERROR_HTML.format(error="No authorization code received"),
                content_type="text/html",
            )

        # Success
        self._result = CallbackResult(
            success=True,
            code=code,
            state=state,
        )
        self._callback_received.set()
        return web.Response(text=SUCCESS_HTML, content_type="text/html")

    async def wait_for_callback(
        self,
        expected_state: Optional[str] = None,
        timeout: float = 300.0,
    ) -> CallbackResult:
        """Start the server and wait for an OAuth callback.

        This method starts the HTTP server, waits for a callback request,
        validates the state parameter, and returns the result.

        Args:
            expected_state: State parameter to validate against.
                If not provided, uses the last generated state.
            timeout: Maximum time to wait for callback in seconds.
                Defaults to 300 seconds (5 minutes).

        Returns:
            CallbackResult containing the authorization code or error.

        Raises:
            asyncio.TimeoutError: If no callback received within timeout.
        """
        # Set expected state
        if expected_state:
            self._state = expected_state

        # Reset state for new wait
        self._result = None
        self._callback_received.clear()

        # Create aiohttp app and routes
        app = web.Application()
        app.router.add_get("/callback", self._handle_callback)

        # Create and start runner
        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        try:
            # Wait for callback with timeout
            await asyncio.wait_for(
                self._callback_received.wait(),
                timeout=timeout,
            )

            if self._result is None:
                return CallbackResult(
                    success=False,
                    error="unknown_error",
                    error_description="Callback received but no result set.",
                )

            return self._result

        except asyncio.TimeoutError:
            return CallbackResult(
                success=False,
                error="timeout",
                error_description=f"No callback received within {timeout} seconds.",
            )

        finally:
            # Clean up server
            await runner.cleanup()
