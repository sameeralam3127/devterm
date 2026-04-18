"""
Patch management module for Ubuntu and RHEL-based systems
Handles OS updates, reboot detection, and notifications
"""

import os
from typing import Tuple, Dict, Any
from devops_toolkit.utils.system import (
    SystemInfo, CommandExecutor, OSType
)
from devops_toolkit.core.logger import get_logger
from devops_toolkit.core.notifier import SlackNotifier, Severity


class PatchManager:
    """Manage system patches and updates"""
    
    def __init__(self, notifier: SlackNotifier, dry_run: bool = False):
        """
        Initialize patch manager
        
        Args:
            notifier: Slack notifier instance
            dry_run: If True, don't apply changes
        """
        self.notifier = notifier
        self.dry_run = dry_run
        self.logger = get_logger().get_logger()
        self.os_type = SystemInfo.detect_os()
        self.package_manager = SystemInfo.get_package_manager()
    
    def check_updates(self) -> Tuple[bool, int, str]:
        """
        Check for available updates
        
        Returns:
            Tuple of (success, update_count, message)
        """
        self.logger.info("Checking for available updates")
        
        if self.os_type == OSType.UNKNOWN:
            msg = "Unknown OS type, cannot check updates"
            self.logger.error(msg)
            return False, 0, msg
        
        try:
            if SystemInfo.is_debian_based():
                return self._check_updates_debian()
            elif SystemInfo.is_rhel_based():
                return self._check_updates_rhel()
            else:
                return False, 0, "Unsupported OS type"
        except Exception as e:
            msg = f"Failed to check updates: {str(e)}"
            self.logger.exception(msg)
            return False, 0, msg
    
    def _check_updates_debian(self) -> Tuple[bool, int, str]:
        """Check updates for Debian-based systems"""
        # Update package lists
        success, stdout, stderr = CommandExecutor.run_shell(
            'apt-get update',
            timeout=300
        )
        
        if not success:
            return False, 0, f"Failed to update package lists: {stderr}"
        
        # Check for upgradable packages
        success, stdout, stderr = CommandExecutor.run_shell(
            'apt list --upgradable 2>/dev/null | grep -c upgradable',
            timeout=60
        )
        
        if success and stdout.strip().isdigit():
            count = int(stdout.strip())
            return True, count, f"{count} updates available"
        
        return True, 0, "No updates available"
    
    def _check_updates_rhel(self) -> Tuple[bool, int, str]:
        """Check updates for RHEL-based systems"""
        pm = self.package_manager or 'yum'
        
        # Check for available updates
        success, stdout, stderr = CommandExecutor.run_shell(
            f'{pm} check-update | grep -v "^$" | wc -l',
            timeout=300
        )
        
        if success and stdout.strip().isdigit():
            count = int(stdout.strip())
            # Subtract header lines
            count = max(0, count - 2)
            return True, count, f"{count} updates available"
        
        return True, 0, "No updates available"
    
    def apply_updates(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Apply system updates
        
        Returns:
            Tuple of (success, message, details_dict)
        """
        self.logger.info("Starting system update process")
        
        if self.dry_run:
            self.logger.info("Dry run mode - no changes will be applied")
            return True, "Dry run - no updates applied", {}
        
        if self.os_type == OSType.UNKNOWN:
            msg = "Unknown OS type, cannot apply updates"
            self.logger.error(msg)
            self.notifier.send_critical(msg, "Patch Management")
            return False, msg, {}
        
        # Check for updates first
        check_success, update_count, check_msg = self.check_updates()
        
        if not check_success:
            self.notifier.send_critical(
                f"Failed to check for updates: {check_msg}",
                "Patch Management"
            )
            return False, check_msg, {}
        
        if update_count == 0:
            msg = "No updates available"
            self.logger.info(msg)
            self.notifier.send_info(msg, "Patch Management")
            return True, msg, {'update_count': 0}
        
        # Apply updates
        try:
            if SystemInfo.is_debian_based():
                success, message, details = self._apply_updates_debian()
            elif SystemInfo.is_rhel_based():
                success, message, details = self._apply_updates_rhel()
            else:
                return False, "Unsupported OS type", {}
            
            details['update_count'] = update_count
            
            # Check if reboot is required
            reboot_required = self.check_reboot_required()
            details['reboot_required'] = reboot_required
            
            if success:
                severity = Severity.WARNING if reboot_required else Severity.INFO
                self.notifier.send(
                    message,
                    severity,
                    "Patch Management",
                    details
                )
            else:
                self.notifier.send_critical(
                    message,
                    "Patch Management",
                    details
                )
            
            return success, message, details
            
        except Exception as e:
            msg = f"Failed to apply updates: {str(e)}"
            self.logger.exception(msg)
            self.notifier.send_critical(msg, "Patch Management")
            return False, msg, {}
    
    def _apply_updates_debian(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Apply updates for Debian-based systems"""
        self.logger.info("Applying updates for Debian-based system")
        
        # Run apt upgrade
        success, stdout, stderr = CommandExecutor.run_shell(
            'DEBIAN_FRONTEND=noninteractive apt-get upgrade -y',
            timeout=1800  # 30 minutes
        )
        
        details = {
            'os_type': 'debian',
            'package_manager': 'apt'
        }
        
        if success:
            msg = "System updates applied successfully"
            self.logger.info(msg)
            return True, msg, details
        else:
            msg = f"Failed to apply updates: {stderr}"
            self.logger.error(msg)
            details['error'] = stderr
            return False, msg, details
    
    def _apply_updates_rhel(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Apply updates for RHEL-based systems"""
        pm = self.package_manager or 'yum'
        self.logger.info(f"Applying updates for RHEL-based system using {pm}")
        
        # Run update
        success, stdout, stderr = CommandExecutor.run_shell(
            f'{pm} update -y',
            timeout=1800  # 30 minutes
        )
        
        details = {
            'os_type': 'rhel',
            'package_manager': pm
        }
        
        if success:
            msg = "System updates applied successfully"
            self.logger.info(msg)
            return True, msg, details
        else:
            msg = f"Failed to apply updates: {stderr}"
            self.logger.error(msg)
            details['error'] = stderr
            return False, msg, details
    
    def check_reboot_required(self) -> bool:
        """
        Check if system reboot is required
        
        Returns:
            True if reboot required, False otherwise
        """
        self.logger.info("Checking if reboot is required")
        
        try:
            if SystemInfo.is_debian_based():
                # Check for reboot-required file
                if os.path.exists('/var/run/reboot-required'):
                    self.logger.warning("Reboot required (Ubuntu/Debian)")
                    return True
            
            elif SystemInfo.is_rhel_based():
                # Use needs-restarting command if available
                if CommandExecutor.check_command_exists('needs-restarting'):
                    success, stdout, stderr = CommandExecutor.run_shell(
                        'needs-restarting -r',
                        timeout=30
                    )
                    # needs-restarting returns 1 if reboot needed
                    if not success:
                        self.logger.warning("Reboot required (RHEL)")
                        return True
                else:
                    # Fallback: check if kernel was updated
                    success, stdout, _ = CommandExecutor.run_shell(
                        'rpm -q --last kernel | head -1',
                        timeout=30
                    )
                    if success:
                        # Compare with running kernel
                        running = os.uname().release
                        if running not in stdout:
                            self.logger.warning(
                                "Kernel updated, reboot recommended"
                            )
                            return True
            
            self.logger.info("No reboot required")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check reboot status: {e}")
            return False
    
    def get_patch_status(self) -> Dict[str, Any]:
        """
        Get comprehensive patch status
        
        Returns:
            Dictionary with patch status information
        """
        self.logger.info("Getting patch status")
        
        status = {
            'os_type': self.os_type.value,
            'package_manager': self.package_manager,
            'reboot_required': self.check_reboot_required()
        }
        
        # Check for available updates
        success, count, message = self.check_updates()
        status['check_success'] = success
        status['available_updates'] = count
        status['check_message'] = message
        
        return status

# Made with Bob
