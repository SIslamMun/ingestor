"""Institutional access client using EZProxy and VPN.

Supports two modes for accessing papers via university subscriptions:
1. VPN mode: When connected to institutional VPN, direct access works
2. EZProxy mode: Uses proxy URL rewriting with browser-based authentication
"""

from __future__ import annotations

import asyncio
import pickle
import subprocess
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse


class InstitutionalAccessClient:
    """Client for accessing papers through institutional proxy (EZProxy).

    Supports two modes:
    1. VPN mode: When connected to institutional VPN, direct access works
    2. EZProxy mode: Uses proxy URL rewriting with Selenium authentication
    """

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        vpn_enabled: bool = False,
        vpn_script: Optional[str] = None,
        vpn_disconnect_script: Optional[str] = None,
        cookies_file: str = ".institutional_cookies.pkl",
        download_dir: str = "./downloads",
        rate_limit: float = 1.0,
    ):
        """Initialize the institutional access client.

        Args:
            proxy_url: EZProxy URL (e.g., "https://ezproxy.gl.iit.edu/login?url=")
            vpn_enabled: If True, assume VPN is connected and use direct access
            vpn_script: Path to script that connects to VPN (run during auth)
            vpn_disconnect_script: Path to script that disconnects VPN
            cookies_file: Path to save/load authentication cookies
            download_dir: Directory to save downloaded PDFs
            rate_limit: Seconds between requests
        """
        self.proxy_url = proxy_url
        self.vpn_enabled = vpn_enabled
        self.vpn_script = vpn_script
        self.vpn_disconnect_script = vpn_disconnect_script
        self.cookies_file = Path(cookies_file)
        self.download_dir = Path(download_dir)
        self.rate_limit = rate_limit
        self._cookies: dict[str, str] = {}
        self._selenium_cookies: list[dict] = []
        self._authenticated = False
        self._vpn_connected = False
        self._last_error: Optional[str] = None
        self._last_request: float = 0.0

        # Auto-load cookies if they exist
        if self.cookies_file.exists():
            self.load_cookies()

    async def _rate_limit(self) -> None:
        """Wait to respect rate limits."""
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def get_proxied_url(self, url: str) -> str:
        """Convert a URL to a proxied URL.

        Args:
            url: Original URL (e.g., DOI URL or publisher URL)

        Returns:
            Proxied URL if proxy is configured, otherwise original URL
        """
        if self.vpn_enabled:
            return url

        if self.proxy_url:
            return f"{self.proxy_url}{url}"

        return url

    def doi_to_proxied_url(self, doi: str) -> str:
        """Convert a DOI to a proxied publisher URL.

        Args:
            doi: The DOI to convert

        Returns:
            Proxied URL for the DOI
        """
        doi_url = f"https://doi.org/{doi}"
        return self.get_proxied_url(doi_url)

    def load_cookies(self) -> bool:
        """Load previously saved authentication cookies.

        Returns:
            True if cookies were loaded successfully
        """
        if not self.cookies_file.exists():
            return False

        try:
            with open(self.cookies_file, "rb") as f:
                data = pickle.load(f)

            # Handle both old format (dict) and new format (dict with selenium_cookies)
            if isinstance(data, dict) and "selenium_cookies" in data:
                self._selenium_cookies = data["selenium_cookies"]
                self._cookies = data["simple_cookies"]
            elif isinstance(data, dict):
                # Old format - just simple cookies
                self._cookies = data
                self._selenium_cookies = []
            else:
                return False

            self._authenticated = True
            return True
        except (pickle.PickleError, EOFError):
            return False

    def save_cookies(self) -> None:
        """Save authentication cookies for reuse."""
        data = {
            "selenium_cookies": self._selenium_cookies,
            "simple_cookies": self._cookies,
        }
        with open(self.cookies_file, "wb") as f:
            pickle.dump(data, f)

    def connect_vpn(self) -> bool:
        """Run the VPN connection script.

        Returns:
            True if VPN connected successfully (or no script configured)
        """
        if not self.vpn_script:
            print("No VPN script configured.")
            return False

        script_path = Path(self.vpn_script)
        if not script_path.exists():
            print(f"VPN script not found: {self.vpn_script}")
            return False

        print(f"\nRunning VPN script: {self.vpn_script}")
        print("=" * 60)

        try:
            # Run the script
            result = subprocess.run(
                [str(script_path)],
                shell=True,
                capture_output=False,  # Let output go to terminal for interactive scripts
                text=True,
            )

            if result.returncode == 0:
                print("=" * 60)
                print("VPN script completed successfully.")
                self._vpn_connected = True
                self._authenticated = True
                return True
            else:
                print("=" * 60)
                print(f"VPN script failed with exit code: {result.returncode}")
                return False

        except Exception as e:
            print(f"Error running VPN script: {e}")
            return False

    def disconnect_vpn(self) -> bool:
        """Run a VPN disconnect script if provided.

        Returns:
            True if disconnect was successful
        """
        if not self.vpn_disconnect_script:
            self._vpn_connected = False
            return True

        script_path = Path(self.vpn_disconnect_script)
        if not script_path.exists():
            print(f"Disconnect script not found: {self.vpn_disconnect_script}")
            return False

        try:
            result = subprocess.run(
                [str(script_path)],
                shell=True,
                capture_output=True,
                text=True,
            )
            self._vpn_connected = False
            return result.returncode == 0
        except Exception as e:
            print(f"Error running disconnect script: {e}")
            return False

    def _check_selenium_available(self) -> bool:
        """Check if Selenium is available."""
        try:
            from selenium import webdriver  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_available_browser(self) -> tuple[Any, str] | None:
        """Detect and return an available browser driver.

        Tries browsers in order: Chrome, Edge, Firefox.
        Returns the first one that works.

        Returns:
            Tuple of (driver, browser_name) or None if no browser available.
        """
        if not self._check_selenium_available():
            return None

        from selenium import webdriver

        browsers = [
            ("chrome", self._try_chrome),
            ("edge", self._try_edge),
            ("firefox", self._try_firefox),
        ]

        for name, try_func in browsers:
            try:
                driver = try_func(webdriver)
                if driver:
                    return driver, name
            except Exception:
                continue

        return None

    def _try_chrome(self, webdriver: Any) -> Any | None:
        """Try to create a Chrome driver."""
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        options = Options()
        options.add_argument("--start-maximized")

        # Try with webdriver-manager first
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
        except Exception:
            pass

        # Try without webdriver-manager
        try:
            return webdriver.Chrome(options=options)
        except Exception:
            return None

    def _try_edge(self, webdriver: Any) -> Any | None:
        """Try to create an Edge driver."""
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.edge.service import Service

        options = Options()
        options.add_argument("--start-maximized")

        # Try with webdriver-manager first
        try:
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            service = Service(EdgeChromiumDriverManager().install())
            return webdriver.Edge(service=service, options=options)
        except Exception:
            pass

        # Try without webdriver-manager
        try:
            return webdriver.Edge(options=options)
        except Exception:
            return None

    def _try_firefox(self, webdriver: Any) -> Any | None:
        """Try to create a Firefox driver."""
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service

        options = Options()

        # Try with webdriver-manager first
        try:
            from webdriver_manager.firefox import GeckoDriverManager
            service = Service(GeckoDriverManager().install())
            return webdriver.Firefox(service=service, options=options)
        except Exception:
            pass

        # Try without webdriver-manager
        try:
            return webdriver.Firefox(options=options)
        except Exception:
            return None

    def authenticate_interactive(self) -> bool:
        """Authenticate using an interactive browser session.

        Opens a browser window for the user to log in through their
        institution's SSO/Shibboleth system. Saves cookies for reuse.

        Returns:
            True if authentication was successful
        """
        if not self._check_selenium_available():
            raise ImportError(
                "Selenium is required for EZProxy authentication. "
                "Install with: pip install selenium webdriver-manager"
            )

        if not self.proxy_url:
            print("No proxy URL configured. Cannot authenticate.")
            return False

        print("\n" + "=" * 60)
        print("Institutional Authentication (EZProxy)")
        print("=" * 60)
        print("\nOpening browser for institutional login...")
        print("Please log in with your university credentials.")
        print("The browser will close automatically when done.")
        print()

        browser_result = self._get_available_browser()
        if not browser_result:
            print("No supported browser found (Chrome, Edge, or Firefox)")
            return False

        driver, browser_name = browser_result
        print(f"Using {browser_name} browser")

        try:
            # Navigate to a test URL through the proxy
            test_url = self.get_proxied_url("https://www.nature.com/")
            driver.get(test_url)

            print("\nWaiting for login to complete...")
            print("(The browser will close automatically after login)")

            # Wait for authentication - check for successful proxy session
            max_wait = 300  # 5 minutes
            check_interval = 2
            elapsed = 0

            while elapsed < max_wait:
                time.sleep(check_interval)
                elapsed += check_interval

                current_url = driver.current_url
                parsed = urlparse(current_url)

                # Check if we've passed through the proxy
                if "ezproxy" not in parsed.netloc.lower() and "login" not in current_url.lower():
                    # Likely authenticated
                    break

                # Check for common success indicators
                if any(x in current_url.lower() for x in ["nature.com", "ieee.org", "acm.org"]):
                    break

            # Save cookies
            self._selenium_cookies = driver.get_cookies()
            self._cookies = {c["name"]: c["value"] for c in self._selenium_cookies}
            self.save_cookies()

            self._authenticated = True
            print("\nAuthentication successful! Cookies saved.")
            return True

        except Exception as e:
            print(f"Authentication error: {e}")
            self._last_error = str(e)
            return False

        finally:
            try:
                driver.quit()
            except Exception:
                pass

    async def get_pdf_url(self, doi: str) -> Optional[str]:
        """Get PDF URL through institutional access.

        Args:
            doi: Paper DOI

        Returns:
            Proxied URL for accessing the paper, or None
        """
        if not self._authenticated and not self.vpn_enabled:
            return None

        await self._rate_limit()

        # Return the proxied DOI URL
        return self.doi_to_proxied_url(doi)

    async def download_pdf(
        self,
        doi: str,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Download a PDF through institutional access.

        Note: This requires Selenium for browser-based download due to
        JavaScript-heavy publisher sites.

        Args:
            doi: Paper DOI
            output_path: Where to save the PDF

        Returns:
            Path to downloaded PDF, or None if failed
        """
        if not self._authenticated and not self.vpn_enabled:
            print("Not authenticated. Run authenticate_interactive() first.")
            return None

        if not self._check_selenium_available():
            print("Selenium required for institutional downloads.")
            return None

        await self._rate_limit()

        # This would require a more complex implementation with
        # Selenium to handle JavaScript-based downloads
        # For now, return the URL and let the user handle it
        print(f"Institutional download requires browser access.")
        print(f"URL: {self.doi_to_proxied_url(doi)}")
        return None

    def is_authenticated(self) -> bool:
        """Check if we have valid authentication.

        Returns:
            True if authenticated (via cookies or VPN)
        """
        return self._authenticated or self.vpn_enabled

    def is_available(self) -> bool:
        """Check if institutional access is available.

        Returns:
            True if proxy URL or VPN is configured
        """
        return bool(self.proxy_url) or self.vpn_enabled

    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error
