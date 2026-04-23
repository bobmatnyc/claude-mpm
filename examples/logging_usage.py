#!/usr/bin/env python3
"""
Example demonstrating standardized logging usage in Claude MPM.

This example shows how to use the new centralized logging infrastructure
with consistent patterns across the codebase.
"""

from claude_mpm.core.logging_config import (
    LOGGING_STANDARDS,
    LogContext,
    configure_logging,
    get_logger,
    log_function_call,
    log_operation,
    log_performance_context,
)

# Configure logging globally (typically done once at startup)
configure_logging(
    level="INFO",
    console_output=True,
    file_output=True,
    json_format=False,  # Set to True for production
)


class ExampleService:
    """Example service demonstrating logging patterns."""

    def __init__(self):
        # Get logger using module name for consistency
        self.logger = get_logger(__name__)
        self.logger.info("ExampleService initialized")

    @log_function_call
    def process_data(self, data: dict) -> dict:
        """Process data with automatic function logging."""
        # Function entry/exit automatically logged by decorator

        # Add contextual information
        with LogContext.context(operation_id="proc_123", user="test_user"):
            self.logger.info("Processing data", extra={"data_size": len(data)})

            # Simulate processing
            result = {"processed": True, "items": len(data)}

            self.logger.info("Data processed successfully", extra={"result": result})
            return result

    def long_operation(self):
        """Demonstrate operation tracking with performance monitoring."""

        # Track entire operation with timing
        with log_operation(self.logger, "database_sync", database="production"):
            self.logger.debug("Starting database synchronization")

            # Monitor performance with thresholds
            with log_performance_context(
                self.logger, "fetch_records", warn_threshold=0.5, error_threshold=2.0
            ):
                # Simulate database fetch
                import time

                time.sleep(0.3)  # Under warning threshold
                self.logger.debug("Fetched 1000 records")

            # Another operation with performance tracking
            with log_performance_context(
                self.logger, "update_records", warn_threshold=0.2, error_threshold=1.0
            ):
                time.sleep(0.25)  # Will trigger warning
                self.logger.debug("Updated records")

            self.logger.info("Database sync completed")

    def handle_error(self):
        """Demonstrate error logging patterns."""

        try:
            # Simulate an operation that might fail
            raise ValueError("Example error for demonstration")
        except ValueError as e:
            # Log with exception info
            self.logger.error("Operation failed", exc_info=True)

            # Or use exception method for automatic exc_info
            self.logger.exception("Failed to process request")

            # Log with additional context
            self.logger.error(
                "Critical operation failed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "recovery_action": "retry",
                },
            )

    def demonstrate_log_levels(self):
        """Show appropriate usage of different log levels."""

        # DEBUG - Detailed diagnostic information
        self.logger.debug("Variable state", extra={"var_x": 42, "var_y": "test"})

        # INFO - Normal operations, significant events
        self.logger.info("Service started successfully")
        self.logger.info("Request processed", extra={"request_id": "req_123"})

        # WARNING - Potentially harmful situations
        self.logger.warning("API rate limit approaching", extra={"usage": 90})
        self.logger.warning("Deprecated method called", extra={"method": "old_func"})

        # ERROR - Error events allowing continued operation
        self.logger.error("Failed to send email, will retry", extra={"attempts": 3})

        # CRITICAL - Events that may cause abort
        self.logger.critical(
            "Database connection lost", extra={"action": "shutting_down"}
        )


def main():
    """Main entry point demonstrating logging usage."""

    # Get logger for main module
    logger = get_logger(__name__)
    logger.info("Application starting", extra={"version": "1.0.0"})

    # Print logging standards for reference
    logger.info("Logging standards:")
    for level, description in LOGGING_STANDARDS.items():
        logger.info(f"  {level}: {description}")

    # Create and use service
    service = ExampleService()

    # Demonstrate various logging patterns
    logger.info("=" * 50)
    logger.info("Demonstrating function call logging:")
    service.process_data({"item1": "value1", "item2": "value2"})

    logger.info("=" * 50)
    logger.info("Demonstrating operation tracking:")
    service.long_operation()

    logger.info("=" * 50)
    logger.info("Demonstrating error handling:")
    service.handle_error()

    logger.info("=" * 50)
    logger.info("Demonstrating log levels:")
    service.demonstrate_log_levels()

    logger.info("Application completed successfully")


if __name__ == "__main__":
    main()
