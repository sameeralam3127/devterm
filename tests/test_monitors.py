"""
Tests for disk, system, and network monitors
"""

from collections import namedtuple
from unittest.mock import Mock, patch

from app.monitors.disk_monitor import DiskMonitor
from app.monitors.network_monitor import NetworkMonitor
from app.monitors.system_monitor import SystemMonitor


def test_disk_monitor_alerts_when_threshold_exceeded(mock_notifier):
    """Disk monitor should report unhealthy paths and send a warning."""
    usage = namedtuple("usage", "total used free percent")(
        100 * 1024**3, 91 * 1024**3, 9 * 1024**3, 91
    )

    with patch("app.monitors.disk_monitor.psutil.disk_usage", return_value=usage):
        ok, results = DiskMonitor(
            mock_notifier, threshold_percent=90
        ).check_disk_usage()

    assert ok is False
    assert results[0]["threshold_exceeded"] is True
    mock_notifier.send_warning.assert_called_once()


def test_disk_monitor_records_path_errors(mock_notifier):
    """Disk monitor should continue reporting when a path cannot be read."""
    with patch(
        "app.monitors.disk_monitor.psutil.disk_usage",
        side_effect=PermissionError("denied"),
    ):
        ok, results = DiskMonitor(
            mock_notifier, paths=["/restricted"]
        ).check_disk_usage()

    assert ok is False
    assert results == [{"path": "/restricted", "error": "denied"}]


def test_system_monitor_aggregates_cpu_memory_and_uptime(mock_notifier):
    """System monitor should combine the major health checks."""
    monitor = SystemMonitor(mock_notifier, cpu_check_interval=0)
    monitor.check_cpu_usage = Mock(return_value=(True, {"cpu_percent": 12}))
    monitor.check_memory_usage = Mock(return_value=(False, {"percent": 93}))
    monitor.get_uptime = Mock(return_value={"uptime_seconds": 42})

    stats = monitor.get_system_stats()

    assert stats["cpu_ok"] is True
    assert stats["memory_ok"] is False
    assert stats["all_ok"] is False
    assert stats["uptime"]["uptime_seconds"] == 42


def test_network_monitor_handles_processes_with_none_cmdline(mock_notifier):
    """Process matching should tolerate psutil returning a missing cmdline."""
    proc = Mock()
    proc.info = {"pid": 123, "name": "nginx", "cmdline": None}

    with patch("app.monitors.network_monitor.psutil.process_iter", return_value=[proc]):
        running, processes = NetworkMonitor(mock_notifier).check_process_running(
            "nginx"
        )

    assert running is True
    assert processes[0]["cmdline"] == ""


def test_network_monitor_reports_closed_ports(mock_notifier):
    """Closed watched ports should make network port checks unhealthy."""
    monitor = NetworkMonitor(mock_notifier, ports=[8080])
    monitor.check_port = Mock(return_value=False)

    ok, results = monitor.check_all_ports()

    assert ok is False
    assert results == [{"port": 8080, "status": "closed", "is_open": False}]
    mock_notifier.send_warning.assert_called_once()
