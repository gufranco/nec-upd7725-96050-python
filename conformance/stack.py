from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import MODELS

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence

LARGER = "upd96050"

LEVELS = 8

RESET = 0x000

INTERRUPT = 0x100

FORM_SHIFT = 22

RETURN = 1

JUMP = 2

LOAD = 3

THROUGH_OUTPUT = 0x000

JUMP_LOW = 0x100

JUMP_HIGH = 0x101

CALL_LOW = 0x140

CALL_HIGH = 0x141

FAR_HALF = 0x2000

BANK_SHIFT = 11

TO_STATUS = 7

ENABLE_BIT = 0x80

PROGRAM_BYTES = 3

TABLE_BYTES = 2

Step = tuple[tuple[int, ...], int | None]


class Census:
    __slots__ = (
        "enables_interrupts",
        "from_interrupt",
        "from_reset",
        "indirect",
        "reached",
        "recursive",
    )

    def __init__(self) -> None:
        self.from_reset = 0
        self.from_interrupt = 0
        self.enables_interrupts = False
        self.reached = 0
        self.recursive: tuple[int, ...] = ()
        self.indirect: tuple[int, ...] = ()

    @property
    def deepest(self) -> int:
        taken = 1 + self.from_interrupt if self.enables_interrupts else 0
        return self.from_reset + taken

    @property
    def bounded(self) -> bool:
        return not self.recursive and not self.indirect


class _Walk:
    def __init__(self, words: Sequence[int], mask: int) -> None:
        self.words = words
        self.mask = mask
        self.depths: dict[int, int] = {}
        self.open: set[int] = set()
        self.reached: set[int] = set()
        self.recursive: set[int] = set()
        self.indirect: set[int] = set()
        self.enables = False

    def depth(self, entry: int) -> int:
        if entry in self.depths:
            return self.depths[entry]
        if entry in self.open:
            self.recursive.add(entry)
            return 0
        self.open.add(entry)
        found = max((1 + self.depth(callee) for callee in self._calls(entry)), default=0)
        self.open.discard(entry)
        self.depths[entry] = found
        return found

    def _calls(self, entry: int) -> list[int]:
        calls: list[int] = []
        seen: set[int] = set()
        waiting = [entry]
        for _ in range(len(self.words)):
            if not waiting:
                break
            at = waiting.pop()
            if at in seen:
                continue
            seen.add(at)
            following, callee = self._after(at)
            waiting.extend(following)
            if callee is not None:
                calls.append(callee)
        self.reached |= seen
        return calls

    def _after(self, at: int) -> Step:
        word = self.words[at]
        form = word >> FORM_SHIFT
        following = at + 1 & self.mask
        if form == RETURN:
            return (), None
        if form == JUMP:
            return self._branch(at, word, following)
        self._note_status(word, form)
        return (following,), None

    def _note_status(self, word: int, form: int) -> None:
        if word & 0xF != TO_STATUS:
            return
        if form != LOAD or word >> 6 & ENABLE_BIT:
            self.enables = True

    def _branch(self, at: int, word: int, following: int) -> Step:
        branch = word >> 13 & 0x1FF
        target = (following & FAR_HALF | (word & 0x3) << BANK_SHIFT | word >> 2 & 0x7FF) & self.mask
        if branch == THROUGH_OUTPUT:
            self.indirect.add(at)
            return (), None
        if branch == JUMP_LOW:
            return (target & ~FAR_HALF,), None
        if branch == JUMP_HIGH:
            return (target | FAR_HALF,), None
        if branch == CALL_LOW:
            return (following,), target & ~FAR_HALF
        if branch == CALL_HIGH:
            return (following,), target | FAR_HALF
        return (target, following), None


def census(words: Sequence[int], model: str = LARGER) -> Census:
    walk = _Walk(words, MODELS[model].program_words - 1)
    found = Census()
    found.from_reset = walk.depth(RESET)
    found.reached = len(walk.reached)
    found.from_interrupt = walk.depth(INTERRUPT)
    found.enables_interrupts = walk.enables
    found.recursive = tuple(sorted(walk.recursive))
    found.indirect = tuple(sorted(walk.indirect))
    return found


def digest(image: bytes) -> str:
    return hashlib.sha256(image).hexdigest()


def program_of(image: bytes, model: str = LARGER) -> list[int] | None:
    part = MODELS[model]
    split = part.program_words * PROGRAM_BYTES
    if len(image) != split + part.table_words * TABLE_BYTES:
        return None
    return [
        int.from_bytes(image[at : at + PROGRAM_BYTES], "big")
        for at in range(0, split, PROGRAM_BYTES)
    ]


def line_for(image: bytes, found: Census) -> str:
    return (
        f"  {digest(image)[:16]}  {found.reached:,} words reached from reset, calls nesting"
        f" {found.from_reset} deep there and {found.from_interrupt} inside the interrupt routine,"
        f" interrupts {'enabled' if found.enables_interrupts else 'never enabled'},"
        f" deepest {found.deepest}, recursive {list(found.recursive)},"
        f" indirect {list(found.indirect)}"
    )


def main(argv: Sequence[str], levels: int = LEVELS, say: Callable[[str], object] = print) -> int:
    if not argv:
        say("  nothing to measure: name at least one image")
        return 2
    verdicts = []
    for name in argv:
        image = Path(name).read_bytes()
        words = program_of(image)
        if words is None:
            say(f"  {name} is {len(image)} bytes, not an image for the larger part")
            return 2
        found = census(words)
        say(line_for(image, found))
        verdicts.append(found.bounded and found.deepest <= levels)
    if all(verdicts):
        say(f"  every image stays within {levels} levels")
        return 0
    say(f"  ! an image needs more than {levels} levels or cannot be bounded")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
