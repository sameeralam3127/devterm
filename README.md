# DevOps Toolkit

A production-grade Linux system health, monitoring, and maintenance toolkit for Ubuntu and RHEL-based systems.

DevOps Toolkit is a comprehensive Python-based automation tool designed for system administrators and DevOps engineers. It provides automated system monitoring, patch management, security auditing, and Slack notifications.

### Key Features

- **Patch Management**: Automated OS updates for Ubuntu and RHEL systems with reboot detection
- **System Monitoring**: CPU, memory, disk usage, and uptime tracking with configurable thresholds
- **Network Monitoring**: Port availability and process monitoring
- **Security Auditing**: File permissions, user/group audits, and cron job validation
- **DevOps Doctor**: One-command readiness score with CI-friendly JSON output and remediation guidance
- **Health Reports**: Combined doctor, monitoring, and inventory reports in text or JSON
- **Slack Integration**: Real-time notifications with severity levels (INFO, WARNING, CRITICAL)
- **Modular Architecture**: Run individual modules or full system checks
- **Cron Integration**: Automated scheduled execution
- **Test Mode**: Dry-run capabilities for safe testing

## Requirements

- **Operating Systems**: Ubuntu 18.04+, Debian 10+, RHEL 7+, CentOS 7+, Rocky Linux, AlmaLinux
- **Python**: 3.8 or higher
- **Privileges**: Root/sudo access for system operations
- **Dependencies**: psutil, requests, PyYAML (auto-installed)

## Quick Start

Use this path when you want to try the toolkit safely before scheduling it on a server.

```bash
# 1. Clone the repository
git clone https://github.com/sameeralam3127/devops-toolkit.git
cd devops-toolkit

# 2. Install locally in a virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Create a starter config you can edit without sudo
cp config.yaml.example config.yaml
```

For a local trial, edit `config.yaml` and set:

```yaml
slack:
  enabled: false
logging:
  log_file: ./devops_toolkit.log
```

You can also trim `monitoring.disk.paths`, `monitoring.ports.check_ports`, and `monitoring.processes.watch_processes` to match services that actually exist on your machine.

```bash
# 4. Run non-mutating checks first
devops-toolkit --config ./config.yaml doctor
devops-toolkit --config ./config.yaml report

# 5. Run monitoring or audit modules when ready
devops-toolkit --config ./config.yaml monitor
devops-toolkit --config ./config.yaml audit
```

For production servers, use the installer in the next section. Most maintenance actions require `sudo` because package management, system logs, and protected audit paths are owned by root.

## Quick Install

**One-line installation:**

```bash
curl -sSL https://raw.githubusercontent.com/sameeralam3127/devops-toolkit/main/install.sh | sudo bash
```

Or clone and install:

```bash
git clone https://github.com/sameeralam3127/devops-toolkit.git
cd devops-toolkit
sudo bash install.sh
```

The installer will:

- Check Python 3.8+ installation
- Install dependencies (with optional uv support)
- Copy files to `/opt/devops_toolkit`
- Create configuration at `/etc/devops_toolkit/config.yaml`
- Setup logging at `/var/log/devops_toolkit.log`
- Optionally configure cron jobs
- Create `devops-toolkit` command

### Configuration

Edit the configuration file:

```bash
sudo vim /etc/devops_toolkit/config.yaml
```

**Required Configuration:**

- Add your Slack webhook URL, or set `slack.enabled: false` while testing without Slack.
- Adjust CPU, memory, and disk thresholds for your server.
- Configure disk paths, processes, and ports that matter for your workload.
- Confirm `logging.log_file` points to a writable location.

Validate the configuration before running maintenance:

```bash
devops-toolkit doctor
devops-toolkit doctor --format json
```

## Usage

### Command-Line Interface

```bash
# Run all modules (monitoring, patching, auditing)
devops-toolkit run

# Run specific modules
devops-toolkit patch      # Patch management only
devops-toolkit monitor    # Monitoring only
devops-toolkit audit      # Auditing only
devops-toolkit doctor     # Readiness score and actionable diagnostics
devops-toolkit report     # Combined health report

# Test mode (dry-run, no changes)
devops-toolkit test

# CI-friendly doctor output
devops-toolkit doctor --format json --fail-on-warning

# Automation-friendly health report
devops-toolkit report --format json

# Include deeper audit scans in the report
devops-toolkit report --full-audit

# Dry-run mode
devops-toolkit --dry-run patch

# Initial setup
devops-toolkit setup

# Help
devops-toolkit --help
```

### Recommended First Runs

Start with read-only commands:

```bash
devops-toolkit doctor
devops-toolkit report --format json
devops-toolkit monitor
```

Then run deeper checks:

```bash
devops-toolkit report --full-audit
devops-toolkit audit
```

Use dry-run mode before patching:

```bash
devops-toolkit --dry-run patch
```

When ready to perform full maintenance:

```bash
sudo devops-toolkit run
```

### Command Reference

| Command | What it does | Mutates the system? |
| --- | --- | --- |
| `devops-toolkit doctor` | Checks readiness, config, OS support, logging, Slack, and package manager setup | No |
| `devops-toolkit report` | Builds a combined doctor, monitoring, and inventory report | No |
| `devops-toolkit report --full-audit` | Adds file permission, user/group, and cron audit details to the report | No |
| `devops-toolkit monitor` | Checks disk, CPU, memory, ports, processes, uptime, and listening ports | No |
| `devops-toolkit audit` | Collects inventory and audits users, files, and cron jobs | No |
| `devops-toolkit --dry-run patch` | Checks patch status without applying updates | No |
| `devops-toolkit patch` | Checks and applies OS package updates | Yes |
| `devops-toolkit run` | Runs patch management, monitoring, and audits according to config | Yes, when patch management is enabled |
| `devops-toolkit test` | Validates config, tests Slack, and runs dry-run checks | No |
| `devops-toolkit setup` | Writes a default config file under `/etc/devops_toolkit` | Yes |

## Configuration Reference

### Complete Configuration Example

```yaml
# Slack Notification Settings
slack:
  webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  enabled: true
  retry_attempts: 3
  retry_delay: 2

# Monitoring Configuration
monitoring:
  disk:
    enabled: true
    threshold_percent: 80
    paths: [/, /home, /var]

  cpu:
    enabled: true
    threshold_percent: 80
    check_interval: 5

  memory:
    enabled: true
    threshold_percent: 80

  ports:
    enabled: true
    check_ports: [22, 80, 443, 3306, 5432]

  processes:
    enabled: true
    watch_processes: [nginx, apache2, mysql, postgresql, docker]

# Maintenance Settings
maintenance:
  patch_management:
    enabled: true
    auto_reboot: false
    reboot_time: "03:00"

  services:
    restart_retry_count: 3
    restart_retry_delay: 5

# Audit Settings
audit:
  file_permissions:
    enabled: true
    scan_paths: [/etc, /var/www, /opt]
    exclude_paths: [/proc, /sys, /dev, /run]

  user_audit:
    enabled: true

  cron_audit:
    enabled: true

# Logging Configuration
logging:
  log_file: /var/log/devops_toolkit.log
  log_level: INFO
  max_bytes: 10485760 # 10MB
  backup_count: 5
```

## Module Details

### 1. Patch Management

**Features:**

- Automatic OS detection (Ubuntu/RHEL)
- Update checking and application
- Reboot requirement detection
- Slack notifications for all outcomes

**Ubuntu/Debian:**

```bash
apt update && apt upgrade -y
```

**RHEL/CentOS:**

```bash
yum update -y  # or dnf update -y
```

**Reboot Detection:**

- Ubuntu: Checks `/var/run/reboot-required`
- RHEL: Uses `needs-restarting -r` command

### 2. System Monitoring

**Disk Usage:**

- Monitors configured paths
- Alerts when usage exceeds threshold
- Reports total, used, free space in GB

**CPU Usage:**

- Overall and per-core usage
- Load averages (1, 5, 15 min)
- Configurable check interval

**Memory Usage:**

- RAM and swap monitoring
- Available memory tracking
- Threshold-based alerts

**Uptime:**

- System uptime reporting
- Boot timestamp tracking

### 3. Network Monitoring

**Port Monitoring:**

- Checks if configured ports are accessible
- Alerts on closed/unreachable ports
- Lists all listening ports on system

**Process Monitoring:**

- Verifies critical processes are running
- Counts process instances
- Critical alerts for missing processes

### 4. System Auditing

**System Inventory:**

- Hostname, OS version, architecture
- CPU cores (physical/logical)
- Total RAM and disk space
- Network interfaces and IP addresses

**User & Group Audit:**

- Lists all system users with UIDs
- Lists all groups and members
- Parses `/etc/passwd` and `/etc/group`

### 5. DevOps Doctor

Run a non-mutating production readiness check before installing, scheduling, or opening a pull request:

```bash
devops-toolkit doctor
devops-toolkit doctor --format json
devops-toolkit doctor --format json --fail-on-warning
```

Doctor validates Python runtime support, configuration health, OS and package manager readiness, disk monitoring paths, logging permissions, Slack alerting, and patch management settings. The JSON mode is designed for GitHub Actions and other CI systems.

**File Permissions Audit:**

- Scans configured paths for security issues
- Detects world-writable files/directories
- Configurable exclusion paths
- Security vulnerability detection

**Cron Job Audit:**

- Lists system crontab entries
- Scans `/etc/cron.d/` directory
- Lists user crontabs
- Detects malformed entries

## Slack Notifications

### Severity Levels

- **INFO** (Green): Normal operations, successful updates
- **WARNING** (Orange): Threshold exceeded, attention needed
- **CRITICAL** (Red): Service down, critical issues

### Notification Format

Each notification includes:

- Hostname
- Timestamp
- Module name
- Severity level
- Detailed information
- Color-coded for quick identification

### Setting Up Slack Webhook

1. Go to your Slack workspace
2. Navigate to Apps → Incoming Webhooks
3. Create a new webhook
4. Copy the webhook URL
5. Add to configuration file

## Cron Setup

### Automated Scheduling

The installer can configure cron jobs automatically. Manual setup:

```bash
# Daily at 2:00 AM
0 2 * * * /usr/local/bin/devops-toolkit run >> /var/log/devops_toolkit.log 2>&1

# Every 6 hours
0 */6 * * * /usr/local/bin/devops-toolkit run >> /var/log/devops_toolkit.log 2>&1

# Weekly on Sunday at 2:00 AM
0 2 * * 0 /usr/local/bin/devops-toolkit run >> /var/log/devops_toolkit.log 2>&1
```

### Monitoring Only (More Frequent)

```bash
# Every hour - monitoring only
0 * * * * /usr/local/bin/devops-toolkit monitor >> /var/log/devops_toolkit.log 2>&1
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/sameeralam3127/devops-toolkit.git
cd devops-toolkit

# Install with development dependencies
make install-dev

# Or using uv (faster)
make install-uv
```

### Available Make Commands

```bash
make help           # Show all available commands
make install        # Install production dependencies
make install-dev    # Install development dependencies
make test           # Run tests with coverage
make lint           # Run all linters
make format         # Format code with black and ruff
make check          # Run all checks (format, lint, test)
make pre-commit     # Install pre-commit hooks
make clean          # Clean build artifacts
```

### Code Quality Tools

This project uses modern Python tooling:

- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **Pylint**: Code analysis
- **Bandit**: Security checks
- **Mypy**: Type checking
- **Pytest**: Testing framework
- **Pre-commit**: Git hooks for code quality

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
pytest tests/test_config_loader.py -v

# Run with coverage report
pytest --cov=app --cov-report=html
```

If your workstation has the `pytest-ansible` plugin installed globally and tests fail while trying to write under your home directory, set a writable Ansible temp directory:

```bash
make test ANSIBLE_LOCAL_TEMP=/tmp
```

### Code Formatting

```bash
# Format all code
make format

# Check formatting without changes
black --check app tests
```

### Linting

```bash
# Run all linters
make lint

# Run specific linter
ruff check app
pylint app
bandit -r app
```

## Advanced Usage

### Custom Configuration Path

```bash
devops-toolkit --config /path/to/custom/config.yaml run
```

### Test Mode

Test configuration and Slack connection without making changes:

```bash
devops-toolkit test
```

Output includes:

- Configuration validation
- Slack connection test
- Dry-run of all checks
- Summary report

### Dry-Run Mode

Run patch management without applying changes:

```bash
devops-toolkit --dry-run patch
```

### Service Management (Python API)

```python
from app.maintenance.service_manager import ServiceManager
from app.core.notifier import SlackNotifier

notifier = SlackNotifier(webhook_url='...')
service_mgr = ServiceManager(notifier)

# Restart a service
success, message = service_mgr.restart_service('nginx')

# Get service status
is_active, status = service_mgr.get_service_status('nginx')
```

## Logging

### Log Location

Default: `/var/log/devops_toolkit.log`

### Log Format

```
2024-01-15 14:30:45 - devops_toolkit - INFO - patch_manager:apply_updates:125 - Starting system update process
```

### Log Rotation

- Maximum size: 10MB (configurable)
- Backup count: 5 files (configurable)
- Automatic rotation when size exceeded

### Viewing Logs

```bash
# View recent logs
tail -f /var/log/devops_toolkit.log

# Search for errors
grep ERROR /var/log/devops_toolkit.log

# View specific module logs
grep "patch_manager" /var/log/devops_toolkit.log
```

## Security Considerations

1. **Root Access**: Required for system operations
2. **Slack Webhook**: Keep webhook URL secure
3. **File Permissions**: Config file should be readable only by root
4. **Audit Logs**: Review regularly for security issues
5. **World-Writable Files**: Address findings from file permission audits

### Securing Configuration

```bash
sudo chmod 600 /etc/devops_toolkit/config.yaml
sudo chown root:root /etc/devops_toolkit/config.yaml
```

## Troubleshooting

### Common Issues

**1. Permission Denied**

```bash
# Run with sudo
sudo devops-toolkit run
```

For read-only checks, try a command that does not need package-manager access:

```bash
devops-toolkit doctor
devops-toolkit report
```

**2. Slack Notifications Not Working**

- Verify webhook URL in config
- Test connection: `devops-toolkit test`
- Check network connectivity
- Temporarily set `slack.enabled: false` if you want to test the rest of the toolkit without Slack

**3. Module Not Found**

```bash
# Reinstall dependencies
sudo pip3 install -r requirements.txt
```

If you installed from a clone, reinstall the package in your active virtual environment:

```bash
pip install -e .
```

**4. Cron Job Not Running**

```bash
# Check cron logs
grep devops-toolkit /var/log/syslog

# Verify cron entry
crontab -l | grep devops-toolkit
```

## Uninstallation

```bash
sudo bash uninstall.sh
```

The uninstaller will:

- Remove cron jobs
- Remove installation files
- Optionally remove configuration
- Optionally remove logs
- Optionally remove Python dependencies

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please ensure:

- Code follows PEP 8 style guidelines
- All modules include proper error handling
- Documentation is updated
- Tests pass successfully

## Support

For issues, questions, or contributions:

- Check logs: `/var/log/devops_toolkit.log`
- Run test mode: `devops-toolkit test`
- Review configuration: `/etc/devops_toolkit/config.yaml`

## Best Practices

1. **Start with Test Mode**: Always test before production use
2. **Configure Thresholds**: Adjust based on your environment
3. **Monitor Slack Alerts**: Set up appropriate channels
4. **Regular Audits**: Run audits weekly or monthly
5. **Review Logs**: Check logs regularly for issues
6. **Backup Configuration**: Keep config backups
7. **Update Regularly**: Keep toolkit and dependencies updated

## Example Workflows

### Daily Monitoring

```bash
# Cron: Every 6 hours
0 */6 * * * /usr/local/bin/devops-toolkit monitor
```

### Weekly Maintenance

```bash
# Cron: Sunday at 2 AM
0 2 * * 0 /usr/local/bin/devops-toolkit run
```

### Monthly Audits

```bash
# Cron: First day of month at 3 AM
0 3 1 * * /usr/local/bin/devops-toolkit audit
```

---

**DevOps Toolkit** - Production-ready system monitoring and maintenance for Linux servers.
