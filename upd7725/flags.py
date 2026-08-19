"""The six bits each accumulator carries, and what sets them.

Two of the six are unusual and are the reason this is its own module. There are
two overflow bits rather than one, and two sign bits rather than one, and the
second of each pair is not a copy of the first.

The second sign follows the first only while no second overflow is held. Once one
is, the second sign freezes at whatever it held, so it records the sign the value
had before the word stopped being able to express it. The second overflow, in
turn, clears only when a fresh overflow arrives while one is already held and the
two signs have parted. That pair is how the part carries a value through a
sequence of sums that leave the word and come back, which is what a fixed point
routine does constantly.
"""

WORD = 0x10000

SIGN = 0x8000

MASK = 0x3F

NAMES = ("ov0", "ov1", "z", "c", "s0", "s1")


class Flags:
    """One accumulator's six bits."""

    __slots__ = NAMES

    def __init__(self):
        for name in NAMES:
            setattr(self, name, False)

    @classmethod
    def of(cls, word):
        """The set a word of six bits describes."""
        found = cls()
        for place, name in enumerate(NAMES):
            setattr(found, name, bool(word >> place & 1))
        return found

    def copy(self):
        return Flags.of(int(self))

    def __int__(self):
        word = 0
        for place, name in enumerate(NAMES):
            word |= int(getattr(self, name)) << place
        return word

    def __repr__(self):
        held = [name for name in NAMES if getattr(self, name)]
        return f"<Flags {' '.join(held) if held else 'none'}>"


def record_result(flags, result):
    """The zero and sign bits every operation with a result sets."""
    flags.z = result == 0
    flags.s0 = bool(result & SIGN)
    if not flags.ov1:
        flags.s1 = flags.s0


def record_logic(flags):
    """What an operation with nothing to carry leaves behind."""
    flags.ov0 = False
    flags.ov1 = False
    flags.c = False


def record_addition(flags, left, right, result, adding):
    """The carry and the two overflows, for the operations that have them.

    The second overflow is the one worth reading twice. While one is already
    held and a fresh one arrives, it survives only if the two signs still agree,
    which is the part's way of noticing that a value has wandered out of the word
    and come back rather than merely left it.
    """
    carries = left ^ right ^ result
    overflow = (left ^ result) & (right ^ (result if adding else left))
    held = flags.ov1
    flags.ov0 = bool(overflow & SIGN)
    flags.ov1 = (flags.s0 == flags.s1) if (flags.ov0 and held) else (flags.ov0 or held)
    flags.c = bool((carries ^ overflow) & SIGN)


def record_right_shift(flags, before):
    flags.ov0 = False
    flags.ov1 = False
    flags.c = bool(before & 1)


def record_left_shift(flags, before):
    flags.ov0 = False
    flags.ov1 = False
    flags.c = bool(before >> 15 & 1)
