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
is not an emulator. A published image for the larger part is exactly 16384 program words of
three bytes plus 2048 table words of two bytes, so a wrong size would fail to
load. That is the artifact corroborating itself. The stack depth has no such
witness and rests on the secondary source alone.

**Where that data sheet is not.** NEC's *DSP and Speech Processor Products*,
1992, 482 pages, is the later edition of the book this project already carries
from 1989. Read on 2026-08-24: it covers the uPD77C20A, 7720A and 77P20, the
uPD77C25 and 77P25, and the uPD77810, and the string 96050 appears on none of
its pages. The only near hit is a uPD9605, which is a PCM codec. A later book
than that one has not been located.

**What would settle it.** An NEC data sheet for the uPD96050, or a measurement:
push past eight levels on a real part and see where the return address comes
from.


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

**What the manufacturer since settled.** The 1989 data book states, for all
sixteen ALU operations, which flags are affected, which are reset, which are
held and which it declines to define. This model agrees with it on every cell,
and `conformance/alu_flags.test.py` drives all sixteen against a run.

**What the recording still carries alone.** The exact value each affected flag
takes, the auxiliary sign the manufacturer calls indefinite, and what a
multi-bit shift brings in at the bottom.

**What would settle the rest.** A recording taken off a real uPD77C25.

### What a two-bit and a four-bit left shift bring in at the bottom.

**The document says.** Table 6 names them a 2-bit left shift and a 4-bit left
shift and says nothing about what arrives in the vacated bits.

**What this project does.** Brings ones in, following the recording, so the
result of either can never be zero.

**Why it is worth naming.** It makes the zero flag unreachable for those two
operations, while the manufacturer's table marks that flag as derived from the
result. Both statements are true at once, and the reason the flag never fires is
a choice taken from an emulator rather than a figure from NEC.

**What would settle it.** A sentence in an NEC document about what a multi-bit
shift shifts in, or a measurement on a real part.

**Where that sentence is not.** The 1989 data book has been read end to end for
it. Inside the µPD77C25/77P25 section every occurrence of the word outside
Table 6 is about the serial port's shift registers, and the table names the two
operations without saying what arrives in the vacated bits.

**Nor is it in the later edition.** The 1992 book carries the same three ALU
tables, for the uPD77C20A family on its page 72, for this part on its page 103,
and for the uPD77810 on its page 221. All three name the two-bit and four-bit
left shifts and none says what arrives at the bottom. Every occurrence of
shifted in across all 482 pages is the serial port, and filled with, are filled,
is filled, fill bit, shifted into, vacated, zero fill, sign extend and bits
become do not occur anywhere in it. Its uPD77C25 chapter also adds nothing on
flag values that the data sheet here does not already print: the sentence about
SA1 holding the corrected sign of an overflow, the saturation constants and the
three successive additions are all in `upd77c25.pdf`.

**A near miss worth naming, so it is not mistaken for an answer later.** The
same book documents the µPD7281 shifting zeros in, in a labelled figure, and
carries a µPD77810 whose flag table has the same six bits under the same names
and marks the same two operations carry-reset. Neither is this part. The 7281 is
a dataflow processor with a different architecture, and a sibling agreeing about
flags is not a sibling agreeing about fill bits. Reading either across would
turn a documented unknown into an undocumented assumption that looks sourced.

## What is not in question

So the boundary is visible rather than implied:

- Every figure the data sheet prints about the uPD77C25 is quoted with its page,
  and the file is pinned by digest so a later reader checks the same scan.
- Two independent implementations are stepped against one corpus and compared on
  the whole processor state after every instruction.
- A published program image for the larger part loads at exactly the sizes the
  record declares, which is an artifact corroborating the record rather than a
  source repeating it.

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
