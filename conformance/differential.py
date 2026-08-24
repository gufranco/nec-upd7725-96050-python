"""The model and the reference, run side by side on cases nobody wrote down.

The gate is `instructions.py`: every field of every instruction form, plus twenty
thousand generated cases, compared against states recorded from the original
implementation before this project's port of it existed. That is the evidence, and
it is a fixed size, because a recording has to be stored.

This is the other half. It runs the model and the ported reference live, on the
same case, and compares what each is left holding. Nothing is stored, so nothing
bounds it: give it a case number to start from and a count, or a number of
seconds, and it explores as far as it is allowed to. Case fifty million is as
reachable as case one and just as repeatable, because a case is derived from its
number rather than drawn from a generator that has to be walked to get there.

What it is worth is narrower than the gate, and saying so matters. Agreement here
is agreement between two implementations in this repository, one of which was
ported by the same hand as the other. It is not evidence about hardware. A
disagreement is the useful direction: it names a case where the two differ, and
that case is then settled against the recordings, which is where the authority
lives. This finds candidates. The corpus decides.

Both are still worth running. The two are built to differ in shape: the reference
dispatches through tables and the model branches through named conditions, so a
mistake made in one has no reason to appear in the other. Two implementations that
disagree on a case the corpus never covered is exactly the thing a fixed corpus
cannot tell you about.
"""

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
"""How many cases a run with no arguments compares.

Small enough to finish while somebody waits, which is what makes it worth running
by hand. The schedule asks for far more.
"""

KEEP = 5
"""How many disagreements are printed. The rest are counted rather than shown."""

Answered = Callable[[int, int, int], str]
"""How one side answers a case: the seed, the part, the instruction, in that order."""


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
    """One case the two did not answer alike."""

    def __init__(self, index: int, case: tuple[int, int, int], model: str, reference: str) -> None:
        self.index = index
        self.case = case
        self.model = model
        self.reference = reference

    @property
    def rerun(self) -> str:
        """The command that runs this one case and nothing else."""
        return f"--from {self.index} --cases 1"

    @override
    def __repr__(self) -> str:
        return f"<Disagreement at case {self.index}>"


class Compared:
    """What a sweep found, and how much of it there was."""

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
    """Every case in that range, put to both, compared.

    The clock is only read when there is a budget to check it against, so a run
    counted in cases does not pay for one and cannot be cut short by one.
    """
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
    """What a sweep found, in the order somebody reading it wants it."""
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
