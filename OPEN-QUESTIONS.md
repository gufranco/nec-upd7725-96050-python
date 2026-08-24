# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful to the silicon is still a claim
rather than a measurement. The record that drives this file is
[`conformance/divergences.json`](conformance/divergences.json); this document is
the same content written for a reader rather than for a test.

The settled surface is not small. Every figure the manufacturer printed about the
uPD77C25 is quoted in [`conformance/hardware.json`](conformance/hardware.json)
with the page it appears on, two independent implementations are stepped against
one corpus, and the whole processor state is compared after every instruction
rather than only the answer. What follows is the residue.

## Why a corpus cannot close these

The corpus is a recording, and the thing recorded was an emulator rather than a
part. It is a good source for behaviour nobody documented, because somebody had
to decide what the silicon does and wrote it down in code. It is a poor source
for a figure a manufacturer printed, because it can only repeat whatever its
author believed.

So where the data sheet and the corpus overlap, the data sheet wins and the
recording is retaken. Where they do not overlap, and that covers most of the flag
rules, there is nothing to check the recording against. That is the shape of
almost everything below.

## What would settle almost all of them

A recording taken off a real part: drive known inputs through a known program and
capture the state after each instruction. Two of the four entries below close
immediately with such a recording, and a third closes with a data sheet nobody
has yet found.

## Where the manufacturer wrote nothing

### There is no document for the uPD96050.

**The document says.** Nothing. No manufacturer document for this part was
located.

**What this project does.** It follows secondary sources, which give 16384
program words, 2048 data ROM words, 2048 data RAM words and eight stack levels.
The part carries `verified: false` in the record.

**Why that is weaker than it looks.** Secondary sources for this family are
emulators, which is the weakest evidence this project accepts for a fact a
manufacturer would have printed.

**What holds it up anyway.** Three of the four figures have a second witness that
is not an emulator. An ST010 firmware image is exactly 16384 program words of
three bytes plus 2048 table words of two bytes, so a wrong size would fail to
load. That is the artifact corroborating itself. The stack depth has no such
witness and rests on the secondary source alone.

**What would settle it.** An NEC data sheet for the uPD96050, or a measurement:
push past eight levels on a real part and see where the return address comes
from.

### How long the console takes to reach this part.

**The document says.** Nothing. That is a property of the cartridge board and the
console bus, not of the DSP.

**What this project does.** Nothing here. The figure belongs to
`snes-mapper-python`, where every implementation costs an access to the
coprocessor region at twelve master cycles, and where it is marked unverified for
the same reason: Nintendo's Book I lists two bus speeds and not a third.

**Why it is named here.** Somebody timing a DSP-1 routine uses both packages and
should not pick the mark up from only one of them.

**What would settle it.** A passage in Nintendo's Book I or Book II giving the
access time for that region, or a measurement on real hardware.

### How many cycles a reset costs.

**The document says.** That a reset happens and what it leaves behind, and
nothing about how long it takes. The pin gets one sentence.

**What this project does.** `reset()` spends no cycles.

**Why that is not a claim.** No silicon resets instantaneously. Zero here is the
absence of a figure rather than a figure. Spending a plausible number would put
an invented one into every tally that crosses a reset, and a caller pacing
against a wall would be pacing partly against this package's guess.

**What would settle it.** A timing figure for the reset pin in an NEC document,
or a measurement on a real part: hold the pin low, release it, and count clocks
until the first program fetch.

## Where the source is a recording rather than a part

### Every flag rule the data sheet does not state.

**The document says.** Widths, stack depth, cycles per instruction and memory
sizes. It is Advance Product Information: it does not specify every flag rule,
every undefined encoding, or the result of every field combination.

**What this project does.** It follows the corpus, which answers all of those,
because a recording answers whatever it was asked.

**Why that is weaker than it looks.** The recording is an emulator. Where the two
overlap the document wins and the recording is retaken; where they do not overlap
there is nothing to check the recording against, and that covers most of the flag
rules.

**What would settle it.** A recording taken off a real uPD77C25.

## What is not in question

So the boundary is visible rather than implied:

- Every figure the data sheet prints about the uPD77C25 is quoted with its page,
  and the file is pinned by digest so a later reader checks the same scan.
- Two independent implementations are stepped against one corpus and compared on
  the whole processor state after every instruction.
- A firmware image is held to loading at exactly the sizes the record declares,
  which is the artifact corroborating the record rather than a source repeating
  it.

## What is deliberately not modelled

### The two parts are treated as one instruction set with different sizes.

This is a decision this package makes rather than a fact either source states.
The data sheet says the uPD77C25 and uPD77P25 are functionally identical, one
mask ROM and one UVEPROM. Nothing states that the uPD96050 shares the instruction
set; it is modelled once with the sizes differing per model, and that would be
wrong if the larger part turned out to differ in behaviour rather than only in
capacity.

The missing uPD96050 data sheet would either confirm the instruction set or name
a difference.
