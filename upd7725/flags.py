from typing import override

WORD = 0x10000

SIGN = 0x8000

MASK = 0x3F

NAMES = ("ov0", "ov1", "z", "c", "s0", "s1")


class Flags:
    __slots__ = NAMES

    def __init__(self) -> None:
        self.ov0 = False
        self.ov1 = False
        self.z = False
        self.c = False
        self.s0 = False
        self.s1 = False

    @classmethod
    def of(cls, word: int) -> "Flags":
        found = cls()
        found.ov0 = bool(word >> 0 & 1)
        found.ov1 = bool(word >> 1 & 1)
        found.z = bool(word >> 2 & 1)
        found.c = bool(word >> 3 & 1)
        found.s0 = bool(word >> 4 & 1)
        found.s1 = bool(word >> 5 & 1)
        return found

    def copy(self) -> "Flags":
        return Flags.of(int(self))

    def __int__(self) -> int:
        return (
            int(self.ov0) << 0
            | int(self.ov1) << 1
            | int(self.z) << 2
            | int(self.c) << 3
            | int(self.s0) << 4
            | int(self.s1) << 5
        )

    @override
    def __repr__(self) -> str:
        held = [name for name in NAMES if getattr(self, name)]
        return f"<Flags {' '.join(held) if held else 'none'}>"


def record_result(flags: Flags, result: int) -> None:
    flags.z = result == 0
    flags.s0 = bool(result & SIGN)
    if not flags.ov1:
        flags.s1 = flags.s0


def record_logic(flags: Flags) -> None:
    flags.ov0 = False
    flags.ov1 = False
    flags.c = False


def record_addition(flags: Flags, left: int, right: int, result: int, adding: bool) -> None:
    carries = left ^ right ^ result
    overflow = (left ^ result) & (right ^ (result if adding else left))
    held = flags.ov1
    flags.ov0 = bool(overflow & SIGN)
    flags.ov1 = (flags.s0 == flags.s1) if (flags.ov0 and held) else (flags.ov0 or held)
    flags.c = bool((carries ^ overflow) & SIGN)


def record_right_shift(flags: Flags, before: int) -> None:
    flags.ov0 = False
    flags.ov1 = False
    flags.c = bool(before & 1)


def record_left_shift(flags: Flags, before: int) -> None:
    flags.ov0 = False
    flags.ov1 = False
    flags.c = bool(before >> 15 & 1)
