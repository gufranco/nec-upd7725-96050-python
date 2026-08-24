"""Every ALU operation, against the flag matrix the manufacturer printed.

The data sheet this project was built on is Advance Product Information and
states no flag rules, so every one of them came from a recording of another
implementation. The 1989 data book states them: its Table 6 gives, for all
sixteen ALU operations, which flags are affected, which are reset, which are
held and which the manufacturer declines to define.

So the flags are checked against the manufacturer here, and against the
recording elsewhere. Where a flag is declared affected, this asks only that the
model can move it, because "may be affected, depending on the results" is not a
value. Where it is declared reset or held, the claim is exact and is tested
exactly.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from upd7725 import core, models  # noqa: E402

HELD = json.loads((ROOT / "conformance" / "hardware.json").read_text())

MATRIX = HELD["parts"][0]["facts"]["aluFlagMatrix"]

ROWS = MATRIX["rows"]

COLUMNS = MATRIX["columns"]

CODES = {
    "NOP": 0,
    "OR": 1,
    "AND": 2,
    "XOR": 3,
    "SUB": 4,
    "ADD": 5,
    "SBB": 6,
    "ADC": 7,
    "DEC": 8,
    "INC": 9,
    "CMP": 10,
    "SHR1": 11,
    "SHL1": 12,
    "SHL2": 13,
    "SHL4": 14,
    "XCHG": 15,
}

INPUTS = (
    (0x0000, 0x0000),
    (0xFFFF, 0x0001),
    (0x8000, 0x8000),
    (0x7FFF, 0x0001),
    (0x00FF, 0xFF00),
    (0x5555, 0xAAAA),
    (0x0001, 0x0001),
    (0xFFFF, 0xFFFF),
)


def settled() -> "core.Core":
    found = core.Core(models.describe("upd7725"), fill=0).reset()
    registers = found.registers
    registers.rp = registers.dp = registers.sp = 0
    registers.k = registers.l = registers.m = registers.n = 0
    registers.a = registers.b = 0
    return found


def an_operation(alu: int, pselect: int = 1, asl: int = 0, src: int = 0) -> int:
    return pselect << 20 | alu << 16 | asl << 15 | src << 4


def loaded(alu: int, left: int, right: int, carry: bool) -> "core.Core":
    """A part holding a stated starting state, with one operation ready to run."""
    chip = settled()
    chip.registers.a = left
    chip.registers.dr = right
    chip.flags_a.c = carry
    chip.flags_a.z = carry
    chip.flags_a.s0 = carry
    chip.flags_a.s1 = carry
    chip.flags_a.ov0 = carry
    chip.flags_a.ov1 = carry
    chip.stores.program[0] = an_operation(alu, src=0x9)
    return chip


def after(alu: int, left: int, right: int, carry: bool) -> dict[str, bool]:
    """The flags an operation leaves, from a stated starting state."""
    chip = loaded(alu, left, right, carry)
    chip.step()
    return {name: bool(getattr(chip.flags_a, name)) for name in COLUMNS}


def result_after(alu: int, left: int, right: int, carry: bool) -> int:
    """The word the operation left in the accumulator."""
    chip = loaded(alu, left, right, carry)
    chip.step()
    word: int = chip.registers.word("a")
    return word


def before(carry: bool) -> dict[str, bool]:
    return dict.fromkeys(COLUMNS, carry)


class MatrixTest(unittest.TestCase):
    """That the model moves each flag exactly where the manufacturer says it may."""

    def outcomes(self, name: str) -> list[tuple[str, dict[str, bool], dict[str, bool], int]]:
        alu = CODES[name]
        found = []
        for left, right in INPUTS:
            for carry in (False, True):
                found.append(
                    (
                        f"{name} {left:04X},{right:04X},c={carry:d}",
                        before(carry),
                        after(alu, left, right, carry),
                        result_after(alu, left, right, carry),
                    )
                )
        return found

    def test_the_matrix_covers_every_operation_the_part_has(self) -> None:
        self.assertEqual(sorted(ROWS), sorted(CODES))

    def test_a_flag_the_document_calls_reset_is_always_reset(self) -> None:
        wrong = [
            f"{what}: {flag}"
            for name, verdicts in ROWS.items()
            for what, _, ended, _word in self.outcomes(name)
            for flag, verdict in zip(COLUMNS, verdicts, strict=True)
            if verdict == "reset" and ended[flag]
        ]

        self.assertEqual(wrong, [])

    def test_a_flag_the_document_calls_held_never_moves(self) -> None:
        wrong = [
            f"{what}: {flag}"
            for name, verdicts in ROWS.items()
            for what, started, ended, _word in self.outcomes(name)
            for flag, verdict in zip(COLUMNS, verdicts, strict=True)
            if verdict == "held" and ended[flag] != started[flag]
        ]

        self.assertEqual(wrong, [])

    def test_a_zero_flag_the_document_calls_affected_follows_the_result(self) -> None:
        """The document says a flag may be affected depending on the result.

        For the zero and sign bits that claim is exact and testable: the flag is
        the result. It is not a claim that both values occur, which matters here
        because a two-bit left shift shifts ones in, so its result is never zero
        and its zero flag is always clear while still being derived from it.
        """
        wrong = [
            f"{what}: z"
            for name, verdicts in ROWS.items()
            for what, _, ended, _word in self.outcomes(name)
            if verdicts[COLUMNS.index("z")] == "affected" and ended["z"] != (_word == 0)
        ]

        self.assertEqual(wrong, [])

    def test_and_so_does_the_sign(self) -> None:
        wrong = [
            f"{what}: s0"
            for name, verdicts in ROWS.items()
            for what, _, ended, _word in self.outcomes(name)
            if verdicts[COLUMNS.index("s0")] == "affected" and ended["s0"] != bool(_word & 0x8000)
        ]

        self.assertEqual(wrong, [])

    def test_the_shifts_that_bring_ones_in_can_never_reach_zero(self) -> None:
        """Recorded because it is the recording speaking, not the manufacturer.

        Table 6 names the operation a two-bit left shift and says nothing about
        what arrives at the bottom. This model brings ones in, following the
        recording, which makes the zero flag unreachable for those two
        operations. A manufacturer statement either way would settle it.
        """
        reached = {word == 0 for _, _, _ended, word in self.outcomes("SHL2")}

        self.assertEqual(reached, {False})

    def test_only_the_one_bit_shifts_take_the_carry_from_the_bit_shifted_out(self) -> None:
        moving = [
            name for name, verdicts in ROWS.items() if verdicts[COLUMNS.index("c")] == "affected"
        ]

        self.assertEqual(
            sorted(moving), sorted(["ADC", "ADD", "DEC", "INC", "SBB", "SHL1", "SHR1", "SUB"])
        )

    def test_the_auxiliary_sign_is_where_the_manufacturer_stops(self) -> None:
        undefined = [name for name, verdicts in ROWS.items() if verdicts[0] == "indefinite"]

        self.assertEqual(len(undefined), 9)

    def test_and_the_record_says_this_model_answers_there_anyway(self) -> None:
        self.assertIn("indefinite", MATRIX["whatItLeavesOpen"])


if __name__ == "__main__":
    unittest.main()
