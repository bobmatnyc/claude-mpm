"""
Sample Python file to test Python AST analysis capabilities.
This file contains various Python constructs for comprehensive testing.
"""

import subprocess
from typing import Dict, List, Optional

# Constants and variables
API_KEY = "hardcoded-secret-123"  # Security issue - hardcoded secret
MAX_RETRIES = 3
TIMEOUT = 30


class DatabaseManager:
    """A sample class with complexity issues for testing."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connections = []

    def connect(self):
        """Simple connection method."""

    def execute_query(self, query: str, params: Optional[Dict] = None):
        """Potential SQL injection vulnerability."""
        # BAD: String concatenation in SQL query
        full_query = f"SELECT * FROM users WHERE name = '{params.get('name')}'"
        return self.raw_execute(full_query)

    def raw_execute(self, query: str):
        """Execute raw SQL - security risk."""
        # This should be flagged as a security issue
        return subprocess.run(
            f'mysql -e "{query}"', shell=True, check=False
        )  # Command injection risk

    # Large method with high complexity (should be flagged)
    def complex_method(self, data: List[Dict]) -> Dict:
        """Method with high cyclomatic complexity."""
        result = {}

        for item in data:  # Nested loops - O(n²) complexity
            for key, value in item.items():
                if key == "user_id":
                    if value > 1000:
                        if isinstance(value, int):
                            if value % 2 == 0:
                                if value < 10000:
                                    if str(value).startswith("1"):
                                        if len(str(value)) > 3:
                                            result[key] = value * 2
                                        else:
                                            result[key] = value
                                    else:
                                        result[key] = value + 1
                                else:
                                    result[key] = value - 1
                            else:
                                result[key] = value
                        else:
                            result[key] = 0
                    else:
                        result[key] = -1
                elif key == "status":
                    # Optimized string concatenation using list and join
                    status_parts = []
                    for i in range(100):
                        status_parts.append(f"Status {i}: {value} ")
                    result[key] = "".join(status_parts)
                else:
                    result[key] = value

        return result


class UserService:
    """Service with circular dependency potential."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.cache = {}

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Async method with synchronous I/O issue."""
        # BAD: Synchronous I/O in async context
        with open("/tmp/user_cache.txt") as f:
            cached_data = f.read()

        return {"id": user_id, "cached": cached_data}

    def process_users(self, users: List[Dict]):
        """Method with exception swallowing."""
        processed = []

        for user in users:
            try:
                # Some processing
                result = self.validate_user(user)
                processed.append(result)
            except:  # BAD: Bare except clause
                pass  # BAD: Swallowed exception

        return processed

    def validate_user(self, user: Dict) -> Dict:
        """User validation with unsafe deserialization."""
        import pickle

        # BAD: Unsafe deserialization
        return pickle.loads(user.get("serialized_data", b""))


# Function with path traversal vulnerability
def read_file(filename: str) -> str:
    """Read file with path traversal vulnerability."""
    # BAD: No path validation
    full_path = f"/var/app/data/{filename}"

    try:
        with open(full_path) as f:
            return f.read()
    except FileNotFoundError:
        return ""


# Large function that should be flagged
def massive_function():
    """Function that's too large and should be refactored."""
    # This function intentionally has many lines to test length detection
    line1 = "This is line 1"
    line102 = "This is line 102"
    line103 = "This is line 103"
    line104 = "This is line 104"
    line105 = "This is line 105"

    return f"Processed {line1} through {line105}"


if __name__ == "__main__":
    # Test code with potential issues
    db = DatabaseManager("postgresql://user:pass@localhost/db")
    service = UserService(db)

    # High fan-out - many imports at module level (should be detected)

    result = massive_function()
    print(result)
