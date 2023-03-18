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

import os, requests, json
from typing import List
from .ItchGame import ItchGame
from .ItchSale import ItchSale
from . import __version__

def get_all_sales(start: int) -> List[ItchGame]:
    """Download details about every sale posted on itch.io

    Args:
        start (int): the ID of the first sale to download
    """
    page = start
    games_num = 0
    while True:
        page += 1
        try:
            current_sale = ItchSale(page)
            if current_sale.err == 'NO_MORE_SALES_AVAILABLE' and current_sale.id > 90000:
                print('No more sales available at the moment')
                break
            elif current_sale.err:
                continue

            games_raw = current_sale.soup.find_all('div', class_="game_cell")
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
                expired_str = '(expired)' if current_sale.is_active else ''
                print(f'Sale page #{page}: added {len(games_raw)} games', expired_str)
        #pylint: disable=broad-exception-caught
        except Exception as ex:
            print(f'Failed to parse sale page {page}. Reason: {ex}')

        with open(os.path.join(ItchGame.games_dir, 'resume_index.txt'), 'w', encoding='utf-8') as f:
            f.write(str(page))

    if games_num == 0:
        print('No new free games found')
    else:
        print(f'Execution finished. Added a total of {games_num} games')

def load_all_games():
    """Load all games cached on the disk"""
    l: List[ItchGame] = []
    for file in os.listdir(ItchGame.games_dir):
        if not file.endswith('.json'):
            continue
        path = os.path.join(ItchGame.games_dir, file)
        l.append(ItchGame.load_from_disk(path))
    return l

def download_from_remote_cache(url: str) -> List[ItchGame]:
    r = requests.get(url, timeout=8)
    games_raw = json.loads(r.text)
    games = []
    for game_json in games_raw:
        game = ItchGame(game_json['id'])
        game.url = game_json['url']
        game.name = game_json['name']
        game.claimable = game_json['claimable']
        games.append(game)
    return games
