"""
Tests for Slack notifier module
"""

from unittest.mock import Mock, patch
import pytest
from app.devops_toolkit.core.notifier import SlackNotifier, Severity


class TestSlackNotifier:
    """Test SlackNotifier class"""

    def test_init(self):
        """Test notifier initialization"""
        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=True,
            retry_attempts=3,
            retry_delay=2
        )
        assert notifier.webhook_url == 'https://hooks.slack.com/test'
        assert notifier.enabled is True
        assert notifier.retry_attempts == 3

    def test_send_disabled(self):
        """Test sending when notifications are disabled"""
        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=False
        )
        result = notifier.send("Test message")
        assert result is True

    @patch('requests.post')
    def test_send_success(self, mock_post):
        """Test successful message sending"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=True
        )
        result = notifier.send("Test message", Severity.INFO)
        assert result is True
        assert mock_post.called

    @patch('requests.post')
    def test_send_failure(self, mock_post):
        """Test failed message sending"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=True,
            retry_attempts=1
        )
        result = notifier.send("Test message")
        assert result is False

    @patch('requests.post')
    def test_send_with_retry(self, mock_post):
        """Test message sending with retry logic"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=True,
            retry_attempts=3,
            retry_delay=0.1
        )
        result = notifier.send("Test message")
        assert result is False
        assert mock_post.call_count == 3

    def test_build_payload(self):
        """Test payload building"""
        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=True
        )
        payload = notifier._build_payload(
            "Test message",
            Severity.WARNING,
            "Test Module",
            {'key': 'value'}
        )
        assert 'attachments' in payload
        assert len(payload['attachments']) > 0
        assert payload['attachments'][0]['text'] == "Test message"

    @patch('requests.post')
    def test_test_connection_success(self, mock_post):
        """Test connection testing - success"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=True
        )
        success, message = notifier.test_connection()
        assert success is True
        assert "successful" in message.lower()

    def test_test_connection_disabled(self):
        """Test connection testing when disabled"""
        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=False
        )
        success, message = notifier.test_connection()
        assert success is False
        assert "disabled" in message.lower()

    def test_test_connection_no_webhook(self):
        """Test connection testing without webhook URL"""
        notifier = SlackNotifier(webhook_url='', enabled=True)
        success, message = notifier.test_connection()
        assert success is False
        assert "not configured" in message.lower()

    @patch('requests.post')
    def test_send_info(self, mock_post):
        """Test sending INFO level message"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=True
        )
        result = notifier.send_info("Info message")
        assert result is True

    @patch('requests.post')
    def test_send_warning(self, mock_post):
        """Test sending WARNING level message"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=True
        )
        result = notifier.send_warning("Warning message")
        assert result is True

    @patch('requests.post')
    def test_send_critical(self, mock_post):
        """Test sending CRITICAL level message"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        notifier = SlackNotifier(
            webhook_url='https://hooks.slack.com/test',
            enabled=True
        )
        result = notifier.send_critical("Critical message")
        assert result is True

    def test_severity_colors(self):
        """Test severity color mapping"""
        assert Severity.INFO in SlackNotifier.SEVERITY_COLORS
        assert Severity.WARNING in SlackNotifier.SEVERITY_COLORS
        assert Severity.CRITICAL in SlackNotifier.SEVERITY_COLORS

    def test_severity_emojis(self):
        """Test severity emoji mapping"""
        assert Severity.INFO in SlackNotifier.SEVERITY_EMOJIS
        assert Severity.WARNING in SlackNotifier.SEVERITY_EMOJIS
        assert Severity.CRITICAL in SlackNotifier.SEVERITY_EMOJIS

# Made with Bob
