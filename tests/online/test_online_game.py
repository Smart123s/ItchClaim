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

import pytest
from ItchClaim.ItchGame import ItchGame


@pytest.mark.online
def test_live_game_from_api():
    """Live test checking that itch.io game /data.json API endpoint returns valid game metadata."""
    game_url = "https://easypeazygames.itch.io/nouveau-pix-pink"
    game = ItchGame.from_api(game_url)

    assert game is not None
    assert isinstance(game.id, int)
    assert game.id > 0
    assert "Nouveau Pix" in game.name
    assert game.url == game_url
    assert isinstance(game.price, (float, int))
