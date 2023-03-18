from typing import List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from . import __version__


class ItchSale:
    def __init__(self, id: int, end: datetime = None, start: datetime = None, first: bool = False) -> None:
        self.id: int = id
        self.end: datetime = end
        self.start: datetime = start
        self.first: bool = first
        self.err: str = None

        if not start and not end:
            self.get_data_online()

        # if sale was saved as upcoming but has started since then
        elif self.start and not self.end and datetime.now() > self.start:
            self.err = 'STATUS_UPDATED'
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

        self.soup = BeautifulSoup(r.text, 'html.parser')

        date_format = '%Y-%m-%dT%H:%M:%SZ'
        sale_date_raw = self.soup.find('span', class_='date_format').text
        sale_date = datetime.strptime(sale_date_raw, date_format)

        # Is the date shown on the site a start or an end?
        not_active_div = self.soup.find('div', class_="not_active_notification")
        if not_active_div and 'Come back ' in not_active_div.text:
            self.start = sale_date
        else:
            self.end = sale_date


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
        start = datetime.fromtimestamp(dict['start']) if 'start' in dict else None
        end = datetime.fromtimestamp(dict['end']) if 'end' in dict else None
        return ItchSale(id, start=start, end=end)


    @staticmethod
    def serialize_list(list: List):
        return [ sale.serialize() for sale in list ]


    @property
    def is_active(self):
        if self.end and datetime.now() < self.end:
            return True
        return False


    @property
    def is_upcoming(self):
        return self.start and datetime.now() < self.start
