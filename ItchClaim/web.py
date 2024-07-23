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

from datetime import datetime
import json
import os
from string import Template
from typing import List
import importlib.resources as pkg_resources

from .ItchGame import ItchGame

DATE_FORMAT = '<span>%Y-%m-%d</span> <span>%H:%M</span>'
ROW_TEMPLATE = Template("""<tr>
        <td>$name</td>
        <td style="text-align:center">$sale_date</td>
        <td style="text-align:center" title="First sale">$first_sale</td>
        <td style="text-align:center" title="$claimable_text">$claimable_icon</td>
        <td><a href="$url" title="URL">&#x1F310;</a></td>
        <td><a href="./data/$id.json" title="JSON data">&#x1F4DC;</a></td>
    </tr>""")

def generate_web(games: List[ItchGame], web_dir: str):
    template = Template(pkg_resources.read_text(__package__, 'index.template.html'))
    games.sort(key=lambda a: (-1*a.sales[-1].id, a.name))

    # Load resume index

    try:
        with open(os.path.join(web_dir, 'data', 'resume_index.txt'), 'r', encoding='utf-8') as f:
            resume_index = int(f.read())
    except FileNotFoundError:
        resume_index = 0

    # ======= HTML =======

    active_sales = list(filter(lambda game: game.active_sale, games))
    active_sales_rows = generate_rows(active_sales, 'active')

    upcoming_sales = list(filter(lambda game: game.last_upcoming_sale, games))
    upcoming_sales_rows = generate_rows(upcoming_sales, 'upcoming')

    html = template.substitute(
            active_sales_rows = '\n'.join(active_sales_rows),
            upcoming_sales_rows = '\n'.join(upcoming_sales_rows),
            last_update = datetime.now().strftime(DATE_FORMAT),
            last_sale = resume_index,
        )

    with open(os.path.join(web_dir, 'index.html'), 'w', encoding="utf-8") as f:
        f.write(html)

    # ======= JSON (active sales) =======
    active_sales_min = [ game.serialize_min() for game in active_sales ]
    with open(os.path.join(web_dir, 'api', 'active.json'), 'w', encoding="utf-8") as f:
        f.write(json.dumps(active_sales_min))

    # ======= JSON (upcoming sales) =======
    upcoming_sales_min = [ game.serialize_min() for game in upcoming_sales ]
    with open(os.path.join(web_dir, 'api', 'upcoming.json'), 'w', encoding="utf-8") as f:
        f.write(json.dumps(upcoming_sales_min))

    # ======= JSON (all sales) =======
    all_min = [ game.serialize_min() for game in games ]
    with open(os.path.join(web_dir, 'api', 'all.json'), 'w', encoding="utf-8") as f:
        f.write(json.dumps(all_min))

def generate_rows(games: List[ItchGame], type: str) -> List[str]:
    rows: List[str] = []
    for game in games:
        if game.claimable == False:
            claimable_text = 'Not claimable'
            claimable_icon = '&#x274C;'
        elif game.claimable == True:
            claimable_text = 'claimable'
            claimable_icon = '&#x2714;'
        else:
            claimable_text = 'Unknown'
            claimable_icon = '&#x1F551;'
        
        if type == 'active':
            sale_date = game.active_sale.end
        elif type == 'upcoming':
            sale_date = game.last_upcoming_sale.start

        rows.append(ROW_TEMPLATE.substitute(
            name = game.name,
            sale_date = sale_date.strftime(DATE_FORMAT),
            first_sale = '&#x1F947;' if game.is_first_sale else '',
            claimable_text = claimable_text,
            claimable_icon = claimable_icon,
            url = game.url,
            id = game.id,
        ))
    return rows
