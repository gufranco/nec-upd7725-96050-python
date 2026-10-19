from __future__ import annotations

WIDE = 16

NARROW = 8

WORD_MASK = 0xFFFF


def serial_width(narrow: bool) -> int:
    return NARROW if narrow else WIDE


def reversed_bits(word: int, width: int) -> int:
    turned = 0
    for place in range(width):
        turned |= (word >> place & 1) << (width - 1 - place)
    return word & ~((1 << width) - 1) & WORD_MASK | turned
