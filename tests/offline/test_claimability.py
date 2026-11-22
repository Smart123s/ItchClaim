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

import time
from unittest.mock import MagicMock, patch
import pytest

from ItchClaim.ItchGame import ItchGame
from ItchClaim.ItchSale import ItchSale


def test_claimability_no_active_sale():
    game = ItchGame(id=1, name="Game Without Sale", url="https://dev.itch.io/no-sale")
    result = game.check_claimability()
    assert result is None
    assert game.claimable is None


def test_claimability_download_or_claim():
    now = int(time.time())
    active_sale = ItchSale(id=1, start_date=now - 100, end_date=now + 100)
    game = ItchGame(id=2, name="Free Claimable Game", url="https://dev.itch.io/claimable", sales=[active_sale])

    mock_html = """
    <html><body>
        <div class="buy_row">
            <a class="button buy_btn">Download or claim</a>
        </div>
    </body></html>
    """
    with patch.object(game.s, "get", return_value=MagicMock(text=mock_html)):
        assert game.check_claimability() is True
        assert game.claimable is True


def test_claimability_buy_now():
    now = int(time.time())
    active_sale = ItchSale(id=1, start_date=now - 100, end_date=now + 100)
    game = ItchGame(id=3, name="Purchase Required Game", url="https://dev.itch.io/buy-now", sales=[active_sale])

    mock_html = """
    <html><body>
        <div class="buy_row">
            <a class="button buy_btn">Buy Now $5.00</a>
        </div>
    </body></html>
    """
    with patch.object(game.s, "get", return_value=MagicMock(text=mock_html)):
        assert game.check_claimability() is None
        assert game.claimable is None


def test_claimability_html5_no_buy_row():
    now = int(time.time())
    active_sale = ItchSale(id=1, start_date=now - 100, end_date=now + 100)
    game = ItchGame(id=4, name="Browser HTML5 Game", url="https://dev.itch.io/html5-game", sales=[active_sale])

    # No div class="buy_row"
    mock_html = "<html><body><div>Play in browser only</div></body></html>"
    with patch.object(game.s, "get", return_value=MagicMock(text=mock_html)):
        assert game.check_claimability() is False
        assert game.claimable is False


def test_claimability_no_buy_button():
    now = int(time.time())
    active_sale = ItchSale(id=1, start_date=now - 100, end_date=now + 100)
    game = ItchGame(id=5, name="No Button Game", url="https://dev.itch.io/no-button", sales=[active_sale])

    mock_html = """
    <html><body>
        <div class="buy_row">
            <span class="info">Sale ended early</span>
        </div>
    </body></html>
    """
    with patch.object(game.s, "get", return_value=MagicMock(text=mock_html)):
        assert game.check_claimability() is False
        assert game.claimable is False
