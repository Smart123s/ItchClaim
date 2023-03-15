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
from string import Template
from typing import List
from .. import DiskManager

DATE_FORMAT = '<span>%Y-%m-%d</span> <span>%H:%M</span>'
ROW_TEMPLATE = Template("""<tr>
        <td>$name</td>
        <td style="text-align:center">$sale_end</td>
        <td style="text-align:center" title="$claimable_text">$claimable_icon</td>
        <td><a href="$url" title="URL">&#x1F310;</a></td>
        <td><a href="./data/$id.json" title="JSON data">&#x1F4DC;</a></td>
    </tr>""")

def generate_html(games):
    with open('ItchClaim/web/template.html', 'r') as f:
        template = Template(f.read())
    games.sort(key=lambda a: (-1*a.sales[-1].id, a.name))
    rows: List[str] = []
    for game in games:
        rows.append(ROW_TEMPLATE.substitute(
            name = game.name,
            sale_end = game.sale_end.strftime(DATE_FORMAT),
            claimable_text = 'Claimable' if game.claimable else 'Not claimable',
            claimable_icon = '&#x2714;' if game.claimable else '&#x274C;',
            url = game.url,
            id = game.id,
        ))
    return template.substitute(
            rows = '\n'.join(rows),
            last_update = datetime.now().strftime(DATE_FORMAT),
        )