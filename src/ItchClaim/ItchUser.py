# The MIT License (MIT)
# 
# Copyright (c) 2022-2023 Péter Tombor.
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
import requests, urllib, pyotp, os, json
from appdirs import user_data_dir
from typing import Optional
from bs4 import BeautifulSoup
from ItchGame import ItchGame

class ItchUser:
    def __init__(self, username):
        self.s = requests.Session()
        self.username = username

    def login(self, password: str, totp: Optional[str]):
        self.s.get('https://itch.io/login')

        data = {
            'csrf_token': self.csrf_token,
            'tz': -120,
            'username': self.username,
            'password': password,
        }
        r = self.s.post('https://itch.io/login', params=data)

        if r.url.find('totp/') != -1:
            soup = BeautifulSoup(r.text, 'html.parser')
            data = {
                'csrf_token': self.csrf_token,
                'userid': soup.find_all(attrs={"name": "user_id"})[0]['value'],
                'code': int(pyotp.TOTP(totp).now()),
            }
            r = self.s.post(r.url, params=data)

        self.save_session()

    def save_session(self):
        os.makedirs(get_users_dir(), exist_ok=True)
        data = {
            'csrf_token': self.csrf_token,
            'itchio': self.s.cookies['itchio']
        }
        with open(self.get_default_session_filename(), 'w') as f:
            f.write(json.dumps(data))

    def load_session(self):
        with open(self.get_default_session_filename(), 'r') as f:
            data = json.load(f)
        self.s.cookies.set('itchio_token', data['csrf_token'], domain='.itch.io')
        self.s.cookies.set('itchio', data['itchio'], domain='.itch.io')

    def get_default_session_filename(self) -> str:
        sessionfilename = f'session-{self.username}.json'
        return os.path.join(get_users_dir(), sessionfilename)

    @cached_property
    def csrf_token(self) -> str:
        return urllib.parse.unquote(self.s.cookies['itchio_token'])

    def owns_game(self, game: ItchGame):
        return self.owns_game_online(game)

    def owns_game_online(self, game: ItchGame):
        r = self.s.get(game.url, json={'csrf_token': self.csrf_token})
        soup = BeautifulSoup(r.text, 'html.parser')
        owned_box = soup.find('span', class_='ownership_reason')
        return owned_box != None

    def claim_game(self, game: ItchGame):
        r = self.s.post(game.url + '/download_url', json={'csrf_token': self.csrf_token})
        resp = json.loads(r.text)
        if 'errors' in resp:
            print(f"ERROR: Failed to claim game {game.name} (url: {game.url})")
            print(f"\t{resp['errors'][0]}")
            return
        download_url = json.loads(r.text)['url']
        r = self.s.get(download_url)
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
        if r.url == 'https://itch.io/':
            print(f"ERROR: Failed to claim game {game.name} (url: {game.url})")
        else:
            print(f"Successfully claimed game {game.name} (url: {game.url})")

    def get_one_library_page(self, page: int):
        r = self.s.get(f"https://itch.io/my-purchases?page={page}&format=json")
        html = json.loads(r.text)['content']
        soup = BeautifulSoup(html, 'html.parser')
        games_raw = soup.find_all('div', class_="game_cell")
        games = []
        for div in games_raw:
            games.append(ItchGame.from_div(div))
        return games

    def reload_owned_games(self):
        for i in range(int(1e18)):
            page = self.get_one_library_page(i)
            if len(page) == 0:
                break
            self.owned_games.extend(page)
            print (f'Library page #{i+1}: added {len(page)} games (total: {len(self.owned_games)})')

@staticmethod
def get_users_dir() -> str:
    """Returns default directory for user storage"""
    return os.path.join(user_data_dir('itchclaim', False), 'users')
