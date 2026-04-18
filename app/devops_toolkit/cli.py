"""
Command-line interface for DevOps Toolkit
"""

import sys
import argparse
from devops_toolkit.config_loader import ConfigLoader
from devops_toolkit.core.logger import get_logger
from devops_toolkit.core.notifier import SlackNotifier
from devops_toolkit.maintenance.patch_manager import PatchManager
from devops_toolkit.maintenance.service_manager import ServiceManager
from devops_toolkit.monitors.disk_monitor import DiskMonitor
from devops_toolkit.monitors.system_monitor import SystemMonitor
from devops_toolkit.monitors.network_monitor import NetworkMonitor
from devops_toolkit.audit.system_audit import SystemAuditor


class DevOpsToolkit:
    """Main DevOps Toolkit application"""
    
    def __init__(self, config_path=None, dry_run=False, test_mode=False):
        """
        Initialize DevOps Toolkit
        
        Args:
            config_path: Path to configuration file
            dry_run: If True, don't make changes
            test_mode: If True, run in test mode
        """
        self.config = ConfigLoader(config_path)
        self.dry_run = dry_run
        self.test_mode = test_mode
        
        # Setup logging
        logger_instance = get_logger()
        logger_instance.setup(
            log_file=self.config.get('logging.log_file'),
            log_level=self.config.get('logging.log_level'),
            max_bytes=self.config.get('logging.max_bytes'),
            backup_count=self.config.get('logging.backup_count')
        )
        self.logger = logger_instance.get_logger()
        
        # Setup notifier
        self.notifier = SlackNotifier(
            webhook_url=self.config.get('slack.webhook_url'),
            enabled=self.config.get('slack.enabled'),
            retry_attempts=self.config.get('slack.retry_attempts'),
            retry_delay=self.config.get('slack.retry_delay')
        )
        
        self.logger.info("DevOps Toolkit initialized")
    
    def run_full(self):
        """Run all modules"""
        self.logger.info("Running full DevOps Toolkit execution")
        
        results = {
            'patch': None,
            'monitor': None,
            'audit': None
        }
        
        # Run patch management
        if self.config.get('maintenance.patch_management.enabled'):
            self.logger.info("Running patch management")
            results['patch'] = self.run_patch()
        
        # Run monitoring
        self.logger.info("Running monitoring checks")
        results['monitor'] = self.run_monitor()
        
        # Run audits
        self.logger.info("Running system audits")
        results['audit'] = self.run_audit()
        
        self.logger.info("Full execution completed")
        return results
    
    def run_patch(self):
        """Run patch management"""
        self.logger.info("Starting patch management")
        
        patch_manager = PatchManager(self.notifier, self.dry_run)
        
        # Get patch status
        status = patch_manager.get_patch_status()
        self.logger.info(f"Patch status: {status}")
        
        if not self.test_mode:
            # Apply updates
            success, message, details = patch_manager.apply_updates()
            return {
                'success': success,
                'message': message,
                'details': details,
                'status': status
            }
        else:
            return {
                'success': True,
                'message': 'Test mode - no patches applied',
                'status': status
            }
    
    def run_monitor(self):
        """Run monitoring checks"""
        self.logger.info("Starting monitoring checks")
        
        results = {}
        
        # Disk monitoring
        if self.config.get('monitoring.disk.enabled'):
            disk_monitor = DiskMonitor(
                self.notifier,
                self.config.get('monitoring.disk.threshold_percent'),
                self.config.get('monitoring.disk.paths')
            )
            disk_ok, disk_results = disk_monitor.check_disk_usage()
            results['disk'] = {
                'ok': disk_ok,
                'results': disk_results
            }
        
        # System monitoring (CPU, Memory, Uptime)
        if (self.config.get('monitoring.cpu.enabled') or
                self.config.get('monitoring.memory.enabled')):
            system_monitor = SystemMonitor(
                self.notifier,
                self.config.get('monitoring.cpu.threshold_percent'),
                self.config.get('monitoring.memory.threshold_percent'),
                self.config.get('monitoring.cpu.check_interval')
            )
            system_stats = system_monitor.get_system_stats()
            results['system'] = system_stats
        
        # Network monitoring (Ports and Processes)
        if (self.config.get('monitoring.ports.enabled') or
                self.config.get('monitoring.processes.enabled')):
            network_monitor = NetworkMonitor(
                self.notifier,
                self.config.get('monitoring.ports.check_ports'),
                self.config.get('monitoring.processes.watch_processes')
            )
            network_stats = network_monitor.get_network_stats()
            results['network'] = network_stats
        
        return results
    
    def run_audit(self):
        """Run system audits"""
        self.logger.info("Starting system audits")
        
        auditor = SystemAuditor(self.notifier)
        results = {}
        
        # System inventory
        results['inventory'] = auditor.collect_inventory()
        
        # User audit
        if self.config.get('audit.user_audit.enabled'):
            results['users'] = auditor.audit_users()
        
        # File permissions audit
        if self.config.get('audit.file_permissions.enabled'):
            perm_ok, perm_results = auditor.audit_file_permissions(
                self.config.get('audit.file_permissions.scan_paths'),
                self.config.get('audit.file_permissions.exclude_paths')
            )
            results['file_permissions'] = {
                'ok': perm_ok,
                'results': perm_results
            }
        
        # Cron audit
        if self.config.get('audit.cron_audit.enabled'):
            results['cron'] = auditor.audit_cron_jobs()
        
        return results
    
    def run_test(self):
        """Run test mode"""
        self.logger.info("Running in test mode")
        
        print("\n=== DevOps Toolkit Test Mode ===\n")
        
        # Validate configuration
        print("1. Validating configuration...")
        is_valid, errors = self.config.validate()
        if is_valid:
            print("   ✓ Configuration is valid")
        else:
            print("   ✗ Configuration errors:")
            for error in errors:
                print(f"     - {error}")
        
        # Test Slack connection
        print("\n2. Testing Slack connection...")
        success, message = self.notifier.test_connection()
        if success:
            print(f"   ✓ {message}")
        else:
            print(f"   ✗ {message}")
        
        # Run dry-run checks
        print("\n3. Running dry-run checks...")
        print("   - Patch management check...")
        patch_manager = PatchManager(self.notifier, dry_run=True)
        status = patch_manager.get_patch_status()
        print(f"     Available updates: {status.get('available_updates', 0)}")
        print(f"     Reboot required: {status.get('reboot_required', False)}")
        
        print("   - Monitoring checks...")
        monitor_results = self.run_monitor()
        print(f"     Disk OK: {monitor_results.get('disk', {}).get('ok', 'N/A')}")
        print(f"     System OK: {monitor_results.get('system', {}).get('all_ok', 'N/A')}")
        
        print("\n=== Test Complete ===\n")
        
        return is_valid and success
    
    def setup(self):
        """Initial setup"""
        print("\n=== DevOps Toolkit Setup ===\n")
        
        # Create default config
        config_path = '/etc/devops_toolkit/config.yaml'
        print(f"Creating default configuration at {config_path}...")
        
        success = ConfigLoader.create_default_config(config_path)
        if success:
            print(f"✓ Configuration created at {config_path}")
            print("\nPlease edit the configuration file to:")
            print("  1. Add your Slack webhook URL")
            print("  2. Adjust monitoring thresholds")
            print("  3. Configure processes and ports to monitor")
            print(f"\nEdit: sudo nano {config_path}")
        else:
            print(f"✗ Failed to create configuration")
            print(f"You may need to run with sudo or create {config_path} manually")
        
        return success


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='DevOps Toolkit - System monitoring and maintenance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run              Run all modules
  %(prog)s patch            Run only patch management
  %(prog)s monitor          Run only monitoring
  %(prog)s audit            Run only audits
  %(prog)s test             Run in test mode
  %(prog)s setup            Initial setup
        """
    )
    
    parser.add_argument(
        'command',
        choices=['run', 'patch', 'monitor', 'audit', 'test', 'setup'],
        default='run',
        nargs='?',
        help='Command to execute (default: run)'
    )
    
    parser.add_argument(
        '--config',
        help='Path to configuration file',
        default=None
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no changes)'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode'
    )
    
    args = parser.parse_args()
    
    # Handle setup command separately
    if args.command == 'setup':
        toolkit = DevOpsToolkit()
        success = toolkit.setup()
        sys.exit(0 if success else 1)
    
    # Initialize toolkit
    toolkit = DevOpsToolkit(
        config_path=args.config,
        dry_run=args.dry_run,
        test_mode=args.test or args.command == 'test'
    )
    
    # Execute command
    try:
        if args.command == 'test':
            success = toolkit.run_test()
            sys.exit(0 if success else 1)
        elif args.command == 'run':
            toolkit.run_full()
        elif args.command == 'patch':
            toolkit.run_patch()
        elif args.command == 'monitor':
            toolkit.run_monitor()
        elif args.command == 'audit':
            toolkit.run_audit()
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}")
        toolkit.logger.exception("Unhandled exception")
        sys.exit(1)


if __name__ == '__main__':
    main()

# Made with Bob
