from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import models

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence

INSTRUCTIONS = 200_000

REPEATS = 7

FLOOR = 250_000

PART_HERTZ = 8_192_000


class Usage(Exception):
    pass


class Timed:
    def __init__(self, part: str, instructions: int, seconds: Sequence[float]) -> None:
        self.part = part
        self.instructions = instructions
        self.seconds = tuple(seconds)

    @property
    def median(self) -> float:
        return statistics.median(self.seconds)

    @property
    def rate(self) -> float:
        return self.instructions / self.median

    @property
    def of_real_time(self) -> float:
        return self.rate / PART_HERTZ

    def beats(self, floor: int) -> bool:
        return self.rate >= floor

    @override
    def __repr__(self) -> str:
        return f"<Timed {self.part}, {self.rate:,.0f} instructions per second>"


def _clock() -> float:  # pragma: no cover
    return time.perf_counter()


def timed(
    part: str = "upd7725",
    instructions: int = INSTRUCTIONS,
    repeats: int = REPEATS,
    clock: Callable[[], float] = _clock,
) -> Timed:
    model = models.lookup(part)
    seconds = []
    for _ in range(repeats):
        chip = model.build(fill=0).reset()
        at = clock()
        chip.run_for(instructions)
        seconds.append(clock() - at)
    return Timed(part, instructions, seconds)


def lines_for(found: Timed, floor: int = FLOOR) -> list[str]:
    said = [
        f"  {found.part}: {found.rate:,.0f} instructions per second at the median"
        f" of {len(found.seconds)} runs of {found.instructions:,}",
        f"     median {found.median:.3f}s, fastest {min(found.seconds):.3f}s,"
        f" slowest {max(found.seconds):.3f}s",
        f"     {found.of_real_time * 100:.1f}% of the {PART_HERTZ:,} instructions"
        " per second the silicon does",
        f"     on Python {sys.version.split()[0]}",
    ]
    if not found.beats(floor):
        said.append(
            f"  ! below the floor of {floor:,} instructions per second."
            " Something got several times slower rather than a little noisier"
        )
    return said


def options(argv: Sequence[str]) -> tuple[int, int]:
    instructions = INSTRUCTIONS
    repeats = REPEATS
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item not in ("--instructions", "--repeats"):
            raise Usage(f"unknown option {item}")
        if not rest:
            raise Usage(f"{item} needs a value")
        if item == "--instructions":
            instructions = int(rest.pop(0))
        else:
            repeats = int(rest.pop(0))
    return instructions, repeats


def main(
    argv: Sequence[str],
    floor: int = FLOOR,
    run: Callable[..., Timed] = timed,
    say: Callable[[str], object] = print,
) -> int:
    try:
        instructions, repeats = options(argv)
    except Usage as error:
        say(str(error))
        return 2

    found = run(instructions=instructions, repeats=repeats)
    for line in lines_for(found, floor):
        say(line)
    return 0 if found.beats(floor) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
