from __future__ import annotations

from typing import Any

from . import clock as clock
from . import core as core
from . import errors as errors
from . import flags as flags
from . import memory as memory
from . import models as models
from . import opcodes as opcodes
from . import ports as ports
from . import registers as registers
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
from .models import MODELS
from .opcodes import Instruction, decode, disassemble
from .version import VERSION

__version__ = VERSION


def Cpu(  # noqa: N802
    model: str | None = None, memory: Any = None, **options: Any
) -> core.Cpu:
    return models.lookup(model).build(memory, **options)


__all__ = [
    "MODELS",
    "UNSET_SEED",
    "Clock",
    "ClockClosed",
    "Cpu",
    "Instruction",
    "NeverReady",
    "NotWholeWords",
    "RunLimit",
    "Store",
    "Stores",
    "TooLarge",
    "UnknownModelError",
    "__version__",
    "decode",
    "disassemble",
    "scramble",
]
