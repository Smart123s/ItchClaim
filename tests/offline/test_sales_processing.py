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

import os
import time
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
import pytest

from ItchClaim import DiskManager
from ItchClaim.database import init_db
from ItchClaim.ItchGame import ItchGame
from ItchClaim.ItchSale import ItchSale


def _build_sale_html(game_id: int, title: str, price_str: str) -> BeautifulSoup:
    html = f"""
    <html><body>
        <div class="game_cell" data-game_id="{game_id}">
            <a class="title game_link" href="https://dev.itch.io/{title.lower().replace(' ', '-')}">{title}</a>
            <div class="price_value">{price_str}</div>
        </div>
    </body></html>
    """
    return BeautifulSoup(html, "html.parser")


def test_finding_and_adding_sale_to_new_game(temp_db_path):
    init_db(temp_db_path)
    ItchGame.database_file = temp_db_path

    now = int(time.time())
    soup = _build_sale_html(game_id=101, title="New Adventure", price_str="$0.00")

    with patch("ItchClaim.DiskManager.ItchSale") as mock_sale_cls:
        real_sale = ItchSale(id=500, start_date=now - 100, end_date=now + 100)
        real_sale.err = None
        real_sale.soup = soup
        mock_sale_cls.return_value = real_sale

        with patch.object(ItchGame, "check_claimability", return_value=True):
            games_added = DiskManager.get_one_sale(500, force=False)

            assert games_added == 1
            saved_game = ItchGame.load_from_database(101, database_file=temp_db_path)
            assert saved_game is not None
            assert saved_game.name == "New Adventure"
            assert saved_game.price == 0.0
            assert len(saved_game.sales) == 1
            assert saved_game.sales[0].id == 500


def test_finding_and_adding_sale_to_existing_game(temp_db_path):
    init_db(temp_db_path)
    ItchGame.database_file = temp_db_path

    now = int(time.time())

    # Pre-populate database with an existing game and earlier sale
    sale_old = ItchSale(id=100, start_date=now - 1000, end_date=now - 500)
    existing_game = ItchGame(
        id=202,
        name="Sequel Quest",
        url="https://dev.itch.io/sequel-quest",
        price=0.0,
        sales=[sale_old],
    )
    existing_game.save_to_database(database_file=temp_db_path)

    # Process new sale 200 featuring that same game
    soup = _build_sale_html(game_id=202, title="Sequel Quest", price_str="$0.00")

    with patch("ItchClaim.DiskManager.ItchSale") as mock_sale_cls:
        real_new_sale = ItchSale(id=200, start_date=now - 50, end_date=now + 200)
        real_new_sale.err = None
        real_new_sale.soup = soup
        mock_sale_cls.return_value = real_new_sale

        with patch.object(ItchGame, "check_claimability", return_value=True):
            games_added = DiskManager.get_one_sale(200, force=False)

            assert games_added == 1
            updated_game = ItchGame.load_from_database(202, database_file=temp_db_path)
            assert updated_game is not None
            assert len(updated_game.sales) == 2
            assert [s.id for s in updated_game.sales] == [100, 200]


def test_handle_not_100_percent_sales(temp_db_path):
    init_db(temp_db_path)
    ItchGame.database_file = temp_db_path

    now = int(time.time())
    # Game with $4.99 price (e.g. only 50% discount, not 100%)
    soup = _build_sale_html(game_id=303, title="Paid Game With Partial Sale", price_str="$4.99")

    with patch("ItchClaim.DiskManager.ItchSale") as mock_sale_cls:
        real_sale = ItchSale(id=600, start_date=now - 50, end_date=now + 50)
        real_sale.err = None
        real_sale.soup = soup
        mock_sale_cls.return_value = real_sale

        games_added = DiskManager.get_one_sale(600, force=False)

        # Non-100% sale must be ignored and not saved to the database
        assert games_added == 0
        game = ItchGame.load_from_database(303, database_file=temp_db_path)
        assert game is None


def test_resume_index_usage_and_duplicate_skip(temp_db_path):
    init_db(temp_db_path)
    ItchGame.database_file = temp_db_path

    now = int(time.time())

    # Pre-populate database with game where sale 400 has already been saved as latest sale
    sale_already_saved = ItchSale(id=400, start_date=now - 100, end_date=now + 100)
    existing_game = ItchGame(
        id=404,
        name="Already Saved Game",
        url="https://dev.itch.io/already-saved",
        price=0.0,
        sales=[sale_already_saved],
    )
    existing_game.save_to_database(database_file=temp_db_path)

    # When get_one_sale is run again on sale 400 with force=False (e.g. wrong resume index)
    soup = _build_sale_html(game_id=404, title="Already Saved Game", price_str="$0.00")

    with patch("ItchClaim.DiskManager.ItchSale") as mock_sale_cls:
        sale_obj = ItchSale(id=400, start_date=now - 100, end_date=now + 100)
        sale_obj.err = None
        sale_obj.soup = soup
        mock_sale_cls.return_value = sale_obj

        games_added = DiskManager.get_one_sale(400, force=False)

        # Should skip adding and not duplicate the sale
        assert games_added == 0
        game = ItchGame.load_from_database(404, database_file=temp_db_path)
        assert len(game.sales) == 1


def test_get_all_sales_writes_resume_index_file(tmp_path):
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    resume_file = web_dir / "resume_index.txt"

    # Patch working directory / open so DiskManager writes to tmp_path/web/resume_index.txt
    with patch("ItchClaim.DiskManager.get_one_sale", return_value=1):
        with patch("builtins.open", side_effect=open) as mock_open:
            # We run a single page starting at 50, max_pages=1
            old_cwd = os.getcwd()
            os.chdir(str(tmp_path))
            try:
                DiskManager.get_all_sales(start=50, max_pages=1)
                assert resume_file.exists()
                saved_index = int(resume_file.read_text(encoding="utf-8"))
                assert saved_index == 51
            finally:
                os.chdir(old_cwd)
