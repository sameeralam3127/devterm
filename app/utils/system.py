"""
System utilities for OS detection and command execution
"""

import os
import platform
import subprocess
from enum import Enum
from typing import List, Optional, Tuple


class OSType(Enum):
    """Supported operating system types"""

    UBUNTU = "ubuntu"
    DEBIAN = "debian"
    RHEL = "rhel"
    CENTOS = "centos"
    FEDORA = "fedora"
    ROCKY = "rocky"
    ALMA = "alma"
    UNKNOWN = "unknown"


class SystemInfo:
    """System information and OS detection"""

    @staticmethod
    def detect_os() -> OSType:
        """
        Detect the operating system type

        Returns:
            OSType enum value
        """
        if not platform.system() == "Linux":
            return OSType.UNKNOWN

        # Check /etc/os-release first (modern standard)
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release") as f:
                    content = f.read().lower()

                    if "ubuntu" in content:
                        return OSType.UBUNTU
                    elif "debian" in content:
                        return OSType.DEBIAN
                    elif "rhel" in content or "red hat" in content:
                        return OSType.RHEL
                    elif "centos" in content:
                        return OSType.CENTOS
                    elif "fedora" in content:
                        return OSType.FEDORA
                    elif "rocky" in content:
                        return OSType.ROCKY
                    elif "almalinux" in content or "alma" in content:
                        return OSType.ALMA
            except Exception:
                pass

        # Fallback to release files
        if os.path.exists("/etc/redhat-release"):
            return OSType.RHEL
        elif os.path.exists("/etc/debian_version"):
            return OSType.DEBIAN

        return OSType.UNKNOWN

    @staticmethod
    def is_debian_based() -> bool:
        """Check if OS is Debian-based (Ubuntu, Debian)"""
        os_type = SystemInfo.detect_os()
        return os_type in [OSType.UBUNTU, OSType.DEBIAN]

    @staticmethod
    def is_rhel_based() -> bool:
        """Check if OS is RHEL-based (RHEL, CentOS, Fedora, Rocky, Alma)"""
        os_type = SystemInfo.detect_os()
        return os_type in [
            OSType.RHEL,
            OSType.CENTOS,
            OSType.FEDORA,
            OSType.ROCKY,
            OSType.ALMA,
        ]

    @staticmethod
    def get_package_manager() -> Optional[str]:
        """
        Get the package manager command for the OS

        Returns:
            Package manager command (apt, yum, dnf) or None
        """
        if SystemInfo.is_debian_based():
            return "apt"
        elif SystemInfo.is_rhel_based():
            # Check if dnf is available (newer RHEL/Fedora)
            if os.path.exists("/usr/bin/dnf"):
                return "dnf"
            else:
                return "yum"
        return None

    @staticmethod
    def get_os_info() -> dict:
        """
        Get detailed OS information

        Returns:
            Dictionary with OS details
        """
        info = {
            "os_type": SystemInfo.detect_os().value,
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "package_manager": SystemInfo.get_package_manager(),
        }

        # Try to get distribution info
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            info["os_name"] = line.split("=")[1].strip("\"'")
                            break
        except Exception:
            pass

        return info


class CommandExecutor:
    """Safe command execution with timeout and error handling"""

    @staticmethod
    def run(
        command: List[str],
        timeout: int = 300,
        check: bool = True,
        capture_output: bool = True,
    ) -> Tuple[bool, str, str, int]:
        """
        Execute a command safely

        Args:
            command: Command and arguments as list
            timeout: Timeout in seconds
            check: Raise exception on non-zero exit
            capture_output: Capture stdout and stderr

        Returns:
            Tuple of (success, stdout, stderr, return_code)
        """
        try:
            result = subprocess.run(
                command,
                timeout=timeout,
                check=check,
                capture_output=capture_output,
                text=True,
            )

            return (
                result.returncode == 0,
                result.stdout if capture_output else "",
                result.stderr if capture_output else "",
                result.returncode,
            )

        except subprocess.TimeoutExpired:
            return (False, "", f"Command timed out after {timeout} seconds", -1)
        except subprocess.CalledProcessError as e:
            return (
                False,
                e.stdout if capture_output else "",
                e.stderr if capture_output else "",
                e.returncode,
            )
        except Exception as e:
            return (False, "", f"Command execution failed: {str(e)}", -1)

    @staticmethod
    def run_shell(command: str, timeout: int = 300) -> Tuple[bool, str, str]:
        """
        Execute a shell command

        Args:
            command: Shell command string
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        success, stdout, stderr, _ = CommandExecutor.run(
            ["bash", "-c", command], timeout=timeout, check=False
        )
        return success, stdout, stderr

    @staticmethod
    def check_command_exists(command: str) -> bool:
        """
        Check if a command exists in PATH

        Args:
            command: Command name

        Returns:
            True if command exists, False otherwise
        """
        success, _, _, _ = CommandExecutor.run(
            ["which", command], check=False, capture_output=True
        )
        return success


# Made with Bob
