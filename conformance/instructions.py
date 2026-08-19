"""Hold every instruction to the reference, one instruction at a time.

A case is a seed, a part, and twenty four bits. The seed fills every store, every
register and both flag sets before the instruction runs, so nothing starts clear:
real silicon powers up holding whatever it holds, and a model that starts at zero
agrees with the part until the first instruction that reads somewhere nothing
wrote.

The seed does that without either side listing twenty thousand words. Every word
of every store is a function of the seed and its own address, so both sides can
compute any one of them without walking to it, and the model computes only the
handful an instruction actually touches.

The instruction words are generated rather than quoted. That is what makes this
evidence complete without any firmware present: a processor is settled by walking
its own encoding, and an encoding belongs to nobody.

Usage:
    python3 conformance/instructions.py [--cases N] [--record]
"""

import base64
import json
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import core, models
from upd7725.flags import Flags

ROOT = Path(__file__).resolve().parent

CORPUS = ROOT / "corpus.json"

DEFINITION = ROOT / "pinned.json"

PROGRAM_WORDS = 16384

TABLE_WORDS = 2048

SCRATCH_WORDS = 2048

STACK_DEPTH = 16

AT_PROGRAM = 0
AT_TABLE = AT_PROGRAM + PROGRAM_WORDS
AT_SCRATCH = AT_TABLE + TABLE_WORDS
AT_STACK = AT_SCRATCH + SCRATCH_WORDS
AT_REGISTERS = AT_STACK + STACK_DEPTH

REPORTED_CHANGES = 2

TOO_MANY_CHANGES = 0xFF

WIDTH = 146

PACKED = 73

REPORT_LIMIT = 5

DEFAULT_RANDOM_CASES = 20000

PARTS = ("upd7725", "upd96050")

REGISTER_ORDER = (
    "pc",
    "rp",
    "dp",
    "sp",
    "si",
    "so",
    "k",
    "l",
    "m",
    "n",
    "a",
    "b",
    "tr",
    "trb",
    "dr",
    "sr",
    "siack",
    "soack",
    "flags_a",
    "flags_b",
)

REGISTER_MASKS = {
    "pc": 0x3FFF,
    "rp": 0x7FF,
    "dp": 0x7FF,
    "sp": 0xF,
    "siack": 1,
    "soack": 1,
    "flags_a": 0x3F,
    "flags_b": 0x3F,
}

NAMED_BRANCHES = (
    *sorted(core.BRANCHES),
    core.JUMP_THROUGH_OUTPUT,
    core.JUMP_LOW,
    core.JUMP_HIGH,
    core.CALL_LOW,
    core.CALL_HIGH,
)


class Usage(Exception):
    pass


class Options:
    def __init__(self, corpus=None, cases=None, record=False):
        self.corpus = corpus
        self.cases = cases
        self.record = record


def word_at(seed, index):
    """The word that seed puts at that address, without walking to it."""
    mixed = (seed + index * 0x9E3779B9) & 0xFFFFFFFF
    mixed ^= mixed >> 16
    mixed = mixed * 0x21F0AAAD & 0xFFFFFFFF
    mixed ^= mixed >> 15
    mixed = mixed * 0x735A2D97 & 0xFFFFFFFF
    mixed ^= mixed >> 15
    return mixed


def _operate(alu=0, pselect=0, asl=0, dpl=0, dphm=0, rpdcr=0, src=0, dst=0):
    return (
        pselect << 20 | alu << 16 | asl << 15 | dpl << 13 | dphm << 9 | rpdcr << 8 | src << 4 | dst
    )


def _settled_opcodes():
    """Every field of every form, walked rather than sampled."""
    found = []

    for alu in range(16):
        for pselect in range(4):
            for asl in range(2):
                found.append(_operate(alu=alu, pselect=pselect, asl=asl))

    for src in range(16):
        for dst in range(16):
            found.append(_operate(alu=core.ADD, pselect=1, src=src, dst=dst))

    for dpl in range(4):
        for dphm in range(16):
            for rpdcr in range(2):
                found.append(_operate(dpl=dpl, dphm=dphm, rpdcr=rpdcr, dst=core.TO_TR))

    for branch in range(0x200):
        found.append(2 << 22 | branch << 13 | 0x123 << 2 | 1)

    for dst in range(16):
        for value in (0x0000, 0x1234, 0x8000, 0xFFFF):
            found.append(3 << 22 | value << 6 | dst)

    for alu in range(16):
        for asl in range(2):
            found.append(1 << 22 | _operate(alu=alu, pselect=1, asl=asl, src=core.FROM_TR))

    return tuple(found)


SETTLED_OPCODES = _settled_opcodes()

SETTLED = len(SETTLED_OPCODES) * len(PARTS)


def case_for(index):
    """The seed, the part and the instruction that case number stands for."""
    seed = (index * 2654435761 + 0x9E3779B9) & 0xFFFFFFFF

    if index < SETTLED:
        return seed, index % len(PARTS), SETTLED_OPCODES[index // len(PARTS)]

    return seed, word_at(seed, 1 << 24) & 1, word_at(seed, 1 << 25) & 0xFFFFFF


def _sources(seed):
    return {
        "program": lambda at: word_at(seed, AT_PROGRAM + at),
        "table": lambda at: word_at(seed, AT_TABLE + at),
        "scratch": lambda at: word_at(seed, AT_SCRATCH + at),
    }


def _start(seed, name, place):
    value = word_at(seed, AT_REGISTERS + place)
    return value & REGISTER_MASKS.get(name, 0xFFFF)


def prepared(seed, part):
    """A processor holding what that seed says it holds, before any instruction."""
    model = models.describe(PARTS[part])
    chip = core.Core(model, sources=_sources(seed))

    registers = chip.registers
    for place, name in enumerate(REGISTER_ORDER):
        value = _start(seed, name, place)
        if name == "sr":
            registers.sr.assign(value)
        elif name in ("siack", "soack"):
            setattr(registers.sr, name, bool(value))
        elif name == "flags_a":
            chip.flags_a = Flags.of(value)
        elif name == "flags_b":
            chip.flags_b = Flags.of(value)
        else:
            setattr(registers, name, value)

    for at in range(STACK_DEPTH):
        registers.stack[at] = word_at(seed, AT_STACK + at) & 0xFFFF

    return chip


def state_of(chip):
    """The processor's whole state, in the shape the recordings are in."""
    registers = chip.registers
    changed = chip.stores.scratch.changed()
    slots = list(changed.items())[:REPORTED_CHANGES]
    slots += [(0, 0)] * (REPORTED_CHANGES - len(slots))

    return "".join(
        (
            f"{registers.pc:04x}",
            f"{registers.rp:04x}",
            f"{registers.dp:04x}",
            f"{registers.sp:01x}",
            f"{registers.si:04x}",
            f"{registers.so:04x}",
            f"{registers.word('k'):04x}",
            f"{registers.word('l'):04x}",
            f"{registers.word('m'):04x}",
            f"{registers.word('n'):04x}",
            f"{registers.word('a'):04x}",
            f"{registers.word('b'):04x}",
            f"{registers.tr:04x}",
            f"{registers.trb:04x}",
            f"{registers.dr:04x}",
            f"{int(registers.sr):04x}",
            f"{int(chip.flags_a):02x}",
            f"{int(chip.flags_b):02x}",
            f"{int(registers.sr.siack) << 1 | int(registers.sr.soack):01x}",
            "".join(f"{word:04x}" for word in registers.stack),
            f"{min(len(changed), TOO_MANY_CHANGES):02x}",
            "".join(f"{at:03x}{word:04x}" for at, word in slots),
        )
    )


def replay(seed, part, opcode):
    """The state the model is left in after that one instruction."""
    chip = prepared(seed, part)
    chip.stores.program[chip.registers.pc] = opcode
    chip.step()
    return state_of(chip)


def encode(states):
    return base64.b64encode(
        zlib.compress(b"".join(bytes.fromhex(state) for state in states), 9)
    ).decode()


def decoded(corpus):
    return zlib.decompress(base64.b64decode(corpus["expected"]))


def expected_of(corpus, index):
    return decoded(corpus)[index * PACKED : (index + 1) * PACKED].hex()


def disagreement(expected, found):
    return None if expected == found else (expected, found)


def load(path=None):
    with Path(path or CORPUS).open() as handle:
        return json.load(handle)


def record(cases=None):
    """Ask the reference for every case, and write down what it answered."""
    import oracle

    total = cases or SETTLED + DEFAULT_RANDOM_CASES
    answered = oracle.answers([case_for(index) for index in range(total)])
    with Path(DEFINITION).open() as handle:
        pinned = json.load(handle)["reference"]
    return {
        "reference": f"{pinned['name']} at {pinned['commit']}",
        "cases": total,
        "expected": encode(answered),
    }


def options(argv):
    chosen = Options()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item == "--record":
            chosen.record = True
            continue
        if item not in ("--corpus", "--cases"):
            raise Usage(f"unknown option {item}")
        if not rest:
            raise Usage(f"{item} needs a value")
        value = rest.pop(0)
        if item == "--corpus":
            chosen.corpus = value
        else:
            chosen.cases = int(value)
    return chosen


def run(argv):
    chosen = options(argv)

    if chosen.record:
        found = record(chosen.cases)
        Path(chosen.corpus or CORPUS).write_text(json.dumps(found, indent=2) + "\n")
        print(f"recorded {found['cases']} cases")
        return 0

    corpus = load(chosen.corpus)
    states = decoded(corpus)
    disagreed = 0

    for index in range(corpus["cases"]):
        expected = states[index * PACKED : (index + 1) * PACKED].hex()
        case = case_for(index)
        found = disagreement(expected, replay(*case))
        if found is None:
            continue
        disagreed += 1
        if disagreed <= REPORT_LIMIT:
            seed, part, opcode = case
            print(f"case {index} (seed {seed:08x}, {PARTS[part]}, {opcode:06x})")
            print(f"  reference {found[0]}")
            print(f"  model     {found[1]}")

    if disagreed > REPORT_LIMIT:
        print(f"and {disagreed - REPORT_LIMIT} more")

    print(f"  {corpus['cases']:,} instructions, {disagreed:,} disagreed")
    return 1 if disagreed else 0


def main(argv):
    try:
        return run(argv)
    except Usage as error:
        print(error)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
