"""
Network port and process monitoring module
"""

import socket
from typing import Any, Dict, List, Tuple

import psutil

from devops_toolkit.core.logger import get_logger
from devops_toolkit.core.notifier import SlackNotifier


class NetworkMonitor:
    """Monitor network ports and processes"""

    def __init__(
        self,
        notifier: SlackNotifier,
        ports: List[int] = None,
        processes: List[str] = None,
    ):
        """
        Initialize network monitor

        Args:
            notifier: Slack notifier instance
            ports: List of ports to check
            processes: List of process names to watch
        """
        self.notifier = notifier
        self.ports = ports or []
        self.processes = processes or []
        self.logger = get_logger().get_logger()

    def check_port(self, port: int, host: str = "localhost") -> bool:
        """
        Check if a port is open/listening

        Args:
            port: Port number to check
            host: Host to check (default: localhost)

        Returns:
            True if port is open, False otherwise
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            self.logger.error(f"Failed to check port {port}: {e}")
            return False

    def check_all_ports(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Check all configured ports

        Returns:
            Tuple of (all_ok, list of port status dicts)
        """
        self.logger.info("Checking configured ports")
        results = []
        all_ok = True

        for port in self.ports:
            is_open = self.check_port(port)

            port_info = {
                "port": port,
                "status": "open" if is_open else "closed",
                "is_open": is_open,
            }

            results.append(port_info)

            if not is_open:
                all_ok = False
                self.logger.warning(f"Port {port} is not accessible")
                self.notifier.send_warning(
                    f"Port {port} is not accessible",
                    "Network Monitor - Ports",
                    port_info,
                )
            else:
                self.logger.info(f"Port {port} is open")

        return all_ok, results

    def check_process_running(
        self, process_name: str
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Check if a process is running

        Args:
            process_name: Name of the process to check

        Returns:
            Tuple of (is_running, list of matching process info)
        """
        matching_processes = []

        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get("name", "")
                    cmdline = " ".join(proc_info.get("cmdline", []))

                    if (
                        process_name.lower() in proc_name.lower()
                        or process_name.lower() in cmdline.lower()
                    ):
                        matching_processes.append(
                            {
                                "pid": proc_info["pid"],
                                "name": proc_name,
                                "cmdline": cmdline,
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            self.logger.error(f"Failed to check process {process_name}: {e}")

        return len(matching_processes) > 0, matching_processes

    def check_all_processes(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Check all configured processes

        Returns:
            Tuple of (all_ok, list of process status dicts)
        """
        self.logger.info("Checking configured processes")
        results = []
        all_ok = True

        for process_name in self.processes:
            is_running, proc_list = self.check_process_running(process_name)

            process_info = {
                "process_name": process_name,
                "is_running": is_running,
                "instance_count": len(proc_list),
                "instances": proc_list,
            }

            results.append(process_info)

            if not is_running:
                all_ok = False
                self.logger.warning(f"Process '{process_name}' is not running")
                self.notifier.send_critical(
                    f"Process '{process_name}' is not running",
                    "Network Monitor - Processes",
                    process_info,
                )
            else:
                self.logger.info(
                    f"Process '{process_name}' is running "
                    f"({len(proc_list)} instances)"
                )

        return all_ok, results

    def get_listening_ports(self) -> List[Dict[str, Any]]:
        """
        Get all listening ports on the system

        Returns:
            List of listening port information
        """
        self.logger.info("Getting all listening ports")
        listening_ports = []

        try:
            connections = psutil.net_connections(kind="inet")

            for conn in connections:
                if conn.status == "LISTEN":
                    port_info = {
                        "port": conn.laddr.port,
                        "address": conn.laddr.ip,
                        "pid": conn.pid,
                    }

                    # Try to get process name
                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            port_info["process_name"] = proc.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            port_info["process_name"] = "unknown"

                    listening_ports.append(port_info)

        except Exception as e:
            self.logger.error(f"Failed to get listening ports: {e}")

        return listening_ports

    def get_network_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive network statistics

        Returns:
            Dictionary with network stats
        """
        self.logger.info("Getting network statistics")

        stats = {}

        # Check configured ports
        if self.ports:
            ports_ok, port_results = self.check_all_ports()
            stats["ports"] = port_results
            stats["ports_ok"] = ports_ok

        # Check configured processes
        if self.processes:
            procs_ok, proc_results = self.check_all_processes()
            stats["processes"] = proc_results
            stats["processes_ok"] = procs_ok

        # Get all listening ports
        stats["listening_ports"] = self.get_listening_ports()

        # Overall status
        stats["all_ok"] = stats.get("ports_ok", True) and stats.get(
            "processes_ok", True
        )

        return stats


# Made with Bob
