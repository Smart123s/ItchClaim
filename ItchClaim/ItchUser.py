# The MIT License (MIT)
#
# Copyright (c) 2022-2024 Péter Tombor.
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

from functools import cached_property
from getpass import getpass
import platform
import re
import tempfile
import urllib
import os
import json
from typing import List, Optional
import requests
import pyotp
from bs4 import BeautifulSoup
from .ItchGame import ItchGame
from . import __version__

class ItchUser:
    def __init__(self, username):
        self.s = requests.Session()
        self.username = username
        self.owned_games: List[ItchGame] = []

        self.s.headers.update({'User-Agent': f'ItchClaim {__version__}'})

    def login(self, password: str, totp: Optional[str]):
        """Create a new session on itch.io"""
        self.s.get('https://itch.io/login')

        if password is None:
            password = getpass(f'Enter password for user {self.username}: ')

        data = {
            'csrf_token': self.csrf_token,
            'tz': -120,
            'username': self.username,
            'password': password,
        }
        r = self.s.post('https://itch.io/login', params=data)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')

        errors_div = soup.find('div', class_='form_errors')
        if errors_div:
            print(f'Error while logging in: ' + errors_div.find('li').text)
            exit(1)

        self.user_id = soup.find_all(attrs={"name": "user_id"})[0]['value']
        if r.url.find('totp/') != -1:
            if totp is None:
                totp = input('Enter 2FA code: ')
            
            self.send_top(totp, r.url)
        self.save_session()

    def send_top(self, totp: str, url: str) -> None:
        if len(totp) != 6:
            totp_secret = totp
            totp = pyotp.TOTP(totp).now()
        data = {
            'csrf_token': self.csrf_token,
            'userid': self.user_id,
            'code': int(totp),
        }
        r = self.s.post(url, params=data)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')

        errors_div = soup.find('div', class_='form_errors')
        if errors_div:
            totp_new = pyotp.TOTP(totp_secret).now()
            if totp_secret and totp_new != totp:
                print(f'TOTP code changed (probably the 30 seconds have elapsed while sending it). Attempting with new code.')
                return self.send_top(totp_new, r.url)
            print(f'Error while logging in: ' + errors_div.find('li').text)
            exit(1)

    def save_session(self):
        """Save session to disk"""
        os.makedirs(ItchUser.get_users_dir(), exist_ok=True)
        data = {
            'csrf_token': self.csrf_token,
            'itchio': self.s.cookies['itchio'],
            'owned_games': [game.id for game in self.owned_games],
        }
        with open(self.get_default_session_filename(), 'w') as f:
            f.write(json.dumps(data))

    def load_session(self):
        """Load a user's session from disk"""
        with open(self.get_default_session_filename(), 'r') as f:
            data = json.load(f)
        self.s.cookies.set('itchio_token', data['csrf_token'], domain='.itch.io')
        self.s.cookies.set('itchio', data['itchio'], domain='.itch.io')
        try:
            self.owned_games  = [ItchGame(id) for id in data['owned_games']]
        except KeyError:
            pass

    def get_default_session_filename(self) -> str:
        """Get the default session path"""
        safe_username = re.sub(r'\W', '_', self.username)
        sessionfilename = f'session-{safe_username}.json'
        return os.path.join(ItchUser.get_users_dir(), sessionfilename)

    @cached_property
    def csrf_token(self) -> str:
        """Extract CSRF token from cookies"""
        return urllib.parse.unquote(self.s.cookies['itchio_token'])

    def owns_game(self, game: ItchGame):
        for oid in [owned_game.id for owned_game in self.owned_games]:
            if game.id == oid:
                return True
        return False

    def owns_game_online(self, game: ItchGame):
        """Check on itch.io if the user own's a game"""
        r = self.s.get(game.url, json={'csrf_token': self.csrf_token})
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        owned_box = soup.find('span', class_='ownership_reason')
        return owned_box != None

    def claim_game(self, game: ItchGame):
        r = self.s.post(game.url + '/download_url', json={'csrf_token': self.csrf_token})
        r.encoding = 'utf-8'
        resp = json.loads(r.text)
        if 'errors' in resp:
            if resp['errors'][0] in ('invalid game', 'invalid user'):
                if game.check_redirect_url():
                    self.claim_game(game)
                    return
            print(f"ERROR: Failed to claim game {game.name} (url: {game.url})")
            print(f"\t{resp['errors'][0]}")
            return
        download_url = json.loads(r.text)['url']
        r = self.s.get(download_url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        claim_box = soup.find('div', class_='claim_to_download_box warning_box')
        if claim_box == None:
            print(f"Game {game.name} is not claimable (url: {game.url})")
            return
        claim_url = claim_box.find('form')['action']
        r = self.s.post(claim_url,
                        data={'csrf_token': self.csrf_token},
                        headers={ 'Content-Type': 'application/x-www-form-urlencoded'}
                        )
        r.encoding = 'utf-8'
        if r.url == 'https://itch.io/':
            if self.owns_game_online(game):
                self.owned_games.append(game)
                print(f"Game {game.name} has already been claimed (url: {game.url})")
            print(f"ERROR: Failed to claim game {game.name} (url: {game.url})")
        else:
            self.owned_games.append(game)
            print(f"Successfully claimed game {game.name} (url: {game.url})")

    def get_one_library_page(self, page: int):
        """Get one page of the user's library"""
        r = self.s.get(f"https://itch.io/my-purchases?page={page}&format=json")
        r.encoding = 'utf-8'
        html = json.loads(r.text)['content']
        soup = BeautifulSoup(html, 'html.parser')
        games_raw = soup.find_all('div', class_="game_cell")
        games = []
        for div in games_raw:
            games.append(ItchGame.from_div(div))
        return games

    def reload_owned_games(self):
        """Reload the cache of the user's library"""
        self.owned_games = []
        for i in range(1, int(1e18)):
            page = self.get_one_library_page(i)
            if len(page) == 0:
                break
            self.owned_games.extend(page)
            print (f'Library page #{i}: added {len(page)} games (total: {len(self.owned_games)})')

    @staticmethod
    def get_users_dir() -> str:
        """Returns default directory for user storage"""
        if os.environ.get('ITCHCLAIM_DOCKER', False):
            return '/data/'

        # Source: https://github.com/instaloader/instaloader/blob/6a3d763c/instaloader/instaloader.py#L30-L39
        if platform.system() == "Windows":
            # on Windows, use %LOCALAPPDATA%\Instaloader
            localappdata = os.getenv("LOCALAPPDATA")
            if localappdata is not None:
                return os.path.join(localappdata, "ItchClaim", "users")
            # legacy fallback - store in temp dir if %LOCALAPPDATA% is not set
            return os.path.join(tempfile.gettempdir(), ".itchclaim", "users")
        # on Unix, use ~/.config/instaloader
        return os.path.join(os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "itchclaim", "users")
