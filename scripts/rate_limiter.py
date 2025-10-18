from collections import defaultdict, deque
from time import time
from typing import Dict


class RateLimiter:
    """
    Rate limiter using sliding window algorithm.

    Tracks request timestamps per user and allows at most N requests
    per time window by removing expired timestamps.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize rate limiter with request limit and time window.

        Args:
            max_requests: Maximum number of requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Store deque of timestamps for each user_id
        self.user_requests: Dict[str, deque] = defaultdict(deque)

    def allow_request(self, user_id: str) -> bool:
        """
        Check if request should be allowed for given user.

        Uses sliding window: removes timestamps outside current window,
        then checks if remaining requests < max_requests.

        Args:
            user_id: Unique identifier for the user

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        current_time = time()
        user_queue = self.user_requests[user_id]

        # Remove timestamps outside the current window (left side of deque)
        # Window starts at (current_time - window_seconds)
        while user_queue and user_queue[0] <= current_time - self.window_seconds:
            user_queue.popleft()

        # Check if we can allow this request
        if len(user_queue) < self.max_requests:
            # Add current request timestamp to the right side
            user_queue.append(current_time)
            return True

        # Rate limit exceeded
        return False
