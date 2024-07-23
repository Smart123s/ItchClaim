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

from typing import List
import os
import json
import requests
from bs4 import BeautifulSoup
from .ItchGame import ItchGame
from .ItchSale import ItchSale
from . import __version__

def get_all_sales(start: int) -> List[ItchGame]:
    """Download details about every sale posted on itch.io

    Args:
        start (int): the ID of the first sale to download
    """
    page = start - 1
    games_num = 0
    while True:
        page += 1
        try:
            games_added = get_one_sale(page, force=False)
            if games_added == -1:
                break
            else:
                games_num += games_added
        #pylint: disable=broad-exception-caught
        except Exception as ex:
            print(f'Failed to parse sale page {page}. Reason: {ex}')

        with open(os.path.join(ItchGame.games_dir, 'resume_index.txt'), 'w', encoding='utf-8') as f:
            f.write(str(page))

    if games_num == 0:
        print('No new free games found')
    else:
        print(f'Execution finished. Added a total of {games_num} games')

def get_one_sale(page: int, force: bool = True) -> int:
    """"Downloads one sale page, and saves the results to the disk

    Args:
        page (int): the sale_id  to be downloaded
        force (bool): set to True if method is not called from refresh_sale_cache.
            Makes sure that the sales array in the game is sorted and doesn't contain duplicate elements.

    Returns:
        int: The number of games saved
    """
    games_num = 0
    current_sale = ItchSale(page)
    if current_sale.err == 'NO_MORE_SALES_AVAILABLE' and current_sale.id > 90000:
        print('No more sales available at the moment')
        return -1
    elif current_sale.err:
        return 0

    games_raw = current_sale.soup.find_all('div', class_="game_cell")

    if len(games_raw) == 0:
        print(f'Sale page #{page}: empty page')
        return 0

    for div in games_raw:
        game: ItchGame = ItchGame.from_div(div, price_needed=True)

        if game.price != 0:
            print(f'Sale page #{page}: games are not discounted by 100%')
            break

        # If the sale is not active, we can't check if it's claimable
        if not current_sale.is_active:
            game.claimable = None

        # load previously saved sales
        if os.path.exists(game.get_default_game_filename()):
            disk_game: ItchGame = ItchGame.load_from_disk(game.get_default_game_filename(), refresh_claimable=True)
            game.sales = disk_game.sales
            if game.sales[-1].id == page and not force:
                print(f'Sale {page} has been already saved for game {game.name} (wrong resume index?)')
                continue
        
        if not force:
            game.sales.append(current_sale)
        else:
            sale_already_exists = False
            for i, sale in enumerate(game.sales):
                if sale.id == page:
                    sale_already_exists = True
                    game.sales[i] = current_sale
                    print(f'Sale page {page}: Updated values for game {game.name} ({game.id})')
                    break
            if not sale_already_exists:
                game.sales.append(current_sale)
                game.sales.sort(key=lambda a: a.id)

        games_num += 1
        game.save_to_disk()

    if game.price == 0:
        expired_str = '(inactive)' if not current_sale.is_active else ''
        print(f'Sale page #{page}: added {len(games_raw)} games', expired_str)
    return games_num

def get_all_sale_pages(category: str = 'games') -> List[ItchGame]:
    """Gets all the pages of the sales feed from itch.io, and saves the missing games

    Args:
        category (str): the category of the items
            Possible values: games, tools, game-assets, comics, books, physical-games,
            soundtracks, game-mods, misc"""
    page = 0
    games_num = 0
    while True:
        page += 1
        try:
            games_added = get_online_sale_page(page, category=category)
            if games_added == -1:
                break
            else:
                games_num += games_added
        #pylint: disable=broad-exception-caught
        except Exception as ex:
            print(f'Failed to parse {category} sale page {page}. Reason: {ex}')

    print(f'Collecting sales from category {category} finished.',
          f'Added a total of {games_num} {category}')

def get_online_sale_page(page: int, category: str = 'games') -> int:
    """Get a page of the sales feed from itch.io, and save the missing ones to the disk.
    Supposed to be ran after get_all_sales() to catch updated sales.
    
    Args:
        page (int): the id of the page to load
        category (str): the category of the items
            Possible values: games, tools, game-assets, comics, books, physical-games,
            soundtracks, game-mods, misc

    Returns:
        int: The number of games updated
    """
    print(f'Processing {category} sale page #{page}')
    r = requests.get(f"https://itch.io/{category}/newest/on-sale?page={page}&format=json",
                    headers={'User-Agent': f'ItchClaim {__version__}'},
                    timeout=8,)
    if r.status_code == 404:
        print('Page returned 404.')
        return -1
    html = json.loads(r.text)['content']
    soup = BeautifulSoup(html, 'html.parser')
    games_raw = soup.find_all('div', class_="game_cell")
    games = []
    games_added = 0
    for div in games_raw:
        game = ItchGame.from_div(div, price_needed=True)
        if game.price == 0:
            # Save game if it's new to us
            if not os.path.exists(game.get_default_game_filename()):
                # Call API to get active sale
                ItchGame.from_api(game.url).save_to_disk()
                print(f'Saved new {category} {game.name} ({game.url})')
                games_added += 1
                continue

            # load previously saved sales
            game = ItchGame.load_from_disk(game.get_default_game_filename(), refresh_claimable=True)
            if game.active_sale:
                print(f'Skipping {category} {game.name} ({game.url}): already active sale found on disk')
                continue

            # Call API to get active sale
            sale = ItchGame.from_api(game.url).active_sale
            game.sales.append(sale)
            game.sales.sort(key=lambda a: a.id)
            game.save_to_disk()
            print(f'Updated values for {category} {game.name} ({game.url})')
            games_added += 1
    if len(games) == 0 and json.loads(r.text)["num_items"] == 0:
        return -1
    return games_added

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
