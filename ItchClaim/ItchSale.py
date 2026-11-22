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
import re
import time
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from bs4 import BeautifulSoup
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from . import __version__
from .CfWrapper import CfWrapper
from .database import Base, game_sales

if TYPE_CHECKING:
    from .ItchGame import ItchGame


class ItchSale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_date: Mapped[int] = mapped_column(Integer, nullable=False)
    end_date: Mapped[int] = mapped_column(Integer, nullable=False)

    games: Mapped[List["ItchGame"]] = relationship(
        "ItchGame",
        secondary=game_sales,
        back_populates="sales",
    )

    def __init__(
        self,
        id: int,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.id = id
        self.err: Optional[str] = None
        self.start_date = start_date
        self.end_date = end_date

        if self.start_date is None or self.end_date is None:
            self.get_data_online()

    def get_data_online(self):
        sale_url = f"https://itch.io/s/{self.id}"
        s = CfWrapper()
        r = s.get(sale_url,
                headers={
                    'User-Agent': f'ItchClaim {__version__}',
                    'Accept-Language': 'en-GB,en;q=0.9',
                    }, timeout=32)
        r.encoding = 'utf-8'

        if r.status_code == 404:
            if r.url == sale_url:
                self.err = 'NO_MORE_SALES_AVAILABLE'
            else:
                print(f'Sale page #{self.id}: 404 Not Found')
                self.err = '404_NOT_FOUND'
            return

        # Used by DiskManager.get_one_sale()
        self.soup = BeautifulSoup(r.text, 'html.parser')

        date_format = '%Y-%m-%dT%H:%M:%SZ'
        sale_data = json.loads(re.findall(r'init_Sale.+, (.+)\);i', r.text)[0])
        self.start_date = int(datetime.strptime(sale_data['start_date'], date_format).timestamp())
        self.end_date = int(datetime.strptime(sale_data['end_date'], date_format).timestamp())

        if self.id != sale_data['id']:
            raise ValueError(f'Sale ID mismatch in parsed <script> tag. Excepted {self.id}')

    def serialize(self):
        return {
            'id': self.id,
            'start': self.start_date,
            'end': self.end_date,
        }

    @classmethod
    def from_dict(cls, dict: dict):
        id = dict['id']
        start_date = dict['start']
        end_date = dict['end']
        return cls(id, start_date=start_date, end_date=end_date)

    @staticmethod
    def serialize_list(list: List):
        return [sale.serialize() for sale in list]

    @property
    def is_active(self) -> bool:
        if self.start_date and self.end_date:
            now = int(time.time())
            return self.start_date < now < self.end_date
        return False

    @property
    def is_upcoming(self) -> bool:
        if self.start_date:
            return int(time.time()) < self.start_date
        return False
