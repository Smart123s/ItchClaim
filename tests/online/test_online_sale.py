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
from ItchClaim.ItchSale import ItchSale


@pytest.mark.online
def test_live_sale_parsing():
    """Live test checking that an itch.io public sale page can be retrieved and parsed."""
    sale_id = 161971
    sale = ItchSale(sale_id)

    assert sale.err is None
    assert sale.id == sale_id
    assert isinstance(sale.start_date, int)
    assert isinstance(sale.end_date, int)
    assert sale.start_date > 0
    assert sale.end_date > sale.start_date
    assert sale.soup is not None
