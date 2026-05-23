"""
Repository and host readiness diagnostics for DevOps Toolkit
"""

import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from app.config_loader import ConfigLoader
from app.utils.system import CommandExecutor, OSType, SystemInfo


@dataclass
class DoctorCheck:
    """Single doctor diagnostic result"""

    name: str
    status: str
    message: str
    remediation: Optional[str] = None


class DevOpsDoctor:
    """Run non-mutating diagnostics and produce a deployment readiness score"""

    SCORE_PENALTIES = {"fail": 20, "warn": 8, "pass": 0}

    def __init__(self, config: ConfigLoader):
        self.config = config

    def run(self) -> Dict[str, Any]:
        """Run all doctor checks and return a structured report"""
        checks = [
            self._check_python_version(),
            self._check_config_validity(),
            self._check_supported_os(),
            self._check_package_manager(),
            self._check_monitoring_paths(),
            self._check_logging_destination(),
            self._check_slack_settings(),
            self._check_maintenance_settings(),
        ]

        status_counts = {
            "pass": sum(1 for check in checks if check.status == "pass"),
            "warn": sum(1 for check in checks if check.status == "warn"),
            "fail": sum(1 for check in checks if check.status == "fail"),
        }
        score = max(
            0,
            100 - sum(self.SCORE_PENALTIES[check.status] for check in checks),
        )
        overall_status = "pass"
        if status_counts["fail"]:
            overall_status = "fail"
        elif status_counts["warn"]:
            overall_status = "warn"

        return {
            "score": score,
            "status": overall_status,
            "status_counts": status_counts,
            "checks": [asdict(check) for check in checks],
        }

    def render_text(self, report: Dict[str, Any]) -> str:
        """Render a human-friendly doctor report"""
        lines = [
            "=== DevOps Toolkit Doctor ===",
            "",
            f"DevOps readiness score: {report['score']}/100",
            f"Overall status: {report['status'].upper()}",
            "",
            "Checks:",
        ]

        symbols = {"pass": "[PASS]", "warn": "[WARN]", "fail": "[FAIL]"}
        for check in report["checks"]:
            lines.append(
                f"  {symbols[check['status']]} {check['name']}: {check['message']}"
            )
            if check.get("remediation"):
                lines.append(f"         Fix: {check['remediation']}")

        return "\n".join(lines)

    def render_json(self, report: Dict[str, Any]) -> str:
        """Render a machine-readable doctor report"""
        return json.dumps(report, indent=2, sort_keys=True)

    def _check_python_version(self) -> DoctorCheck:
        major, minor = sys.version_info[:2]
        if (major, minor) >= (3, 8):
            return DoctorCheck(
                "Python runtime",
                "pass",
                f"Python {major}.{minor} is supported",
            )
        return DoctorCheck(
            "Python runtime",
            "fail",
            f"Python {major}.{minor} is too old",
            "Install Python 3.8 or newer.",
        )

    def _check_config_validity(self) -> DoctorCheck:
        is_valid, errors = self.config.validate()
        if is_valid:
            return DoctorCheck(
                "Configuration",
                "pass",
                f"Configuration loaded from {self.config.config_path}",
            )
        return DoctorCheck(
            "Configuration",
            "fail",
            "; ".join(errors),
            "Update config.yaml or run `devops-toolkit setup` to create a fresh file.",
        )

    def _check_supported_os(self) -> DoctorCheck:
        os_info = SystemInfo.get_os_info()
        os_type = os_info.get("os_type", OSType.UNKNOWN.value)
        os_name = os_info.get("os_name") or os_type
        if os_type == OSType.UNKNOWN.value:
            return DoctorCheck(
                "Operating system",
                "warn",
                f"{os_name} is not in the supported Linux family list",
                "Use Ubuntu, Debian, RHEL, CentOS, Fedora, Rocky Linux, or AlmaLinux.",
            )
        return DoctorCheck("Operating system", "pass", f"{os_name} is supported")

    def _check_package_manager(self) -> DoctorCheck:
        package_manager = SystemInfo.get_package_manager()
        if not package_manager:
            return DoctorCheck(
                "Package manager",
                "fail",
                "No supported package manager was detected",
                "Install apt, dnf, or yum on a supported Linux distribution.",
            )

        if CommandExecutor.check_command_exists(package_manager):
            return DoctorCheck(
                "Package manager",
                "pass",
                f"{package_manager} is available",
            )

        return DoctorCheck(
            "Package manager",
            "fail",
            f"{package_manager} was detected but is not available in PATH",
            f"Install {package_manager} or fix PATH for the service user.",
        )

    def _check_monitoring_paths(self) -> DoctorCheck:
        paths = self.config.get("monitoring.disk.paths", [])
        missing_paths = [path for path in paths if not os.path.exists(path)]
        if not paths:
            return DoctorCheck(
                "Disk monitoring paths",
                "warn",
                "No disk paths are configured",
                "Add at least `/` to monitoring.disk.paths.",
            )
        if missing_paths:
            return DoctorCheck(
                "Disk monitoring paths",
                "fail",
                f"Missing paths: {', '.join(missing_paths)}",
                "Remove stale paths or create the missing mount points.",
            )
        return DoctorCheck(
            "Disk monitoring paths",
            "pass",
            f"{len(paths)} path(s) are reachable",
        )

    def _check_logging_destination(self) -> DoctorCheck:
        log_file = self.config.get("logging.log_file")
        if not log_file:
            return DoctorCheck(
                "Logging",
                "warn",
                "No log file is configured",
                "Set logging.log_file in config.yaml.",
            )

        log_dir = os.path.dirname(log_file) or "."
        if not os.path.isdir(log_dir):
            return DoctorCheck(
                "Logging",
                "fail",
                f"Log directory does not exist: {log_dir}",
                "Create the directory or update logging.log_file.",
            )
        if not os.access(log_dir, os.W_OK):
            return DoctorCheck(
                "Logging",
                "warn",
                f"Log directory may require elevated permissions: {log_dir}",
                "Run with sudo for system logs or choose a writable log path.",
            )
        return DoctorCheck("Logging", "pass", f"Log directory is writable: {log_dir}")

    def _check_slack_settings(self) -> DoctorCheck:
        if not self.config.get("slack.enabled"):
            return DoctorCheck(
                "Slack notifications",
                "warn",
                "Slack notifications are disabled",
                "Enable slack.enabled and set slack.webhook_url for production alerts.",
            )

        webhook_url = self.config.get("slack.webhook_url")
        if webhook_url and webhook_url.startswith("https://hooks.slack.com/"):
            return DoctorCheck(
                "Slack notifications",
                "pass",
                "Slack webhook is configured",
            )
        return DoctorCheck(
            "Slack notifications",
            "fail",
            "Slack is enabled but webhook_url is missing or invalid",
            "Set slack.webhook_url to a valid Slack incoming webhook URL.",
        )

    def _check_maintenance_settings(self) -> DoctorCheck:
        if self.config.get("maintenance.patch_management.enabled"):
            return DoctorCheck(
                "Patch management",
                "pass",
                "Patch management is enabled",
            )
        return DoctorCheck(
            "Patch management",
            "warn",
            "Patch management is disabled",
            "Enable maintenance.patch_management.enabled for automated update checks.",
        )
