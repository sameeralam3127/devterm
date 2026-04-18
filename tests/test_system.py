"""
Tests for system utilities module
"""

from unittest.mock import MagicMock, patch

from app.devops_toolkit.utils.system import CommandExecutor, OSType, SystemInfo


class TestSystemInfo:
    """Test SystemInfo class"""

    @patch("platform.system")
    @patch("os.path.exists")
    @patch("builtins.open")
    def test_detect_ubuntu(self, mock_open, mock_exists, mock_platform):
        """Test Ubuntu OS detection"""
        mock_platform.return_value = "Linux"
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "ubuntu"

        os_type = SystemInfo.detect_os()
        assert os_type == OSType.UBUNTU

    @patch("platform.system")
    @patch("os.path.exists")
    @patch("builtins.open")
    def test_detect_rhel(self, mock_open, mock_exists, mock_platform):
        """Test RHEL OS detection"""
        mock_platform.return_value = "Linux"
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "rhel"

        os_type = SystemInfo.detect_os()
        assert os_type == OSType.RHEL

    @patch("platform.system")
    def test_detect_unknown_os(self, mock_platform):
        """Test unknown OS detection"""
        mock_platform.return_value = "Windows"
        os_type = SystemInfo.detect_os()
        assert os_type == OSType.UNKNOWN

    @patch("app.devops_toolkit.utils.system.SystemInfo.detect_os")
    def test_is_debian_based(self, mock_detect):
        """Test Debian-based OS check"""
        mock_detect.return_value = OSType.UBUNTU
        assert SystemInfo.is_debian_based() is True

        mock_detect.return_value = OSType.RHEL
        assert SystemInfo.is_debian_based() is False

    @patch("app.devops_toolkit.utils.system.SystemInfo.detect_os")
    def test_is_rhel_based(self, mock_detect):
        """Test RHEL-based OS check"""
        mock_detect.return_value = OSType.RHEL
        assert SystemInfo.is_rhel_based() is True

        mock_detect.return_value = OSType.UBUNTU
        assert SystemInfo.is_rhel_based() is False

    @patch("os.path.exists")
    @patch("app.devops_toolkit.utils.system.SystemInfo.is_debian_based")
    @patch("app.devops_toolkit.utils.system.SystemInfo.is_rhel_based")
    def test_get_package_manager_apt(self, mock_rhel, mock_debian, mock_exists):
        """Test getting apt package manager"""
        mock_debian.return_value = True
        mock_rhel.return_value = False

        pm = SystemInfo.get_package_manager()
        assert pm == "apt"

    @patch("os.path.exists")
    @patch("app.devops_toolkit.utils.system.SystemInfo.is_debian_based")
    @patch("app.devops_toolkit.utils.system.SystemInfo.is_rhel_based")
    def test_get_package_manager_dnf(self, mock_rhel, mock_debian, mock_exists):
        """Test getting dnf package manager"""
        mock_debian.return_value = False
        mock_rhel.return_value = True
        mock_exists.return_value = True

        pm = SystemInfo.get_package_manager()
        assert pm == "dnf"

    @patch("platform.node")
    @patch("platform.machine")
    @patch("app.devops_toolkit.utils.system.SystemInfo.detect_os")
    @patch("app.devops_toolkit.utils.system.SystemInfo.get_package_manager")
    def test_get_os_info(self, mock_pm, mock_detect, mock_machine, mock_node):
        """Test getting OS information"""
        mock_node.return_value = "testhost"
        mock_machine.return_value = "x86_64"
        mock_detect.return_value = OSType.UBUNTU
        mock_pm.return_value = "apt"

        info = SystemInfo.get_os_info()
        assert info["hostname"] == "testhost"
        assert info["architecture"] == "x86_64"
        assert info["os_type"] == "ubuntu"
        assert info["package_manager"] == "apt"


class TestCommandExecutor:
    """Test CommandExecutor class"""

    @patch("subprocess.run")
    def test_run_success(self, mock_run):
        """Test successful command execution"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        success, stdout, stderr, code = CommandExecutor.run(["echo", "test"])
        assert success is True
        assert stdout == "Success"
        assert code == 0

    @patch("subprocess.run")
    def test_run_failure(self, mock_run):
        """Test failed command execution"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error"
        mock_run.return_value = mock_result

        success, stdout, stderr, code = CommandExecutor.run(["false"], check=False)
        assert success is False
        assert code == 1

    @patch("subprocess.run")
    def test_run_timeout(self, mock_run):
        """Test command timeout"""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 1)

        success, stdout, stderr, code = CommandExecutor.run(["sleep", "10"], timeout=1)
        assert success is False
        assert "timed out" in stderr.lower()
        assert code == -1

    @patch("subprocess.run")
    def test_run_shell(self, mock_run):
        """Test shell command execution"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Shell output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        success, stdout, stderr = CommandExecutor.run_shell("echo test")
        assert success is True
        assert stdout == "Shell output"

    @patch("subprocess.run")
    def test_check_command_exists_true(self, mock_run):
        """Test checking if command exists - true"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        exists = CommandExecutor.check_command_exists("ls")
        assert exists is True

    @patch("subprocess.run")
    def test_check_command_exists_false(self, mock_run):
        """Test checking if command exists - false"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        exists = CommandExecutor.check_command_exists("nonexistent")
        assert exists is False


# Made with Bob
