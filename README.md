English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

# NEC uPD7725

The NEC uPD7725 and uPD96050 digital signal processors in Python, one instruction per clock cycle, held to NEC's 1987 data sheet and 1989 data book for every printed fact and to a recorded corpus for the whole processor state after every instruction.

[![CI](https://github.com/gufranco/nec-upd7725-96050-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/nec-upd7725-96050-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/nec-upd7725-96050-python)](https://github.com/gufranco/nec-upd7725-96050-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**2** parts, **1,120** encodings walked field by field, **22,240** instructions compared, **0** disagreements, **955** tests, **100%** statement and branch coverage, no dependencies

```python
from upd7725 import Cpu

cpu = Cpu("upd7725")
cpu.reset()
cpu.stores.load_program(bytes([0xC0, 0x0A, 0x81]))

cost = cpu.step()

print(f"{cpu.registers.word('a'):04X}", cost, cpu.registers.pc, cpu.cycles, cpu.steps)
```

```
002A 1 1 5 1
```

The three bytes are one 24-bit program word, `C00A81`. Its top two bits select the load form, the next sixteen carry the value `002A`, and the low four name accumulator A as the destination. The step cost one cycle. The cycle counter reads 5 because `reset()` spends the four cycles NEC gives as the minimum RESET pulse width.

## Install

| Requirement | Version |
|:--|:--|
| Python | 3.12 or newer |
| git | Any |

```bash
git clone https://github.com/gufranco/nec-upd7725-96050-python.git
cd nec-upd7725-96050-python
python3 upd7725/doctor.py
```

The package imports nothing outside the standard library. `python3 -m pip install git+https://github.com/gufranco/nec-upd7725-96050-python.git` installs it with the doctor as the command `upd7725-doctor`.

The doctor checks the machine and the checkout, builds and resets both parts, and ends with one line. It exits 0 when every check passes and 1 otherwise. Paste its whole output into any bug report.

```
  4 checks, nothing to report
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/nec-upd7725-96050-python/releases).

## The interface

`upd7725.Cpu(model, memory=None, *, fill=0, sources=None, seed=UNSET_SEED)` builds one part, powered and not reset.

| Argument | Meaning |
|:--|:--|
| `model` | Required. A model name or alias from the table under [Models](#models). Leaving it out raises `UnknownModelError` |
| `memory` | A `Stores` to use. Left out, the part builds one at its own sizes |
| `fill` | What an unwritten word of each store reads as, masked to the store's width. `0` when left out |
| `sources` | A mapping from `"program"`, `"table"` or `"scratch"` to a function of the address. A store with a source reads unwritten words from it instead of `fill` |
| `seed` | The power-on scramble of the registers. Two parts built with one seed hold the same values |

### Calls

| Call | Effect | Returns |
|:--|:--|:--|
| `reset()` | What the RESET pin does: sets the program counter to 0, sets `steps` to 0, and spends 4 cycles | The part |
| `step()` | Runs one instruction | The cycles it cost, which is 1 for every instruction |
| `run_for(cycles)` | Runs whole instructions until at least `cycles` have passed | The cycles spent |
| `run_until(check, limit=None)` | Steps while `check(cpu)` is false. Raises `RunLimit` after `limit` instructions | The part |
| `held()` | Whether the part has stopped advancing its program. This part has no halt | `False` |
| `irq()` | Raises the interrupt line. On the rising edge, with the EI bit of the status word set, it pushes the program counter, jumps to 100H and spends 1 cycle | `True` when the interrupt was taken |
| `lower_irq()` | Lowers the interrupt line, so the next `irq()` is a new edge | `None` |
| `power_on(seed=UNSET_SEED)` | Scrambles the registers again from `seed`, as construction does | `None` |
| `spend()` | Counts one cycle and calls `on_cycle`. Every cycle the part spends goes through it | `None` |

### State

| Attribute | Meaning |
|:--|:--|
| `model` | The `Model` record the part was built from |
| `registers` | The register file, described below |
| `flags_a`, `flags_b` | The six flags of each accumulator: `s1`, `s0`, `c`, `z`, `ov1`, `ov0`. `int()` packs them with `ov0` in bit 0 and `s1` in bit 5 |
| `stores` | The three stores, described below |
| `cycles` | Cycles since the part was built. A reset adds to it |
| `steps` | Instructions since the last reset |
| `irq_line` | The interrupt line as a level |
| `on_cycle` | `None`, or a function called with no arguments after every cycle |

`registers.pc`, `rp`, `dp` and `sp` mask what is written to them to the part's own widths. `k`, `l`, `m`, `n`, `a` and `b` hold 16 bits and read back signed. `registers.word(name)` reads any of them as an unsigned 16-bit word. `tr`, `trb`, `dr`, `si` and `so` are plain integers. `registers.stack` is a list as long as the part's stack, and `registers.sr` is the status word: the bits `p0`, `p1`, `ei`, `sic`, `soc`, `drc`, `dma`, `usf0`, `usf1`, `rqm` and `drs` sit where Figure 3 of the data sheet puts them, `int(registers.sr)` reads them as one word, and `registers.sr.assign(word)` sets them from one.

```python
from upd7725 import Cpu, disassemble

program = [0xDFFFC1, 0xC00043, 0x150030]
cpu = Cpu("upd7725", fill=0)
cpu.reset()
cpu.stores.load_program(b"".join(word.to_bytes(3, "big") for word in program))
cpu.run_for(3)

registers = cpu.registers
print([found.text for found in disassemble(program)])
print(registers.a, hex(registers.word("a")), cpu.flags_a, int(cpu.flags_a))
print(registers.sr, hex(int(registers.sr)))
```

```
['ld $7FFF,a', 'ld $0001,tr', 'add a idb tr->none']
-32768 0x8000 <Flags ov0 ov1 s0 s1> 51
<Status none> 0x0
```

7FFF plus 1 overflows into the sign bit. Accumulator A reads -32768 signed and 8000 as a word, and the add sets both overflow flags and both sign flags.

### Running, interrupts and the cycle hook

```python
from upd7725 import Cpu, RunLimit

cpu = Cpu("upd7725", fill=0)
cpu.reset()
cpu.stores.load_program(bytes.fromhex("C02007"))
seen = []
cpu.on_cycle = lambda: seen.append(cpu.cycles)

cpu.run_until(lambda part: part.registers.pc == 16)
print(cpu.registers.pc, cpu.steps, cpu.cycles, len(seen), cpu.held())

registers = cpu.registers
print(cpu.irq(), hex(registers.pc), registers.stack[registers.sp - 1], cpu.cycles)
print(cpu.irq(), cpu.irq_line)
cpu.lower_irq()
print(cpu.irq(), registers.stack[registers.sp - 1])

try:
    cpu.run_until(lambda part: False, limit=100)
except RunLimit as error:
    print(error)
```

```
16 16 20 16 False
True 0x100 16 21
False True
True 256
gave up after 100 instructions at 164
```

The first word, `ld $0080,sr`, sets the EI bit, and the zero words after it do nothing. The hook was set after the reset, so it saw the 16 instruction cycles and not the 4 reset cycles. The first `irq()` is a rising edge and is taken. The second finds the line already high and is not. After `lower_irq()` the next one is taken again, from 100H, so 100H is what it pushes. `RunLimit` names the count and the program counter in hexadecimal.

### Stores

`cpu.stores` is a `Stores` holding `program`, `table` and `scratch`. Each is a `Store` exactly as long as the register that addresses it.

| Name | Content |
|:--|:--|
| `Stores(program_words, table_words, scratch_words, fill=0, sources=None)` | The three stores at the given sizes |
| `stores.program`, `stores.table`, `stores.scratch` | 24-bit program words, 16-bit table words, 16-bit scratch words |
| `stores.load_program(image)` | Writes an image from address 0, three bytes to a word, high byte first |
| `stores.load_table(image)` | The same for the table, two bytes to a word |
| `stores.read_byte(at)`, `stores.write_byte(at, value)` | One byte of scratch. An even address is the low byte of word `at // 2` and an odd one the high byte |
| `Store(words, bits, fill=0, source=None)` | One store. `store[at]` reads and writes a word, with `at` taken modulo the length and the value masked to `bits` |
| `store.changed()` | Every written word that differs from what it read before, by address |
| `store.words`, `store.bits`, `store.mask`, `store.source` | The length, the width, the mask for that width, and the source function or `None` |

```python
from upd7725 import Cpu, NotWholeWords, TooLarge

cpu = Cpu("upd7725", fill=0)
stores = cpu.stores
print(len(stores.program), len(stores.table), len(stores.scratch))
print(stores.program.bits, stores.table.bits, hex(stores.scratch.mask))

stores.load_table(bytes.fromhex("12348000"))
print(hex(stores.table[0]), hex(stores.table[1]), hex(stores.table[1024]))

stores.write_byte(1, 0xAB)
print(hex(stores.scratch[0]), hex(stores.read_byte(1)), stores.scratch.changed())

for image in (bytes(4), bytes(3 * 2049)):
    try:
        stores.load_program(image)
    except (NotWholeWords, TooLarge) as error:
        print(type(error).__name__, error)

counted = Cpu("upd7725", fill=0x1234, sources={"table": lambda at: at * 2})
print(hex(counted.stores.scratch[5]), counted.stores.table[5])
```

```
2048 1024 256
24 16 0xffff
0x1234 0x8000 0x1234
0xab00 0xab {0: 43776}
NotWholeWords 4 bytes is not a whole number of 3 byte words
TooLarge 2049 words will not fit in a store of 2048
0x1234 10
```

Table address 1024 wraps to 0 on a uPD7725, whose table is 1024 words long. A load that fails raises before it writes anything.

### The host side

A host sees two addresses: `upd7725.ports.DATA`, which is 0, and `upd7725.ports.STATUS`, which is 1. `upd7725.ports.Host(cpu)` drives them.

| Call | Effect |
|:--|:--|
| `asking` | True while the RQM bit is set, which is when the part waits for the host |
| `settle(limit=200000)` | Steps the part until it asks. Returns the instructions it stepped, and raises `NeverReady` after `limit` |
| `read(address)` | `STATUS` reads the high 8 bits of the status word. `DATA` reads one byte of the data register and clears RQM once the transfer is complete. Any other address reads 0 |
| `write(address, value)` | `DATA` writes one byte of the data register. A write to any other address does nothing, because the status word is read only |
| `send_bytes(values, limit=200000)`, `take_bytes(count, limit=200000)` | Settles before each byte, then writes or reads it |
| `send(word, limit=200000)`, `take(limit=200000)` | A 16-bit word as two bytes, low byte first |

With the DRC bit clear the data register moves 16 bits, a byte at a time, and DRS marks the half already moved. With DRC set it moves 8 bits.

```python
from upd7725 import Cpu, NeverReady
from upd7725.ports import STATUS, Host

cpu = Cpu("upd7725", fill=0)
cpu.reset()
cpu.stores.load_program(bytes.fromhex("C48D06"))
host = Host(cpu)

print(hex(host.read(STATUS)), host.settle(), hex(host.read(STATUS)))
print(hex(host.take()), host.asking)

cpu.reset()
host.send(0xBEEF)
print(hex(cpu.registers.dr), host.asking, cpu.steps)

try:
    host.settle(limit=50)
except NeverReady as error:
    print(error)
```

```
0x0 1 0x80
0x1234 False
0xbeef False 1
the part did not ask for attention within 50 instructions
```

The program is one word, `ld $1234,dr`. Writing the data register sets RQM, which is bit 7 of the byte at `STATUS`. The host takes 1234 in two reads, and the second clears RQM. After a reset the same word asks again, and the host sends BEEF in its place. Nothing after it asks, so the last `settle` gives up.

### Module contents

| Name | Content |
|:--|:--|
| `upd7725.MODELS` | The two `Model` records, keyed by canonical name |
| `upd7725.models.Model` | `name`, `aliases`, `summary`, `counter_bits`, `table_bits`, `pointer_bits`, `stack_levels`, and the derived `program_words`, `table_words`, `scratch_words` and `stack_pointer_bits`. `build(*arguments, **options)` builds a part from it, taking what `Cpu` takes after the model |
| `upd7725.UNSET_SEED` | The seed used when none is given, `0x5A5A5A5A` |
| `upd7725.scramble(size, seed=UNSET_SEED)` | `size` 32-bit values derived from `seed`, the source of the power-on state |
| `upd7725.Store`, `upd7725.Stores` | The store classes described above |
| `upd7725.Clock` | Stepping one cycle at a time, under [Driving it one cycle at a time](#driving-it-one-cycle-at-a-time) |
| `upd7725.decode`, `upd7725.disassemble`, `upd7725.Instruction` | Reading program words, under [Reading without running](#reading-without-running) |
| `upd7725.flags.Flags` | The flag set. `Flags.of(word)` unpacks six bits and `copy()` duplicates one |
| `upd7725.__version__` | The installed version |

### Errors

| Error | Raised when |
|:--|:--|
| `UnknownModelError` | `Cpu` gets no model, a name no model goes by, or a part this package refuses to model. The message lists the names accepted |
| `RunLimit` | `run_until` reaches its `limit` |
| `ClockClosed` | `Clock.tick()` is called after the clock was closed |
| `NotWholeWords` | `load_program` or `load_table` gets an image that is not a whole number of words |
| `TooLarge` | `load_program` or `load_table` gets an image longer than the store |
| `NeverReady` | `Host.settle` reaches its `limit` without the part asking |

All six are importable from `upd7725`.

### Command-line tools

| Command | Arguments | Exit codes |
|:--|:--|:--|
| `python3 upd7725/doctor.py` | None | 0 when every check passes, 1 otherwise |
| `python3 -m conformance.instructions` | `--corpus PATH`, `--cases N`, `--record`, `--retake` | 0 with no disagreement, 1 with any, 2 for a bad argument |
| `python3 -m conformance.differential` | `--from N`, `--cases N` with 5,000 as default, `--seconds S` | 0 when the two implementations agree, 1 when they do not, 2 for a bad argument |
| `python3 -m conformance.speed` | `--instructions N` with 200,000 as default, `--repeats N` with 7 as default | 0 at or above the floor, 1 below it, 2 for a bad argument |
| `python3 -m conformance.documents` | `--check`, `--only SUBSTRING` | 0 when every document matches its digest, 1 otherwise |
| `python3 -m conformance.quotes` | None | 0 when every quote is found or no document is present, 1 otherwise |
| `python3 -m conformance.links` | None | 1 when a link in this file answers 404 or 410, 0 otherwise |
| `python3 -m conformance.package WHEEL` | The wheel to audit | 0 when every module ships and no test does, 1 otherwise, 2 with no wheel named |

`--record` alone refuses to overwrite the corpus. `--record --retake` overwrites it, and is only for carrying a corrected hardware fact.

## Running it at a real speed

A part runs at whatever its crystal says. `step()` reports what an instruction cost, so a host can hold the part to a real clock.

```python
import time

from upd7725 import Cpu

HERTZ = 8_192_000
SLICE = 0.02

cpu = Cpu("upd7725")
cpu.reset()
per_slice = round(HERTZ * SLICE)
owed = 0

for _ in range(5):
    began = time.perf_counter()
    owed += per_slice
    owed -= cpu.run_for(owed)
    time.sleep(max(0.0, SLICE - (time.perf_counter() - began)))
```

8,192,000 Hz is the clock the data sheet quotes its 122 ns instruction cycle at. One instruction is one cycle on this part, so `run_for()` lands exactly on its budget and `owed` stays 0. The loop carries the difference anyway, so it reads the same as the loop for a part whose instructions take several cycles.

`python3 -m conformance.speed` measures the model and prints its rate as a share of the 8,192,000 instructions per second the silicon does. It fails below 250,000 instructions per second.

## Driving it one cycle at a time

`Clock(cpu)` stops the part between any two cycles, which is where a board changes what a read will answer.

```python
from upd7725 import Clock, ClockClosed, Cpu

cpu = Cpu("upd7725", fill=0)
cpu.reset()

with Clock(cpu) as clock:
    clock.tick()
    print(clock.run_for(6), cpu.registers.pc, cpu.cycles)

try:
    clock.tick()
except ClockClosed as error:
    print(clock.closed, error)
```

```
7 7 11
True this clock has been closed
```

| Call | Effect |
|:--|:--|
| `tick()` | Runs to the end of the next cycle and stops. Returns the cycles this clock has run |
| `run_for(cycles)` | `cycles` ticks. Returns the cycles this clock has run |
| `close()` | Stops the part and puts back the `on_cycle` it found. Leaving a `with` block closes it |
| `cycles`, `closed`, `cpu` | The cycles run, whether it is closed, and the part |

Iterating a clock ticks it. An exception the part raises during a tick is raised from `tick()`, and the clock closes.

NEC states the part executes an instruction in one external clock cycle, so a cycle boundary and an instruction boundary are the same place. `Clock` gives this part the same interface as the rest of the family and no finer resolution, and `step()` is the faster call. The clock runs the part on a thread and blocks it at each cycle, because Python cannot suspend a call stack.

## Models

One instruction set, two sizes. Every store is exactly as long as the register that addresses it.

| Build it with | Program store | Table | Scratch | Stack | Program counter |
|:--|--:|--:|--:|--:|--:|
| `Cpu("upd7725")` | 2048 x 24 bits | 1024 x 16 | 256 x 16 | 4 | 11 bits |
| `Cpu("upd96050")` | 16384 x 24 bits | 2048 x 16 | 2048 x 16 | 8 | 14 bits |

NEC's data sheet and data book cover the uPD7725. No NEC document for the uPD96050 was located, so its four figures rest on secondary sources. The record marks it `verified: false`, and [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) says what would settle it.

Each part answers to the numbers NEC sold it under. Case, hyphens and underscores do not matter, so `Cpu("uPD-77C25")` builds a uPD7725.

| Build it with | Also answers to |
|:--|:--|
| `Cpu("upd7725")` | `7725`, `upd77c25`, `77c25`, `necupd7725` |
| `Cpu("upd96050")` | `96050`, `upd96050gf`, `necupd96050` |

```python
import upd7725

for name, model in upd7725.MODELS.items():
    sizes = (model.program_words, model.table_words, model.scratch_words, model.stack_levels)
    print(name, model.aliases, *sizes)

print(upd7725.Cpu("uPD-77C25").model.name, upd7725.Cpu("96050").model.name)

for asked in (None, "upd7720", "upd77p25", "upd7726"):
    try:
        upd7725.Cpu(asked)
    except upd7725.UnknownModelError as error:
        print(error)
```

```
upd7725 ('7725', 'upd77c25', '77c25', 'necupd7725') 2048 1024 256 4
upd96050 ('96050', 'upd96050gf', 'necupd96050') 16384 2048 2048 8
upd7725 upd96050
no model was named, and this package will not choose one for you. Name one of: upd7725, upd96050
upd7720 is not modelled here: the uPD7720 is the earlier part of the same family, and the reference this package is measured against does not implement it; a model of it here would have nothing behind it
upd77p25 is not modelled here: the uPD77P25 is the same processor with its program in erasable storage rather than masked, which changes how it is made rather than what it does; ask for upd7725 and load the program yourself
upd7726 is not a processor this package covers; it has upd7725, upd96050
```

A part number nothing here implements is refused rather than resolved to the nearest one.

## Reading without running

`decode(word, address=0)` reads one program word and `disassemble(words, address=0)` yields one `Instruction` per word, numbered from `address`. An `Instruction` carries `address`, `raw` and `text`.

```python
from upd7725 import decode, disassemble

for found in disassemble([0xC00A81, 0x910040, 0x400000], 0x100):
    print(f"{found.address:04X}  {found.text}")

print(decode(0x8F0000), decode(0x158C51, 0x20).text)
```

```
0100  ld $002A,a
0101  jnza $0010
0102  rt
<Instruction 0000 jp ?078 $0000> add b idb rp->a dphm6
```

It takes words rather than bytes, because the program store is addressed by word. Every 24-bit word decodes to one of the four forms: `op`, `rt`, `jp` and `ld`. A jump whose condition field names no condition prints as `jp ?` with the field in hexadecimal, so nothing raises.

## Nothing starts clean

A built part holds values derived from its seed in `pc`, `rp`, `dp`, `sp`, `k`, `l`, `m`, `n`, `a`, `b`, `tr`, `dr` and every stack slot. There is no argument that clears them. The flags, the status word, `si`, `so` and `trb` start at 0, and every store reads `fill` until it is written.

```python
from upd7725 import Cpu

powered = Cpu("upd7725")
print(hex(powered.registers.pc), hex(powered.registers.word("a")), powered.cycles)
print(hex(Cpu("upd7725", seed=7).registers.pc))
print(Cpu("upd7725", seed=7).registers.pc == Cpu("upd7725", seed=7).registers.pc)

powered.reset()
print(hex(powered.registers.pc), hex(powered.registers.word("a")), powered.cycles)
print(powered.flags_a, powered.registers.sr, hex(powered.stores.program[0]))
```

```
0x4eb 0xa2fb 0
0x438
True
0x0 0xa2fb 4
<Flags none> <Status none> 0x0
```

Before the reset the program counter points at 4EB, so stepping a part nobody reset runs from an address the seed chose. The data sheet says RESET sets the program counter to 0, and that is all `reset()` changes: accumulator A still holds A2FB afterwards.

## Is it right

The corpus walks **1,120** encodings field by field on both parts and adds 20,000 cases derived from a seed. Each case sets up a whole processor state, runs one instruction and records the whole state after it. The model reproduces all of them: **22,240 instructions, no disagreements**.

```bash
python3 -m conformance.instructions
python3 -m conformance.differential --from 70000000 --cases 4000
python3 conformance/alu_flags.test.py
```

```
  22,240 instructions, 0 disagreed
  4,000 cases, the model and the reference agreed on every one
```

The first command is the gate, and it needs nothing outside the repository. The second steps [`conformance/reference.py`](conformance/reference.py), a second implementation written to a different shape, against the model on cases past the end of the corpus. The third drives all sixteen ALU operations against Table 6 of the 1989 data book, which states for each flag whether it is affected, reset, held or indefinite. The model agrees with every cell.

[`conformance/hardware.json`](conformance/hardware.json) holds every fact taken from a document, with the sentence it came from and the page. When the data sheet and the corpus disagree, the data sheet wins and the corpus is retaken. That happened twice, and [`conformance/pinned.json`](conformance/pinned.json) records both: the stack depth, which every implementation in the field gives as sixteen and NEC prints as four, and 581 cases where an arithmetic operation names its own accumulator as the destination of the data move, which NEC says turns the operation into a NOP.

The corpus was recorded from an emulator, so it decides only what NEC did not print. [`conformance/divergences.json`](conformance/divergences.json) holds every place two sources part. [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) names three questions still open and the measurement that would close each one.

## Working on it

| Need | Where |
|:--|:--|
| Every gate and the order to run them | [CONTRIBUTING.md](CONTRIBUTING.md) |
| The same material for a coding agent | [AGENTS.md](AGENTS.md) |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md) |
| Bug reports | [GitHub Issues](https://github.com/gufranco/nec-upd7725-96050-python/issues) |
| Security reports | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx mypy@1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
python3 -m coverage erase
for f in $(find upd7725 conformance -name '*.test.py' | sort); do python3 -m coverage run -a "$f"; done
python3 -m coverage report
```

Each module has a test file beside it, named `<module>.test.py`, and each runs on its own. Coverage is a hard gate at 100% statement and branch, and types are `mypy` at strict.

## References

- NEC Electronics, *uPD77C25/uPD77P25 Digital Signal Processor Data Sheet*, Advance Product Information, August 1987. 36 pages, 1,299,452 bytes, SHA-256 `d043be18d5cd21d90960ffb7e068e3b9a81647c8534a142f29eb11015733d042`. Fetched from https://www.cryptomuseum.com/df/telefunken/e2000/files/uPD77C25.pdf
- NEC Electronics, *Digital Signal Processor and Speech Processor Products Data Book*, document 50052, 1989. 388 pages, 14,316,524 bytes, SHA-256 `2f0190523de99938cc1da1c138f2c5b7f71573eb11bcb3b0dcdd1da1267e85ce`. Fetched from https://bitsavers.trailing-edge.com/components/nec/_dataBooks/1989_DSP_and_Speech_Products_Data_Book.pdf
- ares, https://github.com/ares-emulator/ares, at the commit [`conformance/pinned.json`](conformance/pinned.json) names, studied for instruction-level behaviour the documents do not give. No code is taken.

Neither document is redistributable, and neither is in this repository. [`conformance/documents.json`](conformance/documents.json) carries the digest, the size and the address of each. `python3 -m conformance.documents` downloads both into `docs/`, which git ignores, and refuses a file whose digest does not match. `python3 -m conformance.quotes` then finds every quoted sentence in them.

Both are scans of printed books, so each page was read twice: from the image and from the text layer the file carries. The 1987 text layer prints `lhe` for `the` and an `a-bit data pointer` where the page says `8-bit`. A page recorded beside a quote is one where both readings agree, or one confirmed by reading that page directly. The data book numbers pages per section, as 2-33, so a fact read from it names the section.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
