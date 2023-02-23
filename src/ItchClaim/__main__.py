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

from fire import Fire
from ItchUser import ItchUser
import DiskManager

class ItchClaim:
    def __init__(self,
                login: str = None,
                password: str = None,
                totp: str = None):
        if login is not None:
            self.user = ItchClaim._login(login, password, totp)
    
    def _login(login: str = None,
               password: str = None,
               totp: str = None) -> ItchUser:
        user = ItchUser(login)
        try:
            user.load_session()
            print(f'Session {login} loaded successfully')
        except:
            user.login(password, totp)
            print(f'Logged in as {login}')
        return user
    

def main():
    print('Downloading game sales pages.')
    games_list = []
    
    for i in range(int(1e18)):
        page = DiskManager.get_online_sale_page(i)
        if page == False:
            break
        games_list.extend(page)
        print (f'Sale page #{i+1}: added {len(page)} games (total: {len(games_list)})')

    print('\nClaiming games')
    for game in games_list:
        if user.owns_game(game):
            print(f"Game {game.name} has already been claimed (url: {game.url})")
            continue
        user.claim_game(game)

    user.save_session()

if __name__=="__main__":
    Fire(ItchClaim)