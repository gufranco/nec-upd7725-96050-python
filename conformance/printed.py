import json
from pathlib import Path
from typing import Any

from upd7725 import core, models
from upd7725.flags import Flags

RECORD = Path(__file__).resolve().parent / "hardware.json"

PART = "upd7725"

TOP_WORD = 0xFFFF


def the_part() -> dict[str, Any]:
    record = json.loads(RECORD.read_text())
    found: dict[str, Any] = next(one for one in record["parts"] if one["part"] == PART)
    return found


def fact(name: str) -> dict[str, Any]:
    found: dict[str, Any] = the_part()["facts"][name]
    return found


def a_powered_part() -> core.Cpu:
    return models.lookup(PART).build(fill=0)


def a_part() -> core.Cpu:
    chip = a_powered_part().reset()
    registers = chip.registers
    registers.pc = registers.rp = registers.dp = registers.sp = 0
    registers.k = registers.l = registers.m = registers.n = 0
    registers.a = registers.b = 0
    registers.dr = 0
    registers.sr.assign(0)
    chip.flags_a = Flags()
    chip.flags_b = Flags()
    return chip


def an_operation(
    alu: int = 0,
    pselect: int = 0,
    asl: int = 0,
    dpl: int = 0,
    rpdcr: int = 0,
    src: int = 0,
    dst: int = 0,
) -> int:
    return pselect << 20 | alu << 16 | asl << 15 | dpl << 13 | rpdcr << 8 | src << 4 | dst


def a_load(value: int, dst: int) -> int:
    return core.LOAD << 22 | (value & TOP_WORD) << 6 | dst


def a_jump(branch: int, address: int = 0) -> int:
    return core.JUMP << 22 | branch << 13 | address << 2
