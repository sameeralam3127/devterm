"""
Tests for CLI health report generation
"""

import json
from unittest.mock import Mock, patch

from app.cli import DevOpsToolkit


def _toolkit(mock_notifier):
    toolkit = DevOpsToolkit.__new__(DevOpsToolkit)
    toolkit.config = Mock()
    toolkit.notifier = mock_notifier
    toolkit.logger = Mock()
    toolkit.run_monitor = Mock(
        return_value={
            "disk": {"ok": True},
            "system": {"all_ok": True},
            "network": {"all_ok": True},
        }
    )
    toolkit.run_audit = Mock()
    return toolkit


def _doctor_report(status="pass"):
    return {
        "score": 100 if status == "pass" else 72,
        "status": status,
        "status_counts": {"pass": 1, "warn": 0, "fail": 0},
        "checks": [],
    }


def _inventory():
    return {
        "hostname": "test-host",
        "os_info": {"os_name": "Ubuntu"},
        "cpu": {"logical_cores": 4},
        "memory": {"total_gb": 8},
    }


def test_build_report_collects_doctor_monitor_and_inventory(mock_notifier):
    """Default report should collect inventory without running full audits."""
    toolkit = _toolkit(mock_notifier)

    with patch("app.cli.DevOpsDoctor") as doctor_cls, patch(
        "app.cli.SystemAuditor"
    ) as auditor_cls:
        doctor_cls.return_value.run.return_value = _doctor_report()
        auditor_cls.return_value.collect_inventory.return_value = _inventory()

        report = toolkit.build_report()

    assert report["overall_status"] == "pass"
    assert report["doctor"]["score"] == 100
    assert report["audit"]["inventory"]["hostname"] == "test-host"
    toolkit.run_monitor.assert_called_once()
    toolkit.run_audit.assert_not_called()


def test_build_report_can_include_full_audit(mock_notifier):
    """Full report mode should reuse the existing full audit flow."""
    toolkit = _toolkit(mock_notifier)
    toolkit.run_audit.return_value = {"inventory": _inventory(), "cron": {"issues": []}}

    with patch("app.cli.DevOpsDoctor") as doctor_cls:
        doctor_cls.return_value.run.return_value = _doctor_report()
        report = toolkit.build_report(full_audit=True)

    assert report["full_audit"] is True
    assert report["audit"]["cron"]["issues"] == []
    toolkit.run_audit.assert_called_once()


def test_report_status_warns_when_monitoring_is_unhealthy(mock_notifier):
    """Monitor failures should produce a warning report status."""
    toolkit = _toolkit(mock_notifier)

    status = toolkit._report_status(
        _doctor_report("pass"), {"disk": {"ok": False}, "system": {"all_ok": True}}
    )

    assert status == "warn"


def test_run_report_outputs_json(mock_notifier, capsys):
    """JSON report output should be parseable for automation."""
    toolkit = _toolkit(mock_notifier)
    toolkit.build_report = Mock(
        return_value={
            "generated_at": "2026-05-26T12:00:00+05:30",
            "overall_status": "pass",
            "doctor": _doctor_report(),
            "monitor": {},
            "audit": {"inventory": _inventory()},
            "full_audit": False,
        }
    )

    success = toolkit.run_report(output_format="json")

    payload = json.loads(capsys.readouterr().out)
    assert success is True
    assert payload["overall_status"] == "pass"
    assert payload["audit"]["inventory"]["hostname"] == "test-host"


def test_run_report_writes_json_output_file(mock_notifier, tmp_path, capsys):
    """Report output can be written to a file for CI artifacts or cron jobs."""
    toolkit = _toolkit(mock_notifier)
    toolkit.build_report = Mock(
        return_value={
            "generated_at": "2026-05-26T12:00:00+05:30",
            "overall_status": "pass",
            "doctor": _doctor_report(),
            "monitor": {},
            "audit": {"inventory": _inventory()},
            "full_audit": False,
        }
    )
    output_path = tmp_path / "reports" / "health.json"

    success = toolkit.run_report(output_format="json", output_path=output_path)

    payload = json.loads(output_path.read_text())
    assert success is True
    assert payload["overall_status"] == "pass"
    assert "Report written to" in capsys.readouterr().out


def test_render_report_text_includes_full_audit_summary(mock_notifier):
    """Text report should include compact full-audit details when requested."""
    toolkit = _toolkit(mock_notifier)
    rendered = toolkit.render_report_text(
        {
            "generated_at": "2026-05-26T12:00:00+05:30",
            "overall_status": "warn",
            "doctor": _doctor_report("warn"),
            "monitor": {"disk": {"ok": True}},
            "audit": {
                "inventory": _inventory(),
                "file_permissions": {"ok": False},
                "users": {"user_count": 12},
                "cron": {"issues": ["bad entry"]},
            },
            "full_audit": True,
        }
    )

    assert "Overall status: WARN" in rendered
    assert "Hostname: test-host" in rendered
    assert "File permissions OK: False" in rendered
    assert "Cron issues: 1" in rendered
