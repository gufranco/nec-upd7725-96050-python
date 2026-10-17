from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import upd7725

if TYPE_CHECKING:
    from upd7725.core import Cpu

    Part = Cpu

RECORD = Path(__file__).resolve().parent / "hardware.json"

PART = "upd7725"

TOP_WORD = 0xFFFF

FORM_SHIFT = 22

OPERATE = 0
RETURN = 1
JUMP = 2
LOAD = 3

FROM_TRB = 0
FROM_A = 1
FROM_B = 2
FROM_TR = 3
FROM_POINTER = 4
FROM_TABLE_POINTER = 5
FROM_TABLE = 6
FROM_SATURATION = 7
FROM_DATA_AND_ASK = 8
FROM_DATA = 9
FROM_STATUS = 10
FROM_SERIAL_HIGH = 11
FROM_SERIAL_LOW = 12
FROM_K = 13
FROM_L = 14
FROM_SCRATCH = 15

TO_NOWHERE = 0
TO_A = 1
TO_B = 2
TO_TR = 3
TO_POINTER = 4
TO_TABLE_POINTER = 5
TO_DATA = 6
TO_STATUS = 7
TO_SERIAL_LOW = 8
TO_SERIAL_HIGH = 9
TO_K = 10
TO_K_AND_TABLE = 11
TO_L_AND_SCRATCH = 12
TO_L = 13
TO_TRB = 14
TO_SCRATCH = 15

NOP = 0
OR = 1
AND = 2
XOR = 3
SUBTRACT = 4
ADD = 5
SUBTRACT_WITH_BORROW = 6
ADD_WITH_CARRY = 7
DECREMENT = 8
INCREMENT = 9
NEGATE = 10
SHIFT_RIGHT = 11
SHIFT_LEFT = 12
SHIFT_LEFT_TWICE = 13
SHIFT_LEFT_FOUR_TIMES = 14
SWAP_HALVES = 15

FROM_RAM = 0
FROM_BUS = 1
FROM_M = 2
FROM_N = 3

POINTER_HOLD = 0
POINTER_UP = 1
POINTER_DOWN = 2
POINTER_CLEAR = 3

JUMP_THROUGH_OUTPUT = 0x000
JUMP_IF_NO_CARRY_A = 0x080
JUMP_IF_CARRY_A = 0x082
JUMP_IF_NO_CARRY_B = 0x084
JUMP_IF_CARRY_B = 0x086
JUMP_IF_NOT_ZERO_A = 0x088
JUMP_IF_ZERO_A = 0x08A
JUMP_IF_NOT_ZERO_B = 0x08C
JUMP_IF_ZERO_B = 0x08E
JUMP_IF_NO_OVERFLOW_A0 = 0x090
JUMP_IF_OVERFLOW_A0 = 0x092
JUMP_IF_NO_OVERFLOW_B0 = 0x094
JUMP_IF_OVERFLOW_B0 = 0x096
JUMP_IF_NO_OVERFLOW_A1 = 0x098
JUMP_IF_OVERFLOW_A1 = 0x09A
JUMP_IF_NO_OVERFLOW_B1 = 0x09C
JUMP_IF_OVERFLOW_B1 = 0x09E
JUMP_IF_NOT_SIGN_A0 = 0x0A0
JUMP_IF_SIGN_A0 = 0x0A2
JUMP_IF_NOT_SIGN_B0 = 0x0A4
JUMP_IF_SIGN_B0 = 0x0A6
JUMP_IF_NOT_SIGN_A1 = 0x0A8
JUMP_IF_SIGN_A1 = 0x0AA
JUMP_IF_NOT_SIGN_B1 = 0x0AC
JUMP_IF_SIGN_B1 = 0x0AE
JUMP_IF_POINTER_EMPTY = 0x0B0
JUMP_IF_POINTER_NOT_EMPTY = 0x0B1
JUMP_IF_POINTER_FULL = 0x0B2
JUMP_IF_POINTER_NOT_FULL = 0x0B3
JUMP_IF_NO_INPUT_ACK = 0x0B4
JUMP_IF_INPUT_ACK = 0x0B6
JUMP_IF_NO_OUTPUT_ACK = 0x0B8
JUMP_IF_OUTPUT_ACK = 0x0BA
JUMP_IF_NOT_ASKING = 0x0BC
JUMP_IF_ASKING = 0x0BE
JUMP_LOW = 0x100
JUMP_HIGH = 0x101
CALL_LOW = 0x140
CALL_HIGH = 0x141


def the_part() -> dict[str, Any]:
    record = json.loads(RECORD.read_text())
    found: dict[str, Any] = next(one for one in record["parts"] if one["part"] == PART)
    return found


def fact(name: str) -> dict[str, Any]:
    found: dict[str, Any] = the_part()["facts"][name]
    return found


def a_powered_part() -> Part:
    return upd7725.Cpu(PART, fill=0)


def a_part() -> Part:
    chip = a_powered_part().reset()
    registers = chip.registers
    registers.pc = registers.rp = registers.dp = registers.sp = 0
    registers.k = registers.l = registers.m = registers.n = 0
    registers.a = registers.b = 0
    registers.dr = 0
    registers.sr.assign(0)
    chip.flags_a = upd7725.Flags()
    chip.flags_b = upd7725.Flags()
    return chip


def an_operation(
    alu: int = 0,
    pselect: int = 0,
    asl: int = 0,
    dpl: int = 0,
    rpdcr: int = 0,
    src: int = 0,
    dst: int = 0,
    dphm: int = 0,
) -> int:
    return (
        pselect << 20 | alu << 16 | asl << 15 | dpl << 13 | dphm << 9 | rpdcr << 8 | src << 4 | dst
    )


def a_return(**fields: int) -> int:
    return RETURN << FORM_SHIFT | an_operation(**fields)


def a_load(value: int, dst: int) -> int:
    return LOAD << FORM_SHIFT | (value & TOP_WORD) << 6 | dst


def a_jump(branch: int, address: int = 0, bank: int = 0) -> int:
    return JUMP << FORM_SHIFT | branch << 13 | address << 2 | bank
