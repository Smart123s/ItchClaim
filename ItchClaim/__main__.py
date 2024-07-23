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

import os
from time import sleep
from typing import List

import pycron
from fire import Fire

from . import DiskManager, __version__
from .ItchGame import ItchGame
from .ItchUser import ItchUser
from .web import generate_web


# pylint: disable=missing-class-docstring
class ItchClaim:
    def __init__(self,
                version: bool = False,
                login: str = None,
                password: str = None,
                totp: str = None):
        """Automatically claim free games from itch.io"""
        if version:
            self.version()
        # Try loading username from environment variables if not provided as command line argument
        if login is None and os.getenv('ITCH_USERNAME') is not None:
            login = os.getenv('ITCH_USERNAME')
        if login is not None:
            self.login(login, password, totp)
        else:
            self.user = None

    def version(self):
        """Display the version of the script and exit"""
        print(__version__)
        exit(0)

    def refresh_sale_cache(self, games_dir: str = 'web/data/', sales: List[int] = None):
        """Refresh the cache about game sales
        Opens itch.io and downloads sales posted after the last saved one.

        Args:
            games_dir (str): Output directory
            sales: (List[int]): Only refresh the sales specified in this list"""
        resume = 1
        ItchGame.games_dir = games_dir
        os.makedirs(games_dir, exist_ok=True)

        if sales:
            print('--sales flag found - refreshing only select sale pages')
            for sale_id in sales:
                DiskManager.get_one_sale(sale_id)
            return

        try:
            with open(os.path.join(games_dir, 'resume_index.txt'), 'r', encoding='utf-8') as f:
                resume = int(f.read())
                print(f'Resuming sale downloads from {resume}')
        except FileNotFoundError:
            print('Resume index not found. Downloading sales from beginning')

        DiskManager.get_all_sales(resume)

        print('Updating games from sale lists, to catch updates of already known sales.')

        for category in ['games', 'tools', 'game-assets', 'comics', 'books', 'physical-games',
                'soundtracks', 'game-mods', 'misc']:
            print(f'Collecting sales from {category} list')
            DiskManager.get_all_sale_pages(category=category)

    def refresh_library(self):
        """Refresh the list of owned games of an account. This is used to skip claiming already
        owned games. Requires login."""
        if self.user is None:
            print('You must be logged in')
            return
        self.user.reload_owned_games()
        self.user.save_session()

    def claim(self, url: str = 'https://itchclaim.tmbpeter.com/api/active.json'):
        """Claim all unowned games. Requires login.
        Args:
            url (str): The URL to download the file from"""

        if self.user is None:
            print('You must be logged in')
            return
        if len(self.user.owned_games) == 0:
            print('User\'s library not found in cache. Downloading it now')
            self.user.reload_owned_games()
            self.user.save_session()

        print(f'Downloading free games list from {url}')
        games = DiskManager.download_from_remote_cache(url)

        print('Claiming games')
        claimed_games = 0
        for game in games:
            if not self.user.owns_game(game) and game.claimable:
                self.user.claim_game(game)
                self.user.save_session()
                claimed_games += 1
        if claimed_games == 0:
            print('No new games can be claimed.')

    def schedule(self, cron: str, url: str = 'https://itchclaim.tmbpeter.com/api/active.json'):
        """Start an infinite process of the script that claims games at a given schedule.
        Args:
            cron (str): The cron schedule to claim games
                See crontab.guru for syntax
            url (str): The URL to download the file from"""
        print(f'Starting cron job with schedule {cron}')
        while True:
            if not pycron.is_now(cron):
                sleep(60)
                continue
            self.claim(url)
            sleep(60)
        

    def download_urls(self, game_url: int):
        """Get details about a game, including it's CDN download URLs.

        Args:
            game_url (int): The url of the requested game."""
        game: ItchGame = ItchGame.from_api(game_url)
        session = self.user.s if self.user is not None else None
        print(game.downloadable_files(session))

    def generate_web(self, web_dir: str = 'web'):
        """Generates files that can be served as a static website
        
        Args:
            web_dir (str): Output directory"""

        ItchGame.games_dir = os.path.join(web_dir, 'data')
        os.makedirs(os.path.join(web_dir, 'api'), exist_ok=True)
        os.makedirs(ItchGame.games_dir, exist_ok=True)

        games = DiskManager.load_all_games()
        generate_web(games, web_dir)

    def login(self,
                username: str = None,
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
        self.user = ItchUser(username)
        try:
            self.user.load_session()
            print(f'Session {username} loaded successfully')
        except FileNotFoundError:
            # Try loading password from environment variables if not provided as command line argument
            if password is None:
                password = os.getenv('ITCH_PASSWORD')
            # Try loading TOTP from environment variables if not provided as command line argument
            if totp is None:
                totp = os.getenv('ITCH_TOTP')
            self.user.login(password, totp)
            print(f'Logged in as {username}')

# pylint: disable=missing-function-docstring
def main():
    Fire(ItchClaim)
