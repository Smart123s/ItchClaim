# The MIT License (MIT)
#
# Copyright (c) 2022-2025 Péter Tombor.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""FlareSolverr wrapper for requests."""

from urllib.parse import unquote
import requests

from .flaresolverr import flaresolverr

from . import __version__

CF_ALWAYS_PROTECTED_URL = "https://itch.io/login"


class CfWrapper:
    """A wrapper around requests to handle Cloudflare protection using FlareSolverr.
    Singleton class to maintain a single session.
    """

    _instance = None
    flaresolverr_initialized = False
    session: requests.Session

    # Singleton pattern implementation
    # https://python-patterns.guide/gang-of-four/singleton/
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CfWrapper, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Check if the instance has already been initialized. If so, do nothing.
        if hasattr(self, 'session'):
            return

        self.session = requests.Session()
        # User-Agent header will be changed to a generic Chromium string when the first
        # Cloudflare challenge is solved
        self.session.headers.update({"User-Agent": f"ItchClaim {__version__}"})
        self.session.headers.update({"X-Real-User-Agent": f"ItchClaim {__version__}"})

    def get(self, url, **kwargs):
        """Send a GET request, handling Cloudflare protection if detected."""
        return self._request_with_cf_handling(self.session.get, url, **kwargs)

    def post(self, url, **kwargs):
        """Send a POST request, handling Cloudflare protection if detected."""
        return self._request_with_cf_handling(self.session.post, url, **kwargs)

    def head(self, url, **kwargs):
        """Send a HEAD request, handling Cloudflare protection if detected."""
        return self._request_with_cf_handling(self.session.head, url, **kwargs)

    def _detect_cloudflare(self, response: requests.Response) -> bool:
        """Detect if Cloudflare protection is present in the response."""
        return (
            response.status_code == 403
            and "<title>Just a moment...</title>" in response.text[:80]
        )

    def _request_with_cf_handling(self, method, url, **kwargs):
        """A higher-order function to handle Cloudflare protection for a given request method."""
        # Try sending the request normally first
        response = method(url, **kwargs)

        # If Cloudflare protection is detected, use FlareSolverr to bypass it
        if self._detect_cloudflare(response):
            self._refresh_cf_cookies()

            # Retry the original request with the updated session
            response = method(url, **kwargs)

        return response

    def _refresh_cf_cookies(self):
        """Refresh Cloudflare cookies in session using FlareSolverr."""
        print(
            "Cloudflare protection detected. "
            + "Resolving challenge using FlareSolverr. "
            + "This may take up to a minute."
        )
        print(
            "If you encounter issues with FlareSolverr, "
            + "please try launching ItchClaim with '--flaresolverr-log-level DEBUG'.")

        if not self.flaresolverr_initialized:
            flaresolverr.init()
            self.flaresolverr_initialized = True

        cf_challange_data = flaresolverr.V1RequestBase(
            {"url": CF_ALWAYS_PROTECTED_URL, "maxTimeout": 60000}
        )
        cf_challange = flaresolverr.resolve_challenge(cf_challange_data, "GET")

        # Extract cf_clearance cookie and set it in the session
        for cookie in cf_challange.result.cookies:
            if cookie["name"] == "cf_clearance":
                self.session.cookies.set(
                    cookie["name"], cookie["value"], domain=cookie["domain"]
                )
                self.session.headers.update(
                    {"User-Agent": cf_challange.result.userAgent}
                )
                break

        print("Cloudflare challenge resolved.")

    @property
    def csrf_token(self) -> str:
        """Get CSRF token from cookies."""

        # Load itch.io home page to get CSRF token if not present
        if "itchio_token" not in self.session.cookies:
            self.get("https://itch.io/")

        return unquote(self.session.cookies["itchio_token"])

    @property
    def cookies(self):
        """Get the session cookies."""
        return self.session.cookies

    @cookies.setter
    def cookies(self, value):
        """Set the session cookies."""
        self.session.cookies = value

    @property
    def headers(self):
        """Get the session headers."""
        return self.session.headers

    @headers.setter
    def headers(self, value):
        """Set the session headers."""
        self.session.headers = value
