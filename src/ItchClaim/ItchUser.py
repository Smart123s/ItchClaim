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

import requests, urllib, pyotp, os, json
from appdirs import user_data_dir
from typing import Optional
from bs4 import BeautifulSoup

class ItchUser:
    def __init__(self, username):
        self.s = requests.Session()
        self.username = username

    def login(self, password: str, totp: Optional[str]):
        self.s.get('https://itch.io/login')
        self.update_csrf()

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
        os.makedirs(user_data_dir('itchclaim'), exist_ok=True)
        data = {
            'csrf_token': self.csrf_token,
            'itchio': self.s.cookies['itchio']
        }
        with open(self.get_default_session_filename(), 'w') as f:
            f.write(json.dumps(data))

    def load_session(self):
        with open(self.get_default_session_filename(), 'r') as f:
            data = json.load(f)
        self.csrf_token = data['csrf_token']
        self.s.cookies.set('itchio_token', self.csrf_token, domain='.itch.io')
        self.s.cookies.set('itchio', data['itchio'], domain='.itch.io')

    def get_default_session_filename(self) -> str:
        sessionfilename = f'session-{self.username}.json'
        return os.path.join(user_data_dir('itchclaim', False), sessionfilename)

    def update_csrf(self):
        self.csrf_token = urllib.parse.unquote(self.s.cookies['itchio_token'])
