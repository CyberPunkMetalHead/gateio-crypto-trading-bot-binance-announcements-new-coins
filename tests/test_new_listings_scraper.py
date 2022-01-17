import pytest

# import os
# import sys

# currentdir = os.path.dirname(os.path.realpath(__file__))
# parentdir = os.path.dirname(currentdir)
# sys.path.append(parentdir)


@pytest.mark.skip("Can only be executed locally at this moment")
def test_latest_announcement():
    from gateio_new_coins_announcements_bot.new_listings_scraper import get_announcement

    assert get_announcement()
