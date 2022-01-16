import pytest

@pytest.mark.skip("Can only be executed locally at this moment")
def test_latest_announcement():
    from gateio_new_coins_announcements_bot.new_listings_scraper import get_announcement

    assert get_announcement()

@pytest.mark.skip("Still needs patching to work")
def test_get_last_coin_binance_detects_first_coin_in_single_coin_announcement():
    """
    Makes sure that the coin listed in the announcement is 
    """
    from gateio_new_coins_announcements_bot.new_listings_scraper import get_last_coin

    #TODO: patch get_announcement() to return fake coin announcement
    latest_announcement = "Binance Will List JOE (JOE)"

    assert get_last_coin() == "JOE"

test_get_last_coin_binance_detects_first_coin_in_single_coin_announcement()

@pytest.mark.skip("Still needs patching to work")
def test_get_last_coin_binance_detects_first_coin_in_multi_coin_announcement():
    """
    Makes sure that the first coin in a multi coin announcement is the one that is returned if it's not already listed
    """
    from gateio_new_coins_announcements_bot.new_listings_scraper import get_last_coin

    #TODO: patch get_announcement() to return fake coin announcement
    latest_announcement= "Binance Will List Alchemy Pay (ACH) and Immutable X (IMX)"
    assert get_last_coin() == "ACH"

@pytest.mark.skip("Still needs patching to work")
def test_get_last_coin_binance_detects_second_coin_in_multi_coin_announcement_first_invalid():
    """
    Makes sure that the first coin in the announcement is not returned if it is not available or already listed
    """
    from gateio_new_coins_announcements_bot.new_listings_scraper import get_last_coin

    #TODO: patch get_announcement() to return fake coin announcement
    latest_announcement= "Binance Will List Alchemy Pay (ACH) and Immutable X (IMX)"
    assert get_last_coin() == "IMX"


@pytest.mark.skip("Still needs patching to work")
def test_get_last_coin_binance_detects_no_coin_in_non_listing_coin_announcement():
    """
    Makes sure that the coin is only returned if its an actual listing on Binance Spot
    """
    from gateio_new_coins_announcements_bot.new_listings_scraper import get_last_coin

    #TODO: patch get_announcement() to return fake coin announcement
    latest_announcement = "Introducing Highstreet (HIGH) on Binance Launchpool! Farm HIGH by Staking BNB and BUSD Tokens"
    assert get_last_coin() == None

@pytest.mark.skip("Still needs patching to work")
def test_get_last_coin_binance_detects_no_coin_in_non_listing_coin_announcement():
    """
    Makes sure that the coin is only returned if its an actual listing on Binance Spot
    """
    from gateio_new_coins_announcements_bot.new_listings_scraper import get_last_coin

    #TODO: patch get_announcement() to return fake coin announcement
    latest_announcement = "Binance Will List Convex Finance (CVX) and ConstitutionDAO (PEOPLE) in the Innovation Zone"
    assert get_last_coin() == None


@pytest.mark.skip("Still needs patching to work")
def test_get_last_coin_kucoin_detects_first_coin_in_single_coin_announcement_with_world_premiere_string():
    """
    Makes sure that kucoin announcements are detected correctly if annoucement contains "World Premiere" string
    """
    from gateio_new_coins_announcements_bot.new_listings_scraper import get_last_coin

    #TODO: patch get_announcement() to return fake coin announcement
    #TODO: patch to enable kucoin scraping
    latest_announcement = "Pledge (PLGR) Gets Listed on KuCoin! World Premiere!"
    assert get_last_coin() == "PLGR"


@pytest.mark.skip("Still needs patching to work")
def test_get_last_coin_kucoin_detects_first_coin_in_single_coin_announcement_without_world_premiere_string():
    """
    Makes sure that kucoin announcements are detected correctly if annoucement does not contain "World Premiere" string
    """
    from gateio_new_coins_announcements_bot.new_listings_scraper import get_last_coin

    #TODO: patch get_announcement() to return fake coin announcement
    #TODO: patch to enable kucoin scraping
    latest_announcement = "QuickSwap (QUICK) Gets Listed on KuCoin!"
    assert get_last_coin() == "QUICK"