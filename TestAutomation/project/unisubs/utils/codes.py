"""
Codes
-----

Codes are randomized strings used to generate unique identifiers or
cryptographic nonces.  Codes are made up of the upper/lower case letters, digits, "-", and "_".  This makes for an alphabet of 64 characters.

Codes are created using SystemRandom, so they should not be possible to
predict by an attacker.
"""

import math
import string
from random import SystemRandom

random = SystemRandom()

class CodeGenerator(object):
    def __init__(self, alphabet):
        self.alphabet = alphabet

    def __call__(self, length):
        return ''.join(random.sample(self.alphabet, length))

_make_code_generator = CodeGenerator(
    string.uppercase + string.lowercase + string.digits + '-_'
)
def make_code(bits_needed=64):
    """Make a new code

    Args:
        bits_needed: number of bits needed.  The code will be long enough to
        include at least this many bits.
    """
    # 64 letter alphabet means each char is 6 bits.
    length = int(math.ceil(bits_needed / 6.0))
    return _make_code_generator(length)
