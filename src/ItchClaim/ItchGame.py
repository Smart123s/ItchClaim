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
import json, requests, re
import os
from typing import Self
from bs4.element import Tag
from bs4 import BeautifulSoup
from functools import cached_property
from appdirs import user_data_dir

class ItchGame:
    def __init__(self, id: int):
        self.id = id

    @staticmethod
    def from_div(div: Tag) -> Self:
        id = int(div.attrs['data-game_id'])
        self = ItchGame(id)
        a = div.find('a', class_='title game_link')
        self.name = a.text
        self.url = a.attrs['href']

        self.cover_image = div.find('div', class_='game_thumb').find('img').attrs['data-lazy_src']

        price_element = div.find('div', attrs={'class': 'price_value'})
        # Some elements don't have a price defined
        if price_element != None:
            price_str = re.findall("[-+]?(?:\d*\.\d+|\d+)", price_element.text)[0]
            self.price = float(price_str)
        else:
            self.price = None
        return self

    def save_to_disk(self):
        os.makedirs(ItchGame.get_games_dir(), exist_ok=True)
        data = {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'price': self.price,
            'claimable': self.claimable,
            'sale_end': int(self.sale_end.timestamp()),
            'cover_image': self.cover_image,
        }
        with open(self.get_default_game_filename(), 'w') as f:
            f.write(json.dumps(data))

    @staticmethod
    def load_from_disk(path: str) -> Self:
        with open(path, 'r') as f:
            data = json.loads(f.read())
        id = data['id']
        self = ItchGame(id)
        self.name = data['name']
        self.url = data['url']
        self.price = data['price']
        self.claimable = data['claimable']
        self.sale_end = datetime.fromtimestamp(data['sale_end'])
        self.cover_image = data['cover_image']
        return self

    def get_default_game_filename(self) -> str:
        sessionfilename = f'{self.id}.json'
        return os.path.join(ItchGame.get_games_dir(), sessionfilename)

    @cached_property
    def claimable(self) -> bool:
        r = requests.get(self.url)
        soup = BeautifulSoup(r.text, 'html.parser')
        buy_row = soup.find('div', class_='buy_row')
        if buy_row is None:
            # Game is probably WebGL or HTML5 only
            return False
        buy_box = buy_row.find('a', class_='button buy_btn')
        claimable = buy_box.text == 'Download or claim'
        return claimable

    @cached_property
    def sale_end(self) -> datetime:
        r = requests.get(self.url + '/data.json')
        resp = json.loads(r.text)
        date_str = resp['sale']['end_date']
        date_format = '%Y-%m-%d %H:%M:%S'
        return datetime.strptime(date_str, date_format)
    
    @staticmethod
    def get_games_dir() -> str:
        """Returns default directory for user storage"""
        return os.path.join(user_data_dir('itchclaim', False), 'games')
