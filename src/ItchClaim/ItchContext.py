# The MIT License (MIT)
# 
# Copyright (c) 2022 Péter Tombor.

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

import requests, urllib, pyotp, os, platform, tempfile, json, getpass
from typing import Optional
from bs4 import BeautifulSoup


class ItchContext:
    def __init__(self, username):
        self._s = requests.Session()
        self.username = username

    def login(self, password: str, totp: Optional[str]):
        self._s.get('https://itch.io/login')
        self.update_csrf()

        data = {
            'csrf_token': self.csrf_token,
            'tz': -120,
            'username': self.username,
            'password': password,
        }
        r = self._s.post('https://itch.io/login', params=data)

        if r.url.find('totp/') != -1:
            soup = BeautifulSoup(r.text, 'html.parser')
            data = {
                'csrf_token': self.csrf_token,
                'userid': soup.find_all(attrs={"name": "user_id"})[0]['value'],
                'code': int(pyotp.TOTP(totp).now()),
            }
            r = self._s.post(r.url, params=data)

        self.save_session()

    def save_session(self):
        os.makedirs(_get_config_dir(), exist_ok=True)
        data = {
            'csrf_token': self.csrf_token,
            'itchio': self._s.cookies['itchio']
        }
        with open(self.get_default_session_filename(), 'w') as f:
            f.write(json.dumps(data))

    def load_session(self):
        with open(self.get_default_session_filename(), 'r') as f:
            data = json.load(f)
        self.csrf_token = data['csrf_token']
        self._s.cookies.set('itchio_token', self.csrf_token, domain='.itch.io')
        self._s.cookies.set('itchio', data['itchio'], domain='.itch.io')

    # Source: https://github.com/instaloader/instaloader/blob/853e8603/instaloader/instaloader.py#L42-L46
    def get_default_session_filename(self) -> str:
        """Returns default session filename for the user."""
        configdir = _get_config_dir()
        sessionfilename = "session-{}.json".format(self.username)
        return os.path.join(configdir, sessionfilename)

    def claim_game(self, url: str):
        r = self._s.post(url + '/download_url', json={'csrf_token': self.csrf_token})
        download_url = json.loads(r.text)['url']
        r = self._s.get(download_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        claim_url = soup.find('div', class_='claim_to_download_box warning_box').find('form')['action']
        r = self._s.post(claim_url, 
                        data={'csrf_token': self.csrf_token}, 
                        headers={ 'Content-Type': 'application/x-www-form-urlencoded'}
                        )
        print(r.url)
        # Success: https://dankoff.itch.io/sci-fi-wepon-pack/download/7LPhDDllv1SB__g9KhRzRS36Y7nF4Uefi2CbEKjS
        # Fail: https://itch.io/


    def update_csrf(self):
        self.csrf_token = urllib.parse.unquote(self._s.cookies['itchio_token'])

# Source: https://github.com/instaloader/instaloader/blob/853e8603/instaloader/instaloader.py#L30-L39
def _get_config_dir() -> str:
    if platform.system() == "Windows":
        # on Windows, use %LOCALAPPDATA%\ItchClaim
        localappdata = os.getenv("LOCALAPPDATA")
        if localappdata is not None:
            return os.path.join(localappdata, "ItchClaim")
        # legacy fallback - store in temp dir if %LOCALAPPDATA% is not set
        return os.path.join(tempfile.gettempdir(), ".itchclaim-" + getpass.getuser())
    # on Unix, use ~/.config/itchclaim
    return os.path.join(os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "itchclaim")