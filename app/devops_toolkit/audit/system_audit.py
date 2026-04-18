"""
System audit utilities for inventory, users, files, and cron jobs
"""

import grp
import os
import platform
import pwd
from typing import Any, Dict, List, Tuple

import psutil

from devops_toolkit.core.logger import get_logger
from devops_toolkit.core.notifier import SlackNotifier
from devops_toolkit.utils.system import CommandExecutor, SystemInfo


class SystemAuditor:
    """Perform system audits and inventory collection"""

    def __init__(self, notifier: SlackNotifier):
        """
        Initialize system auditor

        Args:
            notifier: Slack notifier instance
        """
        self.notifier = notifier
        self.logger = get_logger().get_logger()

    def collect_inventory(self) -> Dict[str, Any]:
        """
        Collect comprehensive system inventory

        Returns:
            Dictionary with system inventory
        """
        self.logger.info("Collecting system inventory")

        inventory = {}

        # Basic system info
        inventory["hostname"] = platform.node()
        inventory["os_info"] = SystemInfo.get_os_info()

        # CPU info
        inventory["cpu"] = {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "architecture": platform.machine(),
        }

        # Memory info
        memory = psutil.virtual_memory()
        inventory["memory"] = {
            "total_gb": round(memory.total / (1024**3), 2),
            "total_bytes": memory.total,
        }

        # Disk info
        disk_info = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append(
                    {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                    }
                )
            except PermissionError:
                continue
        inventory["disks"] = disk_info

        # Network interfaces
        net_info = []
        net_if_addrs = psutil.net_if_addrs()
        for interface, addrs in net_if_addrs.items():
            for addr in addrs:
                if addr.family == 2:  # AF_INET (IPv4)
                    net_info.append(
                        {
                            "interface": interface,
                            "ip_address": addr.address,
                            "netmask": addr.netmask,
                        }
                    )
        inventory["network_interfaces"] = net_info

        self.logger.info("System inventory collected successfully")
        return inventory

    def audit_users(self) -> Dict[str, Any]:
        """
        Audit system users and groups

        Returns:
            Dictionary with user audit information
        """
        self.logger.info("Auditing system users and groups")

        audit = {"users": [], "groups": [], "user_count": 0, "group_count": 0}

        # Parse /etc/passwd
        try:
            users = pwd.getpwall()
            for user in users:
                user_info = {
                    "username": user.pw_name,
                    "uid": user.pw_uid,
                    "gid": user.pw_gid,
                    "home": user.pw_dir,
                    "shell": user.pw_shell,
                }
                audit["users"].append(user_info)

            audit["user_count"] = len(users)
            self.logger.info(f"Found {audit['user_count']} users")

        except Exception as e:
            self.logger.error(f"Failed to audit users: {e}")
            audit["user_error"] = str(e)

        # Parse /etc/group
        try:
            groups = grp.getgrall()
            for group in groups:
                group_info = {
                    "groupname": group.gr_name,
                    "gid": group.gr_gid,
                    "members": list(group.gr_mem),
                }
                audit["groups"].append(group_info)

            audit["group_count"] = len(groups)
            self.logger.info(f"Found {audit['group_count']} groups")

        except Exception as e:
            self.logger.error(f"Failed to audit groups: {e}")
            audit["group_error"] = str(e)

        return audit

    def audit_file_permissions(
        self, scan_paths: List[str], exclude_paths: List[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Audit file permissions for security issues

        Args:
            scan_paths: Paths to scan
            exclude_paths: Paths to exclude from scan

        Returns:
            Tuple of (all_ok, audit_results)
        """
        self.logger.info("Auditing file permissions")

        exclude_paths = exclude_paths or []
        world_writable = []
        scan_errors = []

        for scan_path in scan_paths:
            if not os.path.exists(scan_path):
                self.logger.warning(f"Scan path does not exist: {scan_path}")
                continue

            self.logger.info(f"Scanning path: {scan_path}")

            try:
                for root, dirs, files in os.walk(scan_path):
                    # Skip excluded paths
                    if any(root.startswith(ex) for ex in exclude_paths):
                        continue

                    # Check directories
                    for dirname in dirs:
                        dirpath = os.path.join(root, dirname)
                        try:
                            stat_info = os.stat(dirpath)
                            mode = stat_info.st_mode

                            # Check if world-writable (others have write)
                            if mode & 0o002:
                                world_writable.append(
                                    {
                                        "path": dirpath,
                                        "type": "directory",
                                        "mode": oct(mode)[-3:],
                                    }
                                )
                        except (PermissionError, FileNotFoundError):
                            continue

                    # Check files
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        try:
                            stat_info = os.stat(filepath)
                            mode = stat_info.st_mode

                            # Check if world-writable
                            if mode & 0o002:
                                world_writable.append(
                                    {
                                        "path": filepath,
                                        "type": "file",
                                        "mode": oct(mode)[-3:],
                                    }
                                )
                        except (PermissionError, FileNotFoundError):
                            continue

            except Exception as e:
                error_msg = f"Error scanning {scan_path}: {str(e)}"
                self.logger.error(error_msg)
                scan_errors.append(error_msg)

        audit_results = {
            "world_writable_count": len(world_writable),
            "world_writable_files": world_writable[:100],
            "scan_errors": scan_errors,
            "scanned_paths": scan_paths,
        }

        all_ok = len(world_writable) == 0

        if not all_ok:
            self.logger.warning(
                f"Found {len(world_writable)} world-writable files/dirs"
            )
            self.notifier.send_warning(
                f"Found {len(world_writable)} world-writable files/dirs",
                "File Permissions Audit",
                {"count": len(world_writable)},
            )
        else:
            self.logger.info("No world-writable files found")

        return all_ok, audit_results

    def audit_cron_jobs(self) -> Dict[str, Any]:
        """
        Audit cron jobs on the system

        Returns:
            Dictionary with cron job information
        """
        self.logger.info("Auditing cron jobs")

        audit = {"system_crontab": [], "user_crontabs": {}, "cron_d": [], "issues": []}

        # Check system crontab
        if os.path.exists("/etc/crontab"):
            try:
                with open("/etc/crontab") as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines, 1):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            audit["system_crontab"].append(
                                {"line_number": i, "content": line}
                            )
            except Exception as e:
                audit["issues"].append(f"Failed to read /etc/crontab: {e}")

        # Check /etc/cron.d/
        if os.path.exists("/etc/cron.d"):
            try:
                for filename in os.listdir("/etc/cron.d"):
                    filepath = os.path.join("/etc/cron.d", filename)
                    if os.path.isfile(filepath):
                        try:
                            with open(filepath) as f:
                                content = f.read()
                                audit["cron_d"].append(
                                    {"file": filename, "content": content}
                                )
                        except Exception as e:
                            audit["issues"].append(f"Failed to read {filepath}: {e}")
            except Exception as e:
                audit["issues"].append(f"Failed to list /etc/cron.d: {e}")

        # Check user crontabs
        success, stdout, _ = CommandExecutor.run_shell(
            "ls /var/spool/cron/crontabs/ 2>/dev/null || "
            "ls /var/spool/cron/ 2>/dev/null",
            timeout=10,
        )

        if success and stdout:
            for username in stdout.strip().split("\n"):
                if username:
                    success, cron_content, _ = CommandExecutor.run_shell(
                        f"crontab -u {username} -l 2>/dev/null", timeout=10
                    )
                    if success:
                        audit["user_crontabs"][username] = cron_content

        self.logger.info("Cron job audit completed")
        return audit


# Made with Bob
