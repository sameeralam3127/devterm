"""
Pytest configuration and fixtures for DevOps Toolkit tests
"""

import os
import tempfile
from unittest.mock import Mock, MagicMock
import pytest


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        'slack': {
            'webhook_url': 'https://hooks.slack.com/services/TEST/WEBHOOK/URL',
            'enabled': True,
            'retry_attempts': 3,
            'retry_delay': 1
        },
        'monitoring': {
            'disk': {
                'enabled': True,
                'threshold_percent': 80,
                'paths': ['/']
            },
            'cpu': {
                'enabled': True,
                'threshold_percent': 80,
                'check_interval': 1
            },
            'memory': {
                'enabled': True,
                'threshold_percent': 80
            },
            'ports': {
                'enabled': True,
                'check_ports': [22, 80, 443]
            },
            'processes': {
                'enabled': True,
                'watch_processes': ['test_process']
            }
        },
        'maintenance': {
            'patch_management': {
                'enabled': True,
                'auto_reboot': False
            },
            'services': {
                'restart_retry_count': 3,
                'restart_retry_delay': 1
            }
        },
        'audit': {
            'file_permissions': {
                'enabled': True,
                'scan_paths': ['/tmp'],
                'exclude_paths': ['/proc', '/sys']
            },
            'user_audit': {
                'enabled': True
            },
            'cron_audit': {
                'enabled': True
            }
        },
        'logging': {
            'log_file': '/tmp/test_devops_toolkit.log',
            'log_level': 'INFO',
            'max_bytes': 1048576,
            'backup_count': 3
        }
    }


@pytest.fixture
def mock_notifier():
    """Mock Slack notifier for testing"""
    notifier = Mock()
    notifier.send = Mock(return_value=True)
    notifier.send_info = Mock(return_value=True)
    notifier.send_warning = Mock(return_value=True)
    notifier.send_critical = Mock(return_value=True)
    notifier.test_connection = Mock(return_value=(True, "Test successful"))
    return notifier


@pytest.fixture
def temp_config_file(mock_config):
    """Create a temporary config file for testing"""
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(mock_config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    logger.exception = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess execution"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""
    return mock_result


@pytest.fixture
def mock_subprocess_failure():
    """Mock failed subprocess execution"""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Error occurred"
    return mock_result

# Made with Bob
