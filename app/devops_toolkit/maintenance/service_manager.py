"""
Service management utilities with retry logic
"""

import time
from typing import Tuple, Dict, Any
from devops_toolkit.utils.system import CommandExecutor
from devops_toolkit.core.logger import get_logger
from devops_toolkit.core.notifier import SlackNotifier, Severity


class ServiceManager:
    """Manage system services with retry logic"""
    
    def __init__(self, notifier: SlackNotifier,
                 retry_count: int = 3,
                 retry_delay: int = 5):
        """
        Initialize service manager
        
        Args:
            notifier: Slack notifier instance
            retry_count: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.notifier = notifier
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.logger = get_logger().get_logger()
    
    def get_service_status(self, service_name: str) -> Tuple[bool, str]:
        """
        Get service status
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (is_active, status_message)
        """
        self.logger.info(f"Checking status of service: {service_name}")
        
        success, stdout, stderr = CommandExecutor.run_shell(
            f'systemctl is-active {service_name}',
            timeout=10
        )
        
        status = stdout.strip() if stdout else 'unknown'
        is_active = status == 'active'
        
        self.logger.info(f"Service {service_name} status: {status}")
        return is_active, status
    
    def restart_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Restart a service with retry logic
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (success, message)
        """
        self.logger.info(f"Attempting to restart service: {service_name}")
        
        for attempt in range(1, self.retry_count + 1):
            self.logger.info(
                f"Restart attempt {attempt}/{self.retry_count} "
                f"for {service_name}"
            )
            
            # Attempt restart
            success, stdout, stderr = CommandExecutor.run_shell(
                f'systemctl restart {service_name}',
                timeout=60
            )
            
            if not success:
                self.logger.warning(
                    f"Restart attempt {attempt} failed: {stderr}"
                )
                
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    msg = f"Failed to restart {service_name} after {self.retry_count} attempts"
                    self.logger.error(msg)
                    self.notifier.send_critical(
                        msg,
                        "Service Manager",
                        {'service': service_name, 'error': stderr}
                    )
                    return False, msg
            
            # Verify service is running
            time.sleep(2)
            is_active, status = self.get_service_status(service_name)
            
            if is_active:
                msg = f"Service {service_name} restarted successfully"
                self.logger.info(msg)
                self.notifier.send_info(
                    msg,
                    "Service Manager",
                    {'service': service_name, 'attempts': attempt}
                )
                return True, msg
            else:
                self.logger.warning(
                    f"Service {service_name} not active after restart: {status}"
                )
                
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay)
        
        msg = f"Service {service_name} failed to become active"
        self.logger.error(msg)
        self.notifier.send_critical(
            msg,
            "Service Manager",
            {'service': service_name}
        )
        return False, msg
    
    def start_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Start a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (success, message)
        """
        self.logger.info(f"Starting service: {service_name}")
        
        success, stdout, stderr = CommandExecutor.run_shell(
            f'systemctl start {service_name}',
            timeout=60
        )
        
        if success:
            time.sleep(2)
            is_active, status = self.get_service_status(service_name)
            
            if is_active:
                msg = f"Service {service_name} started successfully"
                self.logger.info(msg)
                return True, msg
            else:
                msg = f"Service {service_name} failed to start: {status}"
                self.logger.error(msg)
                return False, msg
        else:
            msg = f"Failed to start {service_name}: {stderr}"
            self.logger.error(msg)
            return False, msg
    
    def stop_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Stop a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (success, message)
        """
        self.logger.info(f"Stopping service: {service_name}")
        
        success, stdout, stderr = CommandExecutor.run_shell(
            f'systemctl stop {service_name}',
            timeout=60
        )
        
        if success:
            msg = f"Service {service_name} stopped successfully"
            self.logger.info(msg)
            return True, msg
        else:
            msg = f"Failed to stop {service_name}: {stderr}"
            self.logger.error(msg)
            return False, msg
    
    def enable_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Enable a service to start on boot
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple of (success, message)
        """
        self.logger.info(f"Enabling service: {service_name}")
        
        success, stdout, stderr = CommandExecutor.run_shell(
            f'systemctl enable {service_name}',
            timeout=30
        )
        
        if success:
            msg = f"Service {service_name} enabled successfully"
            self.logger.info(msg)
            return True, msg
        else:
            msg = f"Failed to enable {service_name}: {stderr}"
            self.logger.error(msg)
            return False, msg
    
    def get_service_info(self, service_name: str) -> Dict[str, Any]:
        """
        Get detailed service information
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dictionary with service information
        """
        self.logger.info(f"Getting info for service: {service_name}")
        
        info = {'service_name': service_name}
        
        # Get status
        is_active, status = self.get_service_status(service_name)
        info['is_active'] = is_active
        info['status'] = status
        
        # Get enabled status
        success, stdout, _ = CommandExecutor.run_shell(
            f'systemctl is-enabled {service_name}',
            timeout=10
        )
        info['is_enabled'] = stdout.strip() == 'enabled' if success else False
        
        return info

# Made with Bob
