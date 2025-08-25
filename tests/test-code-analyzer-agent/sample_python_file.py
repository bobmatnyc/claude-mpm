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
        user_data = pickle.loads(user.get("serialized_data", b""))
        return user_data


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
    line2 = "This is line 2"
    line3 = "This is line 3"
    line4 = "This is line 4"
    line5 = "This is line 5"
    line6 = "This is line 6"
    line7 = "This is line 7"
    line8 = "This is line 8"
    line9 = "This is line 9"
    line10 = "This is line 10"
    line11 = "This is line 11"
    line12 = "This is line 12"
    line13 = "This is line 13"
    line14 = "This is line 14"
    line15 = "This is line 15"
    line16 = "This is line 16"
    line17 = "This is line 17"
    line18 = "This is line 18"
    line19 = "This is line 19"
    line20 = "This is line 20"
    line21 = "This is line 21"
    line22 = "This is line 22"
    line23 = "This is line 23"
    line24 = "This is line 24"
    line25 = "This is line 25"
    line26 = "This is line 26"
    line27 = "This is line 27"
    line28 = "This is line 28"
    line29 = "This is line 29"
    line30 = "This is line 30"
    line31 = "This is line 31"
    line32 = "This is line 32"
    line33 = "This is line 33"
    line34 = "This is line 34"
    line35 = "This is line 35"
    line36 = "This is line 36"
    line37 = "This is line 37"
    line38 = "This is line 38"
    line39 = "This is line 39"
    line40 = "This is line 40"
    line41 = "This is line 41"
    line42 = "This is line 42"
    line43 = "This is line 43"
    line44 = "This is line 44"
    line45 = "This is line 45"
    line46 = "This is line 46"
    line47 = "This is line 47"
    line48 = "This is line 48"
    line49 = "This is line 49"
    line50 = "This is line 50"
    line51 = "This is line 51"
    line52 = "This is line 52"
    line53 = "This is line 53"
    line54 = "This is line 54"
    line55 = "This is line 55"
    line56 = "This is line 56"
    line57 = "This is line 57"
    line58 = "This is line 58"
    line59 = "This is line 59"
    line60 = "This is line 60"
    line61 = "This is line 61"
    line62 = "This is line 62"
    line63 = "This is line 63"
    line64 = "This is line 64"
    line65 = "This is line 65"
    line66 = "This is line 66"
    line67 = "This is line 67"
    line68 = "This is line 68"
    line69 = "This is line 69"
    line70 = "This is line 70"
    line71 = "This is line 71"
    line72 = "This is line 72"
    line73 = "This is line 73"
    line74 = "This is line 74"
    line75 = "This is line 75"
    line76 = "This is line 76"
    line77 = "This is line 77"
    line78 = "This is line 78"
    line79 = "This is line 79"
    line80 = "This is line 80"
    line81 = "This is line 81"
    line82 = "This is line 82"
    line83 = "This is line 83"
    line84 = "This is line 84"
    line85 = "This is line 85"
    line86 = "This is line 86"
    line87 = "This is line 87"
    line88 = "This is line 88"
    line89 = "This is line 89"
    line90 = "This is line 90"
    line91 = "This is line 91"
    line92 = "This is line 92"
    line93 = "This is line 93"
    line94 = "This is line 94"
    line95 = "This is line 95"
    line96 = "This is line 96"
    line97 = "This is line 97"
    line98 = "This is line 98"
    line99 = "This is line 99"
    line100 = "This is line 100"
    line101 = "This is line 101"
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
