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

import json, requests, re
from bs4.element import Tag
from bs4 import BeautifulSoup
from ItchUser import ItchUser

class ItchGame:
    def __init__(self, div: Tag):
        a = div.find('a', class_='title game_link')
        self.name = a.text
        self.url = a.attrs['href']

        price_element = div.find('div', attrs={'class': 'price_value'})
        # Some elements don't have a price defined
        if price_element != None:
            price_str = re.findall("[-+]?(?:\d*\.\d+|\d+)", price_element.text)[0]
            self.price = float(price_str)
        else:
            self.price = -1
            return

        #self.sale_percent (sometimes it's 50%, sometimes it's "In bundle")

    def is_game_owned(self, user: ItchUser):
        r = user.s.get(self.url, json={'csrf_token': user.csrf_token})
        soup = BeautifulSoup(r.text, 'html.parser')
        owned_box = soup.find('span', class_='ownership_reason')
        return owned_box != None

    def is_game_claimable(self):
        r = requests.get(self.url)
        soup = BeautifulSoup(r.text, 'html.parser')
        buy_row = soup.find('div', class_='buy_row')
        if buy_row is None:
            # Game is probably WebGL or HTML5 only
            return False
        buy_box = buy_row.find('a', class_='button buy_btn')
        claimable = buy_box.text == 'Download or claim'
        return claimable

    def claim_game(self, user: ItchUser):
        r = user.s.post(self.url + '/download_url', json={'csrf_token': user.csrf_token})
        resp = json.loads(r.text)
        if 'errors' in resp:
            print(f"ERROR: Failed to claim game {self.name} (url: {self.url})")
            print(f"\t{resp['errors'][0]}")
            return
        download_url = json.loads(r.text)['url']
        r = user.s.get(download_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        claim_box = soup.find('div', class_='claim_to_download_box warning_box')
        if claim_box == None:
            print(f"Game {self.name} is not claimable (url: {self.url})")
            return
        claim_url = claim_box.find('form')['action']
        r = user.s.post(claim_url, 
                        data={'csrf_token': user.csrf_token}, 
                        headers={ 'Content-Type': 'application/x-www-form-urlencoded'}
                        )
        if r.url == 'https://itch.io/':
            print(f"ERROR: Failed to claim game {self.name} (url: {self.url})")
        else:
            print(f"Successfully claimed game {self.name} (url: {self.url})")

    @staticmethod
    def get_sale_page(page: int):
        r = requests.get(f"https://itch.io/games/on-sale?page={page}&format=json")
        html = json.loads(r.text)['content']
        soup = BeautifulSoup(html, 'html.parser')
        games_raw = soup.find_all('div', class_="game_cell")
        games = []
        for div in games_raw:
            game_parsed = ItchGame(div)
            if game_parsed.price == 0:
                games.append(game_parsed)
        if len(games) == 0 and json.loads(r.text)["num_items"] == 0:
            return False
        return games

    @staticmethod
    def get_all_sales():
        pass
