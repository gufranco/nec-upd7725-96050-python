# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this
family carries, byte for byte, and it decides most questions before they are
asked. What follows is only what is true of this member. [README.md](README.md)
is the document written for a person.

## What this project is, in one paragraph

A model of the NEC uPD7725 and uPD96050 digital signal processors. It is a model
of silicon and not of any program written for one: every instruction is settled
by generating instruction words, so the whole gate runs on a machine holding
nothing anybody licensed. No program image is carried here and none ever will be.

What was built around one of these parts is not this package's business. A module
somebody soldered onto a board, what it was called and what machine it plugged
into all belong to whoever models that board.

## The interface a caller drives

The part is powered and not reset when it is built. `reset()` is the caller's to
call, because no board hands over a processor that has reset itself.

Three ways to run it, sharing one place where a cycle is spent:

- `step()` runs one instruction and returns the cycles it cost. Every instruction
  here carries a multiply, so the multiply is part of what a step costs rather
  than an instruction of its own.
- `run_for(cycles)` spends a budget of them and overshoots, because an
  instruction cannot be cut in half.
- `Clock(cpu).tick()` advances exactly one cycle and stops, on a thread, because
  Python cannot suspend a call stack. Far slower, and the only way to change what
  a read answers mid-instruction.

`irq_line` is a line rather than an event, read where the document says the part
reads it. `on_cycle` is called once per cycle, after that cycle's activity.

Memory is three stores rather than one, because the part is: `cpu.stores` holds
`program`, `table` and `scratch`, at three widths, reached by three different
registers. One attribute called `memory` would not answer which of the three a
caller meant.

What a host can see of all this is two addresses, and that lives in
[`upd7725/ports.py`](upd7725/ports.py) rather than in the core. One is a data
register and the other is a status word, and the only thing a host learns about
the program inside is one bit: whether the part is waiting for it.

Every cycle passes through `spend()` and nowhere else. A counter kept in one
method and a hook called from another drift the first time somebody adds a cycle
to only one of them, and nothing catches it. Keep it that way.

## The authority ladder

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

## What is settled and what is not

**Settled: every encoding.** All 1,120 of them are walked field by field and
compared against an independent implementation, 22,240 instructions with no
disagreements. That is as strong as instruction-level evidence gets here.

**Settled: what the manufacturer printed.** The 1987 data sheet and the 1989 data
book give the widths, the stack depth, the cycle counts, the memory sizes and,
for all sixteen ALU operations, which flags are affected, which are reset, which
are held and which the manufacturer declines to define. Every one of those is
recorded in [`conformance/hardware.json`](conformance/hardware.json) with the
quote it came from, and driven against a run.

**Not settled: 3 things**, each named in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)
with the measurement that would close it. The largest is that one of the two
parts has no manufacturer document at all, so what is asserted about it rests on
secondary sources, and secondary sources for this family are emulators. Do not
close one by argument.

## Adding a part to the family

`upd7725/models.py` holds the two parts and their widths. A new entry needs its
counter, table and pointer widths, an entry in the manifest if an image exists
for it, and a case in `conformance/instructions.py`'s `PARTS` so every recorded
case runs on it too. Adding a part without extending `PARTS` means the corpus
never exercises it.

## Every gate, in the order to run them

```bash
ruff format --check .                                  # formatting
ruff check .                                           # lint, zero warnings
mypy                                                   # types, strict
pnpm run format:check                                  # every JSON file
for f in upd7725/*.test.py conformance/*.test.py; do python3 "$f"; done
python3 -m coverage report                             # fails below 100%
python3 -m conformance.instructions                    # the gate
python3 -m conformance.differential                    # unbounded, optional locally
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
| A program image | Never committed, never vendored, never encoded, never generated |

Docstrings explain why, not what. A docstring restating the function name is
worse than none, because it takes space a reason could have used.

## Layout

```
upd7725/
  core.py         the instruction set: four forms, decode and execute
  flags.py        the six bits each accumulator carries
  registers.py    the register file, at each part's own widths
  memory.py       program, table and scratch, filled rather than cleared
  ports.py        the host side: the handshake and both transfer widths
  models.py       the two parts, and what separates them
  doctor.py       what this machine actually has
conformance/
  reference.py        an independent implementation, ported, table-driven
  oracle.py           one case through it, in the shape the recordings are in
  instructions.py     the gate: every form, against the recordings
  differential.py     the two implementations against each other, unbounded
  corpus.json         22,240 recorded states
  pinned.json         which implementation, at which commit
```

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
done
```

Every test that could reach a real image supplies its own path or its own stand-in.
A default is for a person at a command line, never for a test.

**Coverage that depends on what the machine holds is not coverage.** A test that
## Before calling anything finished

[`FAMILY.md`](FAMILY.md) carries a checklist under "What a new repository has to
have before it is a member". Every line on it was a defect found in one of these
repositories and fixed in all of them, so it is the list of things that have
actually gone wrong here rather than a list of good intentions. Read it before
adding a surface, and read it again before saying a change is done.

A change to `FAMILY.md` is a change to every member. Nothing here can catch it
being made in one of them and forgotten in the others, because a test in this
repository cannot see the others, so the check is a command rather than a suite:

```sh
shared() { sed '/^\*Everything above this line/q' "$1"; }

grep -o 'github\.com/[^/]*/\([a-z0-9-]*\))' FAMILY.md | sed 's|.*/||; s|)||' | sort -u |
while read -r member; do
  other="../$member/FAMILY.md"
  [ -f "$other" ] || { echo "not on this machine: $member"; continue; }
  cmp <(shared FAMILY.md) <(shared "$other") && echo "match: $member"
done
```

The members come from the table at the top of `FAMILY.md` rather than from a
glob over the parent directory. Several repositories beside these carry a copy
of this file because somebody started from one. Those are working notes: they
bind nothing, they are not expected to match, and a sweep that reports them as
drifted invites somebody to edit a file that was never a member.

The marker line at the end of the shared part is what bounds the comparison, so
nothing here carries a line number that has to be maintained alongside the file
it counts. Run this after any edit, and read the output rather than the exit
code: a loop over a pattern that matched nothing prints nothing and succeeds.

Two rules from that file are worth repeating because they are the ones skipped
most often, and skipping them is how the rest of the list got written:

**A check nobody has seen fail is not known to work.** Drive it, once,
deliberately, against input that should fail it. Three checks in this family
reported clean while the thing they guarded was broken, and each was believed
because the run stayed green.

**Silence and success produce the same output.** A check that found no files, no
documents or no records exits zero exactly like one that examined everything.
Print what was examined, and say so when the answer is nothing.

## What a change is expected to leave behind

A gate that would have caught the bug. A fix with no test that fails without it
is not finished, and neither is a feature whose error paths are untested. If a
bug got past 100% coverage and a million compared instructions, the interesting
part of the change is the check that would have caught it, not the fix.
