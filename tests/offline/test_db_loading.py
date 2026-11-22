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
import pytest

from ItchClaim.database import init_db
from ItchClaim.ItchGame import ItchGame
from ItchClaim.ItchSale import ItchSale


def test_game_loaded_properly_from_db(temp_db_path):
    init_db(temp_db_path)

    now = int(time.time())
    active_sale = ItchSale(id=101, start_date=now - 500, end_date=now + 500)
    upcoming_sale = ItchSale(id=102, start_date=now + 600, end_date=now + 1200)

    original_game = ItchGame(
        id=42,
        name="Deep Space Exploration",
        url="https://cosmos.itch.io/deep-space",
        price=19.99,
        claimable=True,
        cover_image="https://img.itch.zone/deep-space-cover.jpg",
        sales=[active_sale, upcoming_sale],
    )

    # Persist the game and its sales to the SQLite database
    original_game.save_to_database(database_file=temp_db_path)

    # Load from database without refreshing claimability
    loaded_game = ItchGame.load_from_database(42, database_file=temp_db_path, refresh_claimable=False)

    assert loaded_game is not None
    assert loaded_game.id == 42
    assert loaded_game.name == "Deep Space Exploration"
    assert loaded_game.url == "https://cosmos.itch.io/deep-space"
    assert loaded_game.price == 19.99
    assert loaded_game.claimable is True
    assert loaded_game.cover_image == "https://img.itch.zone/deep-space-cover.jpg"

    # Verify associated sales are eagerly loaded and properly populated
    assert len(loaded_game.sales) == 2
    sale_ids = [s.id for s in loaded_game.sales]
    assert 101 in sale_ids
    assert 102 in sale_ids

    # Verify calculated sale properties work on the loaded game instance
    assert loaded_game.active_sale is not None
    assert loaded_game.active_sale.id == 101
    assert loaded_game.last_upcoming_sale is not None
    assert loaded_game.last_upcoming_sale.id == 102

    # Verify loading with refresh_claimable=True resets claimable to None for re-checking
    reloaded = ItchGame.load_from_database(42, database_file=temp_db_path, refresh_claimable=True)
    assert reloaded.claimable is None


def test_load_nonexistent_game(temp_db_path):
    init_db(temp_db_path)
    result = ItchGame.load_from_database(999999, database_file=temp_db_path)
    assert result is None
