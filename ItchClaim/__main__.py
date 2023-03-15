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

import json
import os
from fire import Fire

from .web.web import generate_html
from . import DiskManager
from .ItchUser import ItchUser
from .ItchGame import ItchGame

class ItchClaim:
    def __init__(self,
                login: str = None,
                password: str = None,
                totp: str = None,
                dir: str = None):
        """Automatically claim free games from itch.io

        Args:
            dir (str): Specify the game cache directory
        """

        ItchGame.custom_dir = dir

        if login is not None:
            self.user = ItchClaim._login(login, password, totp)
        else:
            self.user = None

    def refresh_sale_cache(object, dir: str = None):
        """Refresh the cache about game sales
        Opens itch.io and downloads sales posted after the last saved one."""
        resume = 91000
        try:
            with open(os.path.join(ItchGame.get_games_dir(), 'resume_index.txt'), 'r') as f:
                resume = int(f.read())
                print(f'Resuming sale downloads from {resume}')
        except:
            print('Resume index not found. Downloading sales from 83500')

        DiskManager.get_all_sales(resume)

    def refresh_library(self):
        """Refresh the list of owned games of an account. This is used to skip claiming already owned games. Requires login.
        """
        if self.user is None:
            print('You must be logged in')
            return
        self.user.reload_owned_games()
        self.user.save_session()

    def claim(self, no_cache_refresh: bool = False):
        """Claim all unowned games. Requires login.

        Args:
            no_cache_refresh (bool): Claims locally cached games only
        """
        if self.user is None:
            print('You must be logged in')
            return
        if not no_cache_refresh:
            if len(self.user.owned_games) == 0:
                print('User\'s library not found in cache. Downloading it now')
                self.user.reload_owned_games()
                self.user.save_session()
            self.refresh_from_remote_cache()
        print('Claiming games')
        claimed_games = 0
        for game in DiskManager.load_all_games():
            if not self.user.owns_game(game) and game.claimable:
                self.user.claim_game(game)
                self.user.save_session()
                claimed_games += 1
        if claimed_games == 0:
            print('No new games can be claimed.')
    
    def download_urls(self, id: int):
        """Get details about a game, including it's CDN URLs.

        Args:
            id (int): The ID of the requested game.
            Note: Currently only supports locally cached games
        """
        path = os.path.join(ItchGame.get_games_dir(), str(id) + '.json')
        game: ItchGame = ItchGame.load_from_disk(path)
        session = self.user.s if self.user is not None else None
        print(game.downloadable_files(session))

    def generate_web(object, web_dir: str = 'web'):
        """Generates files that can be served as a static website
        
        Args:
            web_dir (str): Output directory"""

        os.makedirs(os.path.join(web_dir, 'api'), exist_ok=True)

        games = DiskManager.load_all_games()
        active_sales = list(filter(lambda game: game.is_sale_active, games))
        active_sales_min = [ game.serialize_min() for game in active_sales ]
        with open(os.path.join(web_dir, 'api', 'active.json'), 'w', encoding="utf-8") as f:
            f.write(json.dumps(active_sales_min))

        # Create HTML file
        with open(os.path.join(web_dir, 'index.html'), 'w', encoding="utf-8") as f:
            f.write(generate_html(active_sales))

    def refresh_from_remote_cache(self, url: str = 'https://Smart123s.github.io/ItchClaim/index.json'):
        """Download collected sales from remote URL.
        Deletes expired sales from the disk.
        
        Args:
            url (str): The URL to download the file from"""

        num_of_removed_games = DiskManager.remove_expired_sales()
        print(f'Removed {num_of_removed_games} expired sales from disk')

        print(f'Downloading games from {url}')
        DiskManager.refresh_from_remote_cache(url)

    def _login(username: str = None,
               password: str = None,
               totp: str = None) -> ItchUser:
        """Load session from disk if exists, or use password otherwise.

        Args:
            username (str): The username or email address of the user
            password (str): The password of the user
            totp (str): The 2FA code of the user
                Either the 6 digit code, or the secret used to generate the code
        
        Returns:
            ItchUser: a logged in ItchUser instance
        """
        user = ItchUser(username)
        try:
            user.load_session()
            print(f'Session {username} loaded successfully')
        except:
            user.login(password, totp)
            print(f'Logged in as {username}')
        return user

def main():
    Fire(ItchClaim)
