"""The NEC uPD7725 and uPD96050, the processors a shelf of Super Nintendo parts run on.

    from upd7725 import Processor

    chip = Processor("upd96050")
    chip.stores.load_program(program)
    chip.stores.load_table(table)
    chip.run(1000)

One instruction set, two widths, and a console that can see two addresses. Nintendo
shipped four different microcodes on the smaller part under the DSP name, and Seta
shipped two on the larger one under the ST name; what makes a DSP-1 different from
a shogi player is the program masked into it rather than the silicon.

So this package is the processor and nothing else. It carries no program and it
never will: every one of them belongs to whoever wrote it. What it carries instead
is a manifest saying what each of those images is and the digest that identifies
it, so a copy you already own can be confirmed before it is run.

The processor itself is settled without any of them, one instruction at a time,
across every field of its own encoding.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from . import core, firmware, flags, memory, models, ports, registers
from .core import Core
from .models import MODELS, UnknownModelError, carrying, describe
from .version import VERSION

__version__ = VERSION

if TYPE_CHECKING:  # pragma: no cover
    from .core import Core

DEFAULT_MODEL = "upd96050"


def Processor(model: str = DEFAULT_MODEL, **options: Any) -> Core:  # noqa: N802
    """A processor of the named part, however the name happens to be written."""
    return describe(model).build(**options)


__all__ = [
    "MODELS",
    "Core",
    "Processor",
    "UnknownModelError",
    "__version__",
    "carrying",
    "core",
    "describe",
    "firmware",
    "flags",
    "memory",
    "models",
    "ports",
    "registers",
]
