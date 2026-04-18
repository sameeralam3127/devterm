"""
Tests for configuration loader module
"""

import os
import tempfile
import pytest
import yaml
from app.devops_toolkit.config_loader import ConfigLoader


class TestConfigLoader:
    """Test ConfigLoader class"""

    def test_load_default_config(self):
        """Test loading default configuration"""
        config = ConfigLoader('/nonexistent/path.yaml')
        assert config.get('slack.enabled') is True
        assert config.get('monitoring.disk.threshold_percent') == 80

    def test_load_custom_config(self, temp_config_file):
        """Test loading custom configuration"""
        config = ConfigLoader(temp_config_file)
        assert config.get('slack.webhook_url') is not None
        assert config.get('monitoring.cpu.enabled') is True

    def test_get_with_dot_notation(self, temp_config_file):
        """Test getting config values with dot notation"""
        config = ConfigLoader(temp_config_file)
        assert config.get('slack.enabled') is True
        assert config.get('monitoring.disk.threshold_percent') == 80

    def test_get_with_default(self):
        """Test getting config with default value"""
        config = ConfigLoader()
        assert config.get('nonexistent.key', 'default') == 'default'

    def test_validate_valid_config(self, temp_config_file):
        """Test validation of valid configuration"""
        config = ConfigLoader(temp_config_file)
        is_valid, errors = config.validate()
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_webhook(self):
        """Test validation with invalid webhook"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'slack': {
                    'webhook_url': 'invalid_url',
                    'enabled': True
                }
            }, f)
            temp_path = f.name

        try:
            config = ConfigLoader(temp_path)
            is_valid, errors = config.validate()
            assert is_valid is False
            assert len(errors) > 0
        finally:
            os.unlink(temp_path)

    def test_validate_invalid_threshold(self):
        """Test validation with invalid threshold"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'monitoring': {
                    'disk': {
                        'threshold_percent': 150
                    }
                }
            }, f)
            temp_path = f.name

        try:
            config = ConfigLoader(temp_path)
            is_valid, errors = config.validate()
            assert is_valid is False
            assert any('threshold' in err.lower() for err in errors)
        finally:
            os.unlink(temp_path)

    def test_get_all(self, temp_config_file):
        """Test getting all configuration"""
        config = ConfigLoader(temp_config_file)
        all_config = config.get_all()
        assert isinstance(all_config, dict)
        assert 'slack' in all_config
        assert 'monitoring' in all_config

    def test_create_default_config(self):
        """Test creating default configuration file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.yaml')
            success = ConfigLoader.create_default_config(config_path)
            assert success is True
            assert os.path.exists(config_path)

            # Verify content
            with open(config_path, 'r') as f:
                content = yaml.safe_load(f)
                assert 'slack' in content
                assert 'monitoring' in content

    def test_merge_configs(self):
        """Test configuration merging"""
        config = ConfigLoader()
        default = {'a': 1, 'b': {'c': 2}}
        user = {'b': {'d': 3}, 'e': 4}
        merged = config._merge_configs(default, user)
        assert merged['a'] == 1
        assert merged['b']['c'] == 2
        assert merged['b']['d'] == 3
        assert merged['e'] == 4

# Made with Bob
