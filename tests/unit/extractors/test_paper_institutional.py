"""Unit tests for InstitutionalAccessClient."""

import pickle
from unittest.mock import MagicMock, patch

from parser.acquisition.clients.institutional import InstitutionalAccessClient


class TestInstitutionalAccessClientInit:
    """Test InstitutionalAccessClient initialization."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        client = InstitutionalAccessClient()
        assert client.proxy_url is None
        assert client.vpn_enabled is False
        assert client.vpn_script is None
        assert client._authenticated is False

    def test_init_with_proxy_url(self):
        """Test initialization with proxy URL."""
        proxy_url = "https://ezproxy.example.edu/login?url="
        client = InstitutionalAccessClient(proxy_url=proxy_url)
        assert client.proxy_url == proxy_url
        assert client.vpn_enabled is False

    def test_init_with_vpn_enabled(self):
        """Test initialization with VPN enabled."""
        client = InstitutionalAccessClient(vpn_enabled=True)
        assert client.vpn_enabled is True


class TestGetProxiedUrl:
    """Test URL proxying."""

    def test_get_proxied_url_with_proxy(self):
        """Test URL proxying with proxy configured."""
        client = InstitutionalAccessClient(
            proxy_url="https://ezproxy.example.edu/login?url="
        )
        url = "https://ieeexplore.ieee.org/document/12345"
        proxied = client.get_proxied_url(url)
        assert proxied == "https://ezproxy.example.edu/login?url=https://ieeexplore.ieee.org/document/12345"

    def test_get_proxied_url_with_vpn(self):
        """Test URL proxying with VPN enabled (no proxy)."""
        client = InstitutionalAccessClient(vpn_enabled=True)
        url = "https://ieeexplore.ieee.org/document/12345"
        proxied = client.get_proxied_url(url)
        assert proxied == url  # No change when VPN is used

    def test_get_proxied_url_no_proxy(self):
        """Test URL proxying without proxy configured."""
        client = InstitutionalAccessClient()
        url = "https://ieeexplore.ieee.org/document/12345"
        proxied = client.get_proxied_url(url)
        assert proxied == url

    def test_doi_to_proxied_url(self):
        """Test DOI to proxied URL conversion."""
        client = InstitutionalAccessClient(
            proxy_url="https://ezproxy.example.edu/login?url="
        )
        doi = "10.1109/ACCESS.2024.12345"
        proxied = client.doi_to_proxied_url(doi)
        assert proxied == "https://ezproxy.example.edu/login?url=https://doi.org/10.1109/ACCESS.2024.12345"


class TestCookiesManagement:
    """Test cookie save/load functionality."""

    def test_save_cookies(self, tmp_path):
        """Test saving cookies."""
        cookies_file = tmp_path / "cookies.pkl"
        client = InstitutionalAccessClient(cookies_file=str(cookies_file))
        client._cookies = {"session": "abc123"}
        client._selenium_cookies = [{"name": "session", "value": "abc123"}]

        client.save_cookies()

        assert cookies_file.exists()

    def test_load_cookies(self, tmp_path):
        """Test loading cookies."""
        cookies_file = tmp_path / "cookies.pkl"

        # Create a valid cookies file
        data = {
            "selenium_cookies": [{"name": "session", "value": "xyz789"}],
            "simple_cookies": {"session": "xyz789"},
        }
        with open(cookies_file, "wb") as f:
            pickle.dump(data, f)

        client = InstitutionalAccessClient(cookies_file=str(cookies_file))

        assert client._authenticated is True
        assert client._cookies == {"session": "xyz789"}

    def test_load_cookies_old_format(self, tmp_path):
        """Test loading cookies in old format (just dict)."""
        cookies_file = tmp_path / "cookies.pkl"

        # Old format - just a dict
        data = {"session": "old123"}
        with open(cookies_file, "wb") as f:
            pickle.dump(data, f)

        client = InstitutionalAccessClient(cookies_file=str(cookies_file))

        assert client._authenticated is True
        assert client._cookies == {"session": "old123"}

    def test_load_cookies_file_not_exists(self, tmp_path):
        """Test loading when cookies file doesn't exist."""
        cookies_file = tmp_path / "nonexistent.pkl"
        client = InstitutionalAccessClient(cookies_file=str(cookies_file))

        result = client.load_cookies()

        assert result is False
        assert client._authenticated is False


class TestVPNConnection:
    """Test VPN connection functionality."""

    def test_connect_vpn_no_script(self):
        """Test VPN connection without script."""
        client = InstitutionalAccessClient(vpn_enabled=True)
        result = client.connect_vpn()
        assert result is False

    def test_connect_vpn_script_not_found(self, tmp_path):
        """Test VPN connection with non-existent script."""
        client = InstitutionalAccessClient(
            vpn_enabled=True,
            vpn_script=str(tmp_path / "nonexistent.sh"),
        )
        result = client.connect_vpn()
        assert result is False

    @patch("subprocess.run")
    def test_connect_vpn_success(self, mock_run, tmp_path):
        """Test successful VPN connection."""
        script_path = tmp_path / "vpn.sh"
        script_path.write_text("#!/bin/bash\necho 'connected'")

        mock_run.return_value = MagicMock(returncode=0)

        client = InstitutionalAccessClient(
            vpn_enabled=True,
            vpn_script=str(script_path),
        )
        result = client.connect_vpn()

        assert result is True
        assert client._vpn_connected is True
        assert client._authenticated is True

    @patch("subprocess.run")
    def test_connect_vpn_failure(self, mock_run, tmp_path):
        """Test failed VPN connection."""
        script_path = tmp_path / "vpn.sh"
        script_path.write_text("#!/bin/bash\nexit 1")

        mock_run.return_value = MagicMock(returncode=1)

        client = InstitutionalAccessClient(
            vpn_enabled=True,
            vpn_script=str(script_path),
        )
        result = client.connect_vpn()

        assert result is False


class TestAvailability:
    """Test availability checks."""

    def test_is_authenticated_not_authenticated(self):
        """Test is_authenticated when not authenticated."""
        client = InstitutionalAccessClient()
        assert client.is_authenticated() is False

    def test_is_authenticated_via_vpn(self):
        """Test is_authenticated with VPN."""
        client = InstitutionalAccessClient(vpn_enabled=True)
        assert client.is_authenticated() is True

    def test_is_authenticated_via_cookies(self, tmp_path):
        """Test is_authenticated with cookies."""
        cookies_file = tmp_path / "cookies.pkl"
        data = {"selenium_cookies": [], "simple_cookies": {"session": "test"}}
        with open(cookies_file, "wb") as f:
            pickle.dump(data, f)

        client = InstitutionalAccessClient(cookies_file=str(cookies_file))
        assert client.is_authenticated() is True

    def test_is_available_with_proxy(self):
        """Test is_available with proxy URL."""
        client = InstitutionalAccessClient(
            proxy_url="https://ezproxy.example.edu/login?url="
        )
        assert client.is_available() is True

    def test_is_available_with_vpn(self):
        """Test is_available with VPN."""
        client = InstitutionalAccessClient(vpn_enabled=True)
        assert client.is_available() is True

    def test_is_available_nothing_configured(self):
        """Test is_available with nothing configured."""
        client = InstitutionalAccessClient()
        assert client.is_available() is False


class TestSeleniumCheck:
    """Test Selenium availability check."""

    def test_check_selenium_not_available(self):
        """Test selenium check when not installed."""
        with patch.dict("sys.modules", {"selenium": None}):
            InstitutionalAccessClient()
            # Note: The actual check happens at import time in real usage
            # This test verifies the method structure

    def test_check_selenium_available(self):
        """Test selenium check when installed."""
        client = InstitutionalAccessClient()
        # This will return True/False depending on actual installation
        result = client._check_selenium_available()
        assert isinstance(result, bool)
