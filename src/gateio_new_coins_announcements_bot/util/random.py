import random
import string


def random_str():
    """
    Returns a random string of random length, between 10 and 20 characters.
    """
    letters = string.ascii_letters
    return "".join(random.choice(letters) for i in range(random.randint(10, 20)))


def random_int(maxInt=99999999999999999999):
    """
    Returns a random positiveinteger
    """
    return random.randint(1, maxInt)
