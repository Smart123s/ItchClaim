# The MIT License (MIT)
#
# Copyright (c) 2022-2026 Péter Tombor.
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

import json
import os
import re
from datetime import datetime
from typing import List, Optional, Union
from bs4 import BeautifulSoup
from bs4.element import Tag
from sqlalchemy import Boolean, Float, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship, selectinload
from . import __version__
from .CfWrapper import CfWrapper
from .database import Base, game_sales, get_db_session
from .ItchSale import ItchSale


class ItchGame(Base):
    __tablename__ = "games"

    games_dir: str = 'web/data/'
    database_file: str = 'web/data.db'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False, index=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    claimable: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    cover_image: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    sales: Mapped[List[ItchSale]] = relationship(
        "ItchSale",
        secondary=game_sales,
        back_populates="games",
        order_by="ItchSale.id",
    )

    def __init__(
        self,
        id: int,
        name: Optional[str] = None,
        url: Optional[str] = None,
        price: Optional[float] = None,
        claimable: Optional[bool] = None,
        cover_image: Optional[str] = None,
        sales: Optional[List[ItchSale]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.id = id
        self.name = name
        self.url = url
        self.price = price
        self.cover_image = cover_image
        self.sales = sales if sales is not None else []
        self.claimable = claimable

    @property
    def s(self) -> CfWrapper:
        if not hasattr(self, "_s") or self._s is None:
            self._s = CfWrapper()
        return self._s

    @s.setter
    def s(self, value: CfWrapper):
        self._s = value

    def check_claimability(self) -> Optional[bool]:
        """Check online whether the game is claimable during its active sale"""
        if not self.active_sale:
            self.claimable = None
            return None
        r = self.s.get(self.url, timeout=32)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        buy_row = soup.find('div', class_='buy_row')
        if buy_row is None:
            # Game is probably WebGL or HTML5 only
            self.claimable = False
            return False
        buy_box = buy_row.find('a', class_='button buy_btn')
        if buy_box is None:
            # No buy button is visible, so it's probably not claimable
            self.claimable = False
            return False
        if 'Buy Now' in buy_box.text:
            self.claimable = None
            return None
        self.claimable = (buy_box.text == 'Download or claim')
        return self.claimable

    @property
    def active_sale(self) -> Optional[ItchSale]:
        active_sales = [a for a in self.sales if a.is_active]
        if not active_sales:
            return None
        return min(active_sales, key=lambda a: a.end_date)

    @property
    def last_upcoming_sale(self) -> Optional[ItchSale]:
        if not self.sales:
            return None
        last_sale = max(self.sales, key=lambda a: a.start_date)
        if not last_sale.is_upcoming:
            return None
        return last_sale

    @property
    def is_first_sale(self) -> bool:
        return len(self.sales) == 1

    @classmethod
    def from_div(cls, div: Tag, price_needed: bool = False):
        """Create an ItchGame Instance from a div that's found in tables on itch.io.
        These can usually be found on the sale or the my purchases page.
        
        Args:
            div (Tag): A bs4 div element, containing the data of a game
            price_needed (bool): wether to send another request to the API if the div has no
                information about the price"""
        id = int(div.attrs['data-game_id'])
        game = cls(id)
        a = div.find('a', class_='title game_link')
        game.name = a.text
        game.url = a.attrs['href']

        try:
            game.cover_image = div.find('div', class_='game_thumb').find('img').attrs['data-lazy_src']
        except Exception:
            game.cover_image = None

        price_element = div.find('div', attrs={'class': 'price_value'})
        # Some elements don't have a price defined
        if price_element is not None:
            price_str = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", price_element.text)[0]
            game.price = float(price_str)
        elif price_needed:
            # some obscure games have no price (they are always free) and are also
            # discounted by 100% and are claimable, for example:
            # https://web.archive.org/web/20230308004149/https://itch.io/s/88108/100-discount
            api_data = cls.from_api(game.url)

            # only 100% sales are collected by the from_api() method
            # this filters free games in bundles, for example:
            # https://web.archive.org/web/20230328044337/https://itch.io/s/92359/easter-sale
            # https://web.archive.org/web/20230328044523/https://ninjadalua.itch.io/dvirus/data.json
            if api_data is not None and len(api_data.sales) != 0:
                game.price = api_data.price
        return game

    def save_to_disk_json(self):
        """Save the details of game to the disk in JSON format"""
        os.makedirs(ItchGame.games_dir, exist_ok=True)
        with open(self.get_default_game_filename(), 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.serialize()))

    @classmethod
    def load_from_disk_json(cls, path: str, refresh_claimable: bool = False):
        """Load cached details about game from the disk (legacy JSON format)
        
        Args:
            path (str): The location of the JSON file that contains the data about the game
            refresh_claimable (bool): Check claimability online again
                Defaults to False
            """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
        id = data['id']
        game = cls(id)
        game.name = data['name']
        game.url = data['url']
        game.price = data['price']
        game.sales = [ItchSale.from_dict(sale) for sale in data['sales']]
        if data['claimable'] is not None and not refresh_claimable:
            game.claimable = data['claimable']
        game.cover_image = data['cover_image']
        return game

    def save_to_database(self, database_file: Optional[str] = None, session: Optional[Session] = None):
        """Save the details of game and its sales to the SQLite database"""
        if database_file is None:
            database_file = self.database_file

        if session is not None:
            session.merge(self)
            session.flush()
        else:
            with get_db_session(database_file) as s:
                s.merge(self)

    @classmethod
    def load_from_database(
        cls,
        id: int,
        database_file: Optional[str] = None,
        session: Optional[Session] = None,
        refresh_claimable: bool = False,
    ) -> Optional['ItchGame']:
        """Load cached details about game from SQLite database"""
        if database_file is None:
            database_file = cls.database_file
        def _load(s: Session) -> Optional['ItchGame']:
            stmt = select(cls).where(cls.id == id).options(selectinload(cls.sales))
            game = s.scalars(stmt).first()
            if game is None:
                return None
            if refresh_claimable:
                game.claimable = None
            return game

        if session is not None:
            return _load(session)
        else:
            with get_db_session(database_file) as s:
                game = _load(s)
                if game is not None:
                    s.expunge(game)
                    for sale in game.sales:
                        s.expunge(sale)
                return game

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

        s = CfWrapper()
        r = s.get(url + '/data.json',
                        headers={'User-Agent': f'ItchClaim {__version__}'},
                        timeout=32,)
        r.encoding = 'utf-8'
        resp = json.loads(r.text)

        if 'errors' in resp:
            if resp['errors'][0] in ('invalid game', 'invalid user'):
                # Check if the game's URL has been changed
                mock_game = cls(-1)
                mock_game.url = url
                if mock_game.check_redirect_url():
                    return cls.from_api(mock_game.url)
            print(f'Failed to get game {url} from API: {resp["errors"][0]}')
            return None

        game_id = resp['id']
        game = cls(game_id)

        game.url = url
        game.s = s

        # check for redirects in the request
        # sometimes it redirects /data.json requests, sometimes it doesn't
        # With redirect example: https://vronti.itch.io/hp-bar-assets-pack
        # https://web.archive.org/web/20231107063207/https://daions-studio.itch.io/hp-bar-assets-pack/data.json
        # Without redirect example: https://polygon-sphere.itch.io/rogue-ai/data.json
        # https://web.archive.org/web/20231107063001/https://polygon-sphere.itch.io/rogue-ai/data.json
        if len(r.history) > 0 and r.history[0].is_redirect:
            game.url = r.history[0].headers['Location'].replace('/data.json', '')
        try:
            game.price = float(resp['price'][1:])
        except KeyError:
            game.price = None
        game.name = resp['title']
        game.cover_image = resp['cover_image']

        if 'sale' in resp and resp['sale']['rate'] == 100:
            # Don't even bother with parsing the end date, because the JSON we have doesn't have the start date of the sale,
            # so ItchSale will update both dates regardless of what data we pass it here.
            game.sales = [ItchSale(resp['sale']['id'])]

        return game

    def get_default_game_filename(self) -> str:
        """Get the default path of the game's cache file"""
        sessionfilename = f'{self.id}.json'
        return os.path.join(ItchGame.games_dir, sessionfilename)

    def downloadable_files(self) -> List:
        """Get details about a game, including it's CDN URls"""

        r = self.s.post(self.url + '/download_url', json={'csrf_token': self.s.csrf_token})
        r.encoding = 'utf-8'
        resp = json.loads(r.text)
        if 'errors' in resp:
            print(f"ERROR: Failed to get download links for game {self.name} (url: {self.url})")
            print(f"\t{resp['errors'][0]}")
            return
        download_page = json.loads(r.text)['url']
        r = self.s.get(download_page)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        uploads_div = soup.find_all('div', class_='upload')
        uploads = []
        for upload_div in uploads_div:
            uploads.append(self.parse_download_div(upload_div))
        return uploads

    def parse_download_div(self, div: Tag):
        """Extract details about a game. 
        
        Args:
            div (Tag): A div containing download information

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
        r = self.s.post(self.url + f'/file/{id}',
                    json={'csrf_token': self.s.csrf_token},
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

    def serialize(self):
        """Returns a serialized object containing all information about the object"""
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'price': self.price,
            'claimable': self.claimable,
            'sales': ItchSale.serialize_list(self.sales),
            'cover_image': self.cover_image,
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

    def check_redirect_url(self):
        """Checks if a new URL is available for the game, and updates the current one
        Sends an HTTP HEAD requests to the original game's page, and follows HTTP 3xx redirects

        Returns:
            bool: True if a new URL is found"""
        resp_redirect = self.s.head(self.url)
        if not resp_redirect.is_redirect:
            return False
        self.url = resp_redirect.next.url
        self.claimable = None
        print(f"WARN: URL of game {self.name} has changed to {self.url}")
        return True
