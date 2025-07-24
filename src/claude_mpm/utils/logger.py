"""Logging configuration for Claude MPM."""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logging(
    name: str = "claude_mpm",
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    console_output: bool = True,
    file_output: bool = True,
) -> logging.Logger:
    """
    Set up logging with both console and file handlers.
    
    Args:
        name: Logger name
        level: Logging level (OFF, DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (defaults to ~/.claude-mpm/logs)
        console_output: Enable console output
        file_output: Enable file output
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # Handle OFF level
    if level == "OFF":
        logger.setLevel(logging.CRITICAL + 1)  # Higher than CRITICAL
        logger.handlers.clear()
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # Prevent duplicate handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Console handler - only show INFO and above
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    # File handler - always enabled for INFO and DEBUG levels
    if file_output and level in ["INFO", "DEBUG"]:
        if log_dir is None:
            log_dir = Path.home() / ".claude-mpm" / "logs"
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"mpm_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Also create a symlink to latest log
        latest_link = log_dir / "latest.log"
        if latest_link.exists() and latest_link.is_symlink():
            latest_link.unlink()
        if not latest_link.exists():
            latest_link.symlink_to(log_file.name)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"claude_mpm.{name}")