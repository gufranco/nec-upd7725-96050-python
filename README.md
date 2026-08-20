<div align="center">

<h1>NEC uPD7725 &middot; uPD96050</h1>

<strong>The processor a shelf of Super Nintendo coprocessors turns out to be, settled one instruction at a time.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/nec-upd7725-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/nec-upd7725-python/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#tests)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
  <a href="#quick-start">Quick start</a> &nbsp;|&nbsp;
  <a href="#how-this-is-proved">How this is proved</a> &nbsp;|&nbsp;
  <a href="#firmware">Firmware</a> &nbsp;|&nbsp;
  <a href="#the-dsp-1-was-masked-three-times">The DSP-1 revisions</a> &nbsp;|&nbsp;
  <a href="https://github.com/gufranco/nec-upd7725-python/issues">Issues</a>
</p>

**2** parts · **4** instruction forms · **1,120** encodings walked field by field · **1,002,240** instructions compared against the reference, **0** disagreements · **279** tests · **100%** statement and branch coverage · **zero** firmware, ever

```python
from upd7725 import Processor

chip = Processor("upd96050")
chip.stores.load_program(program)
chip.stores.load_table(table)
chip.run(1000)

chip.registers.sr.rqm  # True: it is waiting for the console now
```

---

## The problem

Six different Super Nintendo coprocessors are the same silicon. The DSP-1 does
three-dimensional maths, the DSP-3 decompresses graphics, the DSP-4 draws a road,
the ST010 steers a race car and the ST011 plays shogi, and every one of them is
this processor running a different program masked into it at the factory.

Modelling what each of those programs does is one job, and a good one. Modelling
the thing they all run on is a different job, and it is the one that reaches the
parts whose behaviour cannot be written down. Nobody can describe the ST011's
answers as a set of commands, because its answer is a shogi move and the thing
that chooses it is a program.

## The solution

Model the processor, and let the program be the program.

That splits the problem in a way that also settles the legal question. The
processor is settled by walking its own encoding, which needs no program at all,
so the evidence here is complete with nothing on your disk. A firmware image is
needed only to run one particular cartridge's part, it belongs to whoever wrote
it, and it is never carried here.

<table>
<tr>
<td width="50%" valign="top">

### Nothing starts clear

Every case fills every store, every register and both flag sets before the
instruction runs. Silicon powers up holding whatever it holds.

</td>
<td width="50%" valign="top">

### Every field, not a sample

Every operation against every accumulator and operand, every source and
destination pair, every pointer step, every branch code including the ones the
part does not have.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Two implementations, one corpus

The package and the reference in `conformance/` are built differently on purpose,
and both are held to states recorded from a third implementation.

</td>
<td width="50%" valign="top">

### The whole state, not the answer

Every register, both flag sets, the whole stack, and any scratch word that
changed. A model that disturbs something it should not have fails here.

</td>
</tr>
</table>

## Quick start

### Prerequisites

| Tool | Version | Install |
|:-----|:--------|:--------|
| Python | >= 3.12 | [python.org](https://www.python.org/downloads/) |

### Setup

```bash
git clone https://github.com/gufranco/nec-upd7725-python.git
cd nec-upd7725-python
```

### Verify

```bash
python3 conformance/instructions.py
#   22,240 instructions, 0 disagreed
```

That runs with nothing else on your disk. It is the gate.

## The instruction set

Two bits of every twenty four choose the form, and there are only four of them.

| Form | What it does |
|:-----|:-------------|
| Arithmetic | One of fifteen operations on one of two accumulators, and a move, in that order |
| Return | The same, and then take the way back off the stack |
| Branch | Thirty four conditions, two jumps, two calls, and one jump through a register |
| Load | Sixteen bits into one of sixteen places |

Two things about it are worth knowing before reading the code. Every instruction
ends with a multiply whether it asked for one or not, because the multiplier is
wired to two registers and runs continuously. And the arithmetic form performs its
move **after** its arithmetic, so the value it moves is the one read at the start
rather than the one just computed.

The flags are the other surprise. There are two overflow bits and two sign bits
rather than one of each, and the second of each pair is not a copy of the first:
the second sign freezes once a second overflow is held, so it records the sign a
value had before the word stopped being able to express it. That pair is how the
part carries a value through a run of sums that leave the word and come back,
which is what a fixed-point routine does constantly.

## How this is proved

| Part | Evidence | Strength |
|:-----|:---------|:---------|
| Every instruction | 22,240 recorded states, and 1,002,240 compared while the corpus was built | Differential, over the whole state |
| Every field of every form | 1,120 encodings walked rather than sampled | Exhaustive within each form |
| Both parts | Every case runs on both, at their own register widths | Differential |
| The starting state | Filled from the seed, never cleared | Adversarial |
| The scratch memory | Any word that changed is reported with its address | Total, not spot-checked |
| The parts themselves | Seven firmware images run 200,000 instructions each | Opt-in, on your own copy |

The corpus was recorded from an independent implementation and the two Python
implementations here are both held to it. That is what keeps the comparison from
being two guesses agreeing with each other: neither of them decided what the right
answer is.

```bash
python3 conformance/instructions.py --record   # regenerate from the reference
python3 conformance/instructions.py            # replay the recorded states
```

## Firmware

Nothing in this repository is firmware, and nothing ever will be. Every one of
those programs belongs to whoever wrote it.

What is here is [`artifacts.manifest.json`](artifacts.manifest.json): what each
image is, how long it is, and the digest that identifies it. A digest names a file
and reconstructs nothing.

```bash
export UPD7725_FIRMWARE_DIR=~/nec-upd7725-python/firmware
python3 conformance/against_firmware.py
#   dsp1   DSP-1   on upd7725: 200,000 instructions, still inside its own program store
#   st011  ST011   on upd96050: 200,000 instructions, still inside its own program store
```

Without one, every check that needs it reports as skipped rather than as passed,
including in CI, where the run says so out loud. A check that cannot run is not a
check that succeeded.

A file that does not match is diagnosed rather than merely refused:

```python
from upd7725 import firmware

firmware.identify(open("mystery.bin", "rb").read())
# Unrecognised: this is 8192 bytes, the length of dsp1, dsp1b, dsp2, dsp3, dsp4,
# but its content is altered: its sha256 is ... and no accepted revision has
# that. A file of the right length with the wrong content is usually a different
# revision than the one it is named after, or a bad dump
```

## The DSP-1 was masked three times

The DSP-1, the DSP-1A and the DSP-1B are three different programs, and the last
corrected the first. That is usually asserted. Here it is measured, by running
both images on this processor and asking them the same questions:

```bash
python3 conformance/against_firmware.py
#   the two masks of the DSP-1 answer differently on 217 of 256 command bytes
```

Nearly half the microcode differs between them: 993 of 2,048 instruction words and
537 of 1,024 table words. Most arguments still produce the same answer, which is
why the disagreement took a search to find rather than a guess: whatever the later
mask corrected, the earlier one gets right for the common case.

## Models

| Model | Counter | Table pointer | Scratch pointer | Parts that ran on it |
|:------|--------:|--------------:|----------------:|:---------------------|
| `upd7725` | 11 bits | 10 | 8 | DSP-1, DSP-1A, DSP-1B, DSP-2, DSP-3, DSP-4 |
| `upd96050` | 14 bits | 11 | 11 | ST010, ST011 |

Every store is exactly as long as the register that addresses it. Asking for a
part this package does not have says why rather than only that:

```python
from upd7725 import Processor

Processor("upd7720")
# UnknownModelError: upd7720 is not modelled here: the uPD7720 is the earlier
# part of the same family, and the reference this package is measured against
# does not implement it; a model of it here would have nothing behind it
```

## Project structure

```
upd7725/
  __init__.py     the package, and the part chosen at construction
  core.py         fetch, and the four instruction forms
  registers.py    the register file, at the widths the part has
  flags.py        the six bits each accumulator carries
  memory.py       the three stores, at their own widths and lengths
  ports.py        the two addresses the console sees, and the handshake
  firmware.py     an image its owner supplies, identified before it is run
  models.py       the two parts, and which cartridge chip ran on each
conformance/
  reference.py        an independent implementation, built to a different shape
  oracle.py           one case through it, in the shape the recordings are in
  instructions.py     the runner that settles every instruction
  against_firmware.py the opt-in runner that needs an image you already own
  corpus.json         22,240 recorded states
firmware/         where your own copies go, and nothing is ever committed
```

Each module has its tests beside it as `<module>.test.py`, so a module and the cases that pin its behaviour are read together.

## When something is wrong

```bash
python3 -m upd7725.doctor
```

It looks at this machine and prints what is actually there: the Python it is
running on, both processors and the shape of each, where images are looked for,
what the manifest declares, and every image present with its SHA-256.

That last part settles most reports on its own. Two people running the same part
and getting different answers are almost always running different files, and this
shows it in one glance rather than after a round trip.

Nothing is hidden. A check that fails says what it saw, and a check that itself
throws is reported as what it threw rather than taking the report down with it.
Paste all of it into an issue.

## Tests

```bash
for f in upd7725/*.test.py conformance/*.test.py; do python3 "$f"; done
```

| Suite | File | Covers |
|:------|:-----|:-------|
| Instruction set | [`upd7725/core.test.py`](upd7725/core.test.py) | Every form, source, destination, operation, pointer step and branch |
| Flags | [`upd7725/flags.test.py`](upd7725/flags.test.py) | The six bits, and the two that do not follow the other two |
| Registers | [`upd7725/registers.test.py`](upd7725/registers.test.py) | Widths, wrapping, signedness, the status word |
| Memory | [`upd7725/memory.test.py`](upd7725/memory.test.py) | Word widths, byte halves, loading, computed initial contents |
| Ports | [`upd7725/ports.test.py`](upd7725/ports.test.py) | The handshake, both transfer widths, waiting |
| Firmware | [`upd7725/firmware.test.py`](upd7725/firmware.test.py) | The manifest, identification, diagnosis, loading |
| Reference | [`conformance/reference.test.py`](conformance/reference.test.py) | The independent implementation, on its own |
| Oracle | [`conformance/oracle.test.py`](conformance/oracle.test.py) | That it reproduces every recorded state |
| Corpus | [`conformance/instructions.test.py`](conformance/instructions.test.py) | Case generation, coverage of the encoding, replay |
| Firmware run | [`conformance/against_firmware.test.py`](conformance/against_firmware.test.py) | Booting each image, and the comparison between masks |

Coverage is enforced at 100% of statements and branches by [`pyproject.toml`](pyproject.toml), so a new branch without a test fails the build rather than quietly lowering the number.

## Development

| Command | Description |
|:--------|:------------|
| `ruff format .` | Format |
| `ruff check .` | Lint |
| `python3 -m coverage run -a <file>` | Run one test file under coverage |
| `python3 -m coverage report` | Coverage, which fails below 100% |
| `python3 conformance/instructions.py` | Replay the recorded states |
| `python3 conformance/against_firmware.py` | Run whatever images are on your disk |
| `pnpm run format` | Format every JSON file |

## Project conventions

| Convention | Source |
|:-----------|:-------|
| Commit format | [Conventional Commits](https://www.conventionalcommits.org/) |
| Releases | [semantic-release](https://semantic-release.gitbook.io/), driven by [`.releaserc.json`](.releaserc.json) |
| Lint and format | [Ruff](https://docs.astral.sh/ruff/), configured in [`pyproject.toml`](pyproject.toml) |
| JSON formatting | [Prettier](https://prettier.io/), configured in [`.prettierrc.json`](.prettierrc.json) |
| Test layout | `<module>.test.py` beside the module it covers |

## Versioning

This project follows [Semantic Versioning](https://semver.org/), and every release is tagged from `main` by semantic-release. See [releases](https://github.com/gufranco/nec-upd7725-python/releases).

## FAQ

<details>
<summary><strong>Why model the processor when the microcodes are already modelled elsewhere?</strong></summary>
<br>

Because two of them cannot be. A behavioural model works when a part's answers are
functions of its arguments, which is true of the DSP-1's projections and the
ST010's navigation. It is not true of the ST011, whose answer is a shogi move; the
thing that chooses it is a program, and the only honest way to reproduce a program
is to run it. The processor is what makes that possible without inventing a shogi
engine and calling it a model of somebody's part.

</details>

<details>
<summary><strong>Is this useful without a firmware image?</strong></summary>
<br>

The evidence is. Every instruction is settled by generating instruction words
rather than quoting a program, so the gate runs and passes on a machine with
nothing else on it. What needs an image is running a particular cartridge's part,
which is the one thing nobody else can give you.

</details>

<details>
<summary><strong>Why is there a second implementation in `conformance/`?</strong></summary>
<br>

So the comparison has two sides. The package is written to be read: named
conditions, separate methods, flag rules in their own module. The one in
`conformance/` dispatches through tables instead. Implementations that share a
shape tend to share a mistake, and these two do not share one. Neither of them
decides what the right answer is, either: both are held to states recorded from a
third implementation before either existed.

</details>

<details>
<summary><strong>Will the firmware ever be included?</strong></summary>
<br>

No. Not as files, not as fragments, not encoded, not generated. The manifest
identifies images and reconstructs nothing, and that is the furthest this goes.

</details>

## Contributing

Measurements first. If you have a part, a cartridge, or a machine this has not
been run against, the most useful thing you can send is a run and what it found,
especially a disagreement. [CONTRIBUTING.md](CONTRIBUTING.md) has the gates a
change is expected to pass, [SECURITY.md](SECURITY.md) says what belongs in a
private report, and the [Code of Conduct](CODE_OF_CONDUCT.md) applies wherever
this project is discussed.

Never attach a copyrighted image or a game, and never link to somewhere one can
be downloaded. A digest identifies a file without carrying it.

## Citing this

[CITATION.cff](CITATION.cff) is kept in step with the released version by the
same script that stamps the package, so the version it names is the version that
shipped. GitHub renders it as a Cite this repository button.

## License

[MIT](LICENSE)
