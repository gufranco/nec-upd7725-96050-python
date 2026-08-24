"""Which processors this package covers, and what separates them.

NEC built a family of digital signal processors around one instruction set, and
the members differ in how far three registers can reach rather than in what the
instructions do. That is the whole difference between the two parts here: the
counter, the table pointer and the scratch pointer are wider on the larger one,
and every store is exactly as long as the register that addresses it.

This package is the processor and nothing that was built around one. A module
somebody soldered onto a board is that board's business: what it was called, what
program was masked into it and what machine it plugged into are all outside the
part. Naming any of that here would make a processor package a catalogue of one
system's cartridges, and the processor is not that system's.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, override

from .errors import UnknownModelError

if TYPE_CHECKING:  # pragma: no cover
    from .core import Cpu


class Model:
    """One processor: how far it reaches, and what shipped running on it."""

    def __init__(
        self,
        name: str,
        summary: str,
        counter_bits: int,
        table_bits: int,
        pointer_bits: int,
        stack_levels: int,
        aliases: Iterable[str] = (),
    ) -> None:
        self.name = name
        self.summary = summary
        self.counter_bits = counter_bits
        self.table_bits = table_bits
        self.pointer_bits = pointer_bits
        self.stack_levels = stack_levels
        self.aliases = tuple(aliases)

    @property
    def stack_pointer_bits(self) -> int:
        """How wide the pointer into that stack is.

        A four-level stack is reached by a two-bit pointer, so this follows from
        the depth rather than being a second number that could disagree with it.
        """
        return (self.stack_levels - 1).bit_length()

    @property
    def program_words(self) -> int:
        return 1 << self.counter_bits

    @property
    def table_words(self) -> int:
        return 1 << self.table_bits

    @property
    def scratch_words(self) -> int:
        return 1 << self.pointer_bits

    def build(self, *arguments: Any, **options: Any) -> Cpu:
        from .core import Cpu

        return Cpu(self, *arguments, **options)

    @override
    def __repr__(self) -> str:
        return (
            f"<Model {self.name}, counter {self.counter_bits} bits, "
            f"table {self.table_bits}, pointer {self.pointer_bits}, "
            f"stack {self.stack_levels}>"
        )


_CATALOGUE = (
    Model(
        name="upd7725",
        summary=(
            "The NEC uPD7725, the smaller of the two. Two "
            "thousand and forty eight instructions, a table of a thousand and "
            "twenty four constants, and two hundred and fifty six words of scratch "
            "shared with the console a byte at a time."
        ),
        counter_bits=11,
        table_bits=10,
        pointer_bits=8,
        stack_levels=4,
        aliases=("7725", "upd77c25", "77c25", "necupd7725"),
    ),
    Model(
        name="upd96050",
        summary=(
            "The NEC uPD96050, the larger of the two. Eight times "
            "the program store of the smaller one, twice the table, and eight times "
            "the scratch, which is where the host leaves its questions."
        ),
        counter_bits=14,
        table_bits=11,
        pointer_bits=11,
        stack_levels=8,
        aliases=("96050", "upd96050gf", "necupd96050"),
    ),
)

MODELS = {model.name: model for model in _CATALOGUE}

NOT_MODELLED = {
    "upd7720": (
        "the uPD7720 is the earlier part of the same family, and the reference this "
        "package is measured against does not implement it; a model of it here would "
        "have nothing behind it"
    ),
    "upd77p25": (
        "the uPD77P25 is the same processor with its program in erasable storage "
        "rather than masked, which changes how it is made rather than what it does; "
        "ask for upd7725 and load the program yourself"
    ),
}
"""Names that belong to a real part the package deliberately does not answer to."""

_BY_ALIAS = {}
for _model in _CATALOGUE:
    _BY_ALIAS[_model.name] = _model
    for _alias in _model.aliases:
        _BY_ALIAS[_alias] = _model


def _normalise(name: str) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "")


def describe(name: str) -> Model:
    """The processor of that name, however it happens to be written."""
    wanted = _normalise(name)
    found = _BY_ALIAS.get(wanted)
    if found is not None:
        return found
    if wanted in NOT_MODELLED:
        raise UnknownModelError(f"{name} is not modelled here: {NOT_MODELLED[wanted]}")
    raise UnknownModelError(
        f"{name} is not a processor this package covers; it has {', '.join(sorted(MODELS))}"
    )
