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
import json, requests, re, urllib
import os
from typing import List, Self
from bs4.element import Tag
from bs4 import BeautifulSoup
from functools import cached_property
from appdirs import user_data_dir
from . import __version__

class ItchGame:
    custom_dir: str = None

    def __init__(self, id: int):
        self.id = id
        self.sales: List[Sale] = []

    @staticmethod
    def from_div(div: Tag) -> Self:
        """Create an ItchGame Instance from a div that's found in the sale page or the my purchases page"""
        id = int(div.attrs['data-game_id'])
        self = ItchGame(id)
        a = div.find('a', class_='title game_link')
        self.name = a.text
        self.url = a.attrs['href']

        try:
            self.cover_image = div.find('div', class_='game_thumb').find('img').attrs['data-lazy_src']
        except:
            self.cover_image = None

        price_element = div.find('div', attrs={'class': 'price_value'})
        # Some elements don't have a price defined
        if price_element != None:
            price_str = re.findall("[-+]?(?:\d*\.\d+|\d+)", price_element.text)[0]
            self.price = float(price_str)
        else:
            self.price = None
        return self

    def save_to_disk(self):
        """Save the details of game to the disk"""
        os.makedirs(ItchGame.get_games_dir(), exist_ok=True)
        data = {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'price': self.price,
            'claimable': self.claimable,
            'sales': Sale.serialize_list(self.sales),
            'cover_image': self.cover_image,
        }
        with open(self.get_default_game_filename(), 'w') as f:
            f.write(json.dumps(data))

    @staticmethod
    def load_from_disk(path: str) -> Self:
        """Load cached details about game from the disk"""
        with open(path, 'r') as f:
            data = json.loads(f.read())
        id = data['id']
        self = ItchGame(id)
        self.name = data['name']
        self.url = data['url']
        self.price = data['price']
        self.sales = [ Sale.from_dict(sale) for sale in data['sales'] ]
        if data['claimable'] is not None:
            self.claimable = data['claimable']
        self.cover_image = data['cover_image']
        return self

    def get_default_game_filename(self) -> str:
        """Get the default path of the game's cache file"""
        sessionfilename = f'{self.id}.json'
        return os.path.join(ItchGame.get_games_dir(), sessionfilename)

    @cached_property
    def claimable(self) -> bool:
        if not self.sales[-1].is_active:
            return None
        r = requests.get(self.url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        buy_row = soup.find('div', class_='buy_row')
        if buy_row is None:
            # Game is probably WebGL or HTML5 only
            return False
        buy_box = buy_row.find('a', class_='button buy_btn')
        if 'Buy Now' in buy_box.text:
            return None
        claimable = buy_box.text == 'Download or claim'
        return claimable
    
    @property
    def sale_end(self) -> datetime:
        return self.sales[-1].end

    @property
    def is_sale_active(self) -> bool:
        return self.sales[-1].is_active

    @property
    def is_sale_upcoming(self) -> bool:
        return self.sales[-1].is_upcoming

    @property
    def is_first_sale(self) -> bool:
        return len(self.sales) == 1

    def sale_end_online(self) -> datetime:
        r = requests.get(self.url + '/data.json')
        r.encoding = 'utf-8'
        resp = json.loads(r.text)
        date_str = resp['sale']['end_date']
        date_format = '%Y-%m-%d %H:%M:%S'
        return datetime.strptime(date_str, date_format)

    def downloadable_files(self, s: requests.Session = None) -> List:
        """Get details about a game, including it's CDN URls
       
        Args:
            s (Session): The session used to get the download links"""
        if s is None:
            s = requests.session()
            s.headers.update(headers={'User-Agent': f'ItchClaim {__version__}'})
            s.get('https://itch.io/')
        csrf_token = urllib.parse.unquote(s.cookies['itchio_token'])

        r = s.post(self.url + '/download_url', json={'csrf_token': csrf_token})
        r.encoding = 'utf-8'
        resp = json.loads(r.text)
        if 'errors' in resp:
            print(f"ERROR: Failed to get download links for game {self.name} (url: {self.url})")
            print(f"\t{resp['errors'][0]}")
            return
        download_page = json.loads(r.text)['url']
        r = s.get(download_page)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        uploads_div = soup.find_all('div', class_='upload')
        uploads = []
        for upload_div in uploads_div:
            uploads.append(self.parse_download_div(upload_div, s))
        return uploads

    def parse_download_div(self, div: Tag, s: requests.Session):
        """Extract details about a game. 
        
        Args:
            div (Tag): A div containing download information
            s (Session): The session used to get the download links

        Returns:
            dict: Details about the game's files"""
        id = int(div.find('a', class_ = 'button download_btn').attrs['data-upload_id'])

        # Upload Date
        upload_date_raw = div.find('div', class_ = 'upload_date').find('abbr').attrs['title']
        date_format = '%d %B %Y @ %H:%M'
        upload_date = datetime.strptime(upload_date_raw, date_format)

        # Platforms
        platforms = []
        # List of every platform available on itch.io
        ITCHIO_PLATFORMS = ['windows8', 'android', 'tux', 'apple']
        platforms_span = div.find('span', class_ = 'download_platforms')
        if platforms_span is not None:
            for platform in ITCHIO_PLATFORMS:
                if platforms_span.find('span', class_ = f'icon icon-{platform}'):
                    platforms.append(platform)

        # Get download url
        csrf_token = urllib.parse.unquote(s.cookies['itchio_token'])
        r = s.post(self.url + f'/file/{id}',
                    json={'csrf_token': csrf_token},
                    params={'source': 'game_download'})
        r.encoding = 'utf-8'
        download_url= json.loads(r.text)['url']

        return {
            'id': id,
            'name': div.find('strong', class_ = 'name').text,
            'file_size': div.find('span', class_ = 'file_size').next.text,
            'upload_date': upload_date.timestamp(),
            'platforms': platforms,
            'url': download_url,
        }

    def serialize_min(self):
        """Returns a serialized object containing minimal information about the object"""
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'claimable': self.claimable,
            'sales': Sale.serialize_list(self.sales),
        }
    
    @staticmethod
    def get_games_dir() -> str:
        """Returns default directory for user storage"""
        if ItchGame.custom_dir:
            path = ItchGame.custom_dir
        else:
            path = os.path.join(user_data_dir('itchclaim', False), 'games')
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path

class Sale:
    def __init__(self, id: int, end: datetime = None, start: datetime = None, first: bool = False) -> None:
        self.id: int = id
        self.end: datetime = end
        self.start: datetime = start
        self.first: bool = first


    def serialize(self):
        dict = {
            'id': self.id,
        }
        if self.start:
            dict['start'] = int(self.start.timestamp())
        if self.end:
            dict['end'] = int(self.end.timestamp())
        return dict


    @classmethod
    def from_dict(self, dict: dict):
        id = dict['id']
        sale: Sale = Sale(id)
        if 'start' in dict:
            sale.start = datetime.fromtimestamp(dict['start'])
        if 'end' in dict:
            sale.end = datetime.fromtimestamp(dict['end'])
        return sale

    
    @staticmethod
    def serialize_list(list: List):
        return [ sale.serialize() for sale in list ]


    @property
    def is_active(self):
        if self.start and datetime.now() < self.start:
            return False
        if self.end and datetime.now() > self.end:
            return False
        return True

    @property
    def is_upcoming(self):
        return self.start and datetime.now() < self.start
