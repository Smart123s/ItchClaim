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

from datetime import datetime
import os
from typing import List
import requests, json
from bs4 import BeautifulSoup
from .ItchGame import ItchGame, Sale
from . import __version__

def get_all_sales(start: int) -> List[ItchGame]:
    page = start
    games_num = 0
    while True:
        sale_url = f"https://itch.io/s/{page}"
        r = requests.get(sale_url,
                headers={
                    'User-Agent': f'ItchClaim {__version__}',
                    'Accept-Language': 'en-GB,en;q=0.9',
                    })
        r.encoding = 'utf-8'
    
        if r.status_code == 404:
            print(f'Sale page #{page}: 404 Not Found')
            if r.url == sale_url:
                print(f'No more sales available at the moment')
                break
            else:
                page += 1
                continue

        try:
            soup = BeautifulSoup(r.text, 'html.parser')

            date_format = '%Y-%m-%dT%H:%M:%SZ'
            sale_date_raw = soup.find('span', class_='date_format').text
            sale_date = datetime.strptime(sale_date_raw, date_format)

            # Is the date shown on the site a start or an end?
            not_active_div = soup.find('div', class_="not_active_notification")
            if not_active_div and 'Come back ' in not_active_div.text:
                current_sale = Sale(page, start=sale_date)
            else:
                current_sale = Sale(page, end=sale_date)

            games_raw = soup.find_all('div', class_="game_cell")
            for div in games_raw:
                game: ItchGame = ItchGame.from_div(div)

                # If the sale is not active, we can't check if it's claimable
                if not current_sale.is_active:
                    game.claimable = None

                # load previously saved sales
                if os.path.exists(game.get_default_game_filename()):
                    disk_game: ItchGame = ItchGame.load_from_disk(game.get_default_game_filename())
                    game.sales = disk_game.sales
                    if game.sales[-1].id == page:
                        print(f'Sale {page} has been already saved for game {game.name} (wrong resume index?)')
                        continue

                game.sales.append(current_sale)
                
                if game.price != 0:
                    print(f'Sale page #{page}: games are not discounted by 100%')
                    break

                games_num += 1
                game.save_to_disk()

            if game.price == 0:
                expired = sale_date.timestamp() < datetime.now().timestamp()
                expired_str = '(expired)' if expired else ''
                print(f'Sale page #{page}: added {len(games_raw)} games', expired_str)
        except Exception as e:
            print(f'Failed to parse sale page {page}. Reason: {e}')
        
        with open(os.path.join(ItchGame.get_games_dir(), 'resume_index.txt'), 'w') as f:
            f.write(str(page))

        page += 1

    if games_num == 0:
        print('No new free games found')
    else:
        print(f'Execution finished. Added a total of {games_num} games')

def load_all_games():
    """Load all games cached on the disk"""
    l: List[ItchGame] = []
    for file in os.listdir(ItchGame.get_games_dir()):
        if not file.endswith('.json'):
            continue
        path = os.path.join(ItchGame.get_games_dir(), file)
        l.append(ItchGame.load_from_disk(path))
    return l

def download_from_remote_cache(url: str) -> List[ItchGame]:
    r = requests.get(url)
    games_raw = json.loads(r.text)
    games = []
    for game_json in games_raw:
        game = ItchGame(game_json['id'])
        game.url = game_json['url']
        game.name = game_json['name']
        game.claimable = game_json['claimable']
        games.append(game)
    return games
