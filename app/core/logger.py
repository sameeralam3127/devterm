"""
Logging system with rotation support
"""

import logging
import os
from logging.handlers import RotatingFileHandler


class Logger:
    """Centralized logging system with rotation"""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern to ensure single logger instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize logger (only once)"""
        if not Logger._initialized:
            self.logger = None
            Logger._initialized = True

    def setup(
        self,
        log_file: str = "/var/log/devops_toolkit.log",
        log_level: str = "INFO",
        max_bytes: int = 10485760,
        backup_count: int = 5,
    ):
        """
        Setup logging configuration

        Args:
            log_file: Path to log file
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup files to keep
        """
        # Create logger
        self.logger = logging.getLogger("devops_toolkit")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Remove existing handlers
        self.logger.handlers.clear()

        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except PermissionError:
                # Fallback to local directory if no permission
                log_file = "./devops_toolkit.log"
                print(f"Warning: No permission to create {log_dir}")
                print(f"Using fallback log file: {log_file}")

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(module)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # File handler with rotation
        try:
            file_handler = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except PermissionError:
            print(f"Warning: No permission to write to {log_file}")
            print("File logging disabled")

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self.logger.info("Logger initialized successfully")

    def get_logger(self) -> logging.Logger:
        """
        Get logger instance

        Returns:
            Logger instance
        """
        if self.logger is None:
            # Setup with defaults if not initialized
            self.setup()
        return self.logger

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        if self.logger:
            self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        if self.logger:
            self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        if self.logger:
            self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        if self.logger:
            self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        if self.logger:
            self.logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        if self.logger:
            self.logger.exception(message, **kwargs)


# Global logger instance
logger = Logger()


def get_logger() -> Logger:
    """
    Get global logger instance

    Returns:
        Logger instance
    """
    return logger


# Made with Bob
