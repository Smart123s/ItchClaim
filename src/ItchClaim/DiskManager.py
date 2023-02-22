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

import datetime
import os
from typing import List
import requests, json
from bs4 import BeautifulSoup
from ItchGame import ItchGame

def get_online_sale_page(page: int) -> List[ItchGame]:
    r = requests.get(f"https://itch.io/games/newest/on-sale?page={page}&format=json")
    html = json.loads(r.text)['content']
    soup = BeautifulSoup(html, 'html.parser')
    games_raw = soup.find_all('div', class_="game_cell")
    games = []
    for div in games_raw:
        game_parsed = ItchGame.from_div(div)
        if game_parsed.price == 0:
            games.append(game_parsed)
    if len(games) == 0 and json.loads(r.text)["num_items"] == 0:
        return False
    return games

def load_all_games():
    l = [ItchGame]
    for file in os.listdir(ItchGame.get_games_dir()):
        path = os.path.join(ItchGame.get_games_dir(), file)
        l.append(ItchGame.load_from_disk(path))
    return l

def remove_expired_sales():
    for game in load_all_games():
        if game.sale_end < datetime.datetime.now():
            os.remove(game.get_default_game_filename())