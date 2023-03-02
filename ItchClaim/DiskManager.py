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
from .ItchGame import ItchGame
from . import __version__

def get_all_sales(start: int) -> List[ItchGame]:
    page = start
    no_more_games_count = 0
    games_num = 0
    while no_more_games_count < 11:
        r = requests.get(f"https://itch.io/s/{page}",
                headers={
                    'User-Agent': f'ItchClaim {__version__}',
                    'Accept-Language': 'en-GB,en;q=0.9',
                    })
    
        if r.status_code == 404:
            print(f'Sale page #{page}: 404 Not Found ({10 - no_more_games_count} attempts left)')
            no_more_games_count += 1
            page += 1
            continue
        else:
            no_more_games_count = 0

        soup = BeautifulSoup(r.text, 'html.parser')

        date_format = '%Y-%m-%dT%H:%M:%SZ'
        sale_end_raw = soup.find('span', class_='date_format').text
        sale_end = datetime.strptime(sale_end_raw, date_format)

        try:
            games_raw = soup.find_all('div', class_="game_cell")
            for div in games_raw:
                game = ItchGame.from_div(div)
                game.sale_id = page

                game.sale_end = sale_end
                if game.price != 0:
                    print(f'Sale page #{page}: games are not discounted by 100%')
                    break

                games_num += 1
                game.save_to_disk()
            if game.price == 0:
                print(f'Sale page #{page}: added {len(games_raw)} games')
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

def remove_expired_sales() -> int:
    """Removes expired sales from the disk cache
    
    Returns:
        int: The number of games removed
    """
    i = 0
    for game in load_all_games():
        if game.sale_end < datetime.now():
            os.remove(game.get_default_game_filename())
            i += 1
    return i
