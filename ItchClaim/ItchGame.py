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
from typing import List
from functools import cached_property
import json, requests, re, urllib, os
from bs4.element import Tag
from bs4 import BeautifulSoup
from .ItchSale import ItchSale
from . import __version__

class ItchGame:
    games_dir: str = 'web/data/'

    def __init__(self, id: int):
        self.id = id
        self.name: str = None
        self.url: str = None
        self.price: float = None
        self.sales: List[ItchSale] = []
        self.cover_image: str = None

    @classmethod
    def from_div(cls, div: Tag):
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
            price_str = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", price_element.text)[0]
            self.price = float(price_str)
        else:
            # some obscure games have no price (they are always free) and are also
            # discounted by 100% and are claimable, for example:
            # https://web.archive.org/web/20230308004149/https://itch.io/s/88108/100-discount
            api_data = ItchGame.from_api(self.url)

            # only 100% sales are collected by the from_api() method
            # this filters free games in bundles, for example:
            # https://web.archive.org/web/20230328044337/https://itch.io/s/92359/easter-sale
            # https://web.archive.org/web/20230328044523/https://ninjadalua.itch.io/dvirus/data.json
            if len(api_data.sales) != 0:
                self.price = api_data.price
        return self

    def save_to_disk(self):
        """Save the details of game to the disk"""
        os.makedirs(ItchGame.games_dir, exist_ok=True)
        data = {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'price': self.price,
            'claimable': self.claimable,
            'sales': ItchSale.serialize_list(self.sales),
            'cover_image': self.cover_image,
        }
        with open(self.get_default_game_filename(), 'w', encoding='utf-8') as f:
            f.write(json.dumps(data))

    @classmethod
    def load_from_disk(cls, path: str):
        """Load cached details about game from the disk"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
        id = data['id']
        self = ItchGame(id)
        self.name = data['name']
        self.url = data['url']
        self.price = data['price']
        self.sales = [ ItchSale.from_dict(sale) for sale in data['sales'] ]
        if data['claimable'] is not None:
            self.claimable = data['claimable']
        self.cover_image = data['cover_image']
        return self

    @classmethod
    def from_api(cls, url: str):
        """Get details about a game from the itch.io API
        
        Args:
            url (str): the url of the game
            
        Returns:
            An ItchGame instance, containing the data returned by the API"""
        # remove tailing slash from url
        if url[-1] == '/':
            url = url[:-1]

        r = requests.get(url + '/data.json',
                        headers={'User-Agent': f'ItchClaim {__version__}'},
                        timeout=8,)
        r.encoding = 'utf-8'
        resp = json.loads(r.text)

        if 'errors' in resp:
            print(f'Failed to get game {url} from API: {resp["errors"][0]}')
            return None

        game_id = resp['id']
        game = ItchGame(game_id)

        game.url = url
        game.price = float(resp['price'][1:])
        game.name = resp['title']
        game.cover_image = resp['cover_image']

        if resp['sale'] and resp['sale']['rate'] == 100:
            # Don't even bother with parsing the end date, because the JSON we have doesn't have the start date of the sale,
            # so ItchSale will update both dates regardless of what data we pass it here.
            game.sales = [ItchSale(resp['sale']['id'])]

        return game

    def get_default_game_filename(self) -> str:
        """Get the default path of the game's cache file"""
        sessionfilename = f'{self.id}.json'
        return os.path.join(ItchGame.games_dir, sessionfilename)

    @cached_property
    def claimable(self) -> bool:
        if not self.active_sale:
            return None
        r = requests.get(self.url, timeout=8)
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

    @cached_property
    def active_sale(self) -> ItchSale:
        active_sales = list(filter(lambda a: a.is_active, self.sales))
        if len(active_sales) == 0:
            return None
        return min(active_sales, key=lambda a: a.end)

    @property
    def last_upcoming_sale(self) -> ItchSale:
        last_sale = max(self.sales, key=lambda a: a.start)
        if not last_sale.is_upcoming:
            return None
        return last_sale

    @property
    def is_first_sale(self) -> bool:
        return len(self.sales) == 1

    def downloadable_files(self, s: requests.Session = None) -> List:
        """Get details about a game, including it's CDN URls
       
        Args:
            s (Session): The session used to get the download links"""
        if s is None:
            s = requests.session()
            s.headers.update({'User-Agent': f'ItchClaim {__version__}'})
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
            'sales': ItchSale.serialize_list(self.sales),
        }
