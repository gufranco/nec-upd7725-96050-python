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

`Cpu` is a factory that picks the model, so it cannot name the type it returns.
That type is exported as `Cpu7725`, the class both parts are built from, the way
`mos65xx` exports `Cpu65816`. Annotate with it, and never import
`upd7725.core.Cpu` to get the same thing: tests and conformance tools use the
public interface only.

Three ways to run it, sharing one place where a cycle is spent:

- `step()` runs one instruction and returns the cycles it cost. Every instruction
  here carries a multiply, so the multiply is part of what a step costs rather
  than an instruction of its own.
- `run_for(cycles)` spends a budget of them and overshoots, because an
  instruction cannot be cut in half.
- `Clock(cpu).tick()` advances exactly one cycle and stops, on a thread, because
  Python cannot suspend a call stack. Far slower, and the only way to change what
  a read answers mid-instruction. Only the clock's own thread stops: `irq()`
  called while it is paused acts at once, as between two steps, and its cycle
  counts in `cycles` without being a tick.

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

The serial port and the DMA request live in [`upd7725/pins.py`](upd7725/pins.py)
as `cpu.pins`. Its inputs are levels the host sets between cycles, and `spend()`
samples them once a cycle, so an edge acts at the end of the cycle that sees it.

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

**Not settled: 6 things**, each named in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)
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

## Test cartridges

[`conformance/testroms.json`](conformance/testroms.json) lists seven program
images, five for the smaller part and two for the larger, each keyed by the
SHA-256 of the file on disk and never committed. They live in
`snes-roms/5 Tools & Service Test Carts/CPU/` in the local library. None of
them is a test program and none reports a verdict, and no exchange with an
answer taken from a source outside this member is pinned here, so nothing is
`run`. Every one is `read`:

```bash
python3 -m conformance.testroms "../snes-roms/5 Tools & Service Test Carts/CPU"
python3 -m conformance.testroms --record FOLDER   # only after a census change
```

The runner walks each image with `conformance/stack.py` and compares what it
finds against [`conformance/testroms_measured.json`](conformance/testroms_measured.json):
how many words are reached, how deep calls nest from reset and from the
interrupt vector, and whether that fits the part's stack. With no folder named
it says that nothing was checked and exits 0, and CI runs it that way. The
recorded census is replayed by `conformance/testroms.test.py` on a machine that
holds no image. On 2026-10-19 every image for the smaller part nested at most
three calls deep, inside the four levels NEC prints. One image for the larger
part needs one level; the other jumps through the output register at 13H and
cannot be bounded by a walk.

The files on disk store every word low byte first. Reversing the bytes of each
three-byte program word and each two-byte table word gives the image named by
`canonicalSha256`, which is the digest `snes-dsp-python` and `snes-st-python`
key their manifests on. That is why none of the seven matches those manifests by its own digest, and the runner accepts either layout.

Running a program, with a host writing commands and reading answers, belongs to
`snes-dsp-python` and `snes-st-python`, which drive these images.

## Every gate, in the order to run them

```bash
uvx ruff@0.16.3 format --check .                      # formatting
uvx ruff@0.16.3 check .                               # lint, zero warnings
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1  # types, strict
pnpm run format:check                                  # every JSON file
uvx yamllint==1.38.0 --strict .
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for f in upd7725/*.test.py conformance/*.test.py; do "${cov[@]}" run -a "$f"; done
"${cov[@]}" report                                     # fails below 100%
python3 -m conformance.instructions                    # the gate
python3 -m conformance.differential                    # unbounded, optional locally
python3 -m conformance.stack IMAGE [IMAGE ...]         # images for the larger part, held locally
python3 -m conformance.testroms FOLDER                 # the test images, held locally
```

Coverage is collected by running each test file under `coverage run -a`, not by a
test runner:

```bash
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for f in upd7725/*.test.py conformance/*.test.py; do "${cov[@]}" run -a "$f"; done
"${cov[@]}" report
```

All of it is 100% of statements and branches, and that is enforced rather than
aspired to. A new branch without a test fails the build.

## Conventions that are not negotiable

| Thing                                                         | Rule                                                                                                                                                                                                                                           |
| :------------------------------------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Language                                                      | Python only. Nothing else, anywhere in the project                                                                                                                                                                                             |
| Comments                                                      | None in source, and a docstring counts as one                                                                                                                                                                                                  |
| Test layout                                                   | `<module>.test.py` beside the module it covers                                                                                                                                                                                                 |
| Test structure                                                | Arrange, act, assert, each opened by its bare marker                                                                                                                                                                                           |
| Test data                                                     | Derived from a seed, never hardcoded                                                                                                                                                                                                           |
| Coverage                                                      | 100% statements and branches, enforced                                                                                                                                                                                                         |
| Types                                                         | `mypy` at strict, plus every optional error class the version offers                                                                                                                                                                           |
| Commits                                                       | [Conventional Commits](https://www.conventionalcommits.org/); subject under 50 characters                                                                                                                                                      |
| Releases                                                      | semantic-release from `main`; never tag by hand                                                                                                                                                                                                |
| A program image                                               | Never committed, never vendored, never encoded, never generated                                                                                                                                                                                |
| [`upd7725/core.py`](upd7725/core.py) length                   | Past 500 lines under the exemption for a single calculation engine sharing intermediate state: one `Cpu` whose four instruction forms read and write the same registers, both flag sets, the three stores and the cycle count within each step |
| [`conformance/reference.py`](conformance/reference.py) length | Past 500 lines under the same exemption: one table-driven `Upd96050` whose handlers share its register file and flags, kept whole because it is a transcription whose structure must stay re-derivable                                         |

The linter's ignores in [`pyproject.toml`](pyproject.toml) carry no comments, so
their reasons live here:

- `N818`: some exceptions are control flow signals rather than failures. The
  standard library names those without the suffix too, and the ones that report
  a failure do end in `Error`.
- `N999` in tests: a test file sits beside its module and is named after it with
  a dot, so a module and its tests are read together.
- `T201` in `conformance/`: these are command line tools, and printing is their
  output.
- `BLE001` and `T201` in `environment.py`: a check that throws has to become a
  line in the report rather than end the run, and the report is the product.
- `BLE001` and `T201` in the doctor: it has to survive whatever a check throws
  and report it. A narrower catch would let a traceback take the rest of the
  report with it.

The coverage exclusions carry none either:

- `if __name__ == "__main__":`: the guard hands argv to a function that is
  itself tested, and importing the module to cover it would run the tool.
- `if TYPE_CHECKING:`: the block never runs. Python 3.14 drops it before
  coverage sees it and earlier versions do not, so counting it would make the
  gate mean something different on each runtime.
- `^\s*\.\.\.$` and `: \.\.\.$`: a protocol method's ellipsis is a contract the
  type checker reads and the runtime never runs.
- `@unittest\.skipUnless\(A_PART,`,
  `@unittest\.skipUnless\(A_PART and BUILDABLE,` and
  `^def accounts_for_a_reset\(` in the coverage exclusions: this member is not a
  part, so the family tests that build a `Chip` and account for its reset are
  skipped here and their bodies never run.

The formatter's ignores in [`.prettierignore`](.prettierignore) carry no
comments either, so their reasons live here:

- `pnpm-lock.yaml` and `package-lock.json`: the package manager writes them, in
  its own layout, on every install.
- `node_modules/`, `.venv/`, `venv/`, `build/`, `dist/` and `*.egg-info/`:
  installed or built, never written by hand.
- `.coverage`, `coverage.json`, `htmlcov/` and the tool caches: the output of a
  run, never committed.
- `docs/`, `specs/`, `.work/` and `.claude/`: local working material, never
  committed.

## Layout

```
upd7725/
  core.py         the instruction set: four forms, decode and execute
  flags.py        the six bits each accumulator carries
  registers.py    the register file, at each part's own widths
  memory.py       program, table and scratch, filled rather than cleared
  ports.py        the host side: the handshake and both transfer widths
  pins.py         the serial port and the DMA request, sampled once a cycle
  models.py       the two parts, and what separates them
  doctor.py       what this machine actually has
conformance/
  reference.py        an independent implementation, ported, table-driven
  oracle.py           one case through it, in the shape the recordings are in
  instructions.py     the gate: every form, against the recordings
  differential.py     the two implementations against each other, unbounded
  stack.py            the deepest call a program image can make, walked without running it
  testroms.py         the test images, read by digest and held to their recorded census
  testroms.json       every test image that exercises this member, and its outcome
  testroms_measured.json  what that census found, replayed with no image present
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
runner that does not, and the local run gives no hint. Here the files a default
reaches are the data sheets under `docs/`, which no runner holds.

Every test that could reach a real document supplies its own path or its own
stand-in. A default is for a person at a command line, never for a test.

**Coverage that depends on what the machine holds is not coverage.** A test that
only runs where a data sheet happens to be present is a test that reports a pass
on a machine that ran nothing. Tests that need a file supply their own.

**The two implementations are deliberately shaped differently.** The package
branches through named conditions; [`conformance/reference.py`](conformance/reference.py)
dispatches through tables. Do not refactor one towards the other. Implementations
that share a shape share a mistake, and the whole value of the comparison is that
these two do not.

**The reference is a transcription.** It was ported from a widely used emulator's
core, and its structure, its names and its mixed-case fields come from there. Keep
them. Declaring a field explicitly so the checker can see it is fine; restructuring
the logic makes the port harder to re-derive and weakens the claim that it is
independent.

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
shared() { sed '/^_Everything above this line/q' "$1"; }

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
