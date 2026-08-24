"""The NEC uPD7725 and uPD96050 digital signal processors.

    from upd7725 import Cpu

    chip = Cpu("upd96050").reset()
    chip.stores.load_program(program)
    chip.stores.load_table(table)
    chip.run_for(1000)

One instruction set, two widths, and a host that can see two addresses. Six
coprocessor modules shipped on these two parts, four on the smaller and two on the
larger; what makes one different from another is the program masked into it at the
factory rather than the silicon.

So this package is the processor and nothing else. It carries no program and it
never will: every one of them belongs to whoever wrote it. What it carries instead
is a manifest saying what each of those images is and the digest that identifies
it, so a copy you already own can be confirmed before it is run.

The processor itself is settled without any of them, one instruction at a time,
across every field of its own encoding.
"""

from __future__ import annotations

from typing import Any

from . import clock, core, errors, flags, memory, models, ports, registers
from .clock import Clock
from .errors import (
    ClockClosed,
    NeverReady,
    NotWholeWords,
    RunLimit,
    TooLarge,
    UnknownModelError,
)
from .memory import UNSET_SEED, Store, Stores, scramble
from .models import MODELS, describe
from .version import VERSION

__version__ = VERSION

DEFAULT_MODEL = "upd96050"


def Cpu(  # noqa: N802
    model: str = DEFAULT_MODEL, memory: Any = None, **options: Any
) -> core.Cpu:
    """A part of the named model, however the name happens to be written.

    Named and shaped the way the sibling packages name and shape theirs, so a
    caller moving between them relearns nothing the hardware does not force.
    """
    return describe(model).build(memory, **options)


__all__ = [
    "DEFAULT_MODEL",
    "MODELS",
    "UNSET_SEED",
    "Clock",
    "ClockClosed",
    "Cpu",
    "NeverReady",
    "NotWholeWords",
    "RunLimit",
    "Store",
    "Stores",
    "TooLarge",
    "UnknownModelError",
    "__version__",
    "clock",
    "core",
    "describe",
    "errors",
    "flags",
    "memory",
    "models",
    "ports",
    "registers",
    "scramble",
]
