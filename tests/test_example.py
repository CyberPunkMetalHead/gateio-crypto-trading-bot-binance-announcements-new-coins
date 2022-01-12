import re
from unittest import TestCase

from util.random import random_str, random_int


class RandomUtilsTest(TestCase):
    def test_random_str(self):
        str = random_str()
        assert len(str) >= 10 & len(str) <= 20
        assert re.match(r'[abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~]+', str)

    def test_random_int_default(self):
        int = random_int()
        assert int >= 1
        assert int <= 99999999999999999999

    def test_random_int_with_max(self):
        int = random_int(10)
        assert int >= 1
        assert int <= 10
