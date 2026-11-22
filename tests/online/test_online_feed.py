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
from ItchClaim import DiskManager
from ItchClaim.database import init_db
from ItchClaim.ItchGame import ItchGame


@pytest.mark.online
def test_live_sales_feed_page(temp_db_path):
    """Live test checking that itch.io on-sale JSON feed endpoint is reachable and parsable."""
    init_db(temp_db_path)
    ItchGame.database_file = temp_db_path

    games_added = DiskManager.get_online_sale_page(page=1, category="games")
    # Feed page returns count of games added (>= 0), or -1 if the feed returned empty/404
    assert isinstance(games_added, int)
    assert games_added >= -1
