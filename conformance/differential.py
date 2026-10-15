from __future__ import annotations

import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import instructions, oracle
from conformance.instructions import PARTS, case_for

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable, Sequence

DEFAULT_CASES = 5000

KEEP = 5

Answered = Callable[[int, int, int], str]


class Usage(Exception):
    pass


class Options:
    def __init__(
        self, first: int = 0, cases: int = DEFAULT_CASES, seconds: float | None = None
    ) -> None:
        self.first = first
        self.cases = cases
        self.seconds = seconds


class Disagreement:
    def __init__(self, index: int, case: tuple[int, int, int], model: str, reference: str) -> None:
        self.index = index
        self.case = case
        self.model = model
        self.reference = reference

    @property
    def rerun(self) -> str:
        return f"--from {self.index} --cases 1"

    @override
    def __repr__(self) -> str:
        return f"<Disagreement at case {self.index}>"


class Compared:
    def __init__(self, checked: int, disagreed: int, disagreements: Iterable[Disagreement]) -> None:
        self.checked = checked
        self.disagreed = disagreed
        self.disagreements = tuple(disagreements)

    @property
    def agrees(self) -> bool:
        return self.disagreed == 0

    @override
    def __repr__(self) -> str:
        return f"<Compared {self.checked} cases, {self.disagreed} disagreed>"


def _model(seed: int, part: int, opcode: int) -> str:  # pragma: no cover
    return instructions.replay(seed, part, opcode)


def _reference(seed: int, part: int, opcode: int) -> str:  # pragma: no cover
    return oracle.answer(seed, part, opcode)


def sweep(
    cases: int = DEFAULT_CASES,
    first: int = 0,
    model: Answered = _model,
    reference: Answered = _reference,
    keep: int = KEEP,
    seconds: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> Compared:
    started = clock() if seconds is not None else 0.0
    checked = 0
    disagreed = 0
    kept: list[Disagreement] = []

    for index in range(first, first + cases):
        if seconds is not None and clock() - started >= seconds:
            break
        case = case_for(index)
        said = model(*case)
        wanted = reference(*case)
        checked += 1
        if said == wanted:
            continue
        disagreed += 1
        if len(kept) < keep:
            kept.append(Disagreement(index, case, said, wanted))

    return Compared(checked, disagreed, kept)


def lines_for(found: Compared) -> list[str]:
    said = []
    for one in found.disagreements:
        seed, part, opcode = one.case
        said.append(f"  case {one.index} (seed {seed:08x}, {PARTS[part]}, {opcode:06x})")
        said.append(f"      reference {one.reference}")
        said.append(f"      model     {one.model}")
        said.append(f"      run it alone with {one.rerun}")

    remaining = found.disagreed - len(found.disagreements)
    if remaining > 0:
        said.append(f"  and {remaining:,} more")

    if found.agrees:
        said.append(f"  {found.checked:,} cases, the model and the reference agreed on every one")
    else:
        said.append(f"  {found.checked:,} cases, {found.disagreed:,} disagreed")
    return said


def options(argv: Sequence[str]) -> Options:
    chosen = Options()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item not in ("--from", "--cases", "--seconds"):
            raise Usage(f"unknown option {item}")
        if not rest:
            raise Usage(f"{item} needs a value")
        value = rest.pop(0)
        if item == "--from":
            chosen.first = int(value)
        elif item == "--cases":
            chosen.cases = int(value)
        else:
            chosen.seconds = float(value)
    return chosen


def main(
    argv: Sequence[str],
    model: Answered = _model,
    reference: Answered = _reference,
    say: Callable[[str], object] = print,
) -> int:
    try:
        chosen = options(argv)
    except Usage as error:
        say(str(error))
        return 2

    found = sweep(
        chosen.cases,
        chosen.first,
        model=model,
        reference=reference,
        seconds=chosen.seconds,
    )
    for line in lines_for(found):
        say(line)
    return 0 if found.agrees else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
