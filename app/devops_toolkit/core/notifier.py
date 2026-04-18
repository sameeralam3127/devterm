"""
Slack notification system with retry logic and severity levels
"""

import socket
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

import requests


class Severity(Enum):
    """Notification severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SlackNotifier:
    """Send notifications to Slack with retry logic"""

    SEVERITY_COLORS = {
        Severity.INFO: "#36a64f",  # Green
        Severity.WARNING: "#ff9900",  # Orange
        Severity.CRITICAL: "#ff0000",  # Red
    }

    SEVERITY_EMOJIS = {
        Severity.INFO: ":white_check_mark:",
        Severity.WARNING: ":warning:",
        Severity.CRITICAL: ":rotating_light:",
    }

    def __init__(
        self,
        webhook_url: str,
        enabled: bool = True,
        retry_attempts: int = 3,
        retry_delay: int = 2,
    ):
        """
        Initialize Slack notifier

        Args:
            webhook_url: Slack webhook URL
            enabled: Whether notifications are enabled
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.webhook_url = webhook_url
        self.enabled = enabled
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.hostname = socket.gethostname()

    def send(
        self,
        message: str,
        severity: Severity = Severity.INFO,
        module: str = "DevOps Toolkit",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send notification to Slack

        Args:
            message: Main message text
            severity: Severity level
            module: Module name
            details: Additional details dictionary

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return True

        if not self.webhook_url:
            print("Slack webhook URL not configured")
            return False

        payload = self._build_payload(message, severity, module, details)

        for attempt in range(self.retry_attempts):
            try:
                response = requests.post(self.webhook_url, json=payload, timeout=10)

                if response.status_code == 200:
                    return True
                else:
                    print(f"Slack API error: {response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"Failed to send Slack notification: {e}")

            if attempt < self.retry_attempts - 1:
                wait_time = self.retry_delay * (2**attempt)
                time.sleep(wait_time)

        return False

    def _build_payload(
        self,
        message: str,
        severity: Severity,
        module: str,
        details: Optional[Dict[str, Any]],
    ) -> Dict:
        """
        Build Slack message payload with blocks

        Args:
            message: Main message
            severity: Severity level
            module: Module name
            details: Additional details

        Returns:
            Slack payload dictionary
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        emoji = self.SEVERITY_EMOJIS.get(severity, ":information_source:")
        color = self.SEVERITY_COLORS.get(severity, "#808080")

        # Build fields for details
        fields = [
            {"title": "Hostname", "value": self.hostname, "short": True},
            {"title": "Timestamp", "value": timestamp, "short": True},
            {"title": "Module", "value": module, "short": True},
            {"title": "Severity", "value": severity.value.upper(), "short": True},
        ]

        if details:
            for key, value in details.items():
                fields.append(
                    {"title": key, "value": str(value), "short": len(str(value)) < 40}
                )

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"{emoji} {module}",
                    "text": message,
                    "fields": fields,
                    "footer": "DevOps Toolkit",
                    "ts": int(time.time()),
                }
            ]
        }

        return payload

    def test_connection(self) -> tuple[bool, str]:
        """
        Test Slack webhook connection

        Returns:
            Tuple of (success, message)
        """
        if not self.enabled:
            return False, "Slack notifications are disabled"

        if not self.webhook_url:
            return False, "Slack webhook URL not configured"

        success = self.send(
            message="Test notification from DevOps Toolkit",
            severity=Severity.INFO,
            module="Connection Test",
        )

        if success:
            return True, "Slack connection test successful"
        else:
            return False, "Failed to send test notification to Slack"

    def send_info(
        self,
        message: str,
        module: str = "DevOps Toolkit",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send INFO level notification"""
        return self.send(message, Severity.INFO, module, details)

    def send_warning(
        self,
        message: str,
        module: str = "DevOps Toolkit",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send WARNING level notification"""
        return self.send(message, Severity.WARNING, module, details)

    def send_critical(
        self,
        message: str,
        module: str = "DevOps Toolkit",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send CRITICAL level notification"""
        return self.send(message, Severity.CRITICAL, module, details)


# Made with Bob
