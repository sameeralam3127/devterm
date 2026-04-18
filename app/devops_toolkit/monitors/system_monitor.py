"""
CPU, Memory, and Uptime monitoring module
"""

import time
from datetime import timedelta
from typing import Any, Dict, Tuple

import psutil

from devops_toolkit.core.logger import get_logger
from devops_toolkit.core.notifier import SlackNotifier


class SystemMonitor:
    """Monitor CPU, memory, and system uptime"""

    def __init__(
        self,
        notifier: SlackNotifier,
        cpu_threshold: int = 80,
        memory_threshold: int = 80,
        cpu_check_interval: int = 5,
    ):
        """
        Initialize system monitor

        Args:
            notifier: Slack notifier instance
            cpu_threshold: CPU usage alert threshold percentage
            memory_threshold: Memory usage alert threshold percentage
            cpu_check_interval: Interval for CPU check in seconds
        """
        self.notifier = notifier
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.cpu_check_interval = cpu_check_interval
        self.logger = get_logger().get_logger()

    def check_cpu_usage(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check CPU usage

        Returns:
            Tuple of (ok, cpu_info_dict)
        """
        self.logger.info("Checking CPU usage")

        try:
            # Get CPU usage over interval
            cpu_percent = psutil.cpu_percent(interval=self.cpu_check_interval)
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)

            # Get per-CPU usage
            per_cpu = psutil.cpu_percent(interval=1, percpu=True)

            # Get load average (Unix only)
            try:
                load_avg = psutil.getloadavg()
                load_1, load_5, load_15 = load_avg
            except AttributeError:
                load_1 = load_5 = load_15 = None

            cpu_info = {
                "cpu_percent": cpu_percent,
                "cpu_count_physical": cpu_count,
                "cpu_count_logical": cpu_count_logical,
                "per_cpu_percent": per_cpu,
                "load_average_1min": load_1,
                "load_average_5min": load_5,
                "load_average_15min": load_15,
                "threshold_exceeded": cpu_percent >= self.cpu_threshold,
            }

            if cpu_info["threshold_exceeded"]:
                self.logger.warning(f"CPU usage high: {cpu_percent}%")
                self.notifier.send_warning(
                    f"CPU usage is {cpu_percent}% "
                    f"(threshold: {self.cpu_threshold}%)",
                    "System Monitor - CPU",
                    cpu_info,
                )
                return False, cpu_info
            else:
                self.logger.info(f"CPU usage: {cpu_percent}%")
                return True, cpu_info

        except Exception as e:
            self.logger.error(f"Failed to check CPU usage: {e}")
            return False, {"error": str(e)}

    def check_memory_usage(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check memory usage

        Returns:
            Tuple of (ok, memory_info_dict)
        """
        self.logger.info("Checking memory usage")

        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            memory_info = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent,
                "swap_total_gb": round(swap.total / (1024**3), 2),
                "swap_used_gb": round(swap.used / (1024**3), 2),
                "swap_percent": swap.percent,
                "threshold_exceeded": memory.percent >= self.memory_threshold,
            }

            if memory_info["threshold_exceeded"]:
                self.logger.warning(f"Memory usage high: {memory.percent}%")
                self.notifier.send_warning(
                    f"Memory usage is {memory.percent}% "
                    f"(threshold: {self.memory_threshold}%)",
                    "System Monitor - Memory",
                    memory_info,
                )
                return False, memory_info
            else:
                self.logger.info(f"Memory usage: {memory.percent}%")
                return True, memory_info

        except Exception as e:
            self.logger.error(f"Failed to check memory usage: {e}")
            return False, {"error": str(e)}

    def get_uptime(self) -> Dict[str, Any]:
        """
        Get system uptime

        Returns:
            Dictionary with uptime information
        """
        self.logger.info("Getting system uptime")

        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime_delta = timedelta(seconds=int(uptime_seconds))

            uptime_info = {
                "boot_timestamp": boot_time,
                "uptime_seconds": int(uptime_seconds),
                "uptime_days": uptime_delta.days,
                "uptime_formatted": str(uptime_delta),
            }

            self.logger.info(f"System uptime: {uptime_info['uptime_formatted']}")
            return uptime_info

        except Exception as e:
            self.logger.error(f"Failed to get uptime: {e}")
            return {"error": str(e)}

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics

        Returns:
            Dictionary with all system stats
        """
        self.logger.info("Getting comprehensive system statistics")

        stats = {}

        # CPU
        cpu_ok, cpu_info = self.check_cpu_usage()
        stats["cpu"] = cpu_info
        stats["cpu_ok"] = cpu_ok

        # Memory
        mem_ok, mem_info = self.check_memory_usage()
        stats["memory"] = mem_info
        stats["memory_ok"] = mem_ok

        # Uptime
        stats["uptime"] = self.get_uptime()

        # Overall status
        stats["all_ok"] = cpu_ok and mem_ok

        return stats


# Made with Bob
