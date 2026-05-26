"""
Tests for system audit utilities
"""

import os
from unittest.mock import patch

from app.audit.system_audit import SystemAuditor


def test_audit_file_permissions_finds_world_writable_file(tmp_path, mock_notifier):
    """World-writable files should be reported and trigger a warning."""
    watched = tmp_path / "watched"
    watched.mkdir()
    loose_file = watched / "loose.txt"
    loose_file.write_text("data")
    os.chmod(loose_file, 0o666)

    ok, results = SystemAuditor(mock_notifier).audit_file_permissions([str(watched)])

    assert ok is False
    assert results["world_writable_count"] == 1
    assert results["world_writable_files"][0]["path"] == str(loose_file)
    mock_notifier.send_warning.assert_called_once()


def test_audit_file_permissions_prunes_excluded_paths(tmp_path, mock_notifier):
    """Excluded directories should not be scanned or reported."""
    watched = tmp_path / "watched"
    excluded = watched / "excluded"
    excluded.mkdir(parents=True)
    loose_file = excluded / "loose.txt"
    loose_file.write_text("data")
    os.chmod(loose_file, 0o666)

    ok, results = SystemAuditor(mock_notifier).audit_file_permissions(
        [str(watched)], [str(excluded)]
    )

    assert ok is True
    assert results["world_writable_count"] == 0
    mock_notifier.send_warning.assert_not_called()


def test_audit_file_permissions_does_not_exclude_prefix_siblings(
    tmp_path, mock_notifier
):
    """A path that merely shares an excluded prefix should still be scanned."""
    watched = tmp_path / "watched"
    excluded = watched / "app"
    sibling = watched / "app-data"
    excluded.mkdir(parents=True)
    sibling.mkdir()
    loose_file = sibling / "loose.txt"
    loose_file.write_text("data")
    os.chmod(loose_file, 0o666)

    ok, results = SystemAuditor(mock_notifier).audit_file_permissions(
        [str(watched)], [str(excluded)]
    )

    assert ok is False
    assert results["world_writable_files"][0]["path"] == str(loose_file)


def test_audit_cron_jobs_quotes_usernames(mock_notifier):
    """User crontab shell commands should quote discovered usernames."""
    commands = []

    def fake_run_shell(command, timeout):
        commands.append(command)
        if command.startswith("ls "):
            return True, "normal\nbad;name\n", ""
        return True, "* * * * * echo ok\n", ""

    with patch("app.audit.system_audit.os.path.exists", return_value=False), patch(
        "app.audit.system_audit.CommandExecutor.run_shell",
        side_effect=fake_run_shell,
    ):
        audit = SystemAuditor(mock_notifier).audit_cron_jobs()

    assert set(audit["user_crontabs"]) == {"normal", "bad;name"}
    assert "crontab -u 'bad;name' -l" in commands[-1]
