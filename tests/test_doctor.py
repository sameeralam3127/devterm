"""
Tests for DevOps Toolkit doctor diagnostics
"""

from unittest.mock import patch

from app.config_loader import ConfigLoader
from app.doctor import DevOpsDoctor
from app.utils.system import OSType


def test_doctor_reports_pass_for_ready_configuration(temp_config_file):
    """Doctor should pass when the host and configuration are ready"""
    config = ConfigLoader(temp_config_file)
    doctor = DevOpsDoctor(config)

    with patch("app.doctor.SystemInfo.detect_os", return_value=OSType.UBUNTU), patch(
        "app.doctor.SystemInfo.get_os_info",
        return_value={"os_type": "ubuntu", "os_name": "Ubuntu"},
    ), patch("app.doctor.SystemInfo.get_package_manager", return_value="apt"), patch(
        "app.doctor.CommandExecutor.check_command_exists", return_value=True
    ), patch(
        "app.doctor.os.access", return_value=True
    ):
        report = doctor.run()

    assert report["status"] == "pass"
    assert report["score"] == 100
    assert report["status_counts"]["fail"] == 0


def test_doctor_fails_for_invalid_slack_and_missing_disk_path(temp_config_file):
    """Doctor should surface production-blocking configuration issues"""
    config = ConfigLoader(temp_config_file)
    config.config["slack"]["webhook_url"] = "not-a-webhook"
    config.config["monitoring"]["disk"]["paths"] = ["/definitely/missing/path"]
    doctor = DevOpsDoctor(config)

    with patch("app.doctor.SystemInfo.detect_os", return_value=OSType.UBUNTU), patch(
        "app.doctor.SystemInfo.get_os_info",
        return_value={"os_type": "ubuntu", "os_name": "Ubuntu"},
    ), patch("app.doctor.SystemInfo.get_package_manager", return_value="apt"), patch(
        "app.doctor.CommandExecutor.check_command_exists", return_value=True
    ), patch(
        "app.doctor.os.access", return_value=True
    ):
        report = doctor.run()

    failing_checks = {
        check["name"] for check in report["checks"] if check["status"] == "fail"
    }

    assert report["status"] == "fail"
    assert "Configuration" in failing_checks
    assert "Disk monitoring paths" in failing_checks


def test_doctor_json_renderer_returns_machine_readable_report(temp_config_file):
    """Doctor JSON output should include score and checks"""
    config = ConfigLoader(temp_config_file)
    doctor = DevOpsDoctor(config)
    rendered = doctor.render_json(
        {"score": 92, "status": "warn", "status_counts": {}, "checks": []}
    )

    assert '"score": 92' in rendered
    assert '"checks": []' in rendered
