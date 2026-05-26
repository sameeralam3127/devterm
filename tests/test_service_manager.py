"""
Tests for service management utilities
"""

from unittest.mock import call, patch

from app.maintenance.service_manager import ServiceManager


def test_get_service_status_uses_argument_list(mock_notifier):
    """Service status checks should avoid shell interpolation."""
    with patch(
        "app.maintenance.service_manager.CommandExecutor.run",
        return_value=(True, "active\n", "", 0),
    ) as run:
        is_active, status = ServiceManager(mock_notifier).get_service_status("nginx")

    assert is_active is True
    assert status == "active"
    run.assert_called_once_with(
        ["systemctl", "is-active", "nginx"], timeout=10, check=False
    )


def test_get_service_status_rejects_invalid_service_name(mock_notifier):
    """Invalid service names should not be passed to systemctl."""
    with patch("app.maintenance.service_manager.CommandExecutor.run") as run:
        is_active, status = ServiceManager(mock_notifier).get_service_status("--help")

    assert is_active is False
    assert status == "unknown"
    run.assert_not_called()


def test_restart_service_retries_then_notifies_success(mock_notifier):
    """Restart should retry failed attempts and notify when verification passes."""
    service = ServiceManager(mock_notifier, retry_count=2, retry_delay=0)

    with patch(
        "app.maintenance.service_manager.CommandExecutor.run",
        side_effect=[
            (False, "", "boom", 1),
            (True, "", "", 0),
            (True, "active\n", "", 0),
        ],
    ) as run, patch("app.maintenance.service_manager.time.sleep"):
        success, message = service.restart_service("nginx")

    assert success is True
    assert "successfully" in message
    assert run.call_args_list == [
        call(["systemctl", "restart", "nginx"], timeout=60, check=False),
        call(["systemctl", "restart", "nginx"], timeout=60, check=False),
        call(["systemctl", "is-active", "nginx"], timeout=10, check=False),
    ]
    mock_notifier.send_info.assert_called_once()
