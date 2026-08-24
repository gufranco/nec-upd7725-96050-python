<div align="center">

<h1>NEC uPD7725</h1>

<strong>A uPD7725 you can drive from a clock, held to NEC's own data book for every flag each ALU operation touches and to a per-encoding corpus for the whole processor state after every instruction.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/nec-upd7725-96050-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/nec-upd7725-96050-python/actions/workflows/ci.yml)
[![Conformance](https://img.shields.io/badge/conformance-1%2C002%2C240%20%2F%201%2C002%2C240-brightgreen)](#is-it-right)
[![Encodings](https://img.shields.io/badge/encodings-1%2C120%20walked%20field%20by%20field-brightgreen)](#is-it-right)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#working-on-it)
[![Types](https://img.shields.io/badge/mypy-strict-blue)](pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

**2** parts · **1,002,240** instructions compared and **1,120** encodings walked field by field, **0** disagreements · **703** tests · **100%** statement and branch coverage · no dependencies

```python
from upd7725 import Cpu

cpu = Cpu("upd7725")
cpu.reset()
cpu.stores.load_program(bytes([0xC0, 0x0A, 0x81]))

cpu.step()

print(f"{cpu.registers.word('a'):04X}")
```

```
002A
```

One instruction, loading `002A` into the first accumulator. A word here is
twenty four bits, so a program image is three bytes to the instruction.

## Install

```bash
pip install git+https://github.com/gufranco/nec-upd7725-96050-python.git
```

Python 3.12 or newer. Nothing else.

## The interface

Everything a caller touches. Nothing else is public.

| Call | Does | Returns |
|:--|:--|:--|
| `Cpu(model="upd96050", memory=None, **options)` | Builds a part, powered and not yet reset. Stores of its own if none are given | a `Cpu` |
| `cpu.reset()` | Drives RESET. Costs the four cycles NEC names as the minimum the pin must be held | the `Cpu` |
| `cpu.step()` | Runs one instruction | cycles it cost, always one |
| `cpu.run_for(cycles)` | Runs whole instructions until at least that many cycles have passed | cycles actually spent |
| `cpu.run_until(check, limit=None)` | Steps while `check(cpu)` is false. `limit` bounds the instructions and raises `RunLimit` | the `Cpu` |
| `cpu.held()` | Whether the part has stopped advancing the program | `bool`, always false: this part has no halt |
| `cpu.irq()` | Offers the interrupt line and acts on it now. A call to 100H when the enable bit is set | `True` if taken |
| `identify(image)` | Names an image from its digest, with no machine to run it in | an `Identity` |
| `describe(model)` | The part behind a name, before building one | a `Model` |
| `carrying(part)` | The part a given coprocessor module was built on | a `Model` |

| Pin or attribute | Is |
|:--|:--|
| `cpu.irq_line` | The request line as a level. Edge sensitive: the transition takes the interrupt, and holding it afterwards does not take it again. `cpu.lower_irq()` drops it |
| `cpu.cycles` / `cpu.steps` | Cycles since construction, across resets; instructions since the last reset |
| `cpu.registers` | `a` and `b` with their flag sets, `k`, `l`, `m`, `n`, `tr`, `trb`, `dr`, `si`, `so`, the pointers `pc`, `rp`, `dp`, `sp`, the stack, and `sr`, the status word the host reads |
| `cpu.flags_a` / `cpu.flags_b` | One accumulator's six bits each: `s1`, `s0`, `c`, `z`, `ov1`, `ov0` |
| `cpu.stores` | `program`, `table` and `scratch`, each as long as the register that addresses it |
| `cpu.on_cycle` | Called once per cycle, after that cycle's work |

Options: `seed=` fixes the undefined state, `fill=` and `sources=` decide what an unwritten word answers.

**A part arrives powered, not reset**, because no board hands over one that has reset itself. Every register holds rubbish derived from the seed, the program counter included, so stepping it executes rubbish from a rubbish address. Call `reset()` to get a machine that runs a program.

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

One instruction is one cycle on this part, so `run_for()` lands exactly on its budget rather than overshooting. Carrying the difference anyway is what keeps the loop identical to the ones in the sibling packages, where an instruction spans several cycles and overshoot is unavoidable.

## Driving it one cycle at a time

`Clock` stops the part between any two cycles, which is where a board changes what a read will answer.

```python
from upd7725 import Clock, Cpu

cpu = Cpu("upd7725")
cpu.reset()

with Clock(cpu) as clock:
    clock.tick()
    clock.run_for(6)

print(cpu.registers.pc)
```

```
7
```

On this part a cycle boundary and an instruction boundary are the same place, because NEC states it executes an instruction in one external clock cycle. So `Clock` buys the same interface as the sibling packages rather than finer resolution, and `step()` is the right call when a caller wants speed.

It is not free. An instruction is an ordinary call stack and Python cannot suspend one, so the clock runs the part on a thread and lets it block where the cycle is spent, which is what ares and bsnes do.

## Models

One instruction set, two sizes. Every store is exactly as long as the register that addresses it, which is why the two differ in capacity and in nothing else this package can measure.

| Build it with | Program store | Table | Scratch | Stack | Modules built on it |
|:--|--:|--:|--:|--:|:--|
| `Cpu("upd7725")` | 2048 x 24 bits | 1024 x 16 | 256 x 16 | 4 | DSP-1, DSP-1A, DSP-1B, DSP-2, DSP-3, DSP-4 |
| `Cpu("upd96050")` | 16384 x 24 bits | 2048 x 16 | 2048 x 16 | 8 | ST010, ST011 |

The last column is the one to be careful with. NEC published a data sheet and a data book for the smaller part; **no document for the larger one was located**, so its four figures rest on secondary sources, it carries `verified: false` in the record, and the gap is written up in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md).

Each answers to the numbers NEC sold it under. Case and separators do not matter.

| Build it with | Also answers to |
|:--|:--|
| `Cpu("upd7725")` | `7725`, `upd77c25`, `77c25`, `necupd7725` |
| `Cpu("upd96050")` | `96050`, `upd96050gf`, `necupd96050` |

A part number nothing here implements is refused rather than resolved to something close, so `Cpu("upd7720")` raises `UnknownModelError` instead of handing back a part missing instructions the caller asked for.

## Reading without running

An image on disk has nothing but its bytes, so identifying and running are separate halves.

```python
from upd7725 import firmware

identity = firmware.identify(open("dsp1b.bin", "rb").read())
print(identity.part, identity.revision, identity.processor)
```

```
dsp1b DSP-1B upd7725
```

An image whose length is right but whose content is not raises `Corrupt` with the digest it actually has, rather than loading something that will run wrong. This package carries no image and never will: each belongs to whoever wrote it. [`upd7725/artifacts.manifest.json`](upd7725/artifacts.manifest.json) says what each one is and the digest that identifies it, so a copy you already own can be confirmed before it is run.

## Nothing starts clean

Registers and stores hold a reproducible scrambled pattern. There is no parameter that clears the registers and there will not be one: a part that has been powered and not reset holds rubbish on real silicon, and a model that starts at zero turns a missing reset into a passing test.

```python
from upd7725 import Cpu

powered = Cpu("upd7725")
print(hex(powered.registers.pc), powered.cycles)
print(hex(Cpu("upd7725", seed=7).registers.pc))
print(Cpu("upd7725", seed=7).registers.pc == Cpu("upd7725", seed=7).registers.pc)
```

```
0x4eb 0
0x438
True
```

Rubbish derived from the seed, the same every time, and not zero. The part has spent nothing because nothing has driven RESET yet.

## Is it right

Every encoding is walked field by field and every instruction is compared against a recorded corpus that states the whole processor state after each one, not merely the answer: **1,002,240 instructions, no disagreements**. Two independent implementations are stepped against that one corpus.

```bash
python3 -m conformance.instructions
python3 -m conformance.differential --from 70000000 --cases 4000
python conformance/alu_flags.test.py
```

The first runs with nothing else on your disk. It is the gate.

Where a document and the corpus disagree, both are kept. [`conformance/hardware.json`](conformance/hardware.json) holds every fact taken from a document with the sentence it came from and the page. [`conformance/divergences.json`](conformance/divergences.json) holds every place two sources part, with what would settle it.

The flags are the part worth naming. The 1987 data sheet is Advance Product Information and states no flag rules, so they rested on the corpus alone until NEC's 1989 data book turned up: its Table 6 gives, for all sixteen ALU operations, which flags are affected, which are reset, which are held and which NEC declines to define. This model agrees with it on every cell, and `conformance/alu_flags.test.py` drives all sixteen against a run.

**Four questions remain** where being faithful is a claim rather than a measurement, and each names the measurement that would close it: [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md). One cannot be closed by anyone here: no NEC document for the larger part has been found, so everything asserted about it rests on secondary sources, and secondary sources for this family are emulators.

## Working on it

```bash
python -m coverage erase
for file in $(find upd7725 conformance -name '*.test.py' | sort); do
  python -m coverage run -a "$file"
done
python -m coverage report
```

`python -m upd7725.doctor` says what is actually on this machine: the parts, what makes each one different, and whether the files this repository cannot carry are here and whole. It is what an issue asks for, because a report is only as good as what it says about the machine that produced it.

Tests sit beside the module they cover, named `<module>.test.py`. Coverage is 100% of statements and branches, enforced. Types are `mypy` at strict. Commits follow [Conventional Commits](https://www.conventionalcommits.org/), and releases are cut by [semantic-release](https://semantic-release.gitbook.io/).

[`AGENTS.md`](AGENTS.md) is the document for an agent working here. [`FAMILY.md`](FAMILY.md) is the standard this repository shares with [zilog-z80-python](https://github.com/gufranco/zilog-z80-python) and [mos65xx-python](https://github.com/gufranco/mos65xx-python), kept identical in all three.

```
upd7725/
  core.py          the processor
  clock.py         driving it one cycle at a time
  models.py        the two parts, by name and alias
  memory.py        the three stores, each at its own width
  registers.py     the register file, and the status word
  flags.py         one accumulator's six bits
  ports.py         the two addresses the host sees, and the handshake
  firmware.py      naming an image from its digest
conformance/
  pinned.json      which corpus, from which reference, at which commit
  instructions.py  every encoding, walked field by field
  differential.py  model against reference, on cases the corpus does not cover
  alu_flags.test.py  every ALU operation against the flag matrix NEC printed
  hardware.json    what NEC printed, fact by fact
  divergences.json where sources part
```

## References

This repository carries no documents. Every claim is traced to something published elsewhere, listed here so a reader can fetch the same file and check the same page. Each row gives the page count and the first sixteen characters of the file's SHA-256, because vendor links move and a link that has rotted into a different scan is easy to follow without noticing. Compute the full digest with `shasum -a 256 <file>`.

Every manufacturer document below is copyrighted and not redistributable, which is why none is in this repository. Individual sentences are quoted in [`conformance/hardware.json`](conformance/hardware.json) with the page they are printed on.

| Document | Date | Pages | SHA-256 | Redistributable |
|:---------|:-----|------:|:--------|:----------------|
| [NEC Electronics, *uPD77C25/uPD77P25 Digital Signal Processor Data Sheet*, Advance Product Information](https://www.cryptomuseum.com/df/telefunken/e2000/files/uPD77C25.pdf) | 1987-08 | 36 | `d043be18d5cd21d9…` | No |
| [NEC Electronics, *Digital Signal Processor and Speech Processor Products Data Book*, document 50052](https://bitsavers.trailing-edge.com/components/nec/_dataBooks/1989_DSP_and_Speech_Products_Data_Book.pdf) | 1989 | 388 | `2f0190523de99938…` | No |

The data book is the fuller of the two. The 1987 sheet is Advance Product Information and states no flag rules; the data book's Table 6 gives, for all sixteen ALU operations, which flags are affected, which are reset, which are held and which NEC declines to define. It numbers pages per section, as 2-33, so a fact read from it names the section.

Both are photographs of printed books, so each is read twice: once from the page images and once from the text layer the file carries. Neither is reliable alone. The 1987 layer prints `lhe` for `the` and an `a-bit data pointer` where the page says `8-bit`, and the image read misses a faint line outright. A page recorded beside a quote is one both readings agree on, or one confirmed by reading that page directly.

**No document for the uPD96050 was located.** Everything asserted about that part rests on secondary sources, it carries `verified: false` in the record, and the gap is written up in [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md).

| Source | Used for |
|:-------|:---------|
| [ares-emulator/ares](https://github.com/ares-emulator/ares) | The reference the corpus was recorded from. Commit in [`conformance/pinned.json`](conformance/pinned.json) |

## Citing this

[CITATION.cff](CITATION.cff) is kept in step with the released version by the same script that stamps the package, so the version it names is the version that shipped. GitHub renders it as a Cite this repository button.

## License

[MIT](LICENSE)
