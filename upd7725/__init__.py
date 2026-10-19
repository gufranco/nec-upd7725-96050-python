from __future__ import annotations

from typing import Any

from . import clock as clock
from . import core as core
from . import errors as errors
from . import flags as flags
from . import memory as memory
from . import models as models
from . import opcodes as opcodes
from . import pins as pins
from . import ports as ports
from . import registers as registers
from .clock import Clock
from .core import Cpu as Cpu7725
from .errors import (
    ClockClosed,
    NeverReady,
    NotWholeWords,
    RunLimit,
    TooLarge,
    UnknownModelError,
)
from .flags import Flags
from .memory import UNSET_SEED, Store, Stores, scramble
from .models import MODELS, Model
from .opcodes import Instruction, decode, disassemble
from .pins import Pins
from .ports import DATA, STATUS, Host
from .version import VERSION

__version__ = VERSION


def Cpu(  # noqa: N802
    model: str | None = None, memory: Any = None, **options: Any
) -> core.Cpu:
    return models.lookup(model).build(memory, **options)


__all__ = [
    "DATA",
    "MODELS",
    "STATUS",
    "UNSET_SEED",
    "Clock",
    "ClockClosed",
    "Cpu",
    "Cpu7725",
    "Flags",
    "Host",
    "Instruction",
    "Model",
    "NeverReady",
    "NotWholeWords",
    "Pins",
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
