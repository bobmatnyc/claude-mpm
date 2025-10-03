"""
Database Connector with Fallback Support
=========================================

WHY: Database connectivity packages often have compilation requirements that
can fail on certain systems. This module provides intelligent fallback to
pure Python alternatives when native packages are unavailable.

DESIGN DECISION: We prioritize pure Python implementations over native ones
for better cross-platform compatibility, even if they might be slightly slower.
"""

from typing import Any, ClassVar, Dict, Optional, Tuple

from ..core.logger import get_logger

logger = get_logger(__name__)


class DatabaseConnector:
    """
    Manages database connections with automatic fallback to alternative drivers.

    WHY: Provides a unified interface for database connections that automatically
    handles missing or failed driver installations by falling back to alternatives.
    """

    # Database drivers in order of preference (first is preferred)
    MYSQL_DRIVERS: ClassVar[list] = [
        ("pymysql", "pymysql"),  # Pure Python, no compilation required
        ("mysqlclient", "MySQLdb"),  # Faster but requires MySQL dev headers
        ("mysql-connector-python", "mysql.connector"),  # Oracle's pure Python driver
    ]

    POSTGRESQL_DRIVERS: ClassVar[list] = [
        ("psycopg2-binary", "psycopg2"),  # Binary wheel, no compilation
        ("psycopg2", "psycopg2"),  # Requires PostgreSQL dev headers
        ("pg8000", "pg8000"),  # Pure Python alternative
    ]

    ORACLE_DRIVERS: ClassVar[list] = [
        ("cx_Oracle", "cx_Oracle"),  # Requires Oracle client libraries
        ("oracledb", "oracledb"),  # Pure Python Oracle driver (newer)
    ]

    def __init__(self):
        """Initialize the database connector."""
        self.available_drivers: Dict[str, Tuple[str, Any]] = {}
        self._scan_available_drivers()

    def _scan_available_drivers(self) -> None:
        """
        Scan for available database drivers and cache them.

        WHY: Pre-scanning allows us to know what's available without
        repeatedly trying imports, improving performance.
        """
        # Check MySQL drivers
        for package_name, import_name in self.MYSQL_DRIVERS:
            driver = self._try_import(import_name)
            if driver and "mysql" not in self.available_drivers:
                self.available_drivers["mysql"] = (package_name, driver)
                logger.info(f"MySQL driver available: {package_name}")

        # Check PostgreSQL drivers
        for package_name, import_name in self.POSTGRESQL_DRIVERS:
            driver = self._try_import(import_name)
            if driver and "postgresql" not in self.available_drivers:
                self.available_drivers["postgresql"] = (package_name, driver)
                logger.info(f"PostgreSQL driver available: {package_name}")

        # Check Oracle drivers
        for package_name, import_name in self.ORACLE_DRIVERS:
            driver = self._try_import(import_name)
            if driver and "oracle" not in self.available_drivers:
                self.available_drivers["oracle"] = (package_name, driver)
                logger.info(f"Oracle driver available: {package_name}")

    def _try_import(self, module_name: str) -> Optional[Any]:
        """
        Try to import a module and return it if successful.

        Args:
            module_name: Name of the module to import

        Returns:
            The imported module or None if import fails
        """
        try:
            import importlib

            return importlib.import_module(module_name)
        except ImportError:
            return None

    def get_mysql_connection_string(
        self, host: str, database: str, user: str, password: str, port: int = 3306
    ) -> Optional[str]:
        """
        Get a SQLAlchemy connection string for MySQL with automatic driver selection.

        WHY: SQLAlchemy needs different connection string formats depending on the driver.
        This method automatically selects the best available driver.

        Args:
            host: Database host
            database: Database name
            user: Username
            password: Password
            port: Port number (default 3306)

        Returns:
            SQLAlchemy connection string or None if no driver available
        """
        if "mysql" not in self.available_drivers:
            logger.error(
                "No MySQL driver available. Install one of: pymysql, mysqlclient, or mysql-connector-python"
            )
            return None

        package_name, _ = self.available_drivers["mysql"]

        # Format connection string based on driver
        if package_name == "pymysql":
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        if package_name == "mysqlclient":
            return f"mysql+mysqldb://{user}:{password}@{host}:{port}/{database}"
        if package_name == "mysql-connector-python":
            return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"

        return None

    def get_postgresql_connection_string(
        self, host: str, database: str, user: str, password: str, port: int = 5432
    ) -> Optional[str]:
        """
        Get a SQLAlchemy connection string for PostgreSQL with automatic driver selection.

        Args:
            host: Database host
            database: Database name
            user: Username
            password: Password
            port: Port number (default 5432)

        Returns:
            SQLAlchemy connection string or None if no driver available
        """
        if "postgresql" not in self.available_drivers:
            logger.error(
                "No PostgreSQL driver available. Install one of: psycopg2-binary, psycopg2, or pg8000"
            )
            return None

        package_name, _ = self.available_drivers["postgresql"]

        # Format connection string based on driver
        if package_name in ["psycopg2-binary", "psycopg2"]:
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
        if package_name == "pg8000":
            return f"postgresql+pg8000://{user}:{password}@{host}:{port}/{database}"

        return None

    def get_oracle_connection_string(
        self, host: str, database: str, user: str, password: str, port: int = 1521
    ) -> Optional[str]:
        """
        Get a SQLAlchemy connection string for Oracle with automatic driver selection.

        Args:
            host: Database host
            database: Database name/SID
            user: Username
            password: Password
            port: Port number (default 1521)

        Returns:
            SQLAlchemy connection string or None if no driver available
        """
        if "oracle" not in self.available_drivers:
            logger.error(
                "No Oracle driver available. Install one of: cx_Oracle or oracledb"
            )
            return None

        package_name, _ = self.available_drivers["oracle"]

        # Format connection string based on driver
        if package_name == "cx_Oracle":
            return f"oracle+cx_oracle://{user}:{password}@{host}:{port}/{database}"
        if package_name == "oracledb":
            return f"oracle+oracledb://{user}:{password}@{host}:{port}/{database}"

        return None

    def get_available_drivers(self) -> Dict[str, str]:
        """
        Get a summary of available database drivers.

        Returns:
            Dictionary mapping database type to driver package name
        """
        return {
            db_type: driver_info[0]
            for db_type, driver_info in self.available_drivers.items()
        }

    def suggest_missing_drivers(self) -> Dict[str, str]:
        """
        Suggest drivers to install for databases without drivers.

        Returns:
            Dictionary mapping database type to recommended package
        """
        suggestions = {}

        if "mysql" not in self.available_drivers:
            suggestions["mysql"] = "pymysql"  # Pure Python, always works

        if "postgresql" not in self.available_drivers:
            suggestions["postgresql"] = "psycopg2-binary"  # No compilation needed

        if "oracle" not in self.available_drivers:
            suggestions["oracle"] = "oracledb"  # Pure Python, newer

        return suggestions

    @staticmethod
    def get_installation_help() -> str:
        """
        Get helpful installation instructions for database drivers.

        Returns:
            Formatted help text
        """
        return """
Database Driver Installation Help
=================================

For MySQL:
  Recommended: pip install pymysql (pure Python, no compilation)
  Alternative: pip install mysql-connector-python (Oracle's pure Python)
  Fastest (requires MySQL dev headers):
    macOS: brew install mysql && pip install mysqlclient
    Ubuntu: sudo apt-get install libmysqlclient-dev && pip install mysqlclient

For PostgreSQL:
  Recommended: pip install psycopg2-binary (pre-compiled, no headers needed)
  Alternative: pip install pg8000 (pure Python, slightly slower)
  Fastest (requires PostgreSQL dev headers):
    macOS: brew install postgresql && pip install psycopg2
    Ubuntu: sudo apt-get install libpq-dev && pip install psycopg2

For Oracle:
  Recommended: pip install oracledb (pure Python, no Oracle client needed)
  Alternative (requires Oracle Instant Client):
    1. Download Oracle Instant Client from oracle.com
    2. Set environment variables (LD_LIBRARY_PATH, etc.)
    3. pip install cx_Oracle

Note: Pure Python drivers are slightly slower but much easier to install
and maintain. They're recommended unless you have specific performance needs.
"""


def test_database_connectivity() -> None:
    """
    Test database connectivity and report available drivers.

    WHY: Helps users understand what database drivers are available and
    what they might need to install.
    """
    connector = DatabaseConnector()

    print("Database Driver Status")
    print("=" * 50)

    available = connector.get_available_drivers()
    if available:
        print("\nAvailable Drivers:")
        for db_type, driver in available.items():
            print(f"  {db_type:12} -> {driver}")
    else:
        print("\nNo database drivers found!")

    suggestions = connector.suggest_missing_drivers()
    if suggestions:
        print("\nRecommended installations for missing drivers:")
        for db_type, package in suggestions.items():
            print(f"  {db_type:12} -> pip install {package}")

    print("\n" + connector.get_installation_help())


if __name__ == "__main__":
    # Run connectivity test when module is executed directly
    test_database_connectivity()
