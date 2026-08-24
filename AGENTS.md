# Working in this repository

This file is for a coding agent. A person reading it will not be harmed, but
[README.md](README.md) is the document written for them.

## What this project is, in one paragraph

A model of the NEC uPD7725 and uPD96050, the processor that a shelf of Super
Nintendo coprocessor cartridges turns out to contain. It is a model of silicon,
not of a program: every instruction is settled by generating instruction words,
so the whole gate runs on a machine holding nothing anybody licensed. Firmware is
never carried here and never will be.

## The authority ladder

Every factual question is answered by the highest rung that has an answer, and a
lower rung never overrules a higher one.

1. **`conformance/hardware.json`**, which is NEC's own datasheet pinned fact by
   fact with the sentence each figure came from. It decides anything the
   manufacturer printed: widths, memory sizes, stack depth, clocks per
   instruction, what reset does.
2. **`conformance/corpus.json`**, 22,240 recorded states, which decides
   instruction-level behaviour the document does not specify: exact flag rules,
   undefined encodings, the result of every field combination.
3. **Nothing else.** An emulator, an FPGA core and a wiki are rung 2 at best and
   rung 3 for a printed fact. This matters here more than it sounds: every
   implementation of this family in the field gives the part a sixteen-level
   stack, and NEC prints four. The corpus encoded sixteen until the datasheet was
   read.

When the document and the corpus disagree, the document wins and the corpus is
retaken. Record it in `pinned.json` under `retaken`, saying which fact and why.

Never edit `corpus.json` by hand, and never edit it to make a test pass.
`--record` alone now refuses to overwrite it, because recording from the thing the
corpus is meant to check produces evidence worth nothing. `--record --retake` is
the deliberate act, and it is only for carrying a corrected hardware fact.

## Every gate, in the order to run them

```bash
ruff format --check .                                  # formatting
ruff check .                                           # lint, zero warnings
mypy                                                   # types, strict
pnpm run format:check                                  # every JSON file
for f in upd7725/*.test.py conformance/*.test.py; do python3 "$f"; done
python3 -m coverage report                             # fails below 100%
python3 conformance/instructions.py                    # the gate
python3 conformance/differential.py                    # unbounded, optional locally
```

Coverage is collected by running each test file under `coverage run -a`, not by a
test runner:

```bash
python3 -m coverage erase
for f in upd7725/*.test.py conformance/*.test.py; do python3 -m coverage run -a "$f"; done
python3 -m coverage report
```

All of it is 100% of statements and branches, and that is enforced rather than
aspired to. A new branch without a test fails the build.

## Things that will bite you

**A figure taken from a document is read twice.** Almost every document behind
these projects is a photograph of a printed book. Its text layer, where it has
one, was produced by somebody else's recogniser and prints `lhe` for `the`; the
page read as an image now is cleaner but drops a lone digit and misses a faint
line outright. Read it both ways and record what both agree on. `FAMILY.md`, under
"Reading a document that is a photograph", carries the traps and what the record
has to hold. Skipping this is how a timing table came to name forty three of its
rows after the text sitting next to them.

**Run the suite on the oldest Python supported, not only the newest.** Annotations
are evaluated eagerly before 3.14 and lazily from 3.14 on. A file that names a
type imported only under `TYPE_CHECKING` will import fine on 3.14 and raise
`NameError` on 3.12, and every test will pass locally while the package is broken
for most users. Every file that does this carries
`from __future__ import annotations`. If you add such a file, add the import.

```bash
uvx --python 3.12 python upd7725/core.test.py
```

**A type alias is a runtime value, and the future import does not defer it.**
`Answered = Callable[[int, int, int], str]` at module scope needs `Callable`
imported for real, not under `TYPE_CHECKING`.

**Nothing starts clear.** Registers, flags, the stack, program store, table and
scratch all begin holding what the seed says they hold. A model that starts at
zero passes tests and fails on hardware, because hardware does not start at zero.
Never add a test that assumes a cleared state, and never "fix" a failure by
clearing one.

**Run the suite as a machine that holds nothing.** A test that reaches a default
which opens a real file passes on a workstation holding that file and fails on a
runner that does not, and the local run gives no hint. Point the firmware
directory somewhere empty and run everything before pushing:

```bash
EMPTY=$(mktemp -d)
for f in upd7725/*.test.py conformance/*.test.py; do
  UPD7725_FIRMWARE_DIR="$EMPTY" python3 "$f" || echo "FAILED $f"
done
```

Every test that could reach a real image supplies its own path or its own stand-in.
A default is for a person at a command line, never for a test.

**Coverage that depends on what the machine holds is not coverage.** A test that
only runs where a firmware image happens to be present is a test that reports a
pass on a machine that ran nothing. Tests that need a file supply their own.

**The two implementations are deliberately shaped differently.** The package
branches through named conditions; `conformance/reference.py` dispatches through
tables. Do not refactor one towards the other. Implementations that share a shape
share a mistake, and the whole value of the comparison is that these two do not.

**`conformance/reference.py` is a transcription.** It was ported from a widely
used emulator's core, and its structure, its names and its mixed-case fields come
from there. Keep them. Declaring a field explicitly so the checker can see it is
fine; restructuring the logic makes the port harder to re-derive and weakens the
claim that it is independent.

## Conventions that are not negotiable

| Thing | Rule |
|:------|:-----|
| Language | Python only. Nothing else, anywhere in the project |
| Comments | None in source, ever. Docstrings carry the reasoning |
| Test layout | `<module>.test.py` beside the module it covers |
| Test structure | Arrange, blank line, one act, blank line, assert. No section labels |
| Test data | Derived from a seed, never hardcoded |
| Coverage | 100% statements and branches, enforced |
| Types | `mypy` at strict, plus every optional error class the version offers |
| Commits | [Conventional Commits](https://www.conventionalcommits.org/); subject under 50 characters |
| Releases | semantic-release from `main`; never tag by hand |
| Firmware | Never committed, never vendored, never encoded, never generated |

Docstrings explain why, not what. A docstring restating the function name is
worse than none, because it takes space a reason could have used.

## Layout

```
upd7725/
  core.py         the instruction set: four forms, decode and execute
  flags.py        the six bits each accumulator carries
  registers.py    the register file, at each part's own widths
  memory.py       program, table and scratch, filled rather than cleared
  ports.py        the console side: the handshake and both transfer widths
  firmware.py     identifying an image somebody else supplied
  models.py       the two parts, and which cartridge chip ran on each
  doctor.py       what this machine actually has
conformance/
  reference.py        an independent implementation, ported, table-driven
  oracle.py           one case through it, in the shape the recordings are in
  instructions.py     the gate: every form, against the recordings
  differential.py     the two implementations against each other, unbounded
  against_firmware.py the opt-in runner that needs an image you already own
  corpus.json         22,240 recorded states
  pinned.json         which implementation, at which commit
firmware/         where a user's own copies go; nothing here is ever committed
```

## Adding a part to the family

`upd7725/models.py` holds the two parts and their widths. A new entry needs its
counter, table and pointer widths, an entry in the manifest if an image exists
for it, and a case in `conformance/instructions.py`'s `PARTS` so every recorded
case runs on it too. Adding a part without extending `PARTS` means the corpus
never exercises it.

## What a change is expected to leave behind

A gate that would have caught the bug. A fix with no test that fails without it
is not finished, and neither is a feature whose error paths are untested. If a
bug got past 100% coverage and a million compared instructions, the interesting
part of the change is the check that would have caught it, not the fix.
