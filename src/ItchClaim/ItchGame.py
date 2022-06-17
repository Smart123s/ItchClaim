# The MIT License (MIT)
# 
# Copyright (c) 2022 Péter Tombor.

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

import json, requests
from bs4.element import Tag
from bs4 import BeautifulSoup
from ItchContext import ItchContext

class ItchGame:
    def __init__(self, div: Tag):
        a = div.find('a', class_='title game_link')
        self.name = a.text
        self.url = a.attrs['href']

        price_element = div.find('div', attrs={'class': 'price_value'})
        # Some elements don't have a price defined
        if price_element != None:
            self.price = float(price_element.text[1:])
        else:
            self.price = -1
            self.claimable = False
            return

        #self.sale_percent (sometimes it's 50%, sometimes it's "In bundle")

        #TODO: Implement claimable check
        self.claimable = True

    def claim_game(self, context: ItchContext):
        r = context.s.post(context.url + '/download_url', json={'csrf_token': context.csrf_token})
        download_url = json.loads(r.text)['url']
        r = context.s.get(download_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        claim_url = soup.find('div', class_='claim_to_download_box warning_box').find('form')['action']
        r = context.s.post(claim_url, 
                        data={'csrf_token': context.csrf_token}, 
                        headers={ 'Content-Type': 'application/x-www-form-urlencoded'}
                        )
        print(r.url)
        # Success: https://dankoff.itch.io/sci-fi-wepon-pack/download/7LPhDDllv1SB__g9KhRzRS36Y7nF4Uefi2CbEKjS
        # Fail: https://itch.io/

    @staticmethod
    def get_sale_page(page: int):
        r = requests.get(f"https://itch.io/games/on-sale?page={page}&format=json")
        html = json.loads(r.text)['content']
        soup = BeautifulSoup(html, 'html.parser')
        games_raw = soup.find_all('div', class_="game_cell")
        games = []
        for div in games_raw:
            game_parsed = ItchGame(div)
            if game_parsed.price == 0 & game_parsed.claimable:
                games.append(game_parsed)
        return games

    @staticmethod
    def get_all_sales():
        pass
