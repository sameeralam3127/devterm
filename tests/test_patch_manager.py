"""
Tests for patch management behavior
"""

from unittest.mock import patch

from app.maintenance.patch_manager import PatchManager
from app.utils.system import OSType


def _manager(mock_notifier, os_type=OSType.UBUNTU, package_manager="apt"):
    with patch(
        "app.maintenance.patch_manager.SystemInfo.detect_os", return_value=os_type
    ), patch(
        "app.maintenance.patch_manager.SystemInfo.get_package_manager",
        return_value=package_manager,
    ):
        return PatchManager(mock_notifier)


def test_debian_update_check_counts_upgradable_packages(mock_notifier):
    """Debian update checks should parse apt output without shell pipelines."""
    manager = _manager(mock_notifier)

    with patch(
        "app.maintenance.patch_manager.CommandExecutor.run",
        side_effect=[
            (True, "updated", "", 0),
            (
                True,
                "Listing... Done\nopenssl/stable 1 amd64 [upgradable from: 0]\n",
                "",
                0,
            ),
        ],
    ) as run:
        success, count, message = manager._check_updates_debian()

    assert success is True
    assert count == 1
    assert message == "1 updates available"
    assert run.call_args_list[0].args[0] == ["apt-get", "update"]
    assert run.call_args_list[1].args[0] == ["apt", "list", "--upgradable"]


def test_rhel_update_check_treats_exit_100_as_updates_available(mock_notifier):
    """dnf/yum exit code 100 means updates are available, not command failure."""
    manager = _manager(mock_notifier, os_type=OSType.RHEL, package_manager="dnf")

    with patch(
        "app.maintenance.patch_manager.CommandExecutor.run",
        return_value=(False, "bash.x86_64 1.0 repo\ncurl.x86_64 2.0 repo\n", "", 100),
    ):
        success, count, message = manager._check_updates_rhel()

    assert success is True
    assert count == 2
    assert message == "2 updates available"


def test_apply_updates_in_dry_run_does_not_check_system(mock_notifier):
    """Dry-run mode should avoid invoking package commands."""
    manager = _manager(mock_notifier)
    manager.dry_run = True

    with patch("app.maintenance.patch_manager.CommandExecutor.run") as run:
        success, message, details = manager.apply_updates()

    assert success is True
    assert message == "Dry run - no updates applied"
    assert details == {}
    run.assert_not_called()
