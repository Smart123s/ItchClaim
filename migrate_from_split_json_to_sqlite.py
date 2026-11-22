#!/usr/bin/env python3
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

import argparse
import glob
import json
import os
import sys
from typing import Dict

from ItchClaim.ItchGame import ItchGame
from ItchClaim.ItchSale import ItchSale
from ItchClaim.database import get_db_session, init_db


def migrate(legacy_dir: str, database_file: str):
    if not os.path.isdir(legacy_dir):
        print(f"Error: Legacy directory '{legacy_dir}' does not exist.")
        sys.exit(1)

    json_files = sorted(glob.glob(os.path.join(legacy_dir, "*.json")))
    if not json_files:
        print(f"No JSON files found in '{legacy_dir}'.")
        return

    print(f"Found {len(json_files)} game JSON files in '{legacy_dir}'.")

    db_dir = os.path.dirname(database_file) or "."
    os.makedirs(db_dir, exist_ok=True)
    ItchGame.database_file = database_file

    init_db(database_file)

    migrated_games = 0
    sales_cache: Dict[int, ItchSale] = {}

    with get_db_session(database_file) as session:
        # Preload existing sales if db already has records
        for existing_sale in session.query(ItchSale).all():
            sales_cache[existing_sale.id] = existing_sale

        for filepath in json_files:
            if os.path.getsize(filepath) == 0:
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to read {filepath}: {e}")
                continue

            game_id = data["id"]
            name = data.get("name", "")
            url = data.get("url", "")
            price = data.get("price")
            claimable = data.get("claimable")
            cover_image = data.get("cover_image")

            game = session.get(ItchGame, game_id)
            if game is None:
                game = ItchGame(
                    id=game_id,
                    name=name,
                    url=url,
                    price=price,
                    claimable=claimable,
                    cover_image=cover_image,
                )
                session.add(game)
            else:
                game.name = name
                game.url = url
                game.price = price
                game.claimable = claimable
                game.cover_image = cover_image

            game_sales = []
            for s in data.get("sales", []):
                sale_id = s["id"]
                start_date = s["start"]
                end_date = s["end"]

                if sale_id in sales_cache:
                    sale = sales_cache[sale_id]
                    sale.start_date = start_date
                    sale.end_date = end_date
                else:
                    sale = ItchSale(id=sale_id, start_date=start_date, end_date=end_date)
                    session.add(sale)
                    sales_cache[sale_id] = sale

                game_sales.append(sale)

            game.sales = game_sales
            migrated_games += 1

    print(f"Successfully migrated {migrated_games} games and {len(sales_cache)} distinct sales to '{database_file}'.")
    legacy_resume = os.path.join(legacy_dir, "resume_index.txt")
    target_resume = os.path.join(db_dir, "resume_index.txt")
    print(f"Note: The default path for resume_index.txt has changed from '{legacy_resume}' to '{target_resume}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate legacy split per-game JSON files into a single SQLite database.\n"
                    "Note: The default path for resume_index.txt has changed from web/data/resume_index.txt "
                    "to web/resume_index.txt (alongside data.db)."
    )
    parser.add_argument(
        "--legacy-dir",
        default="web/data/",
        help="Directory containing legacy JSON files (default: web/data/)",
    )
    parser.add_argument(
        "--database-file",
        default="web/data.db",
        help="Path to the destination SQLite database file (default: web/data.db)",
    )

    args = parser.parse_args()
    migrate(
        legacy_dir=args.legacy_dir,
        database_file=args.database_file,
    )


if __name__ == "__main__":
    main()
