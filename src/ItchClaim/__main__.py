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

import os
from fire import Fire
from ItchUser import ItchUser
from ItchGame import ItchGame
import DiskManager

class ItchClaim:
    def __init__(self,
                login: str = None,
                password: str = None,
                totp: str = None):
        if login is not None:
            self.user = ItchClaim._login(login, password, totp)
        else:
            self.user = None

    def refresh_sale_cache(object, clean: bool = False):
        """Refresh the locally stored cache about game sales
        Deletes expired sales from the disk.
        Opens itch.io and downloads details about the latest sales.
        Stops if a saved sale is found.

        Args:
            clean (bool): Re-download cached sales too.
        """
        num_of_removed_games = DiskManager.remove_expired_sales()
        print(f'Removed {num_of_removed_games} expired sales from disk')
        print('Downloading game sales pages.')
        i = 1
        more_games_exist = True
        while more_games_exist:
            page = DiskManager.get_online_sale_page(i)
            if page == False:
                break
            for game in page:
                if os.path.exists(game.get_default_game_filename()) and not clean:
                    more_games_exist = False
                    print(f'Game {game.name} has already been saved. Stopping execution')
                    break
                game.save_to_disk()
            print(f'Sale page #{i+1}: added {len(page)} games')
            i += 1

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
        """
        if self.user is None:
            print('You must be logged in')
            return
        if not no_cache_refresh:
            if len(self.user.owned_games) == 0:
                print('User\'s library not found in cache. Downloading it now')
                self.user.reload_owned_games()
                self.user.save_session()
            print('Looking for new free games')
            self.refresh_sale_cache()
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
        """
        path = os.path.join(ItchGame.get_games_dir(), str(id) + '.json')
        game: ItchGame = ItchGame.load_from_disk(path)
        session = self.user.s if self.user is not None else None
        print(game.downloadable_files(session))

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

if __name__=="__main__":
    Fire(ItchClaim)