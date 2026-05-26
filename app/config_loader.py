"""
Configuration loader for DevOps Toolkit
Handles YAML configuration loading, validation, and default values
"""

import copy
import os
from typing import Any, Dict, List, Optional, Tuple

import yaml


class ConfigLoader:
    """Load and validate configuration from YAML file"""

    DEFAULT_CONFIG_PATH = "/etc/devops_toolkit/config.yaml"

    DEFAULT_CONFIG = {
        "slack": {
            "webhook_url": "",
            "enabled": True,
            "retry_attempts": 3,
            "retry_delay": 2,
        },
        "monitoring": {
            "disk": {"enabled": True, "threshold_percent": 80, "paths": ["/"]},
            "cpu": {"enabled": True, "threshold_percent": 80, "check_interval": 5},
            "memory": {"enabled": True, "threshold_percent": 80},
            "ports": {"enabled": True, "check_ports": [22, 80, 443]},
            "processes": {"enabled": True, "watch_processes": []},
        },
        "maintenance": {
            "patch_management": {
                "enabled": True,
                "auto_reboot": False,
                "reboot_time": "03:00",
            },
            "services": {"restart_retry_count": 3, "restart_retry_delay": 5},
        },
        "audit": {
            "file_permissions": {
                "enabled": True,
                "scan_paths": ["/etc", "/var/www", "/opt"],
                "exclude_paths": ["/proc", "/sys", "/dev"],
            },
            "user_audit": {"enabled": True},
            "cron_audit": {"enabled": True},
        },
        "logging": {
            "log_file": "/var/log/devops_toolkit.log",
            "log_level": "INFO",
            "max_bytes": 10485760,  # 10MB
            "backup_count": 5,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader

        Args:
            config_path: Path to configuration file (default: /etc/devops_toolkit/config.yaml)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file with fallback to defaults

        Returns:
            Configuration dictionary
        """
        config = copy.deepcopy(self.DEFAULT_CONFIG)

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path) as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        config = self._merge_configs(config, user_config)
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
                print("Using default configuration")
        else:
            print(f"Config file not found at {self.config_path}, using defaults")

        return config

    def _merge_configs(
        self, default: Dict[str, Any], user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recursively merge user config with default config

        Args:
            default: Default configuration
            user: User-provided configuration

        Returns:
            Merged configuration
        """
        merged = copy.deepcopy(default)

        for key, value in user.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key_path: Configuration key path (e.g., 'slack.webhook_url')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Validate Slack webhook if enabled
        if self.get("slack.enabled"):
            webhook_url = self.get("slack.webhook_url")
            if not webhook_url or not webhook_url.startswith(
                "https://hooks.slack.com/"
            ):
                errors.append("Invalid or missing Slack webhook URL")

        # Validate thresholds
        for monitor_type in ["disk", "cpu", "memory"]:
            threshold = self.get(f"monitoring.{monitor_type}.threshold_percent")
            if threshold is None:
                continue
            if (
                not isinstance(threshold, (int, float))
                or threshold < 0
                or threshold > 100
            ):
                errors.append(
                    f"Invalid {monitor_type} threshold: must be between 0 and 100"
                )

        # Validate log file path
        log_file = self.get("logging.log_file")
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                errors.append(f"Log directory does not exist: {log_dir}")

        return (len(errors) == 0, errors)

    def get_all(self) -> Dict[str, Any]:
        """
        Get entire configuration

        Returns:
            Complete configuration dictionary
        """
        return copy.deepcopy(self.config)

    @staticmethod
    def create_default_config(output_path: str) -> bool:
        """
        Create a default configuration file

        Args:
            output_path: Path where to create the config file

        Returns:
            True if successful, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w") as f:
                yaml.dump(
                    ConfigLoader.DEFAULT_CONFIG,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                )

            return True
        except Exception as e:
            print(f"Failed to create default config: {e}")
            return False


# Made with Bob
