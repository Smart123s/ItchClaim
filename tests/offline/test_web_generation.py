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

import json
import time
import pytest

from ItchClaim.ItchGame import ItchGame
from ItchClaim.ItchSale import ItchSale
from ItchClaim.web import generate_web


def test_generate_web_dashboard_and_resume_index(tmp_path):
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    api_dir = web_dir / "api"
    api_dir.mkdir()

    # Create resume_index.txt
    resume_file = web_dir / "resume_index.txt"
    resume_file.write_text("98765", encoding="utf-8")

    now = int(time.time())
    active_sale = ItchSale(id=1, start_date=now - 100, end_date=now + 100)
    upcoming_sale = ItchSale(id=2, start_date=now + 200, end_date=now + 400)

    game_active = ItchGame(
        id=10,
        name="Currently Active Game",
        url="https://itch.io/active-game",
        claimable=True,
        sales=[active_sale],
    )
    game_upcoming = ItchGame(
        id=20,
        name="Future Upcoming Game",
        url="https://itch.io/upcoming-game",
        claimable=False,
        sales=[upcoming_sale],
    )

    generate_web([game_active, game_upcoming], str(web_dir))

    # Verify index.html embeds resume index and game data
    index_html = web_dir / "index.html"
    assert index_html.exists()
    content = index_html.read_text(encoding="utf-8")
    assert "98765" in content
    assert "Currently Active Game" in content
    assert "Future Upcoming Game" in content

    # Verify JSON API files
    active_json = api_dir / "active.json"
    assert active_json.exists()
    active_data = json.loads(active_json.read_text(encoding="utf-8"))
    assert len(active_data) == 1
    assert active_data[0]["id"] == 10

    upcoming_json = api_dir / "upcoming.json"
    assert upcoming_json.exists()
    upcoming_data = json.loads(upcoming_json.read_text(encoding="utf-8"))
    assert len(upcoming_data) == 1
    assert upcoming_data[0]["id"] == 20

    all_json = api_dir / "all.json"
    assert all_json.exists()
    all_data = json.loads(all_json.read_text(encoding="utf-8"))
    assert len(all_data) == 2


def test_generate_web_fallback_when_resume_index_missing(tmp_path):
    web_dir = tmp_path / "web_no_index"
    web_dir.mkdir()
    api_dir = web_dir / "api"
    api_dir.mkdir()

    now = int(time.time())
    sale = ItchSale(id=1, start_date=now - 50, end_date=now + 50)
    game = ItchGame(id=1, name="Solo Game", url="https://itch.io/solo", sales=[sale])

    # Should safely fallback to resume_index = 0
    generate_web([game], str(web_dir))

    index_html = web_dir / "index.html"
    assert index_html.exists()
    content = index_html.read_text(encoding="utf-8")
    assert "Solo Game" in content
