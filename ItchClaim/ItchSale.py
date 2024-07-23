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

import json
import re
from typing import List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from . import __version__


class ItchSale:
    def __init__(self, id: int, end: datetime = None, start: datetime = None) -> None:
        self.id: int = id
        self.end: datetime = end
        self.start: datetime = start
        self.err: str = None

        if not start or not end:
            self.get_data_online()


    def get_data_online(self):
        sale_url = f"https://itch.io/s/{self.id}"
        r = requests.get(sale_url,
                headers={
                    'User-Agent': f'ItchClaim {__version__}',
                    'Accept-Language': 'en-GB,en;q=0.9',
                    }, timeout=8)
        r.encoding = 'utf-8'

        if r.status_code == 404:
            print(f'Sale page #{self.id}: 404 Not Found')
            if r.url == sale_url:
                self.err = 'NO_MORE_SALES_AVAILABLE'
            else:
                self.err = '404_NOT_FOUND'
            return

        # Used by DiskManager.get_one_sale()
        self.soup = BeautifulSoup(r.text, 'html.parser')

        date_format = '%Y-%m-%dT%H:%M:%SZ'
        sale_data = json.loads(re.findall(r'init_Sale.+, (.+)\);i', r.text)[0])
        self.start = datetime.strptime(sale_data['start_date'], date_format)
        self.end = datetime.strptime(sale_data['end_date'], date_format)

        if self.id != sale_data['id']:
            raise ValueError(f'Sale ID mismatch in parsed <script> tag. Excepted {self.id}')


    def serialize(self):
        return {
            'id': self.id,
            'start': int(self.start.timestamp()),
            'end': int(self.end.timestamp()),
        }


    @classmethod
    def from_dict(cls, dict: dict):
        id = dict['id']
        start = datetime.fromtimestamp(dict['start'])
        end = datetime.fromtimestamp(dict['end'])
        return ItchSale(id, start=start, end=end)


    @staticmethod
    def serialize_list(list: List):
        return [ sale.serialize() for sale in list ]


    @property
    def is_active(self):
        if datetime.now() < self.end and datetime.now() > self.start:
            return True
        return False


    @property
    def is_upcoming(self):
        return datetime.now() < self.start
