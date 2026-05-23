"""
Disk usage monitoring module
"""

from typing import Any, Dict, List, Tuple

import psutil

from app.core.logger import get_logger
from app.core.notifier import SlackNotifier


class DiskMonitor:
    """Monitor disk usage and alert on thresholds"""

    def __init__(
        self,
        notifier: SlackNotifier,
        threshold_percent: int = 80,
        paths: List[str] = None,
    ):
        """
        Initialize disk monitor

        Args:
            notifier: Slack notifier instance
            threshold_percent: Alert threshold percentage
            paths: List of paths to monitor (default: ['/'])
        """
        self.notifier = notifier
        self.threshold_percent = threshold_percent
        self.paths = paths or ["/"]
        self.logger = get_logger().get_logger()

    def check_disk_usage(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Check disk usage for configured paths

        Returns:
            Tuple of (all_ok, list of disk info dicts)
        """
        self.logger.info("Checking disk usage")
        results = []
        all_ok = True

        for path in self.paths:
            try:
                usage = psutil.disk_usage(path)

                disk_info = {
                    "path": path,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent,
                    "threshold_exceeded": usage.percent >= self.threshold_percent,
                }

                results.append(disk_info)

                if disk_info["threshold_exceeded"]:
                    all_ok = False
                    self.logger.warning(f"Disk usage high on {path}: {usage.percent}%")
                    self.notifier.send_warning(
                        f"Disk usage on {path} is {usage.percent}% "
                        f"(threshold: {self.threshold_percent}%)",
                        "Disk Monitor",
                        disk_info,
                    )
                else:
                    self.logger.info(f"Disk usage on {path}: {usage.percent}%")

            except Exception as e:
                self.logger.error(f"Failed to check disk usage for {path}: {e}")
                results.append({"path": path, "error": str(e)})
                all_ok = False

        return all_ok, results

    def get_all_partitions(self) -> List[Dict[str, Any]]:
        """
        Get information about all disk partitions

        Returns:
            List of partition info dictionaries
        """
        self.logger.info("Getting all disk partitions")
        partitions = []

        try:
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partitions.append(
                        {
                            "device": partition.device,
                            "mountpoint": partition.mountpoint,
                            "fstype": partition.fstype,
                            "total_gb": round(usage.total / (1024**3), 2),
                            "used_gb": round(usage.used / (1024**3), 2),
                            "free_gb": round(usage.free / (1024**3), 2),
                            "percent": usage.percent,
                        }
                    )
                except PermissionError:
                    # Skip partitions we can't access
                    continue
        except Exception as e:
            self.logger.error(f"Failed to get disk partitions: {e}")

        return partitions


# Made with Bob
